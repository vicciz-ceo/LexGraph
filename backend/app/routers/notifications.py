"""Notifications read surface (sprint 2026-07-25-collaborative-assertions,
item B6). Spec §15 / ruling R4: in-app only.

`GET /api/v1/notifications` — returns the caller's own notifications
(scoped purely by recipient via the auth seam), newest first. Not gated
by matter access: a user with no notifications for a matter — including
an outsider with no role on it at all — simply gets an empty list (see
`tests/integration/test_notifications.py::test_notifications_are_matter_scoped`).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.auth import AuthHeaderError, get_bearer_user_id
from app.notifications import list_notifications

router = APIRouter(prefix="/api/v1", tags=["notifications"])


@router.get("/notifications")
def get_notifications(
    request: Request, authorization: str | None = Header(default=None)
) -> list[dict[str, Any]]:
    try:
        user_id = get_bearer_user_id(authorization)
    except AuthHeaderError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    store = request.app.state.notification_store
    return list_notifications(store, user_id)
