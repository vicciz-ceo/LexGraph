"""Persistence invariant: every assertion has a revision row for its
`current_revision_number` (audit findings api:1, pipeline:2, pipeline:3, ui:4).

The REST, agent, CLI and MCP creation path
(`app.routers.assertions._create_assertion`) and offline enrichment
(`app.enrich.pipeline`) write revision 1 themselves. The deterministic
definition-links pass (`app.definition_links.pipeline`, a frozen certified
seam) inserts accepted `system_generated` assertions with
`current_revision_number=1` and nothing else. Without a revision row the
rating routes answer 404 for the revision the API advertises, the revision
history is empty, the first edit loses the original text, and review
decisions cannot name the revision they reviewed.

The invariant is therefore enforced here, at the persistence layer, for
every writer instead of in each one:

* `before_flush` records every `Assertion` the session inserts;
* `before_commit` gives each recorded assertion that still has no revision
  row for its current number an initial revision built from the
  assertion's own fields, plus the `assertion_created` audit event a
  creation path owes (`app.services.audit.record_audit_event`).

Checking only at commit, never per flush, is what keeps writers that add
their own revision untouched: a writer may flush (or autoflush) between
`add(assertion)` and `add(revision)`, and by commit time its revision is
either flushed or pending, so a second revision 1 is never invented. A
transaction that rolls back creates nothing.

Rows written with raw SQL bypass the ORM and therefore this hook; existing
databases are repaired by `app.migrations.m20261116_backfill_initial_assertion_revisions`.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator, Sequence
from datetime import datetime, timezone

from sqlalchemy import event, inspect as sa_inspect, select
from sqlalchemy.orm import Session

from app.models.assertion import Assertion
from app.models.assertion_revision import AssertionRevision

_INSERTED_KEY = "lexgraph.inserted_assertions"
# Well below SQLite's bound-parameter limit (999 before SQLite 3.32).
_QUERY_CHUNK = 500


def initial_revision_reason(origin: str | None) -> str:
    """`revision_reason` for a revision this module (or its backfill
    migration) records on a writer's behalf."""
    return f"initial creation ({(origin or 'unknown').replace('_', '-')})"


def _chunks(items: Sequence[str], size: int) -> Iterator[Sequence[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _record_inserted_assertions(session: Session, _flush_context, _instances) -> None:
    for obj in session.new:
        if isinstance(obj, Assertion):
            session.info.setdefault(_INSERTED_KEY, {})[id(obj)] = obj


def _forget_inserted_assertions(session: Session) -> None:
    # Fires after the outermost commit and after each savepoint release;
    # `before_commit` has handled every recorded assertion by then.
    session.info.pop(_INSERTED_KEY, None)


def _drop_rolled_back_assertions(session: Session, _previous_transaction) -> None:
    # Fires after the rolled-back (sub)transaction's inserts were expunged:
    # keep only assertions inserted before a rolled-back savepoint.
    tracked = session.info.get(_INSERTED_KEY)
    if tracked:
        for key, obj in list(tracked.items()):
            if obj not in session:
                del tracked[key]


def _assertions_to_check(session: Session) -> list[Assertion]:
    candidates: dict[int, Assertion] = dict(session.info.get(_INSERTED_KEY) or {})
    for obj in session.new:
        if isinstance(obj, Assertion):
            candidates[id(obj)] = obj
    # Skip objects expunged, deleted, or rolled back out of the session
    # (e.g. inside a released savepoint) since they were recorded.
    return [
        obj
        for obj in candidates.values()
        if obj in session and obj not in session.deleted and not sa_inspect(obj).deleted
    ]


def _existing_revision_keys(session: Session, assertions: list[Assertion]) -> set[tuple[str, int]]:
    keys = {
        (obj.assertion_id, obj.revision_number)
        for obj in session.new
        if isinstance(obj, AssertionRevision)
    }
    flushed_ids = [a.id for a in assertions if a.id is not None and not sa_inspect(a).pending]
    for chunk in _chunks(flushed_ids, _QUERY_CHUNK):
        keys.update(
            (assertion_id, number)
            for assertion_id, number in session.execute(
                select(AssertionRevision.assertion_id, AssertionRevision.revision_number).where(
                    AssertionRevision.assertion_id.in_(chunk)
                )
            )
        )
    return keys


def ensure_current_revisions(session: Session) -> int:
    """Add the missing current-revision row (and creation audit event) for
    every assertion inserted in this transaction. Returns how many it added.

    Runs as the `before_commit` hook; callable directly for tests.
    """
    assertions = _assertions_to_check(session)
    if not assertions:
        return 0
    # Imported lazily: app.services.audit imports app.models.audit_event,
    # which must not be pulled in while app.models is still initialising.
    from app.services.audit import new_correlation_id, record_audit_event

    added = 0
    correlation_id = None
    with session.no_autoflush:
        existing = _existing_revision_keys(session, assertions)
        for assertion in assertions:
            if assertion.current_revision_number is None:
                continue  # NOT NULL: the INSERT itself reports this writer bug
            if assertion.id is None:
                assertion.id = str(uuid.uuid4())  # the column default, applied early
            key = (assertion.id, assertion.current_revision_number)
            if key in existing:
                continue
            revision = AssertionRevision(
                id=str(uuid.uuid4()),
                assertion_id=assertion.id,
                revision_number=assertion.current_revision_number,
                proposition=assertion.proposition,
                # The writer stored the proposition as authored; it is the
                # best (and, for generated text, exact) raw value available.
                proposition_raw=assertion.proposition,
                assertion_type=assertion.assertion_type,
                subject_entity_type=assertion.subject_entity_type,
                subject_entity_id=assertion.subject_entity_id,
                object_entity_type=assertion.object_entity_type,
                object_entity_id=assertion.object_entity_id,
                jurisdiction=assertion.jurisdiction,
                effective_from=assertion.effective_from,
                effective_to=assertion.effective_to,
                revision_reason=initial_revision_reason(assertion.origin),
                edited_by_user_id=assertion.author_user_id,
                created_at=assertion.created_at or datetime.now(timezone.utc),
            )
            session.add(revision)
            existing.add(key)
            correlation_id = correlation_id or new_correlation_id()
            record_audit_event(
                session,
                actor_user_id=assertion.author_user_id,
                event_type="assertion_created",
                repository_id=assertion.repository_id,
                matter_id=assertion.matter_id,
                assertion_id=assertion.id,
                assertion_revision_id=revision.id,
                new_value=assertion.status,
                correlation_id=correlation_id,
            )
            added += 1
    return added


def _ensure_current_revisions_hook(session: Session) -> None:
    ensure_current_revisions(session)


_LISTENERS = (
    ("before_flush", _record_inserted_assertions),
    ("before_commit", _ensure_current_revisions_hook),
    ("after_commit", _forget_inserted_assertions),
    ("after_soft_rollback", _drop_rolled_back_assertions),
)


def register(target=Session) -> None:
    """Attach the hooks to `target` (every `Session` by default). Idempotent."""
    for name, listener in _LISTENERS:
        if not event.contains(target, name, listener):
            event.listen(target, name, listener)


register()
