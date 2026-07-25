"""Cross-track notification trigger hook (sprint 2026-07-25-collaborative-
assertions, item B6 — ruling R9).

R9: the mutations that must raise notifications live in OTHER tracks'
routers — `POST /api/v1/assertions/{id}/submit` (B1),
`POST /api/v1/assertions/{id}/{accept,reject,dispute,request-revision}`
(B4) — none of which exist in this worktree, and B6 must never edit
another track's router file. The mandated workaround: a mechanism B6
fully owns, registered via a single append-only line in
`app.main.create_app()`.

This module is that mechanism: ASGI middleware that lets every request
pass through unchanged, then — only for a successful (2xx) response whose
path matches a recognized assertion-workflow action — re-derives the
affected assertion's matter/author from the database (the DB row is the
authority; the mutation has already committed by the time middleware
inspects the response) and emits the matching in-app notification(s) via
`app.notifications.create_notification`.

Deliberately NOT wired here: `PUT .../revisions/{n}/rating` (B2). Spec
§15 says not to notify on every individual rating by default — see
`tests/integration/test_notifications.py::
test_every_individual_rating_does_not_generate_a_notification_by_default`.
Omitting a rating trigger is how that rule is enforced from this side.
"""

from __future__ import annotations

import re

from fastapi import FastAPI
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.auth import AuthHeaderError, get_bearer_user_id
from app.notifications import create_notification

_ASSERTION_ACTION_RE = re.compile(
    r"^/api/v1/assertions/(?P<assertion_id>[^/]+)/(?P<action>submit|accept|reject|dispute|request-revision)$"
)

# action -> event_type, for actions that notify every reviewer/admin on the matter.
_NOTIFIES_REVIEWERS = {"submit": "assertion_submitted"}

# action -> event_type, for review decisions that notify the assertion's author.
_NOTIFIES_AUTHOR = {
    "accept": "assertion_accepted",
    "reject": "assertion_rejected",
    "dispute": "assertion_disputed",
    "request-revision": "revision_requested",
}


class NotificationHookMiddleware(BaseHTTPMiddleware):
    """Fires in-app notifications off of recognized assertion-workflow routes.

    Never blocks or alters the underlying response: any error while
    deriving/emitting a notification is swallowed so a notification bug
    can never turn a real 200 into a 500.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        try:
            self._maybe_notify(request, response)
        except Exception:
            pass
        return response

    def _maybe_notify(self, request: Request, response: Response) -> None:
        if response.status_code >= 300:
            return
        if request.method != "POST":
            return
        match = _ASSERTION_ACTION_RE.match(request.url.path)
        if not match:
            return

        action = match.group("action")
        assertion_id = match.group("assertion_id")

        try:
            actor_user_id = get_bearer_user_id(request.headers.get("authorization"))
        except AuthHeaderError:
            return

        session_factory = request.app.state.session_factory
        store = request.app.state.notification_store
        session = session_factory()
        try:
            row = session.execute(
                text("SELECT matter_id, author_user_id FROM assertions WHERE id = :id"),
                {"id": assertion_id},
            ).first()
            if row is None:
                return
            matter_id, author_user_id = row

            if action in _NOTIFIES_REVIEWERS:
                event_type = _NOTIFIES_REVIEWERS[action]
                reviewer_rows = session.execute(
                    text(
                        "SELECT user_id FROM matter_roles WHERE matter_id = :matter_id "
                        "AND role IN ('reviewer', 'admin')"
                    ),
                    {"matter_id": matter_id},
                ).all()
                for (reviewer_id,) in reviewer_rows:
                    create_notification(
                        store,
                        event_type=event_type,
                        actor_user_id=actor_user_id,
                        recipient_user_id=reviewer_id,
                        payload={"assertion_id": assertion_id, "matter_id": matter_id},
                    )
            elif action in _NOTIFIES_AUTHOR:
                event_type = _NOTIFIES_AUTHOR[action]
                if author_user_id:
                    create_notification(
                        store,
                        event_type=event_type,
                        actor_user_id=actor_user_id,
                        recipient_user_id=author_user_id,
                        payload={"assertion_id": assertion_id, "matter_id": matter_id},
                    )
        finally:
            session.close()


def register_notification_hooks(app: FastAPI) -> None:
    """Wire the notification middleware into `app` (called from create_app())."""
    app.add_middleware(NotificationHookMiddleware)
