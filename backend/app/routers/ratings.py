"""Rating routes (item B2).

Implements the rating-owned paths from spec §13:

    PUT    /api/v1/assertions/{assertion_id}/revisions/{revision_number}/rating
    GET    /api/v1/assertions/{assertion_id}/revisions/{revision_number}/rating
    DELETE /api/v1/assertions/{assertion_id}/revisions/{revision_number}/rating
    GET    /api/v1/assertions/{assertion_id}/revisions/{revision_number}/ratings/summary
    GET    /api/v1/assertions/{assertion_id}/revisions/{revision_number}/ratings

Ratings are revision-scoped (ruling R5): `AssertionRating` carries both
`assertion_id` and `assertion_revision_id`, with a unique(user_id,
assertion_revision_id) constraint (see `app/models/assertion_rating.py`,
frozen per R8) -- one current rating per user per revision; prior-revision
ratings are preserved, never auto-copied.

The path segment is the revision *number* (`AssertionRevision.
revision_number`), not the revision's UUID `id` -- this matches every
caller in the test suite (`.../revisions/1/rating`) and B3's
`app/audit_middleware.py::_RATING_RE`, which only recognizes digits there
and fires `rating_created`/`rating_changed` audit rows automatically off
of a successful PUT. This router does NOT duplicate that: the PUT handler
below emits no audit event of its own. DELETE is not matched by that
middleware (audit rows are only emitted for PUT), so the delete handler
below calls B3's `app.services.audit.record_audit_event` directly (R7/R9:
a call-site owned by this router, since the mutation lives in this
router's own file).

Permission checks reuse B4's already-merged, pure `app.services.
permissions.has_permission` matrix (`assertion:rate` for
mutating/removing a rating, `assertion:view` for read access,
`assertion:view_rating_rationales` to gate rationale text in the list
endpoint) -- this is a stable, side-effect-free shared service, not a
call-site inside another track's router, so reading it here does not
violate R9's "don't reach into another track's in-progress work" (B4 is
dev-complete and merged).

DB access is via a small local dependency reading `request.app.state.
session_factory`, mirroring `app/routers/assertions.py` (no shared deps
module, per sprint-harness instruction).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.assertion import Assertion
from app.models.assertion_rating import AssertionRating
from app.models.assertion_revision import AssertionRevision
from app.models.matter_role import MatterRole
from app.services.audit import record_audit_event
from app.services.permissions import has_permission
from app.services.ratings import compute_rating_summary
from app.services.validation import sanitize_for_storage

router = APIRouter(prefix="/api/v1/assertions", tags=["ratings"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- DB session dependency (local to this router) --------------------------


def get_session(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


# --- Auth dependency (local to this router) --------------------------------


def get_current_user_id(request: Request) -> str:
    try:
        return get_bearer_user_id(request.headers.get("Authorization"))
    except AuthHeaderError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


# --- Request/response schemas -----------------------------------------------


class RatingIn(BaseModel):
    strength: int = Field(ge=1, le=5)
    rationale: str | None = None


# --- Lookup + permission helpers (owned by this track; no shared deps) -----


def _get_assertion_or_404(session: Session, assertion_id: str) -> Assertion:
    assertion = session.get(Assertion, assertion_id)
    if assertion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assertion not found")
    return assertion


def _get_revision_or_404(
    session: Session, assertion_id: str, revision_number: int
) -> AssertionRevision:
    revision = session.execute(
        select(AssertionRevision).where(
            AssertionRevision.assertion_id == assertion_id,
            AssertionRevision.revision_number == revision_number,
        )
    ).scalar_one_or_none()
    if revision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="revision not found")
    return revision


def _matter_role(session: Session, user_id: str, matter_id: str) -> str | None:
    return session.execute(
        select(MatterRole.role).where(
            MatterRole.user_id == user_id, MatterRole.matter_id == matter_id
        )
    ).scalar_one_or_none()


def _require_permission(
    session: Session, user_id: str, matter_id: str, permission: str
) -> str:
    role = _matter_role(session, user_id, matter_id)
    if role is None or not has_permission(role, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not permitted")
    return role


def _get_own_rating(
    session: Session, revision_id: str, user_id: str
) -> AssertionRating | None:
    return session.execute(
        select(AssertionRating).where(
            AssertionRating.assertion_revision_id == revision_id,
            AssertionRating.user_id == user_id,
        )
    ).scalar_one_or_none()


def _serialize_rating(r: AssertionRating) -> dict:
    return {
        "id": r.id,
        "assertion_id": r.assertion_id,
        "assertion_revision_id": r.assertion_revision_id,
        "user_id": r.user_id,
        "strength": r.strength,
        "rationale": r.rationale,
        # Track A, item A4 (issue #2, gate G1): the author's exact
        # submitted bytes, independent of whatever sanitize_for_storage
        # did to `rationale` above. Same rationale-visibility permission
        # gate as `rationale` (see list_ratings).
        "rationale_raw": r.rationale_raw,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


# --- Routes ------------------------------------------------------------------


@router.put("/{assertion_id}/revisions/{revision_number}/rating")
def put_rating(
    assertion_id: str,
    revision_number: int,
    body: RatingIn,
    response: Response,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    revision = _get_revision_or_404(session, assertion_id, revision_number)
    _require_permission(session, user_id, assertion.matter_id, "assertion:rate")

    existing = _get_own_rating(session, revision.id, user_id)
    now = _now()
    # B7: rationale is user-submitted free text (spec §7/G10) -- neutralize
    # active markup before storage, same as B5's proposition handling.
    rationale = sanitize_for_storage(body.rationale)

    if existing is not None:
        existing.strength = body.strength
        existing.rationale = rationale
        existing.rationale_raw = body.rationale
        existing.updated_at = now
        session.commit()
        session.refresh(existing)
        response.status_code = status.HTTP_200_OK
        return _serialize_rating(existing)

    rating = AssertionRating(
        id=str(uuid.uuid4()),
        organization_id=assertion.organization_id,
        repository_id=assertion.repository_id,
        matter_id=assertion.matter_id,
        assertion_id=assertion.id,
        assertion_revision_id=revision.id,
        user_id=user_id,
        strength=body.strength,
        rationale=rationale,
        rationale_raw=body.rationale,
        created_at=now,
        updated_at=now,
    )
    session.add(rating)
    session.commit()
    session.refresh(rating)
    response.status_code = status.HTTP_201_CREATED
    return _serialize_rating(rating)


@router.get("/{assertion_id}/revisions/{revision_number}/rating")
def get_own_rating(
    assertion_id: str,
    revision_number: int,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    revision = _get_revision_or_404(session, assertion_id, revision_number)
    _require_permission(session, user_id, assertion.matter_id, "assertion:view")

    rating = _get_own_rating(session, revision.id, user_id)
    if rating is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no rating from this user")
    return _serialize_rating(rating)


@router.delete(
    "/{assertion_id}/revisions/{revision_number}/rating",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_rating(
    assertion_id: str,
    revision_number: int,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> None:
    assertion = _get_assertion_or_404(session, assertion_id)
    revision = _get_revision_or_404(session, assertion_id, revision_number)
    _require_permission(session, user_id, assertion.matter_id, "assertion:rate")

    rating = _get_own_rating(session, revision.id, user_id)
    if rating is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no rating to remove")

    previous_strength = str(rating.strength)
    session.delete(rating)

    # The audit middleware (app/audit_middleware.py, B3) only recognizes PUT
    # on this path -- DELETE is deliberately unmatched there, so this is the
    # one call-site this track owns for the removal audit row (spec: "Removing
    # a rating must create an audit event").
    record_audit_event(
        session,
        actor_user_id=user_id,
        event_type="rating_removed",
        repository_id=assertion.repository_id,
        matter_id=assertion.matter_id,
        assertion_id=assertion.id,
        assertion_revision_id=revision.id,
        previous_value=previous_strength,
        new_value=None,
    )
    session.commit()
    return None


@router.get("/{assertion_id}/revisions/{revision_number}/ratings/summary")
def get_rating_summary(
    assertion_id: str,
    revision_number: int,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    revision = _get_revision_or_404(session, assertion_id, revision_number)
    _require_permission(session, user_id, assertion.matter_id, "assertion:view")

    ratings = (
        session.execute(
            select(AssertionRating).where(AssertionRating.assertion_revision_id == revision.id)
        )
        .scalars()
        .all()
    )
    strengths = [r.strength for r in ratings]
    summary = compute_rating_summary(strengths)

    rationale_count = sum(1 for r in ratings if r.rationale)

    own_rating = next((r for r in ratings if r.user_id == user_id), None)
    current_user_rating = (
        {
            "strength": own_rating.strength,
            "rationale": own_rating.rationale,
            "updated_at": own_rating.updated_at,
        }
        if own_rating is not None
        else None
    )

    if summary is None:
        body = {
            "count": 0,
            "average": None,
            "median": None,
            "distribution": {str(i): 0 for i in range(1, 6)},
        }
    else:
        body = dict(summary)

    body["assertion_id"] = assertion.id
    body["assertion_revision_id"] = revision.id
    body["current_user_rating"] = current_user_rating
    body["rationale_count"] = rationale_count
    return body


@router.get("/{assertion_id}/revisions/{revision_number}/ratings")
def list_ratings(
    assertion_id: str,
    revision_number: int,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    assertion = _get_assertion_or_404(session, assertion_id)
    revision = _get_revision_or_404(session, assertion_id, revision_number)
    role = _require_permission(session, user_id, assertion.matter_id, "assertion:view")

    can_see_rationales = has_permission(role, "assertion:view_rating_rationales")

    ratings = (
        session.execute(
            select(AssertionRating).where(AssertionRating.assertion_revision_id == revision.id)
        )
        .scalars()
        .all()
    )

    results = []
    for r in ratings:
        serialized = _serialize_rating(r)
        if not can_see_rationales and r.user_id != user_id:
            serialized["rationale"] = None
            serialized["rationale_raw"] = None
        results.append(serialized)
    return results
