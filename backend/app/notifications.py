"""In-app notifications: durable store, recipients, read state and
preferences (spec §15; ruling R4: in-app only, no email/push).

Notifications are rows in the `notifications` table
(`app.models.notification`), one per recipient. Earlier they were a Python
list on each app instance, so a restart emptied every feed, each API worker
answered with its own feed, the agent CLI/MCP server could not reach it and
nothing could ever be marked read (findings pipeline:9, ui:7).

Who is notified (spec §15 events; the actor is never notified of their own
action, and only current members of the assertion's matter are):

- `assertion_submitted` -- the matter's reviewers and admins, whenever an
  assertion enters `proposed`: created as proposed (the Suggest form's
  "Submit for review", the agent endpoint) or submitted from draft or
  revision_requested. At most one notice per recipient per submission.
- `revision_requested`, `assertion_accepted`, `assertion_rejected`,
  `assertion_disputed`, `assertion_superseded` -- the assertion's author.
- `revision_created`, `evidence_added` -- the assertion's participants
  (author, editors, evidence contributors, commenters, raters and the last
  reviewer) and, while the assertion is `proposed` (awaiting review), the
  matter's reviewers and admins, because the text or evidence under review
  changed.
- `comment_added` -- the participants, including the author of the
  comment being replied to.
- `assertion_rated` -- the author, only if they opted in: spec §15 says not
  to notify on every rating by default.

Each user can switch any event type on or off (`notification_preferences`);
`DEFAULT_PREFERENCES` applies where they have not chosen.

The trigger hooks live in `app.notification_hooks` (ASGI middleware over
the mutation routes). The `notify_*` functions here take a plain SQLAlchemy
session, so code that changes assertions outside an HTTP request can raise
the same notices into the same table: the agent CLI and MCP server propose
without HTTP, so each calls `notify_submission(session, assertion_id, actor)`
once a proposal is stored.

A notification stores references and event facts only (`payload`); the
readable context (current proposition, matter name, actor name) and the
link are added when a feed is read, and only while the recipient is still
a member of the matter, so revoking access also hides old notices' content.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_rating import AssertionRating
from app.models.assertion_revision import AssertionRevision
from app.models.matter import Matter
from app.models.matter_role import MatterRole
from app.models.notification import Notification, NotificationPreference
from app.models.user import User

logger = logging.getLogger("app.notifications")

# Spec §15 order; also the order preferences are listed in.
EVENT_TYPES = (
    "assertion_submitted",
    "revision_requested",
    "assertion_accepted",
    "assertion_rejected",
    "assertion_disputed",
    "assertion_superseded",
    "revision_created",
    "evidence_added",
    "comment_added",
    "assertion_rated",
)
NOTIFIABLE_EVENTS = frozenset(EVENT_TYPES)

# Spec §15: "Do not send a notification for every rating by default."
DEFAULT_PREFERENCES: dict[str, bool] = {event: event != "assertion_rated" for event in EVENT_TYPES}

# Review status -> the notice its author gets when a reviewer sets it.
DECISION_EVENTS = {
    "revision_requested": "revision_requested",
    "accepted": "assertion_accepted",
    "rejected": "assertion_rejected",
    "disputed": "assertion_disputed",
    "superseded": "assertion_superseded",
}

REVIEWER_ROLES = ("reviewer", "admin")
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
PROPOSITION_EXCERPT_CHARS = 280

# INSERT ... ON CONFLICT DO UPDATE, per database (SQLite is the one shipped).
_UPSERT_INSERTS = {"sqlite": sqlite.insert, "postgresql": postgresql.insert}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    """ISO 8601 with an explicit UTC offset (SQLite returns naive values)."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _excerpt(text: str | None) -> str | None:
    if text is None or len(text) <= PROPOSITION_EXCERPT_CHARS:
        return text
    return text[: PROPOSITION_EXCERPT_CHARS - 1].rstrip() + "…"


# --- Preferences -------------------------------------------------------------


def _enabled_for(session: Session, user_ids: Iterable[str], event_type: str) -> dict[str, bool]:
    ids = sorted(set(user_ids))
    enabled = {user_id: DEFAULT_PREFERENCES[event_type] for user_id in ids}
    if not ids:
        return enabled
    rows = session.execute(
        select(NotificationPreference.user_id, NotificationPreference.enabled).where(
            NotificationPreference.user_id.in_(ids),
            NotificationPreference.event_type == event_type,
        )
    ).all()
    enabled.update({user_id: bool(value) for user_id, value in rows})
    return enabled


def get_preferences(session: Session, user_id: str) -> list[dict[str, Any]]:
    """`user_id`'s setting for every event type, with the default beside it."""
    chosen = dict(
        session.execute(
            select(NotificationPreference.event_type, NotificationPreference.enabled).where(
                NotificationPreference.user_id == user_id
            )
        ).all()
    )
    return [
        {
            "event_type": event,
            "enabled": bool(chosen.get(event, DEFAULT_PREFERENCES[event])),
            "default": DEFAULT_PREFERENCES[event],
        }
        for event in EVENT_TYPES
    ]


def set_preferences(session: Session, user_id: str, changes: dict[str, bool]) -> list[dict[str, Any]]:
    """Record `user_id`'s choices (does not commit). Raises ValueError for an
    unknown event type, before anything is written.

    Each choice is one upsert on the unique (user_id, event_type) key (review
    workflow:4). Reading the stored rows and then inserting the missing ones
    let two overlapping first-time writes both insert, and the second failed
    on the key with a 500. Now concurrent writes apply one after the other
    and the later one wins. A choice equal to the stored one keeps its
    `updated_at`.
    """
    unknown = sorted(set(changes) - NOTIFIABLE_EVENTS)
    if unknown:
        raise ValueError(f"unknown notification event type(s): {', '.join(unknown)}")
    dialect = session.get_bind().dialect.name
    if dialect not in _UPSERT_INSERTS:
        raise NotImplementedError(f"notification preferences need an upsert, implemented for "
                                  f"{' and '.join(_UPSERT_INSERTS)}, not {dialect}")
    insert = _UPSERT_INSERTS[dialect]
    now = _now()
    for event in sorted(changes):  # one row order for every writer
        stmt = insert(NotificationPreference).values(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type=event,
            enabled=bool(changes[event]),
            updated_at=now,
        )
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[NotificationPreference.user_id, NotificationPreference.event_type],
                set_={"enabled": stmt.excluded.enabled, "updated_at": stmt.excluded.updated_at},
                where=NotificationPreference.enabled != stmt.excluded.enabled,
            )
        )
    return get_preferences(session, user_id)


# --- Recipients ----------------------------------------------------------------


def matter_members(session: Session, matter_id: str) -> dict[str, str]:
    """user_id -> role for every current member of `matter_id`."""
    return dict(
        session.execute(
            select(MatterRole.user_id, MatterRole.role).where(MatterRole.matter_id == matter_id)
        ).all()
    )


def reviewers_of(session: Session, matter_id: str) -> set[str]:
    return {user_id for user_id, role in matter_members(session, matter_id).items() if role in REVIEWER_ROLES}


def participants_of(session: Session, assertion: Assertion) -> set[str]:
    """Everyone who has worked on `assertion`: its author and last reviewer,
    the editors of its revisions, whoever attached evidence, commented on it
    (comments not deleted) or rated any of its revisions."""
    ids: set[str | None] = {assertion.author_user_id, assertion.reviewed_by}
    for column, where in (
        (AssertionRevision.edited_by_user_id, AssertionRevision.assertion_id == assertion.id),
        (AssertionEvidence.added_by_user_id, AssertionEvidence.assertion_id == assertion.id),
        (AssertionRating.user_id, AssertionRating.assertion_id == assertion.id),
    ):
        ids |= set(session.scalars(select(column).where(where).distinct()))
    ids |= set(
        session.scalars(
            select(AssertionComment.user_id)
            .where(AssertionComment.assertion_id == assertion.id, AssertionComment.deleted_at.is_(None))
            .distinct()
        )
    )
    ids.discard(None)
    return ids  # type: ignore[return-value]


# --- Writing -------------------------------------------------------------------


def create_notifications(
    session: Session,
    *,
    event_type: str,
    actor_user_id: str,
    recipients: Iterable[str],
    matter_id: str,
    assertion_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> list[Notification]:
    """Add one notification per eligible recipient to `session` and return
    them (the caller commits).

    Eligible: a current member of `matter_id`, not the actor, and not opted
    out of `event_type`. `payload` holds references and event facts only,
    never document or comment text.
    """
    if event_type not in NOTIFIABLE_EVENTS:
        raise ValueError(f"unknown notification event_type: {event_type!r}")
    members = matter_members(session, matter_id)
    candidates = {r for r in recipients if r and r != actor_user_id and r in members}
    if not candidates:
        return []
    enabled = _enabled_for(session, candidates, event_type)
    body = json.dumps(
        {"assertion_id": assertion_id, "matter_id": matter_id, **(payload or {})},
        ensure_ascii=False,
        sort_keys=True,
    )
    now = _now()
    rows = [
        Notification(
            id=str(uuid.uuid4()),
            recipient_user_id=recipient,
            actor_user_id=actor_user_id,
            event_type=event_type,
            matter_id=matter_id,
            assertion_id=assertion_id,
            payload=body,
            created_at=now,
            read_at=None,
        )
        for recipient in sorted(candidates)
        if enabled[recipient]
    ]
    session.add_all(rows)
    return rows


def notify_assertion_submitted(
    session: Session, assertion: Assertion, actor_user_id: str, *, previous_status: str | None = None
) -> list[Notification]:
    """`assertion` has just entered `proposed`: tell the matter's reviewers.

    Safe to call more than once for the same submission (for example by the
    HTTP hook and by a direct caller): a recipient who already has an
    `assertion_submitted` notice created since `assertion.submitted_at` is
    skipped.
    """
    if assertion.status != "proposed":
        return []
    recipients = reviewers_of(session, assertion.matter_id)
    if assertion.submitted_at is not None:
        recipients -= set(
            session.scalars(
                select(Notification.recipient_user_id).where(
                    Notification.event_type == "assertion_submitted",
                    Notification.assertion_id == assertion.id,
                    Notification.created_at >= assertion.submitted_at,
                )
            )
        )
    return create_notifications(
        session,
        event_type="assertion_submitted",
        actor_user_id=actor_user_id,
        recipients=recipients,
        matter_id=assertion.matter_id,
        assertion_id=assertion.id,
        payload={"status": assertion.status, "previous_status": previous_status},
    )


def notify_submission(session: Session, assertion_id: str, actor_user_id: str) -> int:
    """One call for code that proposes assertions outside an HTTP request
    (the agent CLI, the MCP server): if `assertion_id` is proposed, notify
    the reviewers and commit. Returns how many notices were written.

    Never raises -- a notification problem must not fail a suggestion that
    has already been stored -- and is idempotent per submission, so calling
    it on a path the HTTP hook also covers creates no duplicates.
    """
    try:
        assertion = session.get(Assertion, assertion_id)
        if assertion is None:
            return 0
        created = notify_assertion_submitted(session, assertion, actor_user_id)
        session.commit()
        return len(created)
    except Exception:
        session.rollback()
        logger.exception("could not notify reviewers about assertion %s", assertion_id)
        return 0


def notify_review_decision(
    session: Session, assertion: Assertion, actor_user_id: str, *, previous_status: str | None = None
) -> list[Notification]:
    """A reviewer has just set `assertion.status`: tell its author."""
    event_type = DECISION_EVENTS.get(assertion.status)
    if event_type is None:
        return []
    payload: dict[str, Any] = {"status": assertion.status, "previous_status": previous_status}
    if assertion.status == "superseded":
        payload["superseded_by_assertion_id"] = assertion.superseded_by_assertion_id
    return create_notifications(
        session,
        event_type=event_type,
        actor_user_id=actor_user_id,
        recipients={assertion.author_user_id},
        matter_id=assertion.matter_id,
        assertion_id=assertion.id,
        payload=payload,
    )


def _activity_recipients(session: Session, assertion: Assertion) -> set[str]:
    recipients = participants_of(session, assertion)
    if assertion.status == "proposed":
        recipients |= reviewers_of(session, assertion.matter_id)
    return recipients


def notify_revision_created(
    session: Session,
    assertion: Assertion,
    actor_user_id: str,
    *,
    previous_revision_number: int | None = None,
    previous_status: str | None = None,
) -> list[Notification]:
    return create_notifications(
        session,
        event_type="revision_created",
        actor_user_id=actor_user_id,
        recipients=_activity_recipients(session, assertion),
        matter_id=assertion.matter_id,
        assertion_id=assertion.id,
        payload={
            "revision_number": assertion.current_revision_number,
            "previous_revision_number": previous_revision_number,
            "status": assertion.status,
            "previous_status": previous_status,
        },
    )


def notify_evidence_added(
    session: Session, assertion: Assertion, evidence: AssertionEvidence, actor_user_id: str
) -> list[Notification]:
    return create_notifications(
        session,
        event_type="evidence_added",
        actor_user_id=actor_user_id,
        recipients=_activity_recipients(session, assertion),
        matter_id=assertion.matter_id,
        assertion_id=assertion.id,
        payload={"evidence_id": evidence.id, "evidence_role": evidence.evidence_role},
    )


def notify_comment_added(
    session: Session, assertion: Assertion, comment: AssertionComment, actor_user_id: str
) -> list[Notification]:
    recipients = participants_of(session, assertion)
    if comment.parent_comment_id is not None:
        parent = session.get(AssertionComment, comment.parent_comment_id)
        if parent is not None and parent.deleted_at is None:
            recipients.add(parent.user_id)
    return create_notifications(
        session,
        event_type="comment_added",
        actor_user_id=actor_user_id,
        recipients=recipients,
        matter_id=assertion.matter_id,
        assertion_id=assertion.id,
        payload={"comment_id": comment.id, "parent_comment_id": comment.parent_comment_id},
    )


def notify_assertion_rated(
    session: Session,
    assertion: Assertion,
    rating: AssertionRating,
    actor_user_id: str,
    *,
    revision_number: int | None = None,
) -> list[Notification]:
    """Opt-in only (`DEFAULT_PREFERENCES["assertion_rated"]` is False)."""
    return create_notifications(
        session,
        event_type="assertion_rated",
        actor_user_id=actor_user_id,
        recipients={assertion.author_user_id},
        matter_id=assertion.matter_id,
        assertion_id=assertion.id,
        payload={"revision_number": revision_number, "strength": rating.strength},
    )


# --- Reading and read state ------------------------------------------------------


def _serialize(session: Session, user_id: str, rows: list[Notification]) -> list[dict[str, Any]]:
    if not rows:
        return []
    my_matters = set(
        session.scalars(select(MatterRole.matter_id).where(MatterRole.user_id == user_id))
    )
    assertion_ids = {r.assertion_id for r in rows if r.assertion_id}
    matter_ids = {r.matter_id for r in rows if r.matter_id}
    actor_ids = {r.actor_user_id for r in rows}
    assertions = {
        row.id: row
        for row in session.execute(
            select(Assertion.id, Assertion.proposition, Assertion.status, Assertion.origin).where(
                Assertion.id.in_(assertion_ids)
            )
        )
    } if assertion_ids else {}
    matter_names = dict(
        session.execute(select(Matter.id, Matter.name).where(Matter.id.in_(matter_ids))).all()
    ) if matter_ids else {}
    actor_names = dict(
        session.execute(select(User.id, User.display_name).where(User.id.in_(actor_ids))).all()
    )

    result = []
    for row in rows:
        context = link = None
        if row.matter_id is None or row.matter_id in my_matters:
            assertion = assertions.get(row.assertion_id) if row.assertion_id else None
            context = {
                "proposition": _excerpt(assertion.proposition) if assertion else None,
                "assertion_status": assertion.status if assertion else None,
                "assertion_origin": assertion.origin if assertion else None,
                "matter_name": matter_names.get(row.matter_id) if row.matter_id else None,
                "actor_display_name": actor_names.get(row.actor_user_id),
            }
            if assertion is not None:
                link = f"/assertions/{row.assertion_id}"
        try:
            payload = json.loads(row.payload)
        except ValueError:
            payload = {}
        result.append(
            {
                "id": row.id,
                "event_type": row.event_type,
                "actor_user_id": row.actor_user_id,
                "recipient_user_id": row.recipient_user_id,
                "matter_id": row.matter_id,
                "assertion_id": row.assertion_id,
                "link": link,
                "payload": payload,
                "context": context,
                "created_at": _iso(row.created_at),
                "read": row.read_at is not None,
                "read_at": _iso(row.read_at),
            }
        )
    return result


def list_notifications(
    session: Session,
    user_id: str,
    *,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    unread_only: bool = False,
) -> list[dict[str, Any]]:
    """`user_id`'s notifications, newest first, one page at a time.

    Scoped purely by recipient: a user with no notifications -- including
    an outsider with no role anywhere -- gets an empty list.
    """
    stmt = select(Notification).where(Notification.recipient_user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit).offset(offset)
    return _serialize(session, user_id, list(session.scalars(stmt)))


def count_unread(session: Session, user_id: str) -> int:
    return session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.recipient_user_id == user_id, Notification.read_at.is_(None))
    ) or 0


def mark_read(session: Session, user_id: str, notification_id: str) -> dict[str, Any] | None:
    """Mark one of `user_id`'s notifications read (idempotent; the first
    read time is kept). None if it is not theirs or does not exist. Commits."""
    row = session.get(Notification, notification_id)
    if row is None or row.recipient_user_id != user_id:
        return None
    if row.read_at is None:
        row.read_at = _now()
        session.commit()
    return _serialize(session, user_id, [row])[0]


def mark_all_read(session: Session, user_id: str, *, last_read_at: datetime | None = None) -> int:
    """Mark `user_id`'s unread notifications read and return how many.

    With `last_read_at`, notifications created after that instant stay
    unread, so a client can mark exactly what it has shown without racing a
    notice that arrived meanwhile. Commits.
    """
    stmt = update(Notification).where(
        Notification.recipient_user_id == user_id, Notification.read_at.is_(None)
    )
    if last_read_at is not None:
        stmt = stmt.where(Notification.created_at <= last_read_at)
    marked = session.execute(stmt.values(read_at=_now()), execution_options={"synchronize_session": False}).rowcount
    session.commit()
    return marked or 0
