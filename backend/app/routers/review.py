"""Review workflow router (Developer track B4).

Implements the "Review" API surface from spec §13:

    POST /api/v1/assertions/{assertion_id}/accept
    POST /api/v1/assertions/{assertion_id}/reject
    POST /api/v1/assertions/{assertion_id}/dispute
    POST /api/v1/assertions/{assertion_id}/request-revision
    POST /api/v1/assertions/{assertion_id}/supersede

Business rules encoded here (spec §2/§3/§10/§12/§13/§16, sprint gates
G5/G6/G8/G10; the 2026-11-16 spec addendum "Review decision rules"):

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
- Reviving a `rejected` assertion (accept, dispute, request revision)
  re-applies the exact-duplicate rule, as submitting a draft does: if an
  identical live assertion was proposed meanwhile, the decision is a 409
  naming it (`existing_assertion_id`), checked again under the matter's
  write lock.
- Every decision takes the matter's write lock after its unlocked checks
  and re-reads the assertion (reviews authoring:2, workflow:0, workflow:2).
  It stands only on the status and revision this request checked: if
  another decision or edit committed meanwhile, it is refused with 409.
  What else it depends on is read under the lock too -- the evidence an
  accept without justification needs, the successor of a supersede -- so
  a concurrent evidence removal or a crossing supersede cannot slip
  between the check and the write.
- The write is a conditional UPDATE on the status and revision this
  request checked, so a concurrent decision or edit that lands between
  the checks and the write is refused with 409 rather than overwritten.
- An assertion without supporting-role evidence (`evidence_status` other
  than "evidenced", the classification the assertion API exposes) cannot
  be accepted unless the request records a non-blank
  `acceptance_justification`.
- Supersede refuses the assertion itself, a successor from another
  matter, a successor that is a draft or withdrawn, rejected or
  superseded, and any link that would close a supersede cycle, checked
  on the committed rows while the write lock is held.
- Review text (the request-revision comment, the acceptance
  justification) gets the same length cap and sanitizer as every other
  stored text; the comment keeps its raw text in `comment_text_raw`, and
  the audit log only ever holds the sanitized form.
- A review decision records which assertion + revision was reviewed
  (`reviewed_by`, `reviewed_at`, and the current revision's id on the
  audit event this router writes), with a correlation id shared by every
  audit row one request writes.
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

import uuid
from collections.abc import Iterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.assertion_revision import AssertionRevision
from app.models.matter_role import MatterRole
from app.routers.assertions import (
    DuplicateScan,
    _duplicate_conflict,
    _evidence_status,
    _serialize_assertion,
    recheck_duplicate,
    scan_for_duplicate,
)
from app.services.audit import new_correlation_id, record_audit_event
from app.services.duplicates import ENDED_STATUSES
from app.services.permissions import has_permission
from app.services.validation import ValidationError, sanitize_for_storage, validate_text_length
from app.services.write_lock import lock_assertion_writes

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


_CHANGED_MEANWHILE = (
    "assertion was changed by another request; reload it and review the current revision"
)


def _scan_revival(db: Session, assertion: Assertion, new_status: str) -> DuplicateScan | None:
    """409 when the decision would revive an ended (rejected) assertion next
    to an identical live one; else the scan for `_lock_and_recheck`.

    The exact-duplicate rule (spec section 8) lets an ended assertion's
    proposition be proposed again, so an identical live assertion may exist
    by now. Accepting, disputing or returning the rejected one would then
    leave two live copies, so this applies the rule that submitting a draft
    applies: here against the whole matter, and again under the write lock
    against what was committed since (review authoring:3).
    """
    if assertion.status not in ENDED_STATUSES or new_status in ENDED_STATUSES:
        return None
    blocker, scan = scan_for_duplicate(
        db, assertion.matter_id, assertion.proposition,
        owner_user_id=assertion.author_user_id, exclude_id=assertion.id, submitting=True,
    )
    if blocker is not None:
        raise _duplicate_conflict(blocker)
    return scan


def _lock_and_recheck(
    db: Session, assertion: Assertion, body: DecisionBody | None, scan: DuplicateScan | None
) -> None:
    """Take the matter's write lock, held until the decision commits, and
    re-read `assertion`.

    The decision stands only on the status and revision this request
    checked: an edit or another decision committed since is a 409, never
    overwritten (nor re-validated and decided on unseen). A revival is
    re-checked for an identical live assertion committed since `scan`. A
    refusal rolls back, releasing the lock.
    """
    checked = (assertion.status, assertion.current_revision_number)
    lock_assertion_writes(db, assertion.matter_id)
    db.refresh(assertion)
    try:
        _require_expected_revision(assertion, body)
        if (assertion.status, assertion.current_revision_number) != checked:
            raise HTTPException(status_code=409, detail=_CHANGED_MEANWHILE)
        if scan is not None:
            blocker = recheck_duplicate(db, scan, assertion.proposition)
            if blocker is not None:
                raise _duplicate_conflict(blocker)
    except HTTPException:
        db.rollback()
        raise


def _sanitized_text(raw: str | None, *, label: str) -> str | None:
    """Length-check `raw` (422) and return its sanitized form, or None when
    nothing but markup and whitespace was submitted.

    Same rules as every other stored text field: the cap applies to the
    text as submitted (`validate_text_length`, gate G4) and active markup
    is neutralized by `sanitize_for_storage` (spec §7, gate G10).
    """
    if raw is None:
        return None
    try:
        validate_text_length(raw, label=label)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    sanitized = sanitize_for_storage(raw)
    return sanitized if sanitized.strip() else None


def _validated_successor(db: Session, assertion: Assertion, successor_id: str) -> Assertion:
    """Return the superseding assertion, or raise 404/422 if it cannot be one.

    Every row is read from the database, not from the session's identity
    map, so the check run under the write lock sees what was committed by
    then (review workflow:0)."""
    if successor_id == assertion.id:
        raise HTTPException(status_code=422, detail="an assertion cannot supersede itself")
    successor = db.get(Assertion, successor_id, populate_existing=True)
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
        next_row = db.get(Assertion, link, populate_existing=True)
        link = next_row.superseded_by_assertion_id if next_row is not None else None
    return successor


def _current_revision(db: Session, assertion: Assertion) -> AssertionRevision | None:
    return db.execute(
        select(AssertionRevision).where(
            AssertionRevision.assertion_id == assertion.id,
            AssertionRevision.revision_number == assertion.current_revision_number,
        )
    ).scalar_one_or_none()


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
        raise HTTPException(status_code=409, detail=_CHANGED_MEANWHILE)


def _record_decision(
    db: Session,
    *,
    actor_user_id: str,
    event_type: str,
    assertion: Assertion,
    previous_status: str,
    new_status: str,
    correlation_id: str,
    extra_note: str | None = None,
) -> None:
    """Write one audit_events row for a review decision via
    `app.services.audit` (spec §16: actor, timestamp, matter, assertion,
    reviewed revision, before/after and a correlation id). `extra_note`
    only ever carries sanitized text or ids.
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
        correlation_id=correlation_id,
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
    comment: tuple[str, str] | None = None,
) -> dict:
    """Apply an already-validated decision, audit it, commit, and return
    the full assertion. `comment` is `(sanitized_text, raw_text)` for the
    request-revision comment, stored like every other comment."""
    previous_status = assertion.status
    correlation_id = new_correlation_id()
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
        correlation_id=correlation_id,
        extra_note=extra_note,
    )
    if comment is not None:
        now = datetime.now(timezone.utc)
        comment_row = AssertionComment(
            id=str(uuid.uuid4()),
            assertion_id=assertion.id,
            user_id=user_id,
            comment_text=comment[0],
            comment_text_raw=comment[1],
            created_at=now,
            updated_at=now,
        )
        db.add(comment_row)
        record_audit_event(
            db,
            actor_user_id=user_id,
            event_type="comment_created",
            repository_id=assertion.repository_id,
            matter_id=assertion.matter_id,
            assertion_id=assertion.id,
            new_value=comment_row.id,
            correlation_id=correlation_id,
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
    scan = _scan_revival(db, assertion, "accepted")

    justification = _sanitized_text(
        body.acceptance_justification if body else None, label="acceptance_justification"
    )
    justification = justification.strip() if justification else None
    # authoring:2 / workflow:2: the evidence is read under the lock the
    # evidence routes take, so a removal of the last supporting span either
    # commits first (this accept then needs a justification) or finds the
    # assertion accepted and is refused.
    _lock_and_recheck(db, assertion, body, scan)
    if justification is None and _evidence_status(db, assertion.id) != "evidenced":
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=(
                "unsupported assertion (no supporting evidence attached) cannot be accepted "
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
    _lock_and_recheck(db, assertion, body, _scan_revival(db, assertion, "rejected"))
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
    _lock_and_recheck(db, assertion, body, _scan_revival(db, assertion, "disputed"))
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
    scan = _scan_revival(db, assertion, "revision_requested")

    raw_comment = body.comment if body else None
    comment_text = _sanitized_text(raw_comment, label="comment")
    _lock_and_recheck(db, assertion, body, scan)
    return _decide(
        db,
        user_id,
        assertion,
        "revision_requested",
        event_type="assertion.request_revision",
        extra_note=f"comment={comment_text}" if comment_text else None,
        comment=(comment_text, raw_comment) if comment_text else None,
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
    _validated_successor(db, assertion, body.superseded_by_assertion_id)

    # workflow:0: validated again on what is committed once the lock is held,
    # so of two crossing supersedes (A by B, B by A) the second finds its
    # successor superseded (422) instead of closing a cycle.
    _lock_and_recheck(db, assertion, body, None)
    try:
        successor = _validated_successor(db, assertion, body.superseded_by_assertion_id)
    except HTTPException:
        db.rollback()
        raise
    return _decide(
        db,
        user_id,
        assertion,
        "superseded",
        event_type="assertion.supersede",
        extra_note=f"superseded_by_assertion_id={successor.id}",
        superseded_by_assertion_id=successor.id,
    )
