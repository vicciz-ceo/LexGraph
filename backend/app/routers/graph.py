"""Graph read surface (sprint 2026-07-25-collaborative-assertions, item B6).

`GET /api/v1/matters/{matter_id}/graph?show_unreviewed=bool&limit=&offset=` --
gate G7: only accepted assertions appear as accepted relationships in the
default view; the opt-in "show unreviewed" mode adds proposed, disputed,
rejected and superseded assertions with a distinct `review_state` (spec §11;
drafts, withdrawn and revision-requested assertions never appear). The graph's
rating aggregate is a rebuildable projection, never authoritative.

Each request builds its OWN `InMemoryGraphProjection` (`app.graph_projection`)
from the requested matter's authoritative rows: PostgreSQL/SQLite stays the
system of record and the projection stays disposable. Rebuilding the one
app-wide projection from every matter on every request (audit findings
api:23/api:14) raced between concurrent requests and cost a full table read.
The response is bounded (`limit`, default 1000) and reports `total`; rating
aggregates and evidence counts are loaded in batches, not per edge.

`GET /api/v1/matters/{matter_id}/assertion-stats` serves matter-level
assertion aggregates (spec §19) so dashboards need not download every
assertion (audit finding ui:1).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import AuthHeaderError, get_bearer_user_id
from app.graph_projection import DEFAULT_VIEW_STATES, UNREVIEWED_VIEW_STATES, InMemoryGraphProjection
from app.models import Assertion, MatterRole
from app.services.assertion_listing import (
    AssertionStatsQuery,
    assertion_stats,
    assertion_stats_query,
    current_revisions,
    evidence_roles,
    insertion_order,
    ratings_for_revisions,
    reject_unknown_query_params,
)
from app.services.paging import MAX_OFFSET

router = APIRouter(prefix="/api/v1", tags=["graph"])

GRAPH_DEFAULT_LIMIT = 1000
GRAPH_MAX_LIMIT = 5000
_GRAPH_QUERY_PARAMS = frozenset({"show_unreviewed", "limit", "offset"})


def _authenticate(authorization: str | None) -> str:
    try:
        return get_bearer_user_id(authorization)
    except AuthHeaderError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _authenticated_user(authorization: str | None = Header(default=None)) -> str:
    return _authenticate(authorization)


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


def _rating_aggregate(strengths: list[int]) -> dict[str, Any]:
    """A rebuildable rating-aggregate projection for one assertion's current
    revision -- computed fresh from `assertion_ratings` on every read, never
    stored."""
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


@router.get("/matters/{matter_id}/graph")
def get_matter_graph(
    matter_id: str,
    request: Request,
    show_unreviewed: bool = False,
    limit: int = Query(default=GRAPH_DEFAULT_LIMIT, ge=1, le=GRAPH_MAX_LIMIT),
    offset: int = Query(default=0, ge=0, le=MAX_OFFSET),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    session_factory = request.app.state.session_factory
    session: Session = session_factory()
    try:
        actor_user_id = _authenticate(authorization)
        reject_unknown_query_params(request, _GRAPH_QUERY_PARAMS)
        _require_matter_access(session, matter_id, actor_user_id)

        states = UNREVIEWED_VIEW_STATES if show_unreviewed else DEFAULT_VIEW_STATES
        visible = (Assertion.matter_id == matter_id, Assertion.status.in_(states))
        total = session.scalar(select(func.count(Assertion.id)).where(*visible))
        rows = session.scalars(
            select(Assertion).where(*visible).order_by(*insertion_order(session)).limit(limit).offset(offset)
        ).all()

        projection = InMemoryGraphProjection()  # request-local, never shared
        projection.rebuild([_project(a) for a in rows])
        projected = projection.get_visible_assertions(matter_id, show_unreviewed=show_unreviewed)

        ids = [p["id"] for p in projected]
        revisions = current_revisions(session, matter_id, ids)
        ratings = ratings_for_revisions(session, matter_id, [revision_id for revision_id, _ in revisions.values()])
        roles = evidence_roles(session, matter_id, ids)

        edges = []
        for p in projected:
            revision_id = revisions.get(p["id"], (None, None))[0]
            strengths = [r.strength for r in ratings.get(revision_id, [])] if revision_id else []
            edges.append({
                "assertion_id": p["id"],
                "review_state": p["status"],
                "subject_entity_id": p.get("subject_entity_id"),
                "subject_entity_type": p.get("subject_entity_type"),
                "object_entity_id": p.get("object_entity_id"),
                "object_entity_type": p.get("object_entity_type"),
                "rating_aggregate": _rating_aggregate(strengths),
                # Spec §11: evidence count is its own field, never merged into
                # the rating aggregate or the review state.
                "evidence_count": len(roles.get(p["id"], [])),
            })
        return {"matter_id": matter_id, "edges": edges, "total": total, "limit": limit, "offset": offset}
    finally:
        session.close()


@router.get("/matters/{matter_id}/assertion-stats")
def get_assertion_stats(
    matter_id: str,
    request: Request,
    actor_user_id: str = Depends(_authenticated_user),
    query: AssertionStatsQuery = Depends(assertion_stats_query),
) -> dict[str, Any]:
    """Counts by status, origin, type, evidence status and author; model
    confidence and current-revision rating aggregates; creation counts per
    caller-supplied time bucket. Accepts the list endpoint's filters
    (except `q`), so e.g. `author_user_id` gives one user's statistics.
    """
    session: Session = request.app.state.session_factory()
    try:
        _require_matter_access(session, matter_id, actor_user_id)
        return assertion_stats(session, query, user_id=actor_user_id)
    finally:
        session.close()
