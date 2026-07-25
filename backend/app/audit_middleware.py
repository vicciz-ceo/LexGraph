"""Cross-track audit-event hook (item B3, ruling R9).

Some mutations that must produce `audit_events` rows live in OTHER
tracks' already-merged router files -- e.g. `POST /api/v1/assertions`
(B1) must produce an `assertion_created` row
(`tests/integration/test_comments_audit.py::
test_assertion_created_produces_audit_event`), but B3 must never edit
B1's router file to add the call-site (ruling R9). The mandated
workaround, mirroring B6's `app.notification_hooks` pattern: ASGI
middleware fully owned by this track, registered via one append-only
line in `app.main.create_app()`.

Deliberately NOT matched here: B4's review-decision routes (`accept`/
`reject`/`dispute`/`request-revision`/`supersede`). Those already write
their own `audit_events` rows directly (see
`app/routers/review.py::_record_decision`) -- matching them here too
would double-write audit rows for the same decision.

B2's rating route (`PUT /api/v1/assertions/{id}/revisions/{n}/rating`)
does not exist in this worktree yet (Wave 2). It is matched here anyway
so that once it merges, `rating_created`/`rating_changed` audit rows
appear automatically with zero further changes to this file -- the
intended payoff of an owned mechanism over a cross-track call-site (R9).
If B2 instead calls `app.services.audit.record_audit_event` directly from
its own router, that is equally correct; this middleware is a no-op for
any path/status it does not recognize.
"""

from __future__ import annotations

import json
import re

from fastapi import FastAPI
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.auth import AuthHeaderError, get_bearer_user_id
from app.services.audit import record_audit_event

_CREATE_ASSERTION_RE = re.compile(r"^/api/v1/assertions/?$")
_RATING_RE = re.compile(
    r"^/api/v1/assertions/(?P<assertion_id>[^/]+)/revisions/(?P<revision_number>\d+)/rating$"
)


class AuditHookMiddleware(BaseHTTPMiddleware):
    """Fires audit-event writes off of recognized cross-track mutation
    routes. Never blocks or alters the underlying response: any error
    while deriving/emitting an audit row is swallowed so an audit bug can
    never turn a real 2xx into a 500 (same contract as
    `app.notification_hooks.NotificationHookMiddleware`).
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        try:
            await self._maybe_record(request, response)
        except Exception:
            pass
        return response

    async def _maybe_record(self, request: Request, response: Response) -> None:
        if response.status_code >= 300:
            return

        if request.method == "POST" and _CREATE_ASSERTION_RE.match(request.url.path):
            await self._record_assertion_created(request, response)
            return

        rating_match = _RATING_RE.match(request.url.path)
        if request.method == "PUT" and rating_match:
            await self._record_rating_mutation(request, response, rating_match)

    async def _read_json_body(self, response: Response) -> dict | None:
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        async def _replay():
            yield body

        response.body_iterator = _replay()
        try:
            return json.loads(body)
        except ValueError:
            return None

    def _actor(self, request: Request) -> str | None:
        try:
            return get_bearer_user_id(request.headers.get("authorization"))
        except AuthHeaderError:
            return None

    async def _record_assertion_created(self, request: Request, response: Response) -> None:
        if response.status_code != 201:
            return
        actor_user_id = self._actor(request)
        if not actor_user_id:
            return
        data = await self._read_json_body(response)
        if not data:
            return

        session = request.app.state.session_factory()
        try:
            record_audit_event(
                session,
                actor_user_id=actor_user_id,
                event_type="assertion_created",
                repository_id=data["repository_id"],
                matter_id=data["matter_id"],
                assertion_id=data["id"],
                previous_value=None,
                new_value=data.get("status"),
            )
            session.commit()
        finally:
            session.close()

    async def _record_rating_mutation(self, request: Request, response: Response, match) -> None:
        actor_user_id = self._actor(request)
        if not actor_user_id:
            return
        data = await self._read_json_body(response)
        if not data:
            return

        assertion_id = match.group("assertion_id")
        event_type = "rating_created" if response.status_code == 201 else "rating_changed"

        session = request.app.state.session_factory()
        try:
            row = session.execute(
                text("SELECT matter_id, repository_id FROM assertions WHERE id = :id"),
                {"id": assertion_id},
            ).first()
            if row is None:
                return
            matter_id, repository_id = row
            strength = data.get("strength")
            record_audit_event(
                session,
                actor_user_id=actor_user_id,
                event_type=event_type,
                repository_id=repository_id,
                matter_id=matter_id,
                assertion_id=assertion_id,
                previous_value=None,
                new_value=str(strength) if strength is not None else None,
            )
            session.commit()
        finally:
            session.close()


def register_audit_hooks(app: FastAPI) -> None:
    """Wire the audit middleware into `app` (called from create_app())."""
    app.add_middleware(AuditHookMiddleware)
