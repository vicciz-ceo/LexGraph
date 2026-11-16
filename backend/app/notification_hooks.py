"""Notification triggers (spec §15; sprint 2026-07-25 ruling R9: an
owned mechanism instead of call-sites in other tracks' routers).

ASGI middleware over the assertion mutation routes. Every request passes
through unchanged. For a recognized route it records the assertion's state
just before the request (status, current revision, successor) and, after a
successful response, re-reads the committed row -- the database is the
authority -- and raises the notices that the actual state change calls for
via `app.notifications`:

    POST  /api/v1/assertions                (created as proposed)   assertion_submitted
    POST  /api/v1/agent/assertions          (created as proposed)   assertion_submitted
    POST  /api/v1/assertions/{id}/submit    (entered proposed)      assertion_submitted
    POST  /api/v1/assertions/{id}/accept|reject|dispute|request-revision|supersede
                                            (status changed)        decision notice to the author
    PATCH /api/v1/assertions/{id}, POST .../revisions
                                            (new revision number)   revision_created
    POST  /api/v1/assertions/{id}/evidence  (201)                   evidence_added
    POST  /api/v1/assertions/{id}/comments  (201)                   comment_added
    PUT   /api/v1/assertions/{id}/revisions/{n}/rating
                                            (200/201)               assertion_rated (opt-in only)

Because notices follow the state change rather than the route, saving a
draft notifies nobody, re-submitting an assertion that is already proposed
does not notify the reviewers a second time (finding api:12), a repeated
decision that changes nothing is silent, and an edit that creates no
revision is silent. Creation as proposed -- the Suggest form's "Submit for
review" and the agent endpoint -- notifies exactly like draft + submit
(findings ui:6, pipeline:4). For a submit, the status it moved the assertion
from is read from the request's own `assertion_submitted` audit row, since
the snapshot can be stale when two submits race (review workflow:3).

Notices are written in their own transaction right after the mutation has
committed. A failure is logged and never changes the response the client
gets. Agent proposals made through the CLI or the MCP server do not pass
through HTTP; they raise the same notice by calling
`app.notifications.notify_submission` on their own session (idempotent per
submission, so it never duplicates a notice this hook already wrote).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from fastapi import FastAPI
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app import notifications
from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_rating import AssertionRating
from app.models.audit_event import AuditEvent
from app.services.audit import request_correlation_id

logger = logging.getLogger("app.notification_hooks")

_ID = r"(?P<assertion_id>[^/]+)"
_ROUTES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("POST", re.compile(r"^/api/v1/(?:agent/)?assertions/?$"), "create"),
    ("POST", re.compile(rf"^/api/v1/assertions/{_ID}/submit/?$"), "submit"),
    (
        "POST",
        re.compile(
            rf"^/api/v1/assertions/{_ID}/(?P<action>accept|reject|dispute|request-revision|supersede)/?$"
        ),
        "decision",
    ),
    ("PATCH", re.compile(rf"^/api/v1/assertions/{_ID}/?$"), "revise"),
    ("POST", re.compile(rf"^/api/v1/assertions/{_ID}/revisions/?$"), "revise"),
    ("POST", re.compile(rf"^/api/v1/assertions/{_ID}/evidence/?$"), "evidence"),
    ("POST", re.compile(rf"^/api/v1/assertions/{_ID}/comments/?$"), "comment"),
    (
        "PUT",
        re.compile(rf"^/api/v1/assertions/{_ID}/revisions/(?P<revision_number>\d+)/rating/?$"),
        "rating",
    ),
)
# Kinds whose notice depends on what the request changed.
_NEEDS_SNAPSHOT = frozenset({"submit", "decision", "revise"})
# Kinds that identify the created row by the response body's `id`.
_READS_BODY = frozenset({"create", "evidence", "comment", "rating"})
# Success statuses that mean "the row in the response body was written".
_CREATED_STATUSES = {"create": {201}, "evidence": {201}, "comment": {201}, "rating": {200, 201}}

_DECISION_STATUS = {
    "accept": "accepted",
    "reject": "rejected",
    "dispute": "disputed",
    "request-revision": "revision_requested",
    "supersede": "superseded",
}


@dataclass(frozen=True)
class _Hook:
    kind: str
    assertion_id: str | None = None
    action: str | None = None
    revision_number: int | None = None


@dataclass(frozen=True)
class _Snapshot:
    status: str
    revision_number: int
    superseded_by: str | None


def _match(method: str, path: str) -> _Hook | None:
    for route_method, pattern, kind in _ROUTES:
        if method != route_method:
            continue
        found = pattern.match(path)
        if found:
            groups = found.groupdict()
            revision = groups.get("revision_number")
            return _Hook(
                kind=kind,
                assertion_id=groups.get("assertion_id"),
                action=groups.get("action"),
                revision_number=int(revision) if revision is not None else None,
            )
    return None


def _actor_user_id(request: Request) -> str | None:
    """The authenticated caller, resolved exactly as the routers resolve it."""
    try:
        return get_bearer_user_id(request.headers.get("authorization"))
    except AuthHeaderError:
        return None


def _snapshot(session_factory, assertion_id: str) -> _Snapshot | None:
    # Closed before the request runs: an open read on SQLite would hold up
    # the handler's commit.
    with session_factory() as session:
        row = session.execute(
            select(
                Assertion.status,
                Assertion.current_revision_number,
                Assertion.superseded_by_assertion_id,
            ).where(Assertion.id == assertion_id)
        ).first()
    return _Snapshot(*row) if row is not None else None


async def _read_json_body(response: Response):
    """Drain the response body, put an identical replay back, parse it."""
    body = b""
    async for chunk in response.body_iterator:
        body += chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")

    async def _replay():
        yield body

    response.body_iterator = _replay()
    try:
        return json.loads(body)
    except ValueError:
        return None


def _submitted_from(session, assertion_id: str) -> str | None:
    """The status this request's own submit replaced, from the audit row it
    wrote (review workflow:3), or None when there is none to read.

    The snapshot is read before the request runs, so a submit racing another
    one could still see 'draft' after the other had moved the assertion into
    review; its own audit row then says proposed -> proposed."""
    correlation_id = request_correlation_id()
    if correlation_id is None:
        return None
    return session.scalar(
        select(AuditEvent.previous_value).where(
            AuditEvent.assertion_id == assertion_id,
            AuditEvent.event_type == "assertion_submitted",
            AuditEvent.correlation_id == correlation_id,
        ).limit(1)
    )


def _created_row(session, model, body, assertion_id: str):
    row_id = body.get("id") if isinstance(body, dict) else None
    if not isinstance(row_id, str):
        return None
    row = session.get(model, row_id)
    if row is None or row.assertion_id != assertion_id:
        return None
    return row


def _raise_notices(session, hook: _Hook, actor: str, before: _Snapshot | None, body) -> list:
    if hook.kind == "create":
        assertion_id = body.get("id") if isinstance(body, dict) else None
        assertion = session.get(Assertion, assertion_id) if isinstance(assertion_id, str) else None
        if assertion is None or assertion.status != "proposed":
            return []  # saved as a draft: nothing was submitted for review
        return notifications.notify_assertion_submitted(session, assertion, actor)

    assertion = session.get(Assertion, hook.assertion_id)
    if assertion is None:
        return []
    previous_status = before.status if before is not None else None

    if hook.kind == "submit":
        previous_status = _submitted_from(session, assertion.id) or previous_status
        if assertion.status != "proposed" or previous_status == "proposed":
            return []
        return notifications.notify_assertion_submitted(
            session, assertion, actor, previous_status=previous_status
        )

    if hook.kind == "decision":
        if assertion.status != _DECISION_STATUS[hook.action]:
            return []
        if before is not None and (before.status, before.superseded_by) == (
            assertion.status,
            assertion.superseded_by_assertion_id,
        ):
            return []  # nothing changed, so there is nothing new to tell the author
        return notifications.notify_review_decision(
            session, assertion, actor, previous_status=previous_status
        )

    if hook.kind == "revise":
        if before is None or assertion.current_revision_number <= before.revision_number:
            return []  # e.g. a PATCH with no changes creates no revision
        return notifications.notify_revision_created(
            session,
            assertion,
            actor,
            previous_revision_number=before.revision_number,
            previous_status=previous_status,
        )

    if hook.kind == "evidence":
        evidence = _created_row(session, AssertionEvidence, body, assertion.id)
        return [] if evidence is None else notifications.notify_evidence_added(
            session, assertion, evidence, actor
        )

    if hook.kind == "comment":
        comment = _created_row(session, AssertionComment, body, assertion.id)
        if comment is None or comment.deleted_at is not None:
            return []
        return notifications.notify_comment_added(session, assertion, comment, actor)

    if hook.kind == "rating":
        rating = _created_row(session, AssertionRating, body, assertion.id)
        return [] if rating is None else notifications.notify_assertion_rated(
            session, assertion, rating, actor, revision_number=hook.revision_number
        )
    return []


def _emit(session_factory, hook: _Hook, actor: str, before: _Snapshot | None, body) -> None:
    session = session_factory()
    try:
        if _raise_notices(session, hook, actor, before, body):
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class NotificationHookMiddleware(BaseHTTPMiddleware):
    """Raises in-app notifications after recognized assertion mutations.

    Never blocks or alters the underlying response: an error while deriving
    or storing a notification is logged, so a notification bug can never
    turn a real 2xx into a 500.
    """

    async def dispatch(self, request: Request, call_next):
        hook = _match(request.method, request.url.path)
        if hook is None:
            return await call_next(request)

        session_factory = request.app.state.session_factory
        before = None
        if hook.kind in _NEEDS_SNAPSHOT:
            try:
                before = await run_in_threadpool(_snapshot, session_factory, hook.assertion_id)
            except Exception:
                logger.exception("notification hook: could not read %s before the request", hook.assertion_id)

        response = await call_next(request)

        if not 200 <= response.status_code < 300:
            return response
        if hook.kind in _CREATED_STATUSES and response.status_code not in _CREATED_STATUSES[hook.kind]:
            return response
        try:
            actor = _actor_user_id(request)
            if actor is None:
                return response
            body = await _read_json_body(response) if hook.kind in _READS_BODY else None
            await run_in_threadpool(_emit, session_factory, hook, actor, before, body)
        except Exception:
            logger.exception(
                "notification hook failed for %s %s", request.method, request.url.path
            )
        return response


def register_notification_hooks(app: FastAPI) -> None:
    """Wire the notification middleware into `app` (called from create_app())."""
    app.add_middleware(NotificationHookMiddleware)
