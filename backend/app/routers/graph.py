"""Graph read surface (sprint 2026-07-25-collaborative-assertions, item B6).

`GET /api/v1/matters/{matter_id}/graph?show_unreviewed=bool` — gate G7:
only accepted assertions appear as accepted relationships in the default
view; proposed/disputed/rejected/superseded appear only in the opt-in
"show unreviewed" mode with a distinct `review_state`; the graph's rating
aggregate is a rebuildable projection, never authoritative (spec §11).

The route re-derives `InMemoryGraphProjection` (`app.graph_projection`,
shared per-app-instance via `app.state.graph_projection`) from the
authoritative `assertions` table on every read — PostgreSQL/SQLite rows
remain the system of record; the projection is disposable and rebuilt in
full each time, never trusted as incremental state.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.graph_projection import InMemoryGraphProjection
from app.models import (
    Assertion,
    AssertionEvidence,
    AssertionRating,
    AssertionRevision,
    MatterRole,
)

router = APIRouter(prefix="/api/v1", tags=["graph"])


def _authenticate(authorization: str | None) -> str:
    try:
        return get_bearer_user_id(authorization)
    except AuthHeaderError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _require_matter_access(session: Session, matter_id: str, user_id: str) -> None:
    row = session.execute(
        select(MatterRole.id).where(
            MatterRole.matter_id == matter_id, MatterRole.user_id == user_id
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=403, detail="no access to this matter")


def _project(assertion: Assertion) -> dict[str, Any]:
    return {
        "id": assertion.id,
        "matter_id": assertion.matter_id,
        "status": assertion.status,
        "subject_entity_type": assertion.subject_entity_type,
        "subject_entity_id": assertion.subject_entity_id,
        "object_entity_type": assertion.object_entity_type,
        "object_entity_id": assertion.object_entity_id,
        "current_revision_number": assertion.current_revision_number,
    }


def _empty_aggregate() -> dict[str, Any]:
    return {"count": 0, "mean": None, "median": None, "distribution": {str(i): 0 for i in range(1, 6)}}


def _rating_aggregate(session: Session, assertion_id: str, revision_number: int | None) -> dict[str, Any]:
    """A rebuildable rating-aggregate projection for one assertion's current
    revision — computed fresh from `assertion_ratings` every call, never
    stored. Kept separate from B2's `app.services.ratings` (a sibling
    track's owned module) so this route never depends on another track's
    in-flight implementation.
    """
    if revision_number is None:
        return _empty_aggregate()

    revision_row = session.execute(
        select(AssertionRevision.id).where(
            AssertionRevision.assertion_id == assertion_id,
            AssertionRevision.revision_number == revision_number,
        )
    ).first()
    if revision_row is None:
        return _empty_aggregate()

    revision_id = revision_row[0]
    strengths = [
        row[0]
        for row in session.execute(
            select(AssertionRating.strength).where(
                AssertionRating.assertion_revision_id == revision_id
            )
        ).all()
    ]
    distribution = {str(i): strengths.count(i) for i in range(1, 6)}
    if not strengths:
        return {"count": 0, "mean": None, "median": None, "distribution": distribution}

    count = len(strengths)
    mean = sum(strengths) / count
    sorted_strengths = sorted(strengths)
    mid = count // 2
    median = (
        sorted_strengths[mid]
        if count % 2
        else (sorted_strengths[mid - 1] + sorted_strengths[mid]) / 2
    )
    return {"count": count, "mean": mean, "median": median, "distribution": distribution}


def _evidence_count(session: Session, assertion_id: str) -> int:
    """Count of `assertion_evidence` rows attached to this assertion (spec
    §11: the graph may surface an evidence count, kept as its own field --
    never merged into the rating aggregate or review-state fields above).
    """
    return session.execute(
        select(func.count()).select_from(AssertionEvidence).where(
            AssertionEvidence.assertion_id == assertion_id
        )
    ).scalar_one()


def _edge(session: Session, projected: dict[str, Any]) -> dict[str, Any]:
    return {
        "assertion_id": projected["id"],
        "review_state": projected["status"],
        "subject_entity_id": projected.get("subject_entity_id"),
        "subject_entity_type": projected.get("subject_entity_type"),
        "object_entity_id": projected.get("object_entity_id"),
        "object_entity_type": projected.get("object_entity_type"),
        "rating_aggregate": _rating_aggregate(
            session, projected["id"], projected.get("current_revision_number")
        ),
        "evidence_count": _evidence_count(session, projected["id"]),
    }


@router.get("/matters/{matter_id}/graph")
def get_matter_graph(
    matter_id: str,
    request: Request,
    show_unreviewed: bool = False,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    session_factory = request.app.state.session_factory
    session: Session = session_factory()
    try:
        actor_user_id = _authenticate(authorization)
        _require_matter_access(session, matter_id, actor_user_id)

        all_assertions = session.execute(select(Assertion)).scalars().all()
        projection: InMemoryGraphProjection = request.app.state.graph_projection
        projection.rebuild([_project(a) for a in all_assertions])

        visible = projection.get_visible_assertions(matter_id, show_unreviewed=show_unreviewed)
        edges = [_edge(session, projected) for projected in visible]
        return {"matter_id": matter_id, "edges": edges}
    finally:
        session.close()
