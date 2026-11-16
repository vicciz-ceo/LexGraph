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
caller in the test suite (`.../revisions/1/rating`).

Audit (spec section 16, finding api:5): `rating_created` and
`rating_changed` are written by a `before_flush` hook in
`app.services.audit` from the rating row itself (previous -> new strength,
the rated revision), inside the PUT's own transaction. The PUT handler
below therefore records no rating event of its own; adding one would write
it twice. The hook does not see a deleted row's meaning, so the delete
handler records `rating_removed` with `record_audit_event` itself.

Concurrency (review listing:3): PUT and DELETE read the caller's rating and
then insert, update or delete it. Two requests from one user (a double
submit, two tabs, an agent's retry) used to read the same state: two first
ratings both inserted, and the second failed the unique (user, revision)
constraint with a 500; an update racing a removal updated a row that no
longer existed, another 500. Both routes now take the database write lock
(`app.services.write_lock`) before they read the rating, so they apply one
after the other and answer as they would in sequence: 201 for the first
rating, 200 for every later one, 204 and then 404 for two removals.

Finding api:30 confirmed the revision number as the deliberate design (it
is also what `current_revision_number`, `expected_revision_number` and the
history feed's `assertion_revision_number` use), so spec §13 was corrected
to `{revision_number}`; a revision UUID in that segment stays a 422. So
that a client holding any rating payload can build these routes, every
rating row and summary carries both `assertion_revision_id` and
`assertion_revision_number`.

PUT body (spec §4, §18; findings api:22 and review:7): `strength` must be
a JSON integer 1-5 -- booleans, numeric strings and floats are rejected,
not coerced. `rationale` omitted keeps the stored rationale and its exact
raw text (a new rating has none), so a strength-only update never rewrites
`rationale_raw`; `null`, `""` or whitespace-only text removes it; any
other string replaces it (`rationale_raw` = the exact text, `rationale` =
its sanitized form).

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
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.assertion import Assertion
from app.models.assertion_rating import AssertionRating
from app.models.assertion_revision import AssertionRevision
from app.models.matter_role import MatterRole
from app.services.audit import record_audit_event
from app.services.permissions import has_permission
from app.services.ratings import compute_rating_summary
from app.services.validation import ValidationError, sanitize_for_storage, validate_text_length
from app.services.write_lock import lock_assertion_writes

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
    # Strict (finding api:22, spec §18 "Non-integer ratings are rejected"):
    # lax mode would store JSON `true` as 1 and `"4"` or `4.0` as 4.
    strength: int = Field(strict=True, ge=1, le=5)
    # Omitted = keep the stored rationale; see the module docstring.
    rationale: str | None = None


# --- Lookup + permission helpers (owned by this track; no shared deps) -----


def _get_assertion_or_404(session: Session, assertion_id: str) -> Assertion:
    assertion = session.get(Assertion, assertion_id)
    if assertion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assertion not found")
    return assertion


# `AssertionRevision.revision_number` is an `Integer` column (32-bit on
# PostgreSQL); revisions are numbered from 1.
_MAX_REVISION_NUMBER = 2**31 - 1


def _get_revision_or_404(
    session: Session, assertion_id: str, revision_number: int
) -> AssertionRevision:
    # Audit finding api:20: a number no revision can have is simply not found --
    # never bound into the query, where SQLite raises OverflowError (a 500).
    if not 1 <= revision_number <= _MAX_REVISION_NUMBER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="revision not found")
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


def _has_readable_text(rationale: str | None) -> bool:
    return bool(rationale and rationale.strip())


def _serialize_rating(r: AssertionRating, revision_number: int) -> dict:
    return {
        "id": r.id,
        "assertion_id": r.assertion_id,
        "assertion_revision_id": r.assertion_revision_id,
        "assertion_revision_number": revision_number,
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

    # Track A, item A8 (issue #2 sub-item, gate G4): length cap checked
    # against the raw submitted text, before sanitization.
    try:
        validate_text_length(body.rationale, label="rationale")
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail=str(exc)
        ) from exc
    try:
        # JSON can escape a lone UTF-16 surrogate ("\ud800") that no UTF-8
        # database can store; the write used to fail with a 500.
        (body.rationale or "").encode("utf-8")
    except UnicodeEncodeError as exc:
        raise HTTPException(
            status_code=422, detail="rationale contains an unpaired surrogate character"
        ) from exc

    # listing:3: read the caller's rating under the write lock (held until
    # the commit), so a concurrent PUT or DELETE of it is applied before or
    # after this one, never in between.
    lock_assertion_writes(session, assertion.matter_id)
    existing = _get_own_rating(session, revision.id, user_id)
    now = _now()
    # Finding review:7 / spec addendum "The current rating rationale is
    # preserved when updating a rating": an omitted `rationale` keeps the
    # stored one byte-for-byte. Whitespace-only text means "no rationale".
    rationale_raw = body.rationale if _has_readable_text(body.rationale) else None
    # B7: rationale is user-submitted free text (spec §7/G10) -- neutralize
    # active markup before storage, same as B5's proposition handling.
    rationale = sanitize_for_storage(rationale_raw)

    if existing is not None:
        existing.strength = body.strength
        if "rationale" in body.model_fields_set:
            existing.rationale = rationale
            existing.rationale_raw = rationale_raw
        existing.updated_at = now
        session.commit()
        session.refresh(existing)
        response.status_code = status.HTTP_200_OK
        return _serialize_rating(existing, revision.revision_number)

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
        rationale_raw=rationale_raw,
        created_at=now,
        updated_at=now,
    )
    session.add(rating)
    session.commit()
    session.refresh(rating)
    response.status_code = status.HTTP_201_CREATED
    return _serialize_rating(rating, revision.revision_number)


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
    return _serialize_rating(rating, revision.revision_number)


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

    lock_assertion_writes(session, assertion.matter_id)  # listing:3, as in put_rating
    rating = _get_own_rating(session, revision.id, user_id)
    if rating is None:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no rating to remove")

    previous_strength = str(rating.strength)
    session.delete(rating)

    # The before_flush hook in app.services.audit writes rating_created and
    # rating_changed; the removal row is this route's own (spec: "Removing a
    # rating must create an audit event"), in the same transaction.
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

    # Spec §4 "Number of ratings containing a rationale": only rationales
    # with readable text once sanitized (not "" from markup-only input, nor
    # whitespace written before blank rationales were normalized away).
    rationale_count = sum(1 for r in ratings if _has_readable_text(r.rationale))

    own_rating = next((r for r in ratings if r.user_id == user_id), None)
    current_user_rating = (
        {
            "strength": own_rating.strength,
            "rationale": own_rating.rationale,
            # Finding review:7: the caller's own exact text, so an editor
            # can be prefilled with it rather than with the sanitized copy.
            "rationale_raw": own_rating.rationale_raw,
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
    body["assertion_revision_number"] = revision.revision_number
    body["current_user_rating"] = current_user_rating
    body["rationale_count"] = rationale_count
    # Finding ui:12 / spec §10 ("Inform users that the revised assertion has
    # not yet been rated"): ratings recorded against this assertion's earlier
    # revisions. They stay on their own revision; this only counts them.
    body["prior_revision_rating_count"] = session.scalar(
        select(func.count(AssertionRating.id))
        .join(AssertionRevision, AssertionRating.assertion_revision_id == AssertionRevision.id)
        .where(
            AssertionRating.assertion_id == assertion.id,
            AssertionRevision.assertion_id == assertion.id,
            AssertionRevision.revision_number < revision.revision_number,
        )
    ) or 0
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

    # Spec §5/§10/§12 (finding ui:16): reviewers and admins read every
    # rater's rationale; everyone else reads their own and sees `null` for
    # other raters' rationale text (strengths stay visible).
    can_see_rationales = has_permission(role, "assertion:view_rating_rationales")

    ratings = (
        session.execute(
            select(AssertionRating)
            .where(AssertionRating.assertion_revision_id == revision.id)
            .order_by(AssertionRating.created_at.asc(), AssertionRating.id.asc())
        )
        .scalars()
        .all()
    )

    results = []
    for r in ratings:
        serialized = _serialize_rating(r, revision.revision_number)
        if not can_see_rationales and r.user_id != user_id:
            serialized["rationale"] = None
            serialized["rationale_raw"] = None
        results.append(serialized)
    return results
