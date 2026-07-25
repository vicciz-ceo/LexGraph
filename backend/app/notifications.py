"""In-app notification abstraction (shape only).

Spec §15 / Manager ruling R4: in-app notifications only for this sprint
(no email/push). Signatures only — a Developer track (B6) implements the
bodies, including the "do not notify on every rating by default" digest
rule.
"""

from __future__ import annotations

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
    *, event_type: str, actor_user_id: str, recipient_user_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    raise NotImplementedError("developer: implement notification creation (B6)")


def list_notifications(user_id: str) -> list[dict[str, Any]]:
    raise NotImplementedError("developer: implement notification listing (B6)")
