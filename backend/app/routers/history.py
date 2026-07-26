"""Assertion history route (item B3, ruling R10).

    GET /api/v1/assertions/{assertion_id}/history

Read-only, audit-backed timeline for one assertion: every `audit_events`
row referencing the assertion (written by this track's comment routes,
this track's `app.audit_middleware`, and directly by other tracks' own
routers -- e.g. B4's `app/routers/review.py` review decisions), ordered
oldest-first. Each event is annotated with `assertion_revision_number`
(via a left join on `assertion_revisions`) when the audit row references a
specific revision -- consumed by
`tests/integration/test_review_workflow.py::
test_review_decision_records_reviewed_revision` and the E1 end-to-end
flow.

Matter-scoped: same membership check as every other route in this
codebase (a user with no `matter_roles` row for the assertion's matter
gets 403). DB access via a local dependency reading
`request.app.state.session_factory` (no shared deps module).
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.assertion import Assertion
from app.models.assertion_revision import AssertionRevision
from app.models.audit_event import AuditEvent
from app.models.matter_role import MatterRole

router = APIRouter(prefix="/api/v1/assertions", tags=["history"])


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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def _require_matter_member(session: Session, user_id: str, matter_id: str) -> None:
    role = session.execute(
        select(MatterRole.role).where(
            MatterRole.user_id == user_id, MatterRole.matter_id == matter_id
        )
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="no access to matter")


@router.get("/{assertion_id}/history")
def get_assertion_history(
    assertion_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    assertion = session.get(Assertion, assertion_id)
    if assertion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assertion not found")
    _require_matter_member(session, user_id, assertion.matter_id)

    rows = session.execute(
        select(AuditEvent, AssertionRevision.revision_number)
        .outerjoin(AssertionRevision, AuditEvent.assertion_revision_id == AssertionRevision.id)
        .where(AuditEvent.assertion_id == assertion_id)
        .order_by(AuditEvent.timestamp.asc())
    ).all()

    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "actor_user_id": event.actor_user_id,
            "timestamp": event.timestamp,
            "assertion_revision_number": revision_number,
            "previous_value": event.previous_value,
            "new_value": event.new_value,
            "correlation_id": event.correlation_id,
        }
        for event, revision_number in rows
    ]
