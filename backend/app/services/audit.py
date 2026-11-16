"""Audit event recording service (item B3, spec §16).

`record_audit_event` is the single write path for every `audit_events`
row in this system. A mutation records its audit rows in its own database
transaction, so a mutation never commits without its audit rows and an
audit row never outlives a rolled-back mutation (findings api:4, api:5,
review:2, pipeline:5):

1. A router calls `record_audit_event` (or `record_assertion_event`, which
   fills the repository, matter, assertion and current revision in from
   the assertion row) before it commits -- the call-site is next to the
   mutation it describes.
2. Rating creations and changes are recorded by a flush hook registered
   below, from the rating row itself, in the transaction that writes the
   rating (`app/routers/ratings.py`'s PUT handler records none of its own;
   its DELETE handler records `rating_removed`).

Every row carries what spec §16 requires:

- actor, timestamp, repository, matter, assertion;
- the assertion revision: a revision-specific event names its revision
  (the rated revision of a rating event, the revision an edit created);
  any other event about an assertion records the assertion's current
  revision at the time of the event -- `record_audit_event` looks it up
  when the caller names an assertion but no revision;
- previous/new value where appropriate (see the value conventions in
  docs/specs/collaborative-assertions.md, section 16);
- a request or correlation id, one per unit of work, so that the rows one
  action wrote can be found together:
    * inside an API request, the request's id: `app.audit_middleware`
      binds a fresh server-generated id for every HTTP request
      (`bind_request_correlation_id`) and returns it as the
      `X-Request-ID` response header;
    * elsewhere (agent CLI, MCP server, offline pipelines), one id per
      database transaction: the first row a transaction records picks a
      fresh id and later rows in that transaction reuse it;
    * an explicit `correlation_id` argument always wins.

Callers must never pass raw document/source-span/full-proposition content
as `previous_value`/`new_value` -- spec §16: "Do not include confidential
full-document content in routine audit logs." Short status/summary
strings and row ids only.
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import event, inspect as sa_inspect, select
from sqlalchemy.orm import Session

from app.models.assertion import Assertion
from app.models.assertion_rating import AssertionRating
from app.models.assertion_revision import AssertionRevision
from app.models.audit_event import AuditEvent

# The correlation id of the API request being served, bound by
# `app.audit_middleware` for the duration of each HTTP request.
_REQUEST_CORRELATION_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "lexgraph_audit_request_correlation_id", default=None
)
# session.info key: (root SessionTransaction, correlation id) of the
# transaction that last recorded an audit row outside a bound request.
_TRANSACTION_CORRELATION_KEY = "lexgraph.audit.transaction_correlation"


def _fresh_correlation_id() -> str:
    return str(uuid.uuid4())


@contextmanager
def bind_request_correlation_id(correlation_id: str | None = None) -> Iterator[str]:
    """Make `correlation_id` (default: a fresh one) the correlation id of
    every audit row recorded until the block exits, and yield it.

    `app.audit_middleware` wraps every HTTP request in this. Context
    variables follow the request into the worker threads FastAPI runs sync
    routes and dependencies in, so every router and hook sees it.
    """
    bound = correlation_id or _fresh_correlation_id()
    token = _REQUEST_CORRELATION_ID.set(bound)
    try:
        yield bound
    finally:
        _REQUEST_CORRELATION_ID.reset(token)


def request_correlation_id() -> str | None:
    """The bound request's correlation id, or None outside a bound request."""
    return _REQUEST_CORRELATION_ID.get()


def new_correlation_id() -> str:
    """The correlation id for a new group of audit rows.

    Inside a bound API request this is the request's id, so every row the
    request writes shares it (whichever helper the writer used); elsewhere
    it is a fresh uuid4.
    """
    return _REQUEST_CORRELATION_ID.get() or _fresh_correlation_id()


def current_correlation_id(session: Session | None = None) -> str:
    """The correlation id an audit row recorded now belongs to: the bound
    request's id, else (given a session) the id of the session's current
    transaction, else a fresh one."""
    bound = _REQUEST_CORRELATION_ID.get()
    if bound:
        return bound
    if session is None:
        return _fresh_correlation_id()
    transaction = session.get_transaction()
    held = session.info.get(_TRANSACTION_CORRELATION_KEY)
    if held is not None and transaction is not None and held[0] is transaction:
        return held[1]
    correlation_id = _fresh_correlation_id()
    if transaction is not None:
        session.info[_TRANSACTION_CORRELATION_KEY] = (transaction, correlation_id)
    return correlation_id


# --- Revision lookup ------------------------------------------------------------


def _pending(session: Session, cls: type, **values) -> object | None:
    for obj in session.new:
        if isinstance(obj, cls) and all(getattr(obj, k) == v for k, v in values.items()):
            return obj
    return None


def revision_id_for(session: Session, assertion_id: str, revision_number: int | None) -> str | None:
    """Id of revision `revision_number` of the assertion, pending or stored.

    A database that has not run the unique (assertion_id, revision_number)
    migration may hold two rows for one number; the newest is used, as in
    `app.routers.assertions._current_revision`.
    """
    if revision_number is None:
        return None
    pending = _pending(
        session, AssertionRevision, assertion_id=assertion_id, revision_number=revision_number
    )
    if pending is not None:
        if pending.id is None:
            pending.id = str(uuid.uuid4())  # the column default, applied early
        return pending.id
    with session.no_autoflush:
        return session.execute(
            select(AssertionRevision.id)
            .where(
                AssertionRevision.assertion_id == assertion_id,
                AssertionRevision.revision_number == revision_number,
            )
            .order_by(AssertionRevision.created_at.desc(), AssertionRevision.id.desc())
            .limit(1)
        ).scalar_one_or_none()


def current_revision_id(session: Session, assertion_id: str) -> str | None:
    """Id of the assertion's current revision, or None if it has none."""
    with session.no_autoflush:
        assertion = _pending(session, Assertion, id=assertion_id) or session.get(
            Assertion, assertion_id
        )
    if assertion is None:
        return None
    return revision_id_for(session, assertion.id, assertion.current_revision_number)


# --- Write path -------------------------------------------------------------------


def record_audit_event(
    session: Session,
    *,
    actor_user_id: str,
    event_type: str,
    repository_id: str,
    matter_id: str,
    assertion_id: str | None = None,
    assertion_revision_id: str | None = None,
    previous_value: str | None = None,
    new_value: str | None = None,
    correlation_id: str | None = None,
) -> AuditEvent:
    """Add one `AuditEvent` row to `session` (does NOT commit -- the caller
    commits as part of its own transaction, same convention as every other
    router in this codebase).

    `assertion_revision_id` defaults to the current revision of
    `assertion_id`; `correlation_id` defaults to `current_correlation_id`
    (the request's id, else the transaction's). See the module docstring.
    """
    if assertion_revision_id is None and assertion_id is not None:
        assertion_revision_id = current_revision_id(session, assertion_id)
    event_row = AuditEvent(
        id=str(uuid.uuid4()),
        actor_user_id=actor_user_id,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        repository_id=repository_id,
        matter_id=matter_id,
        assertion_id=assertion_id,
        assertion_revision_id=assertion_revision_id,
        previous_value=previous_value,
        new_value=new_value,
    )
    session.add(event_row)  # begins the session's transaction if none is open
    event_row.correlation_id = correlation_id or current_correlation_id(session)
    return event_row


def record_assertion_event(
    session: Session,
    assertion: Assertion,
    *,
    actor_user_id: str,
    event_type: str,
    previous_value: str | None = None,
    new_value: str | None = None,
    assertion_revision_id: str | None = None,
    correlation_id: str | None = None,
) -> AuditEvent:
    """`record_audit_event` for an event about `assertion`: repository,
    matter and assertion come from the row, and the revision defaults to
    the assertion's current revision (pending or stored)."""
    if assertion_revision_id is None:
        assertion_revision_id = revision_id_for(
            session, assertion.id, assertion.current_revision_number
        )
    return record_audit_event(
        session,
        actor_user_id=actor_user_id,
        event_type=event_type,
        repository_id=assertion.repository_id,
        matter_id=assertion.matter_id,
        assertion_id=assertion.id,
        assertion_revision_id=assertion_revision_id,
        previous_value=previous_value,
        new_value=new_value,
        correlation_id=correlation_id,
    )


# --- Rating writes: audited from the row, in the writing transaction --------------


def _stored_strength(session: Session, rating: AssertionRating) -> int | None:
    """The strength the database holds for `rating` (read before the flush
    writes the new one), for a change made to an unloaded attribute."""
    with session.no_autoflush:
        return session.execute(
            select(AssertionRating.strength).where(AssertionRating.id == rating.id)
        ).scalar_one_or_none()


def _record_rating(
    session: Session, rating: AssertionRating, event_type: str, previous_strength: int | None
) -> None:
    record_audit_event(
        session,
        actor_user_id=rating.user_id,
        event_type=event_type,
        repository_id=rating.repository_id,
        matter_id=rating.matter_id,
        assertion_id=rating.assertion_id,
        # The rated revision, which need not be the current one.
        assertion_revision_id=rating.assertion_revision_id,
        previous_value=str(previous_strength) if previous_strength is not None else None,
        new_value=str(rating.strength) if rating.strength is not None else None,
    )


def _audit_rating_writes(session: Session, _flush_context, _instances) -> None:
    """`before_flush`: record `rating_created` for every rating this flush
    inserts and `rating_changed` (previous -> new strength) for every rating
    it updates. Objects added here are part of the same flush. Deletions
    are recorded by the DELETE handler (`rating_removed`)."""
    for obj in list(session.new):
        if isinstance(obj, AssertionRating):
            _record_rating(session, obj, "rating_created", None)
    for obj in list(session.dirty):
        if not isinstance(obj, AssertionRating) or not session.is_modified(obj):
            continue
        history = sa_inspect(obj).attrs.strength.history
        if history.deleted:
            previous = history.deleted[0]
        elif history.unchanged:
            previous = history.unchanged[0]
        else:  # set while unloaded: the stored value is the previous one
            previous = _stored_strength(session, obj)
        _record_rating(session, obj, "rating_changed", previous)


def register_flush_hooks(target=Session) -> None:
    """Attach the rating audit hook to `target` (every `Session` by default).
    Idempotent."""
    if not event.contains(target, "before_flush", _audit_rating_writes):
        event.listen(target, "before_flush", _audit_rating_writes)


register_flush_hooks()
