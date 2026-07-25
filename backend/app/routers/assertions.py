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

Review-decision routes (accept/reject/dispute/request-revision/supersede),
ratings, comments, and search/duplicate-detection query params belong to
other tracks (B4, B2, B3, B5 respectively) and are intentionally absent
here — see `app/routers/__init__.py` for ownership.

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

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.assertion import Assertion
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_revision import AssertionRevision
from app.models.matter import Matter
from app.models.matter_role import MatterRole
from app.models.repository import Repository

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
    return {
        "id": a.id,
        "organization_id": a.organization_id,
        "repository_id": a.repository_id,
        "matter_id": a.matter_id,
        "assertion_type": a.assertion_type,
        "proposition": a.proposition,
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

    now = _now()
    assertion = Assertion(
        id=str(uuid.uuid4()),
        organization_id=repository.organization_id,
        repository_id=body.repository_id,
        matter_id=body.matter_id,
        assertion_type=body.assertion_type,
        proposition=body.proposition,
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
    return _serialize_assertion(session, assertion)


@router.get("")
def list_assertions(
    matter_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    _require_matter_member(session, user_id, matter_id)
    assertions = (
        session.execute(select(Assertion).where(Assertion.matter_id == matter_id))
        .scalars()
        .all()
    )
    return [_serialize_assertion(session, a) for a in assertions]


@router.get("/{assertion_id}")
def get_assertion(
    assertion_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_matter_member(session, user_id, assertion.matter_id)
    return _serialize_assertion(session, assertion)


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

    now = _now()
    new_revision_number = assertion.current_revision_number + 1

    if "proposition" in updates:
        assertion.proposition = body.proposition
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

    now = _now()
    new_revision_number = assertion.current_revision_number + 1

    if body.proposition is not None:
        assertion.proposition = body.proposition
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
