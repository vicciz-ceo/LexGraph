"""In-app notification abstraction (sprint 2026-07-25-collaborative-
assertions, item B6).

Spec §15 / Manager ruling R4: in-app notifications only for this sprint
(no email/push). Storage is a plain in-process list handed in by the
caller (see `app.state.notification_store`, initialized once per app
instance in `app.main.create_app()`) rather than a new ORM model — R8
freezes `app/models/**` for all B-tracks, so persistence here rides on
the same "rebuildable projection, not authoritative store" pattern as
`app.graph_projection`; nothing here is a system of record.

Spec §15 explicitly says: do not send a notification for every individual
rating by default. That rule is enforced by omission — the only mutation
hook wired up for this sprint (`app.notification_hooks`) never emits an
`assertion_rated` notification. `assertion_rated` stays in
`NOTIFIABLE_EVENTS` as a valid, allow-listed event type (e.g. for a future
digest), it is just never triggered per-rating here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

NOTIFIABLE_EVENTS = frozenset(
    {
        "assertion_submitted",
        "revision_requested",
        "assertion_accepted",
        "assertion_rejected",
        "assertion_disputed",
        "revision_created",
        "evidence_added",
        "comment_added",
        "assertion_rated",
    }
)


def create_notification(
    store: list[dict[str, Any]],
    *,
    event_type: str,
    actor_user_id: str,
    recipient_user_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Append one in-app notification for `recipient_user_id` to `store`.

    `store` is the app-instance-scoped list at `app.state.notification_store`
    — passed explicitly (rather than held as module global state) so each
    FastAPI app instance (one per test, one in production) gets an
    isolated notification feed.
    """
    if event_type not in NOTIFIABLE_EVENTS:
        raise ValueError(f"unknown notification event_type: {event_type!r}")

    notification = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "actor_user_id": actor_user_id,
        "recipient_user_id": recipient_user_id,
        "payload": payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False,
    }
    store.append(notification)
    return notification


def list_notifications(store: list[dict[str, Any]], user_id: str) -> list[dict[str, Any]]:
    """Return `user_id`'s notifications from `store`, newest first.

    Scoped purely by recipient — a user who is not on a matter at all
    simply has zero notifications for it (see
    `tests/integration/test_notifications.py::test_notifications_are_matter_scoped`),
    there is no separate matter-membership gate on this read.
    """
    mine = [n for n in store if n["recipient_user_id"] == user_id]
    return list(reversed(mine))
