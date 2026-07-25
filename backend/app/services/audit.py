"""Audit event recording service (item B3, spec §16).

`record_audit_event` is the single write path for every `audit_events` row
in this system. Two call patterns are expected:

1. A track's own router calls this function directly (e.g. this track's
   `app/routers/comments.py`, or B2's future `app/routers/ratings.py` once
   it merges into this worktree) -- the preferred path when the mutation
   lives in a file this track (or a track that wants audit coverage) can
   edit directly.
2. `app/audit_middleware.py` (owned by this track) calls this function
   from an ASGI middleware hook for mutations that live in OTHER tracks'
   already-merged router files (e.g. B1's `POST /api/v1/assertions`) --
   ruling R9 forbids editing another track's router file to add the
   call-site, so the middleware is the mandated workaround.

Callers must never pass raw document/source-span/full-proposition content
as `previous_value`/`new_value` -- spec §16: "Do not include confidential
full-document content in routine audit logs." Short status/summary
strings only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def new_correlation_id() -> str:
    return str(uuid.uuid4())


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

    Always assigns a `correlation_id` (caller-supplied, or a fresh uuid4)
    since every audited mutation must be traceable to a single request.
    """
    event = AuditEvent(
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
        correlation_id=correlation_id or new_correlation_id(),
    )
    session.add(event)
    return event
