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
and the new `GET .../related` route (ruling R10). PATCH and
`POST .../revisions` share one edit path (`_edit_assertion`): an edit that
changes nothing material creates no revision (PATCH answers 200 with the
unchanged assertion, POST .../revisions 200 with the unchanged current
revision instead of 201).

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
import json
import sqlite3
from collections import namedtuple
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.models.audit_event import AuditEvent
from app.models.document import Document
from app.services.audit import record_assertion_event, record_audit_event
from app.services.source_access import validate_entity, validate_span
from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_rating import AssertionRating
from app.models.assertion_revision import AssertionRevision
from app.models.matter import Matter
from app.models.matter_role import MatterRole
from app.models.repository import Repository
from app.models.source_span import SourceSpan
from app.services.duplicates import (
    DuplicateAssertionError,
    blocks_exact_duplicate,
    find_related_assertions,
    first_blocking_duplicate,
    normalize_proposition,
    surface_similar,
)
from app.services.jurisdiction import JURISDICTION_CODES, validate_jurisdiction
from app.services.ratings import compute_standing
from app.services.validation import (
    ValidationError,
    normalize_effective_datetime,
    sanitize_for_storage,
    validate_assertion_type,
    validate_effective_dates,
    validate_evidence_matter_scope,
    validate_matter_scoped_entity_id,
    validate_proposition_not_empty,
    validate_text_length,
)
from app.services.write_lock import lock_assertion_writes

router = APIRouter(prefix="/api/v1/assertions", tags=["assertions"])

# Sprint 2026-08-02-us-state-law, item 1 (ruling R5): the canonical
# jurisdiction vocabulary endpoint, prefix-separate from the assertions
# router above (`/api/v1/assertions/...`) since this serves
# `/api/v1/jurisdictions`, not an assertions sub-resource. Registered
# alongside `assertions_router` in `app.main.create_app()`. Route handler
# itself is defined below `get_current_user_id` (needs that dependency).
jurisdictions_router = APIRouter(prefix="/api/v1", tags=["jurisdictions"])

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


@jurisdictions_router.get("/jurisdictions")
def list_jurisdictions(
    user_id: str = Depends(get_current_user_id),
) -> list[str]:
    """Serve the canonical jurisdiction controlled vocabulary (G5, R5): the
    frontend's runtime source of truth, so a dropdown can never drift from
    the backend list without a code change on both sides.
    """
    return list(JURISDICTION_CODES)


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


#: Keys of the agent contract (`POST /api/v1/agent/assertions`) that the
#: lawyer endpoint refuses with a pointer to the agent endpoint (agent:11).
_AGENT_ONLY_FIELDS = ("agent", "confidence")


class AssertionCreate(BaseModel):
    # agent:11: an undeclared key is a 422, never silently dropped -- the
    # agent JSON posted here used to be stored as a lawyer's user_suggested
    # assertion without its provenance or confidence.
    model_config = ConfigDict(extra="forbid")

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

    @model_validator(mode="before")
    @classmethod
    def _agent_fields_go_to_the_agent_endpoint(cls, data):
        # Inert for AgentAssertionCreate, which declares both fields.
        if isinstance(data, dict):
            sent = [key for key in _AGENT_ONLY_FIELDS if key in data and key not in cls.model_fields]
            if sent:
                raise PydanticCustomError(
                    "agent_endpoint_required",
                    " and ".join(sent) + (" is" if len(sent) == 1 else " are")
                    + " not accepted on POST /api/v1/assertions: send agent suggestions, "
                    "with their provenance and confidence, to POST /api/v1/agent/assertions",
                    {"fields": sent},
                )
        return data


class AssertionPatch(BaseModel):
    assertion_type: str | None = Field(default=None, min_length=1)
    # api:21 / review:4: the edit-side counterpart of AssertionCreate's flag.
    # Consulted only when assertion_type changes: an assertion keeps its own
    # type, proposed-new or not, without it.
    assertion_type_is_proposed_new: bool = False
    proposition: str | None = Field(default=None, min_length=1)
    subject_entity: EntityRef | None = None
    object_entity: EntityRef | None = None
    jurisdiction: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    revision_reason: str | None = None
    expected_revision_number: int | None = Field(default=None, ge=1)


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


def _agent_provenance(session: Session, assertion: Assertion) -> dict | None:
    if assertion.origin != "model_suggested":
        return None
    event = session.scalars(select(AuditEvent).where(
        AuditEvent.assertion_id == assertion.id,
        AuditEvent.event_type == "assertion_agent_provenance",
    ).order_by(AuditEvent.timestamp).limit(1)).first()
    return json.loads(event.new_value) if event and event.new_value else None


def _serialize_assertion(session: Session, a: Assertion) -> dict:
    current_revision = _current_revision(session, a)
    ratings = _rating_pairs_for_revision(
        session, current_revision.id if current_revision else None
    )
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
        "agent_provenance": _agent_provenance(session, a),
        "status": a.status,
        # Sprint 2026-07-30-ratings-grade, item B1 (ruling R3): derived at
        # read time, never persisted -- `status` itself is untouched.
        "standing": compute_standing(a.status, ratings, a.author_user_id),
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


def _serialize_evidence(e: AssertionEvidence, session: Session | None = None) -> dict:
    span = session.get(SourceSpan, e.source_span_id) if session else None
    doc = session.get(Document, span.document_id) if span else None
    assertion = session.get(Assertion, e.assertion_id) if session else None
    if not assertion or not span or not doc or span.matter_id != assertion.matter_id or doc.matter_id != assertion.matter_id:
        span = doc = None
    return {
        "quote_text": span.quote_text if span else None,
        "document_id": doc.id if doc else None,
        "document_title": doc.title if doc else None,
        "id": e.id,
        "assertion_id": e.assertion_id,
        "source_span_id": e.source_span_id,
        "evidence_role": e.evidence_role,
        "added_by_user_id": e.added_by_user_id,
        "created_at": e.created_at,
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
    # Same thread as GET .../comments (finding api:25): creation order, and
    # redacted tombstones for deleted parents that still have live replies.
    from app.routers.comments import list_visible_comments

    return list_visible_comments(session, assertion_id)


def _current_revision(session: Session, assertion: Assertion) -> AssertionRevision | None:
    # (assertion_id, revision_number) is unique, but a database that has not
    # run the unique-index migration may still hold two rows with one
    # number (api:0); read the newest instead of failing the whole matter.
    return session.execute(
        select(AssertionRevision).where(
            AssertionRevision.assertion_id == assertion.id,
            AssertionRevision.revision_number == assertion.current_revision_number,
        ).order_by(AssertionRevision.created_at.desc(), AssertionRevision.id.desc()).limit(1)
    ).scalars().first()


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


def _rating_pairs_for_revision(session: Session, revision_id: str | None) -> list[dict]:
    """Return `{"user_id": ..., "strength": ...}` rows for `revision_id`.

    Unlike `_rating_strengths_for_revision` (bare strengths, used by the
    pre-existing `ratings_summary` aggregate which counts every rating
    including the author's), this also carries `user_id` -- needed by
    `app.services.ratings.compute_standing` (item B1) to exclude the
    author's own rating from the derived `standing` grade.
    """
    if revision_id is None:
        return []
    rows = session.execute(
        select(AssertionRating.user_id, AssertionRating.strength).where(
            AssertionRating.assertion_revision_id == revision_id
        )
    ).all()
    return [{"user_id": user_id, "strength": strength} for user_id, strength in rows]


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
    if role in _REVIEWER_ROLES:
        return
    if (role != "contributor" or user_id != assertion.author_user_id
            or assertion.status not in ("draft", "proposed", "revision_requested")):
        raise HTTPException(403, "Only the author of an unreviewed assertion or a reviewer may modify it")


# --- Conflict helpers (duplicates, stale revisions) -------------------------

_STALE_REVISION_DETAIL = "assertion has been modified since expected_revision_number"


def _stale_revision_conflict() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_STALE_REVISION_DETAIL)


_JURISDICTION_HINT = (
    "use IL, US-<postal code> (US-IL is Illinois), US-DC, US-PR or US-FED; "
    "GET /api/v1/jurisdictions lists them"
)


def _validate_jurisdiction(code: str) -> None:
    """`validate_jurisdiction` plus a hint naming the valid codes (XREQ-4).

    app/services/jurisdiction.py is part of the certified seam, so its own
    message cannot list them; agents and lawyers otherwise learn only that
    their code is not in the vocabulary."""
    try:
        validate_jurisdiction(code)
    except ValidationError as exc:
        raise ValidationError(f"{exc}; {_JURISDICTION_HINT}") from exc


def _duplicate_conflict(existing_assertion_id: str) -> HTTPException:
    # ui:5: the API answers the existing assertion's id as data next to the
    # unchanged detail text (`existing_assertion_id`, app.request_guards).
    return DuplicateAssertionError(existing_assertion_id)


# Columns the duplicate/related scans compare and report: narrow rows, never
# whole ORM objects of the matter (agent:2).
_MATCH_COLUMNS = (
    Assertion.id,
    Assertion.proposition,
    Assertion.assertion_type,
    Assertion.subject_entity_type,
    Assertion.subject_entity_id,
    Assertion.object_entity_type,
    Assertion.object_entity_id,
    Assertion.status,
    Assertion.author_user_id,
)
_MatchRow = namedtuple("_MatchRow", [column.key for column in _MATCH_COLUMNS])

# Review authoring:3. The scans read every assertion of a matter. A plain
# SELECT hands the rows over one at a time, and between two rows the reading
# thread has to win the GIL back from the request threads busy with CPU work
# (the similarity pass of the concurrent requests). Measured on a matter of
# 220,000 rows with one such thread, 5,000 rows took 42 s: the read held
# SQLite's SHARED lock for minutes, so every COMMIT in the database waited
# behind it and failed with "database is locked". On SQLite the rows are
# therefore built into one JSON value by SQLite itself, in one step that
# holds the lock for well under a second whatever the load (0.4-0.7 s).
_MATTER_ROWS_AS_JSON = text(
    "SELECT json_group_array(json_array("
    + ", ".join(column.key for column in _MATCH_COLUMNS)
    + ", created_at)) FROM assertions WHERE matter_id = :matter_id"
)
_SQLITE_HAS_JSON = sqlite3.sqlite_version_info >= (3, 38, 0)


def _matter_rows(session: Session, matter_id: str) -> list[_MatchRow]:
    """Every assertion of `matter_id` as `_MATCH_COLUMNS` rows, oldest first
    (created_at, then id)."""
    if _SQLITE_HAS_JSON and session.get_bind().dialect.name == "sqlite":
        value = session.execute(_MATTER_ROWS_AS_JSON, {"matter_id": matter_id}).scalar_one()
        rows = json.loads(value) if value else []
        rows.sort(key=lambda row: (str(row[-1]), row[0]))
        return [_MatchRow(*row[:-1]) for row in rows]
    return [_MatchRow(*row) for row in session.execute(
        select(*_MATCH_COLUMNS)
        .where(Assertion.matter_id == matter_id)
        .order_by(Assertion.created_at, Assertion.id)
    ).all()]


def _match_candidate(row) -> dict:
    """`find_related_assertions`' view of an assertion (an ORM object or a
    `_MATCH_COLUMNS` row)."""
    return {
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


def _blocking_duplicate_id(
    session: Session,
    matter_id: str,
    proposition: str,
    *,
    owner_user_id: str,
    exclude_id: str | None = None,
    submitting: bool = False,
) -> str | None:
    """Exact-duplicate check against the committed state (spec §7/§8 and the
    "Exact duplicates" rule): the oldest blocking assertion's id, or None.
    It reads the whole matter: run it before `lock_assertion_writes` (see
    `DuplicateScan`), and re-check under the lock with `recheck_duplicate`."""
    rows = [(row.id, row.proposition, row.status, row.author_user_id) for row in _matter_rows(session, matter_id)]
    return first_blocking_duplicate(
        proposition, rows, owner_user_id=owner_user_id, exclude_id=exclude_id, submitting=submitting
    )


# --- Exact duplicates under the write lock (review authoring:3) -------------
#
# The exact-duplicate rule must hold at commit, so writers re-check it under
# `lock_assertion_writes`. Re-reading a whole matter there held SQLite's
# database-wide write lock for a full Python pass over every row (0.35 s at
# 220,000 rows, seconds under load), long enough for queued writers to hit the
# busy timeout. The scan over the matter therefore runs before the lock, and
# the locked re-check reads only what was committed after the scan began:
# rows inserted since (higher rowid) and assertions with an audit row since.
# Every writer that changes an assertion's proposition or status (edit, submit,
# withdraw, review decisions) records an audit row in the same transaction,
# and assertions are never deleted, so no other row can have started to block.

_WATERMARK_SQL = text(
    "SELECT (SELECT coalesce(max(rowid), 0) FROM assertions), "
    "(SELECT coalesce(max(rowid), 0) FROM audit_events)"
)
# Rows changed since a watermark. No matter filter in SQL: it would steer
# SQLite to the matter index (every row of the matter) instead of the rowid
# ranges, which hold only the few rows written since.
_CHANGED_SINCE_SQL = text(
    "SELECT id, matter_id, proposition, status, author_user_id, created_at FROM assertions "
    "WHERE rowid > :assertion_rowid "
    "UNION "
    "SELECT id, matter_id, proposition, status, author_user_id, created_at FROM assertions "
    "WHERE id IN (SELECT assertion_id FROM audit_events WHERE rowid > :audit_rowid)"
)


@dataclass(frozen=True)
class DuplicateScan:
    """An exact-duplicate check run without the write lock, and where the
    database stood when it began: the newest assertion and audit rowids
    (SQLite only; None elsewhere, where the re-check reads the matter)."""

    matter_id: str
    proposition: str
    owner_user_id: str
    exclude_id: str | None
    submitting: bool
    watermark: tuple[int, int] | None

    @property
    def rule(self) -> dict:
        return dict(owner_user_id=self.owner_user_id, exclude_id=self.exclude_id, submitting=self.submitting)


def write_watermark(session: Session) -> tuple[int, int] | None:
    """The newest committed assertion and audit rowids, read in one statement."""
    if session.get_bind().dialect.name != "sqlite":
        return None
    assertion_rowid, audit_rowid = session.execute(_WATERMARK_SQL).one()
    return int(assertion_rowid), int(audit_rowid)


def scan_for_duplicate(
    session: Session,
    matter_id: str,
    proposition: str,
    *,
    owner_user_id: str,
    exclude_id: str | None = None,
    submitting: bool = False,
) -> tuple[str | None, DuplicateScan]:
    """The unlocked exact-duplicate check: the blocking assertion's id (or
    None), and the scan to hand to `recheck_duplicate` under the lock."""
    scan = DuplicateScan(matter_id, proposition, owner_user_id, exclude_id, submitting, write_watermark(session))
    return _blocking_duplicate_id(session, matter_id, proposition, **scan.rule), scan


def recheck_duplicate(session: Session, scan: DuplicateScan, proposition: str | None = None) -> str | None:
    """Under `lock_assertion_writes`: the oldest assertion that blocks
    `proposition` (default: the scanned one) and was committed or changed
    after `scan` began, or None.

    The whole matter is re-read only when the scan cannot be trusted: off
    SQLite, when the proposition differs from the scanned one (the assertion
    was edited meanwhile), or when the newest rowids went backwards (rows
    deleted or renumbered by a VACUUM)."""
    proposition = scan.proposition if proposition is None else proposition
    watermark = scan.watermark
    if watermark is not None and normalize_proposition(proposition) == normalize_proposition(scan.proposition):
        now = write_watermark(session)
        if now is not None and now[0] >= watermark[0] and now[1] >= watermark[1]:
            rows = session.execute(
                _CHANGED_SINCE_SQL, {"assertion_rowid": watermark[0], "audit_rowid": watermark[1]}
            ).all()
            changed = sorted(
                (row for row in rows if row.matter_id == scan.matter_id),
                key=lambda row: (str(row.created_at), row.id),
            )
            return first_blocking_duplicate(
                proposition,
                [(row.id, row.proposition, row.status, row.author_user_id) for row in changed],
                **scan.rule,
            )
    return _blocking_duplicate_id(session, scan.matter_id, proposition, **scan.rule)


def _revision_number_taken(session: Session, assertion_id: str, revision_number: int) -> bool:
    return session.execute(
        select(AssertionRevision.id).where(
            AssertionRevision.assertion_id == assertion_id,
            AssertionRevision.revision_number == revision_number,
        ).limit(1)
    ).first() is not None


# --- Edit helpers -------------------------------------------------------------

# Body fields that steer an edit but are not values of the assertion: on
# their own they are never a change (api:18).
_EDIT_CONTROL_FIELDS = {"expected_revision_number", "revision_reason", "assertion_type_is_proposed_new"}


def _changed_fields(assertion: Assertion, current: AssertionRevision | None, updates: dict) -> list[str]:
    """The submitted fields whose value differs from the stored one (api:18,
    review:3, ui:11): the proposition as authored (the current revision's raw
    text, else the stored proposition -- what the editor shows), entities as
    {type, id}, effective dates as UTC instants, everything else as is."""
    changed = []
    for field, value in updates.items():
        if field == "proposition":
            stored = (current.proposition_raw if current is not None and current.proposition_raw is not None
                      else assertion.proposition)
        elif field in ("subject_entity", "object_entity"):
            side = field.removesuffix("_entity")
            entity_type = getattr(assertion, f"{side}_entity_type")
            stored = (None if entity_type is None
                      else {"type": entity_type, "id": getattr(assertion, f"{side}_entity_id")})
        elif field in ("effective_from", "effective_to"):
            stored = normalize_effective_datetime(getattr(assertion, field), label=field)
        else:
            stored = getattr(assertion, field)
        if value != stored:
            changed.append(field)
    return changed


# --- Evidence helpers ---------------------------------------------------------


def _validate_distinct_evidence(items: list[EvidenceIn]) -> None:
    """One span is attached at most once per role (api:11)."""
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item.source_span_id, item.evidence_role)
        if key in seen:
            raise ValidationError(
                f"evidence lists source span {item.source_span_id} more than once "
                f"with role '{item.evidence_role}'"
            )
        seen.add(key)


def _evidence_exists(session: Session, assertion_id: str, *, exclude_id: str | None = None,
                     source_span_id: str | None = None, roles: tuple[str, ...] | None = None) -> bool:
    stmt = select(AssertionEvidence.id).where(AssertionEvidence.assertion_id == assertion_id)
    if exclude_id is not None:
        stmt = stmt.where(AssertionEvidence.id != exclude_id)
    if source_span_id is not None:
        stmt = stmt.where(AssertionEvidence.source_span_id == source_span_id)
    if roles is not None:
        stmt = stmt.where(AssertionEvidence.evidence_role.in_(roles))
    return session.execute(stmt.limit(1)).first() is not None


# --- Routes ------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED)
def create_assertion(
    body: AssertionCreate,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    return _create_assertion(body, session, user_id)


def _create_assertion(body: AssertionCreate, session: Session, user_id: str, *,
                      agent: dict | None = None, confidence: float | None = None) -> dict:
    # review:17: authorize before reading anything else in the payload, so a
    # caller without a suggesting role in the matter gets the same 403 for
    # any matter, repository or pairing and learns nothing from the answer.
    role = _matter_role(session, user_id, body.matter_id)
    if role not in ("contributor", "reviewer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not permitted to suggest assertions"
        )
    matter = session.get(Matter, body.matter_id)
    if matter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="matter not found")
    repository = session.get(Repository, body.repository_id)
    if repository is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="repository not found")
    if matter.repository_id != body.repository_id:
        raise HTTPException(422, "Repository does not belong to the selected matter")

    validate_entity(session, body.subject_entity, body.matter_id, strict=agent is not None)
    if body.object_entity:
        validate_entity(session, body.object_entity, body.matter_id, strict=agent is not None)
    for item in body.evidence:
        validate_span(session, item.source_span_id, body.matter_id, body.repository_id)

    # --- B5: validate + sanitize the submitted payload before storage ------
    # Submitted text (proposition, etc.) is never treated as instructions —
    # sanitize_for_storage only strips active markup; validation errors are
    # surfaced as 422s, never silently corrected.
    try:
        # Track A, item A8 (issue #2 sub-item, gate G4): length caps are
        # checked against the raw submitted text, before sanitization: the
        # sanitizer is super-linear on hostile markup, so over-cap text must
        # never reach it (review:5).
        validate_text_length(body.proposition, label="proposition")
        if body.explanation is not None:
            validate_text_length(body.explanation, label="explanation")
        proposition = sanitize_for_storage(body.proposition)
        validate_proposition_not_empty(proposition)
        # agent:7 / api:19: stored as UTC instants, so an offset is applied
        # rather than dropped and the stored range is the validated one.
        effective_from = normalize_effective_datetime(body.effective_from, label="effective_from")
        effective_to = normalize_effective_datetime(body.effective_to, label="effective_to")
        validate_effective_dates(effective_from, effective_to)
        validate_assertion_type(
            body.assertion_type, is_proposed_new=body.assertion_type_is_proposed_new
        )
        if body.jurisdiction is not None:
            _validate_jurisdiction(body.jurisdiction)
        validate_matter_scoped_entity_id(body.subject_entity.id, label="subject_entity")
        if body.object_entity is not None:
            validate_matter_scoped_entity_id(body.object_entity.id, label="object_entity")
        for item in body.evidence:
            span = session.get(SourceSpan, item.source_span_id)
            validate_evidence_matter_scope(
                span.matter_id if span is not None else None, body.matter_id
            )
        _validate_distinct_evidence(body.evidence)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail=str(exc)
        ) from exc
    # review:20: an explanation is preserved as the initial comment, stored
    # as POST .../comments stores the same text (sanitized text plus the raw
    # authored text) even when nothing survives sanitization. Only a blank
    # explanation is no explanation. Sanitized here, before the write lock.
    explanation_raw = body.explanation if body.explanation and body.explanation.strip() else None
    explanation = sanitize_for_storage(explanation_raw) if explanation_raw is not None else None

    # --- B5: duplicate/related-assertion detection (spec §8) ---------------
    # Exact proposition matches block submission; every other match kind is
    # surfaced as a non-blocking warning (spec §7: "similarity warnings must
    # not prevent submission unless there is an exact duplicate").
    scan = DuplicateScan(body.matter_id, proposition, user_id, None, False, write_watermark(session))
    existing_rows = _matter_rows(session, body.matter_id)
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
    matches = find_related_assertions(candidate, [_match_candidate(row) for row in existing_rows])
    # api:16: only live assertions and the author's own drafts block; an
    # exact match with a withdrawn/rejected/superseded assertion or another
    # user's draft is returned below as a non-blocking similar assertion.
    rows_by_id = {row.id: row for row in existing_rows}
    blocking = [
        m["assertion_id"]
        for m in matches
        if m["match_kind"] == "exact_proposition"
        and blocks_exact_duplicate(
            rows_by_id[m["assertion_id"]].status,
            rows_by_id[m["assertion_id"]].author_user_id,
            owner_user_id=user_id,
        )
    ]
    if blocking:
        raise _duplicate_conflict(blocking[0])
    # agent:2 / ui:5: the strongest matches with their text, status and type;
    # the count of all of them goes next to the list.
    similar, similar_total = surface_similar(matches, rows_by_id)

    # agent:1 / api:17: the scan above holds no lock, so another submitter
    # (request, agent CLI or MCP server) may have stored the same
    # proposition since. Serialize writers and re-check before inserting;
    # the lock lasts until the commit below (or the rollback on 409). The
    # re-check reads only what was written after the scan (authoring:3).
    lock_assertion_writes(session, body.matter_id)
    blocker = recheck_duplicate(session, scan)
    if blocker is not None:
        session.rollback()
        raise _duplicate_conflict(blocker)

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
        origin="model_suggested" if agent else "user_suggested",
        status=body.save_as,
        author_user_id=user_id,
        confidence=confidence if agent else None,
        jurisdiction=body.jurisdiction,
        effective_from=effective_from,
        effective_to=effective_to,
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

    session.flush()
    record_audit_event(session, actor_user_id=user_id, event_type="assertion_created",
                       repository_id=assertion.repository_id, matter_id=assertion.matter_id,
                       assertion_id=assertion.id, assertion_revision_id=revision.id,
                       new_value=assertion.status)
    for evidence_row in _evidence_rows(session, assertion.id):  # audit api:4/review:2
        record_assertion_event(session, assertion, actor_user_id=user_id, event_type="evidence_added",
                               assertion_revision_id=revision.id, new_value=evidence_row.id)
    if agent:
        record_audit_event(session, actor_user_id=user_id, event_type="assertion_agent_provenance",
                           repository_id=assertion.repository_id, matter_id=assertion.matter_id,
                           assertion_id=assertion.id, assertion_revision_id=revision.id,
                           new_value=json.dumps(agent, ensure_ascii=False))
    if explanation_raw is not None:
        comment = AssertionComment(id=str(uuid.uuid4()), assertion_id=assertion.id,
            user_id=user_id, comment_text=explanation,
            comment_text_raw=explanation_raw, created_at=now, updated_at=now)
        session.add(comment)
        record_audit_event(session, actor_user_id=user_id, event_type="comment_created",
                           repository_id=assertion.repository_id, matter_id=assertion.matter_id,
                           assertion_id=assertion.id, new_value=comment.id)
    session.commit()
    session.refresh(assertion)
    result = _serialize_assertion(session, assertion)
    result["similar_assertions"] = similar
    result["similar_assertions_total"] = similar_total
    result["similar_assertions_truncated"] = similar_total > len(similar)
    return result


from app.services.assertion_listing import (  # noqa: E402 - list endpoint section
    AssertionListQuery,
    assertion_list_query,
    list_assertions_page,
)


@router.get("")
def list_assertions(
    user_id: str = Depends(get_current_user_id),
    query: AssertionListQuery = Depends(assertion_list_query),
    session: Session = Depends(get_session),
) -> dict:
    """Search, filter, sort and page a matter's assertions (spec §13, §17).

    Query parameters, validation, the SQL and the batched serialization live
    in `app.services.assertion_listing` (audit findings api:13, api:14, ui:1).
    Returns ``{"items", "total", "limit", "offset"}``: without ``limit``
    every match comes back, as before; ``total`` always counts every match.
    Unknown parameters and sort keys get a 422 instead of being ignored.
    """
    _require_matter_member(session, user_id, query.filters.matter_id)
    return list_assertions_page(session, query, user_id=user_id)


@router.get("/{assertion_id}/related")
def get_related_assertions(
    assertion_id: str,
    response: Response,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    """B5 / ruling R10: duplicate/related-assertion surface (spec §8, §13).

    agent:2 / ui:5: the strongest matches (`surface_similar`), each with the
    matched assertion's text, status and type; the X-Total-Count header
    gives the number of all matches."""
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_matter_member(session, user_id, assertion.matter_id)

    others = [row for row in _matter_rows(session, assertion.matter_id) if row.id != assertion.id]
    matches = find_related_assertions(_match_candidate(assertion), [_match_candidate(row) for row in others])
    related, total = surface_similar(matches, {row.id: row for row in others})
    response.headers["X-Total-Count"] = str(total)
    return related


@router.get("/{assertion_id}")
def get_assertion(
    assertion_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_matter_member(session, user_id, assertion.matter_id)
    result = _serialize_assertion(session, assertion)
    # Finding ui:30: name the subject/object (same-matter entities only).
    from app.services.entity_labels import label_entities

    label_entities(session, assertion.matter_id, result)
    result["evidence"] = [_serialize_evidence(e, session) for e in _evidence_rows(session, assertion_id)]
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
    assertion, _revision = _edit_assertion(assertion_id, body, session, user_id)
    return _serialize_assertion(session, assertion)


def _edit_assertion(
    assertion_id: str, body: AssertionPatch, session: Session, user_id: str
) -> tuple[Assertion, AssertionRevision | None]:
    """Apply an edit (PATCH or POST .../revisions): return the assertion and
    the revision the edit created, or None when nothing material changed.

    Order: permission (403), stale base revision (409), validation (422),
    then the no-op guard, then the duplicate rule and the write."""
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_can_modify(session, user_id, assertion)
    # The revision this edit is based on: the caller's expected revision, or
    # (when omitted) the one current when this request read the assertion.
    base_revision_number = assertion.current_revision_number

    if (
        body.expected_revision_number is not None
        and body.expected_revision_number != base_revision_number
    ):
        raise _stale_revision_conflict()

    updates = body.model_dump(exclude_unset=True, exclude=_EDIT_CONTROL_FIELDS)
    if not updates:
        return assertion, None

    new_proposition = None
    try:
        for field in ("proposition", "assertion_type", "subject_entity"):
            if field in updates and updates[field] is None:
                raise ValidationError(f"{field} cannot be null")
        if "proposition" in updates:
            # Track A, item A8 (issue #2 sub-item, gate G4): length cap
            # checked against the raw submitted text, before the sanitizer
            # -- super-linear on hostile markup -- runs, once (review:5).
            validate_text_length(body.proposition, label="proposition")
            new_proposition = sanitize_for_storage(body.proposition)
            validate_proposition_not_empty(new_proposition)
        if "assertion_type" in updates and body.assertion_type != assertion.assertion_type:
            # api:21 / review:4: the assertion's own type, proposed-new or
            # not, is kept as is; a different type follows the creation rule.
            validate_assertion_type(
                body.assertion_type, is_proposed_new=body.assertion_type_is_proposed_new
            )
        if "jurisdiction" in updates and body.jurisdiction is not None:
            _validate_jurisdiction(body.jurisdiction)
        dates_set = [bound for bound in ("effective_from", "effective_to") if bound in updates]
        for bound in dates_set:
            # agent:7 / api:19: stored as UTC instants (offset applied).
            updates[bound] = normalize_effective_datetime(updates[bound], label=bound)
        if dates_set:
            # Checked when the edit sets a date. An edit that leaves the dates
            # alone is not blocked by the stored range, which a row written
            # while offsets were still dropped may hold inverted (api:19).
            validate_effective_dates(updates.get("effective_from", assertion.effective_from),
                                     updates.get("effective_to", assertion.effective_to))
        for field in ("subject_entity", "object_entity"):
            entity = getattr(body, field)
            if entity is not None:
                validate_matter_scoped_entity_id(entity.id, label=field)
                validate_entity(session, entity, assertion.matter_id)
    except (ValidationError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc

    # api:18 / review:3 / review:8 / ui:11: "every material edit creates a
    # new revision" (spec section 3) -- and nothing else does. When every
    # submitted value equals the stored one (a revision_reason alone is not
    # a change) nothing is written: no revision, no audit event, and an
    # accepted assertion keeps its status, review metadata and ratings.
    if not _changed_fields(assertion, _current_revision(session, assertion), updates):
        return assertion, None

    # api:17: an edit is held to the same exact-duplicate rule as creation
    # (it may not take the proposition of another live assertion or of the
    # author's own draft); keeping the current proposition is never a
    # duplicate. Checked here without a lock, and again under it below.
    takes_new_proposition = new_proposition is not None and (
        normalize_proposition(new_proposition) != normalize_proposition(assertion.proposition)
    )
    scan = None
    if takes_new_proposition:
        blocker, scan = scan_for_duplicate(session, assertion.matter_id, new_proposition,
                                           owner_user_id=assertion.author_user_id, exclude_id=assertion.id)
        if blocker is not None:
            raise _duplicate_conflict(blocker)

    # api:0: serialize writers, then re-read the assertion. A concurrent edit
    # of the same base revision has committed if the number moved on; the
    # unique (assertion_id, revision_number) index is the backstop below.
    lock_assertion_writes(session, assertion.matter_id)
    session.refresh(assertion)
    if assertion.current_revision_number != base_revision_number:
        session.rollback()
        raise _stale_revision_conflict()
    try:
        _require_can_modify(session, user_id, assertion)
    except HTTPException:
        session.rollback()
        raise
    if scan is not None:
        blocker = recheck_duplicate(session, scan)
        if blocker is not None:
            session.rollback()
            raise _duplicate_conflict(blocker)

    # Track A, item A2 (issue #2, gate G1): carry the previous revision's
    # raw text forward when this PATCH doesn't touch proposition, so a new
    # revision's raw column is never silently blanked out.
    previous_revision = _current_revision(session, assertion)
    proposition_raw = previous_revision.proposition_raw if previous_revision else None

    now = _now()
    new_revision_number = base_revision_number + 1

    if "proposition" in updates:
        # B5 (qa-fail fix): sanitize like CREATE does -- PATCH is a storage
        # path for the proposition too (gate G10).
        assertion.proposition = new_proposition
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
        assertion.effective_from = updates["effective_from"]
    if "effective_to" in updates:
        assertion.effective_to = updates["effective_to"]

    assertion.current_revision_number = new_revision_number
    assertion.updated_at = now
    previous_status = assertion.status
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
    if assertion.status == "proposed":
        assertion.reviewed_by = None
        assertion.reviewed_at = None
    session.add(revision)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        if _revision_number_taken(session, assertion_id, new_revision_number):
            raise _stale_revision_conflict() from exc
        raise
    record_audit_event(session, actor_user_id=user_id, event_type="assertion_revised",
                       repository_id=assertion.repository_id, matter_id=assertion.matter_id,
                       assertion_id=assertion.id, assertion_revision_id=revision.id,
                       previous_value=str(new_revision_number - 1), new_value=str(new_revision_number))
    if assertion.status != previous_status:  # accepted -> proposed (audit api:4/review:2)
        record_assertion_event(session, assertion, actor_user_id=user_id, event_type="assertion_status_changed",
                               assertion_revision_id=revision.id, previous_value=previous_status,
                               new_value=assertion.status)
    session.commit()
    session.refresh(assertion)
    session.refresh(revision)  # answer with stored values, as GET .../revisions does
    return assertion, revision


# --- Status transitions (submit, withdraw) ------------------------------------
#
# Reviews authoring:1, persistence:1, workflow:1 and workflow:3: a submit or
# withdraw used to check the status it read and then write unconditionally,
# so a review decision that committed in between was silently overwritten
# (an accepted assertion withdrawn by its author, a rejected one back in the
# queue), and two simultaneous submits both recorded the move out of draft.
# Each transition now takes the write lock, re-reads the row and re-runs its
# checks on it (403/409 when they no longer pass), then writes as a
# compare-and-swap on the status and revision it re-read. The audit row is
# written after the swap, so its previous value is the status replaced.

_UNREVIEWED_STATUSES = ("draft", "proposed", "revision_requested")
_CHANGED_MEANWHILE = "assertion was changed by another request; reload it"


def _require_submittable(assertion: Assertion) -> None:
    if assertion.status not in _UNREVIEWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"cannot submit assertion in status '{assertion.status}'",
        )


def _require_withdrawable(assertion: Assertion) -> None:
    if assertion.status not in _UNREVIEWED_STATUSES:
        raise HTTPException(409, "Only an unreviewed assertion can be withdrawn")


def _lock_and_reread(session: Session, assertion: Assertion, check) -> None:
    """Take the write lock (held until the commit), re-read `assertion` and
    run `check()` on the committed row; a refusal rolls back, releasing it."""
    lock_assertion_writes(session, assertion.matter_id)
    session.refresh(assertion)
    try:
        check()
    except HTTPException:
        session.rollback()
        raise


def _write_status(session: Session, assertion: Assertion, **values) -> None:
    """UPDATE the row only while it still has the status and revision of
    `assertion` (as re-read under the lock); otherwise roll back and 409.
    Under the lock the swap cannot miss on SQLite; it is what keeps the write
    conditional where the lock does not exclude every writer (PostgreSQL)."""
    result = session.execute(
        update(Assertion)
        .where(
            Assertion.id == assertion.id,
            Assertion.status == assertion.status,
            Assertion.current_revision_number == assertion.current_revision_number,
        )
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_CHANGED_MEANWHILE)


@router.post("/{assertion_id}/submit")
def submit_assertion(
    assertion_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    _require_can_modify(session, user_id, assertion)
    _require_submittable(assertion)
    # api:16: a draft does not block other authors' identical propositions,
    # so leaving draft is where it first claims one: checked here, and again
    # under the lock below against what was committed since.
    scan = None
    if assertion.status == "draft":
        blocker, scan = scan_for_duplicate(
            session, assertion.matter_id, assertion.proposition,
            owner_user_id=assertion.author_user_id, exclude_id=assertion.id, submitting=True,
        )
        if blocker is not None:
            raise _duplicate_conflict(blocker)

    def still_submittable() -> None:
        _require_can_modify(session, user_id, assertion)
        _require_submittable(assertion)

    _lock_and_reread(session, assertion, still_submittable)
    if assertion.status == "draft":
        blocker = (
            recheck_duplicate(session, scan, assertion.proposition) if scan is not None
            else _blocking_duplicate_id(session, assertion.matter_id, assertion.proposition,
                                        owner_user_id=assertion.author_user_id, exclude_id=assertion.id,
                                        submitting=True)
        )
        if blocker is not None:
            session.rollback()
            raise _duplicate_conflict(blocker)

    previous_status = assertion.status
    now = _now()
    # api:29 / review:12: a proposal awaiting review names no reviewer, as
    # after an edit that returns an assertion to proposed; the earlier
    # decision (e.g. request-revision) stays in the audit trail.
    _write_status(session, assertion, status="proposed", reviewed_by=None, reviewed_at=None,
                  submitted_at=now, updated_at=now)
    record_assertion_event(session, assertion, actor_user_id=user_id, event_type="assertion_submitted",
                           previous_value=previous_status, new_value="proposed")
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
    _require_withdrawable(assertion)

    def still_withdrawable() -> None:
        _require_can_modify(session, user_id, assertion)
        _require_withdrawable(assertion)

    _lock_and_reread(session, assertion, still_withdrawable)
    previous_status = assertion.status
    _write_status(session, assertion, status="withdrawn", updated_at=_now())
    record_assertion_event(session, assertion, actor_user_id=user_id, event_type="assertion_withdrawn",
                           previous_value=previous_status, new_value="withdrawn")
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
    response: Response,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """PATCH's body and semantics, answering with a revision: 201 and the new
    revision, or -- when nothing material changed, so none was created --
    200 and the unchanged current revision, never 201 (api:18, review:3)."""
    assertion, revision = _edit_assertion(assertion_id, body, session, user_id)
    if revision is None:
        response.status_code = status.HTTP_200_OK
        revision = _current_revision(session, assertion)
        if revision is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="revision not found")
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
    return [_serialize_evidence(e, session) for e in rows]


@router.post("/{assertion_id}/evidence", status_code=status.HTTP_201_CREATED)
def add_evidence(
    assertion_id: str,
    body: EvidenceCreate,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    assertion = _get_assertion_or_404(session, assertion_id)
    # api:11: attaching evidence changes what the assertion rests on, so it
    # follows the edit rule (spec section 12): the author of an unreviewed
    # assertion, or a reviewer/admin.
    _require_can_modify(session, user_id, assertion)

    # B5: a resolvable source span must belong to this assertion's matter
    # (spec §7 "a user cannot attach evidence from another inaccessible
    # matter") — see validate_evidence_matter_scope for why an unresolved
    # span id is not itself grounds for rejection here.
    span = validate_span(session, body.source_span_id, assertion.matter_id, assertion.repository_id)
    try:
        validate_evidence_matter_scope(span.matter_id if span is not None else None, assertion.matter_id)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail=str(exc)
        ) from exc

    # Serialize evidence writers so the checks below still hold at commit.
    lock_assertion_writes(session, assertion.matter_id)
    session.refresh(assertion)
    _require_can_modify(session, user_id, assertion)
    if _evidence_exists(session, assertion_id, source_span_id=body.source_span_id,
                        roles=(body.evidence_role,)):
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(f"source span {body.source_span_id} is already attached to this assertion "
                    f"with role '{body.evidence_role}'"),
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
    record_assertion_event(session, assertion, actor_user_id=user_id, event_type="evidence_added",
                           new_value=evidence.id)
    session.commit()
    session.refresh(evidence)
    return _serialize_evidence(evidence, session)


@router.delete("/{assertion_id}/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_evidence(
    assertion_id: str,
    evidence_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user_id),
) -> None:
    assertion = _get_assertion_or_404(session, assertion_id)
    # api:11: removing evidence modifies the assertion: the author of an
    # unreviewed assertion, or a reviewer/admin -- a contributor can no
    # longer strip someone else's (accepted) assertion of its evidence.
    _require_can_modify(session, user_id, assertion)

    lock_assertion_writes(session, assertion.matter_id)
    session.refresh(assertion)
    _require_can_modify(session, user_id, assertion)
    evidence = session.get(AssertionEvidence, evidence_id)
    if evidence is None or evidence.assertion_id != assertion_id:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evidence not found")
    # An accepted assertion stays supported (spec section 2: it cannot be
    # accepted unsupported without a recorded reason, so it is not made
    # unsupported afterwards either).
    if (assertion.status == "accepted" and evidence.evidence_role in SUPPORTING_EVIDENCE_ROLES
            and not _evidence_exists(session, assertion_id, exclude_id=evidence_id,
                                     roles=SUPPORTING_EVIDENCE_ROLES)):
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("cannot remove the last supporting evidence of an accepted assertion; "
                    "attach other supporting evidence first, or return the assertion to review"),
        )

    session.delete(evidence)
    record_assertion_event(session, assertion, actor_user_id=user_id, event_type="evidence_removed",
                           new_value=evidence_id)
    session.commit()
    return None
