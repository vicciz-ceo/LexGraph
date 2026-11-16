"""Notifications API (spec §15 / ruling R4: in-app only).

    GET  /api/v1/notifications                     the caller's feed, newest first
    GET  /api/v1/notifications/unread-count        {"unread_count": n}
    POST /api/v1/notifications/{notification_id}/read
    POST /api/v1/notifications/read-all            optional {"last_read_at": ISO-8601}
    GET  /api/v1/notifications/preferences
    PUT  /api/v1/notifications/preferences         {"preferences": {event_type: bool}}

Every route acts on the caller's own notifications only (scoped purely by
recipient via the auth seam); there is no matter gate on the feed itself,
so a user with no notifications -- including an outsider with no role on
any matter -- simply gets an empty list (see
`tests/integration/test_notifications.py::test_notifications_are_matter_scoped`).
Another user's notification id answers 404, exactly like an unknown one.

`GET /notifications` pages with `limit` (1-200, default 50) and `offset`,
and `unread_only=true` filters to unread notices. Each item carries the
assertion id, a `link` to it in the web app and a `context` block (current
proposition excerpt, assertion status and origin, matter name, actor name)
while the caller is still a member of the matter; see `app.notifications`.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import notifications
from app.auth import AuthHeaderError, get_bearer_user_id

router = APIRouter(prefix="/api/v1", tags=["notifications"])


def get_session(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_current_user_id(request: Request) -> str:
    try:
        return get_bearer_user_id(request.headers.get("Authorization"))
    except AuthHeaderError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


class ReadAllBody(BaseModel):
    # Notifications created after this instant stay unread (the client sends
    # the newest one it has shown). Omitted: everything unread is marked.
    last_read_at: datetime | None = None


class PreferencesBody(BaseModel):
    preferences: dict[str, bool]


@router.get("/notifications")
def get_notifications(
    limit: int = Query(default=notifications.DEFAULT_PAGE_SIZE, ge=1, le=notifications.MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = False,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    return notifications.list_notifications(
        session, user_id, limit=limit, offset=offset, unread_only=unread_only
    )


@router.get("/notifications/unread-count")
def get_unread_count(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, int]:
    return {"unread_count": notifications.count_unread(session, user_id)}


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    body: ReadAllBody | None = None,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, int]:
    marked = notifications.mark_all_read(
        session, user_id, last_read_at=body.last_read_at if body is not None else None
    )
    return {"marked_read": marked, "unread_count": notifications.count_unread(session, user_id)}


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    item = notifications.mark_read(session, user_id, notification_id)
    if item is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return item


@router.get("/notifications/preferences")
def get_notification_preferences(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    return notifications.get_preferences(session, user_id)


@router.put("/notifications/preferences")
def put_notification_preferences(
    body: PreferencesBody,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    try:
        result = notifications.set_preferences(session, user_id, body.preferences)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session.commit()
    return result
