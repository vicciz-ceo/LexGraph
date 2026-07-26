"""Assertion CRUD, submission, evidence, and revision routes (item B1).

Implements the assertion-owned paths from spec §13:

    POST   /api/v1/assertions
    GET    /api/v1/assertions
    GET    /api/v1/assertions/{assertion_id}
    PATCH  /api/v1/assertions/{assertion_id}
    POST   /api/v1/assertions/{assertion_id}/submit
    POST   /api/v1/assertions/{assertion_id}/withdraw
    GET    /api/v1/assertions/{assertion_id}/revisions
    POST   /api/v1/assertions/{assertion_id}/revisions
    GET    /api/v1/assertions/{assertion_id}/evidence
    POST   /api/v1/assertions/{assertion_id}/evidence
    DELETE /api/v1/assertions/{assertion_id}/evidence/{evidence_id}
    GET    /api/v1/assertions/{assertion_id}/related

Review-decision routes (accept/reject/dispute/request-revision/supersede),
ratings, and comments belong to other tracks (B4, B2, B3 respectively) and
are intentionally absent here — see `app/routers/__init__.py` for
ownership.

Item B5 (this track, wave 2) extended the original B1 handlers in place
with: query-param search/sort/filter on the list endpoint (spec §17),
proposition/date/type/entity validation plus sanitization and an inline
duplicate check on create (`app/services/validation.py`,
`app/services/duplicates.py`), a matter-scope check on attached evidence,
and the new `GET .../related` route (ruling R10). B1's original handler
bodies (submit/withdraw/patch/revisions) are unchanged.

DB access is via a small local dependency reading `request.app.state.
session_factory` (per sprint-harness instruction: no shared deps module).
Permission checks are inline and owned by this track only: this file does
NOT import `app.services.permissions` (that module is a B4-owned stub
that currently raises NotImplementedError) — see ruling R9, which prefers
mechanisms fully owned by the owning track over reaching into another
track's in-progress work.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_rating import AssertionRating
from app.models.assertion_revision import AssertionRevision
from app.models.matter import Matter
from app.models.matter_role import MatterRole
from app.models.repository import Repository
from app.models.source_span import SourceSpan
from app.services.duplicates import find_related_assertions
from app.services.validation import (
    ValidationError,
    sanitize_for_storage,
    validate_assertion_type,
    validate_effective_dates,
    validate_evidence_matter_scope,
    validate_matter_scoped_entity_id,
    validate_proposition_not_empty,
    validate_text_length,
)

router = APIRouter(prefix="/api/v1/assertions", tags=["assertions"])

EVIDENCE_ROLES = (
    "supports",
    "contradicts",
    "contextualizes",
    "qualifies",
    "primary_basis",
    "secondary_basis",
)
SUPPORTING_EVIDENCE_ROLES = ("supports", "primary_basis", "secondary_basis")

_REVIEWER_ROLES = ("reviewer", "admin")


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


class EntityRef(BaseModel):
    type: str
    id: str


class EvidenceIn(BaseModel):
    source_span_id: str
    evidence_role: Literal[
        "supports",
        "contradicts",
        "contextualizes",
        "qualifies",
        "primary_basis",
        "secondary_basis",
    ]


class AssertionCreate(BaseModel):
    repository_id: str
    matter_id: str
    assertion_type: str = Field(min_length=1)
    proposition: str = Field(min_length=1)
    subject_entity: EntityRef
    object_entity: EntityRef | None = None
    jurisdiction: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    evidence: list[EvidenceIn] = Field(default_factory=list)
    explanation: str | None = None
    save_as: Literal["draft", "proposed"] = "draft"
    # B5: explicit opt-in for an assertion_type outside the controlled
    # vocabulary (spec §7 "explicitly marked as a proposed new type").
    assertion_type_is_proposed_new: bool = False


class AssertionPatch(BaseModel):
    assertion_type: str | None = Field(default=None, min_length=1)
    proposition: str | None = Field(default=None, min_length=1)
    subject_entity: EntityRef | None = None
    object_entity: EntityRef | None = None
    jurisdiction: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    revision_reason: str | None = None
    expected_revision_number: int | None = None


class EvidenceCreate(BaseModel):
    source_span_id: str
    evidence_role: Literal[
        "supports",
        "contradicts",
        "contextualizes",
        "qualifies",
        "primary_basis",
        "secondary_basis",
    ]


# --- Serialization helpers ---------------------------------------------------


def _evidence_status(session: Session, assertion_id: str) -> str:
    rows = session.execute(
        select(AssertionEvidence.evidence_role).where(
            AssertionEvidence.assertion_id == assertion_id
        )
    ).scalars().all()
    if not rows:
        return "awaiting_evidence"
    if any(role in SUPPORTING_EVIDENCE_ROLES for role in rows):
        return "evidenced"
    return "unsupported"


def _serialize_assertion(session: Session, a: Assertion) -> dict:
    current_revision = _current_revision(session, a)
    return {
        "id": a.id,
        "organization_id": a.organization_id,
        "repository_id": a.repository_id,
        "matter_id": a.matter_id,
        "assertion_type": a.assertion_type,
        "proposition": a.proposition,
        # Track A, item A2 (issue #2, gate G1): the current revision's raw,
        # byte-exact authored text -- never the (possibly lossy) sanitized
        # `proposition` column above.
        "proposition_raw": current_revision.proposition_raw if current_revision else None,
        "subject_entity": {"type": a.subject_entity_type, "id": a.subject_entity_id},
        "object_entity": (
            {"type": a.object_entity_type, "id": a.object_entity_id}
            if a.object_entity_type is not None
            else None
        ),
        "origin": a.origin,
        "status": a.status,
        "author_user_id": a.author_user_id,
        "confidence": a.confidence,
        "jurisdiction": a.jurisdiction,
        "effective_from": a.effective_from,
        "effective_to": a.effective_to,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
        "submitted_at": a.submitted_at,
        "reviewed_by": a.reviewed_by,
        "reviewed_at": a.reviewed_at,
        "superseded_by_assertion_id": a.superseded_by_assertion_id,
        "current_revision_number": a.current_revision_number,
        "evidence_status": _evidence_status(session, a.id),
    }


def _serialize_revision(r: AssertionRevision) -> dict:
    return {
        "id": r.id,
        "assertion_id": r.assertion_id,
        "revision_number": r.revision_number,
        "proposition": r.proposition,
        # Track A, item A2 (issue #2, gate G1): raw, byte-exact authored
        # text for this specific revision.
        "proposition_raw": r.proposition_raw,
        "assertion_type": r.assertion_type,
        "subject_entity": {"type": r.subject_entity_type, "id": r.subject_entity_id},
        "object_entity": (
            {"type": r.object_entity_type, "id": r.object_entity_id}
            if r.object_entity_type is not None
            else None
        ),
        "jurisdiction": r.jurisdiction,
        "effective_from": r.effective_from,
        "effective_to": r.effective_to,
        "revision_reason": r.revision_reason,
        "edited_by_user_id": r.edited_by_user_id,
        "created_at": r.created_at,
    }


def _serialize_evidence(e: AssertionEvidence) -> dict:
    return {
        "id": e.id,
        "assertion_id": e.assertion_id,
        "source_span_id": e.source_span_id,
        "evidence_role": e.evidence_role,
        "added_by_user_id": e.added_by_user_id,
        "created_at": e.created_at,
    }


def _serialize_comment_summary(c: AssertionComment) -> dict:
    return {
        "id": c.id,
        "assertion_id": c.assertion_id,
        "user_id": c.user_id,
        "parent_comment_id": c.parent_comment_id,
        "comment_text": c.comment_text,
        "comment_text_raw": c.comment_text_raw,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


# --- Evidence/comments/revisions/ratings read helpers (GET detail, B5) -----
#
# These back the `evidence`/`ratings_summary`/`comments`/`revision_history`
# keys on GET /assertions/{id} (gate G5). Ratings are computed directly
# from `assertion_ratings` rows rather than via
# `app.services.ratings.compute_rating_summary` (B2-owned) so this read
# path stays correct regardless of that track's merge state into this
# worktree; the math mirrors spec §4/§13 exactly (unrounded mean, do not
# fabricate an aggregate when there are no ratings).


def _evidence_rows(session: Session, assertion_id: str) -> list[AssertionEvidence]:
    return (
        session.execute(
            select(AssertionEvidence).where(AssertionEvidence.assertion_id == assertion_id)
        )
        .scalars()
        .all()
    )


def _revision_history(session: Session, assertion_id: str) -> list[dict]:
    revisions = (
        session.execute(
            select(AssertionRevision)
            .where(AssertionRevision.assertion_id == assertion_id)
            .order_by(AssertionRevision.revision_number.asc())
        )
        .scalars()
        .all()
    )
    return [_serialize_revision(r) for r in revisions]


def _comments_for_assertion(session: Session, assertion_id: str) -> list[dict]:
    rows = (
        session.execute(
            select(AssertionComment).where(
                AssertionComment.assertion_id == assertion_id,
                AssertionComment.deleted_at.is_(None),
            )
        )
        .scalars()
        .all()
    )
    return [_serialize_comment_summary(c) for c in rows]


def _current_revision(session: Session, assertion: Assertion) -> AssertionRevision | None:
    return session.execute(
        select(AssertionRevision).where(
            AssertionRevision.assertion_id == assertion.id,
            AssertionRevision.revision_number == assertion.current_revision_number,
        )
    ).scalar_one_or_none()


def _rating_strengths_for_revision(session: Session, revision_id: str | None) -> list[int]:
    if revision_id is None:
        return []
    return (
        session.execute(
            select(AssertionRating.strength).where(
                AssertionRating.assertion_revision_id == revision_id
            )
        )
        .scalars()
        .all()
    )


def _user_rating_for_revision(
    session: Session, revision_id: str | None, user_id: str
) -> int | None:
    if revision_id is None:
        return None
    return session.execute(
        select(AssertionRating.strength).where(
            AssertionRating.assertion_revision_id == revision_id,
            AssertionRating.user_id == user_id,
        )
    ).scalar_one_or_none()


def _ratings_summary(session: Session, assertion: Assertion) -> dict | None:
    revision = _current_revision(session, assertion)
    strengths = _rating_strengths_for_revision(session, revision.id if revision else None)
    if not strengths:
        return None
    count = len(strengths)
    average = sum(strengths) / count
    ordered = sorted(strengths)
    mid = count // 2
    median = ordered[mid] if count % 2 == 1 else (ordered[mid - 1] + ordered[mid]) / 2
    distribution = {str(v): strengths.count(v) for v in range(1, 6)}
    return {
        "assertion_id": assertion.id,
        "assertion_revision_id": revision.id if revision else None,
        "average": average,
        "median": median,
        "count": count,
        "distribution": distribution,
    }


# --- Permission helpers (owned by this track; no shared deps module) -------


def _matter_role(session: Session, user_id: str, matter_id: str) -> str | None:
    return session.execute(
        select(MatterRole.role).where(
            MatterRole.user_id == user_id, MatterRole.matter_id == matter_id
        )
    ).scalar_one_or_none()


def _require_matter_member(session: Session, user_id: str, matter_id: str) -> str:
    role = _matter_role(session, user_id, matter_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="no access to matter")
    return role


def _get_assertion_or_404(session: Session, assertion_id: str) -> Assertion:
    assertion = session.get(Assertion, assertion_id)
    if assertion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assertion not found")
    return assertion


def _require_can_modify(session: Session, user_id: str, assertion: Assertion) -> None:
    """Author may modify their own assertion; reviewer/admin may modify any."""
    role = _matter_role(session, user_id, assertion.matter_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="no access to matter")
    if user_id != assertion.author_user_id and role not in _REVIEWER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not permitted to modify this assertion"
        )


# --- Routes ------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED)
def create_assertion(
    body: AssertionCreate,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    matter = session.get(Matter, body.matter_id)
    if matter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="matter not found")
    repository = session.get(Repository, body.repository_id)
    if repository is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="repository not found")

    role = _matter_role(session, user_id, body.matter_id)
    if role is None or role not in ("contributor", "reviewer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not permitted to suggest assertions"
        )

    # --- B5: validate + sanitize the submitted payload before storage ------
    # Submitted text (proposition, etc.) is never treated as instructions —
    # sanitize_for_storage only strips active markup; validation errors are
    # surfaced as 422s, never silently corrected.
    proposition = sanitize_for_storage(body.proposition)
    try:
        # Track A, item A8 (issue #2 sub-item, gate G4): length cap is
        # checked against the raw submitted text, before sanitization.
        validate_text_length(body.proposition, label="proposition")
        validate_proposition_not_empty(proposition)
        validate_effective_dates(body.effective_from, body.effective_to)
        validate_assertion_type(
            body.assertion_type, is_proposed_new=body.assertion_type_is_proposed_new
        )
        validate_matter_scoped_entity_id(body.subject_entity.id, label="subject_entity")
        if body.object_entity is not None:
            validate_matter_scoped_entity_id(body.object_entity.id, label="object_entity")
        for item in body.evidence:
            span = session.get(SourceSpan, item.source_span_id)
            validate_evidence_matter_scope(
                span.matter_id if span is not None else None, body.matter_id
            )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    # --- B5: duplicate/related-assertion detection (spec §8) ---------------
    # Exact proposition matches block submission; every other match kind is
    # surfaced as a non-blocking warning (spec §7: "similarity warnings must
    # not prevent submission unless there is an exact duplicate").
    existing_rows = (
        session.execute(select(Assertion).where(Assertion.matter_id == body.matter_id))
        .scalars()
        .all()
    )
    candidate = {
        "proposition": proposition,
        "assertion_type": body.assertion_type,
        "subject_entity": {"type": body.subject_entity.type, "id": body.subject_entity.id},
        "object_entity": (
            {"type": body.object_entity.type, "id": body.object_entity.id}
            if body.object_entity is not None
            else None
        ),
    }
    existing_candidates = [
        {
            "id": row.id,
            "proposition": row.proposition,
            "assertion_type": row.assertion_type,
            "subject_entity": {"type": row.subject_entity_type, "id": row.subject_entity_id},
            "object_entity": (
                {"type": row.object_entity_type, "id": row.object_entity_id}
                if row.object_entity_type is not None
                else None
            ),
        }
        for row in existing_rows
    ]
    matches = find_related_assertions(candidate, existing_candidates)
    exact_matches = [m for m in matches if m["match_kind"] == "exact_proposition"]
    if exact_matches:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "duplicate: an identical proposition already exists in this matter "
                f"(assertion {exact_matches[0]['assertion_id']})"
            ),
        )
    similar_matches = [m for m in matches if m["match_kind"] != "exact_proposition"]

    now = _now()
    assertion = Assertion(
        id=str(uuid.uuid4()),
        organization_id=repository.organization_id,
        repository_id=body.repository_id,
        matter_id=body.matter_id,
        assertion_type=body.assertion_type,
        proposition=proposition,
        subject_entity_type=body.subject_entity.type,
        subject_entity_id=body.subject_entity.id,
        object_entity_type=body.object_entity.type if body.object_entity else None,
        object_entity_id=body.object_entity.id if body.object_entity else None,
        origin="user_suggested",
        status=body.save_as,
        author_user_id=user_id,
        confidence=None,
        jurisdiction=body.jurisdiction,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        created_at=now,
        updated_at=now,
        submitted_at=now if body.save_as == "proposed" else None,
        reviewed_by=None,
        reviewed_at=None,
        superseded_by_assertion_id=None,
        current_revision_number=1,
    )
    session.add(assertion)

    revision = AssertionRevision(
        id=str(uuid.uuid4()),
        assertion_id=assertion.id,
        revision_number=1,
        proposition=assertion.proposition,
        # Track A, item A2 (issue #2, gate G1): the author's exact
        # submitted bytes, independent of whatever sanitize_for_storage
        # did to `proposition` above.
        proposition_raw=body.proposition,
        assertion_type=assertion.assertion_type,
        subject_entity_type=assertion.subject_entity_type,
        subject_entity_id=assertion.subject_entity_id,
        object_entity_type=assertion.object_entity_type,
        object_entity_id=assertion.object_entity_id,
        jurisdiction=assertion.jurisdiction,
        effective_from=assertion.effective_from,
        effective_to=assertion.effective_to,
        revision_reason="initial creation",
        edited_by_user_id=user_id,
        created_at=now,
    )
    session.add(revision)

    for item in body.evidence:
        session.add(
            AssertionEvidence(
                id=str(uuid.uuid4()),
                assertion_id=assertion.id,
                source_span_id=item.source_span_id,
                evidence_role=item.evidence_role,
                added_by_user_id=user_id,
                created_at=now,
            )
        )

    session.commit()
    session.refresh(assertion)
    result = _serialize_assertion(session, assertion)
    result["similar_assertions"] = similar_matches
    return result


_SORT_KEYS = {
    "created_at": lambda a: a.created_at,
    "updated_at": lambda a: a.updated_at,
    "proposition": lambda a: a.proposition,
    "assertion_type": lambda a: a.assertion_type,
}


@router.get("")
def list_assertions(
    matter_id: str,
    q: str | None = None,
    origin: str | None = None,
    status_: str | None = Query(default=None, alias="status"),
    evidence_status: str | None = None,
    jurisdiction: str | None = None,
    min_average_rating: float | None = None,
    min_rating_count: int | None = None,
    unrated_by_me: bool | None = None,
    my_rating: int | None = None,
    sort: str | None = None,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """B5: search/filter/sort (spec §17) on top of B1's matter-scoped list.

    `status` is aliased to avoid shadowing the `fastapi.status` module used
    throughout this file.
    """
    _require_matter_member(session, user_id, matter_id)

    stmt = select(Assertion).where(Assertion.matter_id == matter_id)
    if origin:
        stmt = stmt.where(Assertion.origin == origin)
    if status_:
        stmt = stmt.where(Assertion.status == status_)
    if jurisdiction:
        stmt = stmt.where(Assertion.jurisdiction == jurisdiction)
    assertions = session.execute(stmt).scalars().all()

    if q:
        # Track A, item A6 (issue #2, gate G1): match against the current
        # revision's RAW proposition, not the (possibly lossy) sanitized
        # `proposition` column -- a search term the sanitizer legitimately
        # dropped (e.g. "appendix A") must still find the assertion.
        needle = q.strip().lower()

        def _matches(a: Assertion) -> bool:
            revision = _current_revision(session, a)
            raw = revision.proposition_raw if revision else None
            haystack = raw if raw is not None else a.proposition
            return needle in (haystack or "").lower()

        assertions = [a for a in assertions if _matches(a)]

    if evidence_status:
        assertions = [a for a in assertions if _evidence_status(session, a.id) == evidence_status]

    if (
        min_average_rating is not None
        or min_rating_count is not None
        or unrated_by_me is not None
        or my_rating is not None
    ):
        kept = []
        for a in assertions:
            revision = _current_revision(session, a)
            strengths = _rating_strengths_for_revision(session, revision.id if revision else None)
            if min_rating_count is not None and len(strengths) < min_rating_count:
                continue
            if min_average_rating is not None:
                if not strengths or (sum(strengths) / len(strengths)) < min_average_rating:
                    continue
            if unrated_by_me or my_rating is not None:
                user_rating = _user_rating_for_revision(
                    session, revision.id if revision else None, user_id
                )
                if unrated_by_me and user_rating is not None:
                    continue
                if my_rating is not None and user_rating != my_rating:
                    continue
            kept.append(a)
        assertions = kept

    if sort:
        reverse = sort.startswith("-")
        key_name = sort[1:] if reverse else sort
        keyfn = _SORT_KEYS.get(key_name, _SORT_KEYS["created_at"])
        assertions = sorted(assertions, key=keyfn, reverse=reverse)

    items = [_serialize_assertion(session, a) for a in assertions]
    return {"items": items, "total": len(items)}


@router.get("/{assertion_id}/related")
def get_related_assertions(
    assertion_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    """B5 / ruling R10: duplicate/related-assertion surface (spec §8, §13)."""
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_matter_member(session, user_id, assertion.matter_id)

    others = (
        session.execute(
            select(Assertion).where(
                Assertion.matter_id == assertion.matter_id, Assertion.id != assertion.id
            )
        )
        .scalars()
        .all()
    )
    candidate = {
        "id": assertion.id,
        "proposition": assertion.proposition,
        "assertion_type": assertion.assertion_type,
        "subject_entity": {"type": assertion.subject_entity_type, "id": assertion.subject_entity_id},
        "object_entity": (
            {"type": assertion.object_entity_type, "id": assertion.object_entity_id}
            if assertion.object_entity_type is not None
            else None
        ),
    }
    existing_candidates = [
        {
            "id": row.id,
            "proposition": row.proposition,
            "assertion_type": row.assertion_type,
            "subject_entity": {"type": row.subject_entity_type, "id": row.subject_entity_id},
            "object_entity": (
                {"type": row.object_entity_type, "id": row.object_entity_id}
                if row.object_entity_type is not None
                else None
            ),
        }
        for row in others
    ]
    return find_related_assertions(candidate, existing_candidates)  # type: ignore[return-value]


@router.get("/{assertion_id}")
def get_assertion(
    assertion_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_matter_member(session, user_id, assertion.matter_id)
    result = _serialize_assertion(session, assertion)
    result["evidence"] = [_serialize_evidence(e) for e in _evidence_rows(session, assertion_id)]
    result["ratings_summary"] = _ratings_summary(session, assertion)
    result["comments"] = _comments_for_assertion(session, assertion_id)
    result["revision_history"] = _revision_history(session, assertion_id)
    return result


@router.patch("/{assertion_id}")
def patch_assertion(
    assertion_id: str,
    body: AssertionPatch,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_can_modify(session, user_id, assertion)

    if (
        body.expected_revision_number is not None
        and body.expected_revision_number != assertion.current_revision_number
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="assertion has been modified since expected_revision_number",
        )

    updates = body.model_dump(
        exclude_unset=True, exclude={"expected_revision_number", "revision_reason"}
    )
    if not updates:
        return _serialize_assertion(session, assertion)

    # Track A, item A8 (issue #2 sub-item, gate G4): length cap checked
    # against the raw submitted text, before sanitization.
    if "proposition" in updates and body.proposition is not None:
        try:
            validate_text_length(body.proposition, label="proposition")
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

    # Track A, item A2 (issue #2, gate G1): carry the previous revision's
    # raw text forward when this PATCH doesn't touch proposition, so a new
    # revision's raw column is never silently blanked out.
    previous_revision = _current_revision(session, assertion)
    proposition_raw = previous_revision.proposition_raw if previous_revision else None

    now = _now()
    new_revision_number = assertion.current_revision_number + 1

    if "proposition" in updates:
        # B5 (qa-fail fix): sanitize like CREATE does -- PATCH is a storage
        # path for the proposition too (gate G10).
        assertion.proposition = sanitize_for_storage(body.proposition)
        proposition_raw = body.proposition
    if "assertion_type" in updates:
        assertion.assertion_type = body.assertion_type
    if "subject_entity" in updates and body.subject_entity is not None:
        assertion.subject_entity_type = body.subject_entity.type
        assertion.subject_entity_id = body.subject_entity.id
    if "object_entity" in updates:
        assertion.object_entity_type = body.object_entity.type if body.object_entity else None
        assertion.object_entity_id = body.object_entity.id if body.object_entity else None
    if "jurisdiction" in updates:
        assertion.jurisdiction = body.jurisdiction
    if "effective_from" in updates:
        assertion.effective_from = body.effective_from
    if "effective_to" in updates:
        assertion.effective_to = body.effective_to

    assertion.current_revision_number = new_revision_number
    assertion.updated_at = now
    # Editing an accepted assertion creates a new proposed revision rather
    # than silently modifying the accepted assertion (spec §3).
    if assertion.status == "accepted":
        assertion.status = "proposed"

    revision = AssertionRevision(
        id=str(uuid.uuid4()),
        assertion_id=assertion.id,
        revision_number=new_revision_number,
        proposition=assertion.proposition,
        proposition_raw=proposition_raw,
        assertion_type=assertion.assertion_type,
        subject_entity_type=assertion.subject_entity_type,
        subject_entity_id=assertion.subject_entity_id,
        object_entity_type=assertion.object_entity_type,
        object_entity_id=assertion.object_entity_id,
        jurisdiction=assertion.jurisdiction,
        effective_from=assertion.effective_from,
        effective_to=assertion.effective_to,
        revision_reason=body.revision_reason,
        edited_by_user_id=user_id,
        created_at=now,
    )
    session.add(revision)
    session.commit()
    session.refresh(assertion)
    return _serialize_assertion(session, assertion)


@router.post("/{assertion_id}/submit")
def submit_assertion(
    assertion_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_can_modify(session, user_id, assertion)

    if assertion.status not in ("draft", "proposed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"cannot submit assertion in status '{assertion.status}'",
        )

    assertion.status = "proposed"
    assertion.submitted_at = _now()
    assertion.updated_at = _now()
    session.commit()
    session.refresh(assertion)
    return _serialize_assertion(session, assertion)


@router.post("/{assertion_id}/withdraw")
def withdraw_assertion(
    assertion_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_can_modify(session, user_id, assertion)

    assertion.status = "withdrawn"
    assertion.updated_at = _now()
    session.commit()
    session.refresh(assertion)
    return _serialize_assertion(session, assertion)


@router.get("/{assertion_id}/revisions")
def list_revisions(
    assertion_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_matter_member(session, user_id, assertion.matter_id)
    revisions = (
        session.execute(
            select(AssertionRevision)
            .where(AssertionRevision.assertion_id == assertion_id)
            .order_by(AssertionRevision.revision_number.asc())
        )
        .scalars()
        .all()
    )
    return [_serialize_revision(r) for r in revisions]


@router.post("/{assertion_id}/revisions", status_code=status.HTTP_201_CREATED)
def create_revision(
    assertion_id: str,
    body: AssertionPatch,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Explicit revision-create endpoint (spec §13); shares the same
    material-edit semantics as PATCH, always recording a new revision.
    """
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_can_modify(session, user_id, assertion)

    if (
        body.expected_revision_number is not None
        and body.expected_revision_number != assertion.current_revision_number
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="assertion has been modified since expected_revision_number",
        )

    # Track A, item A8 (issue #2 sub-item, gate G4): length cap checked
    # against the raw submitted text, before sanitization.
    if body.proposition is not None:
        try:
            validate_text_length(body.proposition, label="proposition")
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

    # Track A, item A2 (issue #2, gate G1): carry the previous revision's
    # raw text forward when this call doesn't touch proposition.
    previous_revision = _current_revision(session, assertion)
    proposition_raw = previous_revision.proposition_raw if previous_revision else None

    now = _now()
    new_revision_number = assertion.current_revision_number + 1

    if body.proposition is not None:
        # B5 (qa-fail fix): sanitize like CREATE does (gate G10).
        assertion.proposition = sanitize_for_storage(body.proposition)
        proposition_raw = body.proposition
    if body.assertion_type is not None:
        assertion.assertion_type = body.assertion_type
    if body.subject_entity is not None:
        assertion.subject_entity_type = body.subject_entity.type
        assertion.subject_entity_id = body.subject_entity.id
    if body.object_entity is not None:
        assertion.object_entity_type = body.object_entity.type
        assertion.object_entity_id = body.object_entity.id
    if body.jurisdiction is not None:
        assertion.jurisdiction = body.jurisdiction
    if body.effective_from is not None:
        assertion.effective_from = body.effective_from
    if body.effective_to is not None:
        assertion.effective_to = body.effective_to

    assertion.current_revision_number = new_revision_number
    assertion.updated_at = now
    if assertion.status == "accepted":
        assertion.status = "proposed"

    revision = AssertionRevision(
        id=str(uuid.uuid4()),
        assertion_id=assertion.id,
        revision_number=new_revision_number,
        proposition=assertion.proposition,
        proposition_raw=proposition_raw,
        assertion_type=assertion.assertion_type,
        subject_entity_type=assertion.subject_entity_type,
        subject_entity_id=assertion.subject_entity_id,
        object_entity_type=assertion.object_entity_type,
        object_entity_id=assertion.object_entity_id,
        jurisdiction=assertion.jurisdiction,
        effective_from=assertion.effective_from,
        effective_to=assertion.effective_to,
        revision_reason=body.revision_reason,
        edited_by_user_id=user_id,
        created_at=now,
    )
    session.add(revision)
    session.commit()
    session.refresh(revision)
    return _serialize_revision(revision)


@router.get("/{assertion_id}/evidence")
def list_evidence(
    assertion_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_matter_member(session, user_id, assertion.matter_id)
    rows = (
        session.execute(
            select(AssertionEvidence).where(AssertionEvidence.assertion_id == assertion_id)
        )
        .scalars()
        .all()
    )
    return [_serialize_evidence(e) for e in rows]


@router.post("/{assertion_id}/evidence", status_code=status.HTTP_201_CREATED)
def add_evidence(
    assertion_id: str,
    body: EvidenceCreate,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    role = _matter_role(session, user_id, assertion.matter_id)
    if role is None or role not in ("contributor", "reviewer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not permitted to attach evidence"
        )

    # B5: a resolvable source span must belong to this assertion's matter
    # (spec §7 "a user cannot attach evidence from another inaccessible
    # matter") — see validate_evidence_matter_scope for why an unresolved
    # span id is not itself grounds for rejection here.
    span = session.get(SourceSpan, body.source_span_id)
    try:
        validate_evidence_matter_scope(span.matter_id if span is not None else None, assertion.matter_id)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    evidence = AssertionEvidence(
        id=str(uuid.uuid4()),
        assertion_id=assertion_id,
        source_span_id=body.source_span_id,
        evidence_role=body.evidence_role,
        added_by_user_id=user_id,
        created_at=_now(),
    )
    session.add(evidence)
    session.commit()
    session.refresh(evidence)
    return _serialize_evidence(evidence)


@router.delete("/{assertion_id}/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_evidence(
    assertion_id: str,
    evidence_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> None:
    assertion = _get_assertion_or_404(session, assertion_id)
    role = _matter_role(session, user_id, assertion.matter_id)
    if role is None or role not in ("contributor", "reviewer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not permitted to remove evidence"
        )

    evidence = session.get(AssertionEvidence, evidence_id)
    if evidence is None or evidence.assertion_id != assertion_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evidence not found")

    session.delete(evidence)
    session.commit()
    return None
