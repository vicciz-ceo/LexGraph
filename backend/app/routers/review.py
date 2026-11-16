"""Review workflow router (Developer track B4).

Implements the "Review" API surface from spec §13:

    POST /api/v1/assertions/{assertion_id}/accept
    POST /api/v1/assertions/{assertion_id}/reject
    POST /api/v1/assertions/{assertion_id}/dispute
    POST /api/v1/assertions/{assertion_id}/request-revision
    POST /api/v1/assertions/{assertion_id}/supersede

Business rules encoded here (spec §3/§10/§12/§13/§16, sprint gates
G5/G6/G8; the 2026-11-16 spec addendum "Review decision rules"):

- Only a role granted the relevant `assertion:*` permission (reviewer or
  admin) may change review status; a role with no matter access at all
  (no matter_roles row) is treated as having no permissions.
- Every decision body may carry `expected_revision_number`, the revision
  the reviewer looked at. A stale value is refused with 409 before
  anything changes, so a decision always applies to the revision that
  was reviewed. Checks run in the order 404 -> 403 -> 409 -> 422.
- A decision is only recorded from a reviewable status: never on an
  unsubmitted `draft`, a `withdrawn` assertion or a `superseded` one, and
  never as a repeat of the current status (409). Moving between the
  reviewed statuses stays open (contested rulings, re-review).
- The write is a conditional UPDATE on the status and revision this
  request checked, so a concurrent decision or edit that lands between
  the checks and the write is refused with 409 rather than overwritten.
- An "unsupported" assertion (zero `assertion_evidence` rows) cannot be
  accepted unless the request records an `acceptance_justification`.
- Supersede refuses the assertion itself, a successor from another
  matter, a successor that is a draft or withdrawn, rejected or
  superseded, and any link that would close a supersede cycle.
- A review decision records which assertion + revision was reviewed
  (`reviewed_by`, `reviewed_at`, and the current revision's id on the
  audit event this router writes, which carries a correlation id).
- Every route returns the full assertion, like the other assertion
  mutation routes.
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
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_revision import AssertionRevision
from app.models.matter_role import MatterRole
from app.routers.assertions import _serialize_assertion
from app.services.audit import record_audit_event
from app.services.permissions import has_permission

router = APIRouter(prefix="/api/v1/assertions", tags=["review"])

# Statuses a review decision may be recorded from. `draft` has never been
# submitted for review, `withdrawn` was retracted by its author, and
# `superseded` is terminal: it points at its successor through
# `superseded_by_assertion_id`. Mirrors the source-status preconditions of
# the sibling submit/withdraw routes in `app/routers/assertions.py`.
DECIDABLE_STATUSES = frozenset(
    {"proposed", "revision_requested", "disputed", "accepted", "rejected"}
)

# Statuses an assertion may hold to supersede another one: submitted and
# still live. A rejected, withdrawn or never-submitted assertion replaces
# nothing, and refusing an already-superseded successor keeps every
# supersede chain pointing at a current assertion.
SUCCESSOR_STATUSES = frozenset({"proposed", "revision_requested", "disputed", "accepted"})

_ACTION_VERB = {
    "accepted": "accept",
    "rejected": "reject",
    "disputed": "dispute",
    "revision_requested": "request revision of",
    "superseded": "supersede",
}


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


class DecisionBody(BaseModel):
    """Fields every review decision accepts.

    `expected_revision_number` is the revision the reviewer was looking at.
    It is optional, as on PATCH; when supplied and no longer the current
    revision the decision is refused with 409 before anything changes.
    """

    expected_revision_number: int | None = Field(default=None, ge=1)


class AcceptBody(DecisionBody):
    acceptance_justification: str | None = None


class RequestRevisionBody(DecisionBody):
    comment: str | None = None


class SupersedeBody(DecisionBody):
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


def _require_expected_revision(assertion: Assertion, body: DecisionBody | None) -> None:
    """409 when the reviewer decided on a revision that is no longer current."""
    expected = body.expected_revision_number if body is not None else None
    if expected is not None and expected != assertion.current_revision_number:
        raise HTTPException(
            status_code=409,
            detail="assertion has been modified since expected_revision_number",
        )


def _require_decidable(assertion: Assertion, new_status: str) -> None:
    """409 unless a review decision may move `assertion` to `new_status`."""
    if assertion.status not in DECIDABLE_STATUSES:
        hint = "; it must be submitted for review first" if assertion.status == "draft" else ""
        raise HTTPException(
            status_code=409,
            detail=(
                f"cannot {_ACTION_VERB[new_status]} an assertion in status "
                f"'{assertion.status}'{hint}"
            ),
        )
    if assertion.status == new_status:
        raise HTTPException(status_code=409, detail=f"assertion is already '{new_status}'")


def _validated_successor(db: Session, assertion: Assertion, successor_id: str) -> Assertion:
    """Return the superseding assertion, or raise 404/422 if it cannot be one."""
    if successor_id == assertion.id:
        raise HTTPException(status_code=422, detail="an assertion cannot supersede itself")
    successor = db.get(Assertion, successor_id)
    if successor is None:
        raise HTTPException(status_code=404, detail="superseding assertion not found")
    if successor.matter_id != assertion.matter_id:
        raise HTTPException(
            status_code=422, detail="superseding assertion must belong to the same matter"
        )
    if successor.status not in SUCCESSOR_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                "superseding assertion must be submitted and not rejected, withdrawn or "
                f"superseded (it is '{successor.status}')"
            ),
        )
    # Follow the successor's own supersede links (rows decided before this
    # router enforced statuses can carry one without being superseded):
    # reaching `assertion` again would close a cycle.
    seen = {successor.id}
    link = successor.superseded_by_assertion_id
    while link is not None and link not in seen:
        if link == assertion.id:
            raise HTTPException(
                status_code=422,
                detail="superseding assertion leads back to this assertion (supersede cycle)",
            )
        seen.add(link)
        next_row = db.get(Assertion, link)
        link = next_row.superseded_by_assertion_id if next_row is not None else None
    return successor


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


def _apply_decision(
    db: Session,
    user_id: str,
    assertion: Assertion,
    new_status: str,
    *,
    superseded_by_assertion_id: str | None = None,
) -> None:
    """Write the decision as a compare-and-swap on status and revision.

    The row only changes while it still carries the status and revision
    this request checked, so a concurrent decision (a double-click, a
    second reviewer) or an edit landing between the checks and this write
    is refused with 409 instead of being overwritten or accepted unread.
    `superseded_by_assertion_id` is set by a supersede and cleared by every
    other decision: the link exists exactly while the assertion is
    superseded. The ORM object is left untouched; callers refresh it after
    commit.
    """
    now = datetime.now(timezone.utc)
    result = db.execute(
        update(Assertion)
        .where(
            Assertion.id == assertion.id,
            Assertion.status == assertion.status,
            Assertion.current_revision_number == assertion.current_revision_number,
        )
        .values(
            status=new_status,
            reviewed_by=user_id,
            reviewed_at=now,
            updated_at=now,
            superseded_by_assertion_id=superseded_by_assertion_id,
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "assertion was changed by another request; reload it and review the "
                "current revision"
            ),
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
    """Write one audit_events row for a review decision via
    `app.services.audit` (spec §16: actor, timestamp, matter, assertion,
    reviewed revision, before/after and a correlation id).
    """
    revision = _current_revision(db, assertion)
    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        event_type=event_type,
        repository_id=assertion.repository_id,
        matter_id=assertion.matter_id,
        assertion_id=assertion.id,
        assertion_revision_id=revision.id if revision else None,
        previous_value=previous_status,
        new_value=new_status if not extra_note else f"{new_status}; {extra_note}",
    )


def _decide(
    db: Session,
    user_id: str,
    assertion: Assertion,
    new_status: str,
    *,
    event_type: str,
    extra_note: str | None = None,
    superseded_by_assertion_id: str | None = None,
    comment_text: str | None = None,
) -> dict:
    """Apply an already-validated decision, audit it, commit, and return
    the full assertion."""
    previous_status = assertion.status
    _apply_decision(
        db, user_id, assertion, new_status, superseded_by_assertion_id=superseded_by_assertion_id
    )
    _record_decision(
        db,
        actor_user_id=user_id,
        event_type=event_type,
        assertion=assertion,
        previous_status=previous_status,
        new_status=new_status,
        extra_note=extra_note,
    )
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
    db.commit()
    db.refresh(assertion)
    return _serialize_assertion(db, assertion)


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
    _require_expected_revision(assertion, body)
    _require_decidable(assertion, "accepted")

    justification = body.acceptance_justification if body else None
    if not _has_evidence(db, assertion) and not justification:
        raise HTTPException(
            status_code=422,
            detail=(
                "unsupported assertion (no evidence attached) cannot be accepted "
                "without a recorded acceptance_justification"
            ),
        )

    return _decide(
        db,
        user_id,
        assertion,
        "accepted",
        event_type="assertion.accept",
        extra_note=f"acceptance_justification={justification}" if justification else None,
    )


@router.post("/{assertion_id}/reject")
def reject_assertion(
    assertion_id: str,
    body: DecisionBody | None = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(db, assertion_id)
    _require_permission(db, user_id, assertion, "assertion:reject")
    _require_expected_revision(assertion, body)
    _require_decidable(assertion, "rejected")
    return _decide(db, user_id, assertion, "rejected", event_type="assertion.reject")


@router.post("/{assertion_id}/dispute")
def dispute_assertion(
    assertion_id: str,
    body: DecisionBody | None = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(db, assertion_id)
    _require_permission(db, user_id, assertion, "assertion:dispute")
    _require_expected_revision(assertion, body)
    _require_decidable(assertion, "disputed")
    return _decide(db, user_id, assertion, "disputed", event_type="assertion.dispute")


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
    _require_expected_revision(assertion, body)
    _require_decidable(assertion, "revision_requested")

    comment_text = body.comment if body else None
    return _decide(
        db,
        user_id,
        assertion,
        "revision_requested",
        event_type="assertion.request_revision",
        extra_note=f"comment={comment_text}" if comment_text else None,
        comment_text=comment_text,
    )


@router.post("/{assertion_id}/supersede")
def supersede_assertion(
    assertion_id: str,
    body: SupersedeBody,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(db, assertion_id)
    _require_permission(db, user_id, assertion, "assertion:review")
    _require_expected_revision(assertion, body)
    _require_decidable(assertion, "superseded")

    successor = _validated_successor(db, assertion, body.superseded_by_assertion_id)
    return _decide(
        db,
        user_id,
        assertion,
        "superseded",
        event_type="assertion.supersede",
        extra_note=f"superseded_by_assertion_id={successor.id}",
        superseded_by_assertion_id=successor.id,
    )
