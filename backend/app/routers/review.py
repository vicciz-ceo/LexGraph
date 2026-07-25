"""Review workflow router (Developer track B4).

Implements the "Review" API surface from spec §13:

    POST /api/v1/assertions/{assertion_id}/accept
    POST /api/v1/assertions/{assertion_id}/reject
    POST /api/v1/assertions/{assertion_id}/dispute
    POST /api/v1/assertions/{assertion_id}/request-revision
    POST /api/v1/assertions/{assertion_id}/supersede

Business rules encoded here (spec §10/§12, sprint gates G5/G6/G8):

- Only a role granted the relevant `assertion:*` permission (reviewer or
  admin) may change review status; a role with no matter access at all
  (no matter_roles row) is treated as having no permissions.
- An "unsupported" assertion (zero `assertion_evidence` rows) cannot be
  accepted unless the request records an `acceptance_justification`.
- A review decision never touches `assertion_ratings` rows.
- A review decision records which assertion + revision was reviewed
  (`reviewed_by`, `reviewed_at`, and the current revision's id on the
  audit event this router writes).
- No decision here ever mutates `assertion_ratings` — ratings are owned by
  track B2 and are read-only from this router's point of view.

DB session comes from `request.app.state.session_factory` via a local
dependency (this file) rather than `app.db.get_db_dependency`, since the
session factory is created per-`create_app()` call (see
`tests/conftest.py`'s `app` fixture) and isn't known at import time.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_revision import AssertionRevision
from app.models.audit_event import AuditEvent
from app.models.matter_role import MatterRole
from app.services.permissions import has_permission

router = APIRouter(prefix="/api/v1/assertions", tags=["review"])


# --- Local dependencies ---------------------------------------------------


def get_db(request: Request) -> Iterator[Session]:
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


# --- Request bodies --------------------------------------------------------


class AcceptBody(BaseModel):
    acceptance_justification: str | None = None


class RequestRevisionBody(BaseModel):
    comment: str | None = None


class SupersedeBody(BaseModel):
    superseded_by_assertion_id: str


# --- Helpers ----------------------------------------------------------------


def _get_assertion_or_404(db: Session, assertion_id: str) -> Assertion:
    assertion = db.get(Assertion, assertion_id)
    if assertion is None:
        raise HTTPException(status_code=404, detail="assertion not found")
    return assertion


def _role_for(db: Session, user_id: str, matter_id: str) -> str | None:
    return db.execute(
        select(MatterRole.role).where(
            MatterRole.user_id == user_id, MatterRole.matter_id == matter_id
        )
    ).scalar_one_or_none()


def _require_permission(db: Session, user_id: str, assertion: Assertion, permission: str) -> str:
    """Return the caller's role for `assertion`'s matter, or raise 403."""
    role = _role_for(db, user_id, assertion.matter_id)
    if not has_permission(role or "", permission):
        raise HTTPException(status_code=403, detail=f"missing permission: {permission}")
    return role  # type: ignore[return-value]


def _current_revision(db: Session, assertion: Assertion) -> AssertionRevision | None:
    return db.execute(
        select(AssertionRevision).where(
            AssertionRevision.assertion_id == assertion.id,
            AssertionRevision.revision_number == assertion.current_revision_number,
        )
    ).scalar_one_or_none()


def _has_evidence(db: Session, assertion: Assertion) -> bool:
    return (
        db.execute(
            select(AssertionEvidence.id).where(AssertionEvidence.assertion_id == assertion.id)
        ).first()
        is not None
    )


def _record_decision(
    db: Session,
    *,
    actor_user_id: str,
    event_type: str,
    assertion: Assertion,
    previous_status: str,
    new_status: str,
    extra_note: str | None = None,
) -> None:
    """Write one audit_events row for a review decision (B4-owned mechanism;

    does not call into track B3's `app.services.audit`, which is not part
    of this track's write-set and may not exist in this worktree — see
    ruling R9).
    """
    revision = _current_revision(db, assertion)
    new_value = new_status if not extra_note else f"{new_status}; {extra_note}"
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            repository_id=assertion.repository_id,
            matter_id=assertion.matter_id,
            assertion_id=assertion.id,
            assertion_revision_id=revision.id if revision else None,
            previous_value=previous_status,
            new_value=new_value,
        )
    )


def _apply_decision(db: Session, user_id: str, assertion: Assertion, new_status: str) -> None:
    assertion.status = new_status
    assertion.reviewed_by = user_id
    now = datetime.now(timezone.utc)
    assertion.reviewed_at = now
    assertion.updated_at = now
    db.add(assertion)


def _serialize(assertion: Assertion) -> dict:
    return {
        "id": assertion.id,
        "matter_id": assertion.matter_id,
        "repository_id": assertion.repository_id,
        "status": assertion.status,
        "reviewed_by": assertion.reviewed_by,
        "reviewed_at": assertion.reviewed_at.isoformat() if assertion.reviewed_at else None,
        "current_revision_number": assertion.current_revision_number,
        "superseded_by_assertion_id": assertion.superseded_by_assertion_id,
    }


# --- Routes -----------------------------------------------------------------


@router.post("/{assertion_id}/accept")
def accept_assertion(
    assertion_id: str,
    body: AcceptBody | None = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(db, assertion_id)
    _require_permission(db, user_id, assertion, "assertion:accept")

    justification = body.acceptance_justification if body else None
    if not _has_evidence(db, assertion) and not justification:
        raise HTTPException(
            status_code=422,
            detail=(
                "unsupported assertion (no evidence attached) cannot be accepted "
                "without a recorded acceptance_justification"
            ),
        )

    previous_status = assertion.status
    _apply_decision(db, user_id, assertion, "accepted")
    _record_decision(
        db,
        actor_user_id=user_id,
        event_type="assertion.accept",
        assertion=assertion,
        previous_status=previous_status,
        new_status="accepted",
        extra_note=f"acceptance_justification={justification}" if justification else None,
    )
    db.commit()
    db.refresh(assertion)
    return _serialize(assertion)


@router.post("/{assertion_id}/reject")
def reject_assertion(
    assertion_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(db, assertion_id)
    _require_permission(db, user_id, assertion, "assertion:reject")

    previous_status = assertion.status
    _apply_decision(db, user_id, assertion, "rejected")
    _record_decision(
        db,
        actor_user_id=user_id,
        event_type="assertion.reject",
        assertion=assertion,
        previous_status=previous_status,
        new_status="rejected",
    )
    db.commit()
    db.refresh(assertion)
    return _serialize(assertion)


@router.post("/{assertion_id}/dispute")
def dispute_assertion(
    assertion_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(db, assertion_id)
    _require_permission(db, user_id, assertion, "assertion:dispute")

    previous_status = assertion.status
    _apply_decision(db, user_id, assertion, "disputed")
    _record_decision(
        db,
        actor_user_id=user_id,
        event_type="assertion.dispute",
        assertion=assertion,
        previous_status=previous_status,
        new_status="disputed",
    )
    db.commit()
    db.refresh(assertion)
    return _serialize(assertion)


@router.post("/{assertion_id}/request-revision")
def request_revision(
    assertion_id: str,
    body: RequestRevisionBody | None = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(db, assertion_id)
    # "Return it to the author with comments" is a Reviewer capability
    # (spec §10); gated on the general `assertion:review` permission since
    # the spec's permission list has no dedicated request-revision entry.
    _require_permission(db, user_id, assertion, "assertion:review")

    comment_text = body.comment if body else None
    previous_status = assertion.status
    _apply_decision(db, user_id, assertion, "revision_requested")

    if comment_text:
        now = datetime.now(timezone.utc)
        db.add(
            AssertionComment(
                assertion_id=assertion.id,
                user_id=user_id,
                comment_text=comment_text,
                created_at=now,
                updated_at=now,
            )
        )

    _record_decision(
        db,
        actor_user_id=user_id,
        event_type="assertion.request_revision",
        assertion=assertion,
        previous_status=previous_status,
        new_status="revision_requested",
        extra_note=f"comment={comment_text}" if comment_text else None,
    )
    db.commit()
    db.refresh(assertion)
    return _serialize(assertion)


@router.post("/{assertion_id}/supersede")
def supersede_assertion(
    assertion_id: str,
    body: SupersedeBody,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(db, assertion_id)
    _require_permission(db, user_id, assertion, "assertion:review")

    successor = db.get(Assertion, body.superseded_by_assertion_id)
    if successor is None:
        raise HTTPException(status_code=404, detail="superseding assertion not found")
    if successor.matter_id != assertion.matter_id:
        raise HTTPException(
            status_code=422, detail="superseding assertion must belong to the same matter"
        )

    previous_status = assertion.status
    assertion.superseded_by_assertion_id = successor.id
    _apply_decision(db, user_id, assertion, "superseded")
    _record_decision(
        db,
        actor_user_id=user_id,
        event_type="assertion.supersede",
        assertion=assertion,
        previous_status=previous_status,
        new_status="superseded",
        extra_note=f"superseded_by_assertion_id={successor.id}",
    )
    db.commit()
    db.refresh(assertion)
    return _serialize(assertion)
