"""Filtered, sorted and paginated assertion reads (spec §13, §17, §19).

Backs ``GET /api/v1/assertions`` and ``GET /api/v1/matters/{id}/assertion-stats``
(audit findings api:13, api:14 and ui:1):

* Every filter and sort key is evaluated in SQL. A page of a large matter
  costs a count, one page query and a fixed number of batched lookups, never
  queries per row. The exception is ``q``: it is matched in Python against
  the current revision's raw proposition so that it keeps Python's Unicode
  case folding (SQLite's ``lower()`` and ``LIKE`` fold ASCII only).
* Unknown query parameters and sort keys get a 422. They are never ignored.
* Ties are broken by insertion order (the SQLite ``rowid``), so pages are
  stable even though one pipeline run stamps thousands of rows with a single
  ``created_at``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy import and_, case, func, literal_column, or_, select
from sqlalchemy.orm import Session, aliased

from app.models.assertion import Assertion
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_rating import AssertionRating
from app.models.assertion_revision import AssertionRevision
from app.models.audit_event import AuditEvent
from app.models.user import User
from app.services.jurisdiction import validate_jurisdiction
from app.services.ratings import compute_rating_summary, compute_standing
from app.services.validation import ValidationError

SUPPORTING_EVIDENCE_ROLES = ("supports", "primary_basis", "secondary_basis")
LIST_MAX_LIMIT = 500
# Largest id list bound into one IN (...). A bigger set is read with one
# matter-scoped query instead of many chunks, so the statement count stays
# constant whatever the page size.
_IN_LIMIT = 500
_MAX_BUCKET_EDGES = 101


# --- Query parameters ---------------------------------------------------------


@dataclass(frozen=True)
class AssertionFilters:
    """Spec §10/§17 filters. Empty strings mean "not filtered", as before."""

    matter_id: str
    q: str | None = None
    origin: str | None = None
    status: str | None = None
    assertion_type: str | None = None
    author_user_id: str | None = None
    subject_entity_type: str | None = None
    subject_entity_id: str | None = None
    object_entity_type: str | None = None
    object_entity_id: str | None = None
    jurisdiction: str | None = None
    evidence_status: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    last_activity_from: datetime | None = None
    last_activity_to: datetime | None = None
    effective_on: date | None = None
    min_average_rating: float | None = None
    min_rating_count: int | None = None
    unrated_by_me: bool | None = None
    my_rating: int | None = None


FILTER_QUERY_PARAMS = frozenset(AssertionFilters.__dataclass_fields__)
LIST_QUERY_PARAMS = FILTER_QUERY_PARAMS | {"sort", "limit", "offset"}
# The stats route takes matter_id from its path, so a query copy would be ignored.
STATS_QUERY_PARAMS = (FILTER_QUERY_PARAMS - {"q", "matter_id"}) | {"created_bucket_edges"}


def reject_unknown_query_params(request: Request, allowed: frozenset[str]) -> None:
    unknown = sorted(set(request.query_params) - allowed)
    if unknown:
        raise HTTPException(
            422,
            f"unsupported query parameter(s): {', '.join(unknown)}. "
            f"Supported: {', '.join(sorted(allowed))}",
        )


def assertion_filters(
    matter_id: str,
    q: str | None = None,
    origin: str | None = None,
    status: str | None = None,
    assertion_type: str | None = None,
    author_user_id: str | None = None,
    subject_entity_type: str | None = None,
    subject_entity_id: str | None = None,
    object_entity_type: str | None = None,
    object_entity_id: str | None = None,
    jurisdiction: str | None = None,
    evidence_status: str | None = Query(
        default=None, pattern="^(evidenced|unsupported|awaiting_evidence)$"
    ),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    last_activity_from: datetime | None = None,
    last_activity_to: datetime | None = None,
    effective_on: date | None = None,
    min_average_rating: float | None = None,
    min_rating_count: int | None = None,
    unrated_by_me: bool | None = None,
    my_rating: int | None = Query(default=None, ge=1, le=5),
) -> AssertionFilters:
    """FastAPI dependency declaring the shared filter parameters.

    ``matter_id`` is a query parameter on ``/assertions`` and the path
    parameter on ``/matters/{matter_id}/assertion-stats``.
    """
    if jurisdiction:
        try:
            validate_jurisdiction(jurisdiction)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AssertionFilters(
        matter_id=matter_id,
        q=q,
        origin=origin,
        status=status,
        assertion_type=assertion_type,
        author_user_id=author_user_id,
        subject_entity_type=subject_entity_type,
        subject_entity_id=subject_entity_id,
        object_entity_type=object_entity_type,
        object_entity_id=object_entity_id,
        jurisdiction=jurisdiction,
        evidence_status=evidence_status,
        created_from=created_from,
        created_to=created_to,
        last_activity_from=last_activity_from,
        last_activity_to=last_activity_to,
        effective_on=effective_on,
        min_average_rating=min_average_rating,
        min_rating_count=min_rating_count,
        unrated_by_me=unrated_by_me,
        my_rating=my_rating,
    )


@dataclass(frozen=True)
class AssertionListQuery:
    filters: AssertionFilters
    sort: tuple[tuple[str, bool], ...] = ()
    limit: int | None = None
    offset: int = 0


def assertion_list_query(
    request: Request,
    filters: AssertionFilters = Depends(assertion_filters),
    sort: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=LIST_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> AssertionListQuery:
    """Filters plus ``sort``, ``limit`` and ``offset``.

    ``limit`` is optional with no default, so existing callers that expect
    the whole match set keep receiving it.
    """
    reject_unknown_query_params(request, LIST_QUERY_PARAMS)
    return AssertionListQuery(filters=filters, sort=parse_sort(sort), limit=limit, offset=offset)


@dataclass(frozen=True)
class AssertionStatsQuery:
    filters: AssertionFilters
    created_bucket_edges: tuple[datetime, ...] = ()


def assertion_stats_query(
    request: Request,
    filters: AssertionFilters = Depends(assertion_filters),
    created_bucket_edges: str | None = None,
) -> AssertionStatsQuery:
    reject_unknown_query_params(request, STATS_QUERY_PARAMS)
    return AssertionStatsQuery(filters=filters, created_bucket_edges=parse_bucket_edges(created_bucket_edges))


def parse_bucket_edges(raw: str | None) -> tuple[datetime, ...]:
    """Comma-separated ISO-8601 instants, strictly increasing. A naive value is UTC."""
    if not raw:
        return ()
    edges = []
    for token in raw.split(","):
        try:
            value = datetime.fromisoformat(token.strip())
        except ValueError as exc:
            raise HTTPException(
                422,
                f"created_bucket_edges: {token.strip()!r} is not an ISO-8601 date-time "
                "(write UTC as 'Z', or percent-encode '+' as %2B)",
            ) from exc
        edges.append(value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc))
    if not 2 <= len(edges) <= _MAX_BUCKET_EDGES:
        raise HTTPException(422, f"created_bucket_edges takes 2 to {_MAX_BUCKET_EDGES} instants")
    if any(later <= earlier for earlier, later in zip(edges, edges[1:])):
        raise HTTPException(422, "created_bucket_edges must be strictly increasing")
    return tuple(edges)


# --- Derived per-assertion values, evaluated in SQL ---------------------------


class _Derived:
    """Values computed per assertion in SQL, outer-joined the first time a
    filter or sort key needs them. Every join is one-to-one, so counts and
    pages stay exact.
    """

    def __init__(self, matter_id: str, user_id: str) -> None:
        self.matter_id = matter_id
        self.user_id = user_id
        self._joins: list[tuple[object, object]] = []
        self._targets: dict[str, object] = {}

    def apply(self, stmt):
        for target, onclause in self._joins:
            stmt = stmt.outerjoin(target, onclause)
        return stmt

    def _join(self, key: str, build: Callable[[], tuple[object, object]]):
        if key not in self._targets:
            target, onclause = build()
            self._joins.append((target, onclause))
            self._targets[key] = target
        return self._targets[key]

    def current_revision_id(self):
        def build():
            # min(id) keeps the join one-to-one even if a revision number was
            # ever written twice.
            sub = (
                select(
                    AssertionRevision.assertion_id.label("assertion_id"),
                    func.min(AssertionRevision.id).label("revision_id"),
                )
                .join(Assertion, _is_current_revision())
                .where(Assertion.matter_id == self.matter_id)
                .group_by(AssertionRevision.assertion_id)
                .subquery("current_revision")
            )
            return sub, sub.c.assertion_id == Assertion.id

        return self._join("current_revision", build).c.revision_id

    def proposition_raw(self):
        revision_id = self.current_revision_id()

        def build():
            row = aliased(AssertionRevision, name="current_revision_row")
            return row, row.id == revision_id

        return self._join("current_revision_row", build).proposition_raw

    def _rating_stats(self):
        revision_id = self.current_revision_id()

        def build():
            sub = (
                select(
                    AssertionRating.assertion_revision_id.label("revision_id"),
                    func.count(AssertionRating.id).label("n_ratings"),
                    func.avg(AssertionRating.strength).label("average_strength"),
                )
                .where(AssertionRating.matter_id == self.matter_id)
                .group_by(AssertionRating.assertion_revision_id)
                .subquery("rating_stats")
            )
            return sub, sub.c.revision_id == revision_id

        return self._join("rating_stats", build)

    def average_rating(self):
        """Mean strength on the current revision, NULL when it is unrated."""
        return self._rating_stats().c.average_strength

    def rating_count(self):
        return func.coalesce(self._rating_stats().c.n_ratings, 0)

    def my_rating(self):
        revision_id = self.current_revision_id()

        def build():
            mine = aliased(AssertionRating, name="my_rating")
            return mine, and_(mine.assertion_revision_id == revision_id, mine.user_id == self.user_id)

        return self._join("my_rating", build).strength

    def evidence_status(self):
        def build():
            sub = (
                select(
                    AssertionEvidence.assertion_id.label("assertion_id"),
                    func.count(AssertionEvidence.id).label("n_evidence"),
                    func.sum(
                        case((AssertionEvidence.evidence_role.in_(SUPPORTING_EVIDENCE_ROLES), 1), else_=0)
                    ).label("n_supporting"),
                )
                .join(Assertion, Assertion.id == AssertionEvidence.assertion_id)
                .where(Assertion.matter_id == self.matter_id)
                .group_by(AssertionEvidence.assertion_id)
                .subquery("evidence_stats")
            )
            return sub, sub.c.assertion_id == Assertion.id

        sub = self._join("evidence_stats", build)
        return case(
            (sub.c.n_evidence.is_(None), "awaiting_evidence"),
            (sub.c.n_supporting > 0, "evidenced"),
            else_="unsupported",
        )

    def last_activity(self):
        """The later of ``updated_at`` and the newest audit event (rating,
        comment, review decision, edit, evidence change) on the assertion."""

        def build():
            sub = (
                select(
                    AuditEvent.assertion_id.label("assertion_id"),
                    func.max(AuditEvent.timestamp).label("last_event_at"),
                )
                .where(AuditEvent.matter_id == self.matter_id, AuditEvent.assertion_id.is_not(None))
                .group_by(AuditEvent.assertion_id)
                .subquery("activity")
            )
            return sub, sub.c.assertion_id == Assertion.id

        last_event_at = self._join("activity", build).c.last_event_at
        return case((last_event_at > Assertion.updated_at, last_event_at), else_=Assertion.updated_at)

    def author_name(self):
        def build():
            author = aliased(User, name="author")
            return author, author.id == Assertion.author_user_id

        return self._join("author", build).display_name


def _is_current_revision():
    return and_(
        Assertion.id == AssertionRevision.assertion_id,
        Assertion.current_revision_number == AssertionRevision.revision_number,
    )


def _conditions(f: AssertionFilters, d: _Derived) -> list:
    conditions = [Assertion.matter_id == f.matter_id]
    for column, value in (
        (Assertion.origin, f.origin),
        (Assertion.status, f.status),
        (Assertion.assertion_type, f.assertion_type),
        (Assertion.author_user_id, f.author_user_id),
        (Assertion.subject_entity_type, f.subject_entity_type),
        (Assertion.subject_entity_id, f.subject_entity_id),
        (Assertion.object_entity_type, f.object_entity_type),
        (Assertion.object_entity_id, f.object_entity_id),
        (Assertion.jurisdiction, f.jurisdiction),
    ):
        if value:
            conditions.append(column == value)
    # Instant ranges are half-open: [from, to).
    if f.created_from is not None:
        conditions.append(Assertion.created_at >= f.created_from)
    if f.created_to is not None:
        conditions.append(Assertion.created_at < f.created_to)
    if f.last_activity_from is not None:
        conditions.append(d.last_activity() >= f.last_activity_from)
    if f.last_activity_to is not None:
        conditions.append(d.last_activity() < f.last_activity_to)
    if f.effective_on is not None:
        # In effect on that calendar day; an open bound is unbounded.
        day = datetime.combine(f.effective_on, time.min)
        conditions.append(or_(Assertion.effective_from.is_(None), Assertion.effective_from < day + timedelta(days=1)))
        conditions.append(or_(Assertion.effective_to.is_(None), Assertion.effective_to >= day))
    if f.evidence_status:
        conditions.append(d.evidence_status() == f.evidence_status)
    if f.min_rating_count is not None:
        conditions.append(d.rating_count() >= f.min_rating_count)
    if f.min_average_rating is not None:
        conditions.append(d.average_rating() >= f.min_average_rating)
    if f.unrated_by_me:
        conditions.append(d.my_rating().is_(None))
    if f.my_rating is not None:
        conditions.append(d.my_rating() == f.my_rating)
    return conditions


# --- Sorting --------------------------------------------------------------------

# name -> (expression, nullable) pairs. Nullable keys sort NULL last in both
# directions: an unrated assertion is not the lowest-rated one.
SORT_KEYS: dict[str, Callable[[_Derived], list[tuple[object, bool]]]] = {
    "created_at": lambda d: [(Assertion.created_at, False)],
    "updated_at": lambda d: [(Assertion.updated_at, False)],
    "last_activity": lambda d: [(d.last_activity(), False)],
    "proposition": lambda d: [(Assertion.proposition, False)],
    "assertion_type": lambda d: [(Assertion.assertion_type, False)],
    "subject": lambda d: [(Assertion.subject_entity_type, False), (Assertion.subject_entity_id, False)],
    "object": lambda d: [(Assertion.object_entity_type, True), (Assertion.object_entity_id, True)],
    "origin": lambda d: [(Assertion.origin, False)],
    "author": lambda d: [(d.author_name(), True), (Assertion.author_user_id, False)],
    "status": lambda d: [(Assertion.status, False)],
    "evidence_status": lambda d: [(d.evidence_status(), False)],
    "average_rating": lambda d: [(d.average_rating(), True)],
    "rating_count": lambda d: [(d.rating_count(), False)],
    "my_rating": lambda d: [(d.my_rating(), True)],
    "jurisdiction": lambda d: [(Assertion.jurisdiction, True)],
    "effective_from": lambda d: [(Assertion.effective_from, True)],
    "effective_to": lambda d: [(Assertion.effective_to, True)],
}


def parse_sort(sort: str | None) -> tuple[tuple[str, bool], ...]:
    """``-key`` sorts descending; several keys are comma-separated."""
    if not sort:
        return ()
    keys = []
    for token in (part.strip() for part in sort.split(",")):
        descending = token.startswith("-")
        name = token[1:] if descending else token
        if name not in SORT_KEYS:
            raise HTTPException(
                422,
                f"unsupported sort key {token!r}. Supported: {', '.join(SORT_KEYS)} "
                "(prefix '-' for descending; separate several keys with commas)",
            )
        keys.append((name, descending))
    return tuple(keys)


def insertion_order(session: Session) -> list:
    """Final tiebreaker: insertion order on SQLite, as the unsorted list always
    returned; created_at then id elsewhere."""
    if session.get_bind().dialect.name == "sqlite":
        return [literal_column("assertions.rowid")]
    return [Assertion.created_at, Assertion.id]


def _order_by(keys: Iterable[tuple[str, bool]], d: _Derived, session: Session) -> list:
    clauses = []
    for name, descending in keys:
        for expression, nullable in SORT_KEYS[name](d):
            if nullable:
                clauses.append(expression.is_(None))
            clauses.append(expression.desc() if descending else expression.asc())
    return clauses + insertion_order(session)


# --- Batched lookups for a set of rows -----------------------------------------


@dataclass(frozen=True)
class RatingRow:
    user_id: str
    strength: int
    rationale: str | None
    updated_at: datetime


def current_revisions(
    session: Session, matter_id: str, assertion_ids: Sequence[str]
) -> dict[str, tuple[str, str | None]]:
    """``assertion_id -> (current revision id, its proposition_raw)``.

    Rows written by the definition-link pipeline have no revision row and are
    simply absent.
    """
    if not assertion_ids:
        return {}
    stmt = (
        select(AssertionRevision.assertion_id, AssertionRevision.id, AssertionRevision.proposition_raw)
        .join(Assertion, _is_current_revision())
        .where(Assertion.matter_id == matter_id)
        .order_by(AssertionRevision.id)
    )
    if len(assertion_ids) <= _IN_LIMIT:
        stmt = stmt.where(Assertion.id.in_(assertion_ids))
    wanted = set(assertion_ids)
    revisions: dict[str, tuple[str, str | None]] = {}
    for assertion_id, revision_id, raw in session.execute(stmt):
        if assertion_id in wanted:
            revisions.setdefault(assertion_id, (revision_id, raw))
    return revisions


def ratings_for_revisions(
    session: Session, matter_id: str, revision_ids: Sequence[str]
) -> dict[str, list[RatingRow]]:
    if not revision_ids:
        return {}
    stmt = select(
        AssertionRating.assertion_revision_id,
        AssertionRating.user_id,
        AssertionRating.strength,
        AssertionRating.rationale,
        AssertionRating.updated_at,
    ).where(AssertionRating.matter_id == matter_id)
    if len(revision_ids) <= _IN_LIMIT:
        stmt = stmt.where(AssertionRating.assertion_revision_id.in_(revision_ids))
    wanted = set(revision_ids)
    ratings: dict[str, list[RatingRow]] = defaultdict(list)
    for revision_id, user_id, strength, rationale, updated_at in session.execute(stmt):
        if revision_id in wanted:
            ratings[revision_id].append(RatingRow(user_id, strength, rationale, updated_at))
    return ratings


def evidence_roles(session: Session, matter_id: str, assertion_ids: Sequence[str]) -> dict[str, list[str]]:
    if not assertion_ids:
        return {}
    stmt = (
        select(AssertionEvidence.assertion_id, AssertionEvidence.evidence_role)
        .join(Assertion, Assertion.id == AssertionEvidence.assertion_id)
        .where(Assertion.matter_id == matter_id)
    )
    if len(assertion_ids) <= _IN_LIMIT:
        stmt = stmt.where(AssertionEvidence.assertion_id.in_(assertion_ids))
    wanted = set(assertion_ids)
    roles: dict[str, list[str]] = defaultdict(list)
    for assertion_id, role in session.execute(stmt):
        if assertion_id in wanted:
            roles[assertion_id].append(role)
    return roles


def _evidence_status(roles: list[str] | None) -> str:
    if not roles:
        return "awaiting_evidence"
    if any(role in SUPPORTING_EVIDENCE_ROLES for role in roles):
        return "evidenced"
    return "unsupported"


@dataclass
class _RowContext:
    """Everything a list item needs beyond the assertion row, loaded in a
    fixed number of queries for the whole page."""

    user_id: str
    revisions: dict[str, tuple[str, str | None]] = field(default_factory=dict)
    ratings: dict[str, list[RatingRow]] = field(default_factory=dict)
    roles: dict[str, list[str]] = field(default_factory=dict)
    provenance: dict[str, dict | None] = field(default_factory=dict)
    last_event_at: dict[str, datetime] = field(default_factory=dict)

    @classmethod
    def load(cls, session: Session, matter_id: str, user_id: str, rows: Sequence[Assertion]) -> _RowContext:
        context = cls(user_id=user_id)
        ids = [a.id for a in rows]
        if not ids:
            return context
        context.revisions = current_revisions(session, matter_id, ids)
        context.ratings = ratings_for_revisions(
            session, matter_id, [revision_id for revision_id, _ in context.revisions.values()]
        )
        context.roles = evidence_roles(session, matter_id, ids)

        model_ids = [a.id for a in rows if a.origin == "model_suggested"]
        if model_ids:
            stmt = (
                select(AuditEvent.assertion_id, AuditEvent.new_value)
                .where(AuditEvent.matter_id == matter_id, AuditEvent.event_type == "assertion_agent_provenance")
                .order_by(AuditEvent.timestamp, AuditEvent.id)
            )
            if len(model_ids) <= _IN_LIMIT:
                stmt = stmt.where(AuditEvent.assertion_id.in_(model_ids))
            wanted = set(model_ids)
            for assertion_id, new_value in session.execute(stmt):
                if assertion_id in wanted and assertion_id not in context.provenance:
                    context.provenance[assertion_id] = json.loads(new_value) if new_value else None

        stmt = (
            select(AuditEvent.assertion_id, func.max(AuditEvent.timestamp))
            .where(AuditEvent.matter_id == matter_id, AuditEvent.assertion_id.is_not(None))
            .group_by(AuditEvent.assertion_id)
        )
        if len(ids) <= _IN_LIMIT:
            stmt = stmt.where(AuditEvent.assertion_id.in_(ids))
        wanted = set(ids)
        context.last_event_at = {
            assertion_id: at for assertion_id, at in session.execute(stmt) if assertion_id in wanted
        }
        return context

    def list_item(self, a: Assertion) -> dict:
        """The detail serializer's keys, plus three list-only additions."""
        revision_id, proposition_raw = self.revisions.get(a.id, (None, None))
        ratings = self.ratings.get(revision_id, []) if revision_id else []
        summary = compute_rating_summary([r.strength for r in ratings])
        mine = next((r for r in ratings if r.user_id == self.user_id), None)
        last_event_at = self.last_event_at.get(a.id)
        return {
            "id": a.id,
            "organization_id": a.organization_id,
            "repository_id": a.repository_id,
            "matter_id": a.matter_id,
            "assertion_type": a.assertion_type,
            "proposition": a.proposition,
            "proposition_raw": proposition_raw,
            "subject_entity": {"type": a.subject_entity_type, "id": a.subject_entity_id},
            "object_entity": (
                {"type": a.object_entity_type, "id": a.object_entity_id}
                if a.object_entity_type is not None
                else None
            ),
            "origin": a.origin,
            "agent_provenance": self.provenance.get(a.id) if a.origin == "model_suggested" else None,
            "status": a.status,
            "standing": compute_standing(
                a.status, [{"user_id": r.user_id, "strength": r.strength} for r in ratings], a.author_user_id
            ),
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
            "evidence_status": _evidence_status(self.roles.get(a.id)),
            # List-only: the current revision's rating aggregate (every rating,
            # the author's included, as on the detail page; `standing` above
            # still excludes the author), so a list needs no request per row.
            "ratings_summary": (
                {
                    "assertion_id": a.id,
                    "assertion_revision_id": revision_id,
                    "average": summary["average"],
                    "median": summary["median"],
                    "count": summary["count"],
                    "distribution": summary["distribution"],
                }
                if summary is not None
                else None
            ),
            "current_user_rating": (
                {"strength": mine.strength, "rationale": mine.rationale, "updated_at": mine.updated_at}
                if mine is not None
                else None
            ),
            "last_activity_at": (
                last_event_at if last_event_at is not None and last_event_at > a.updated_at else a.updated_at
            ),
        }


# --- Endpoints' bodies -----------------------------------------------------------


def _assertions_by_id(session: Session, matter_id: str, ids: Sequence[str]) -> list[Assertion]:
    stmt = select(Assertion).where(Assertion.matter_id == matter_id)
    if len(ids) <= _IN_LIMIT:
        stmt = stmt.where(Assertion.id.in_(ids))
    wanted = set(ids)
    found = {a.id: a for a in session.scalars(stmt) if a.id in wanted}
    return [found[assertion_id] for assertion_id in ids if assertion_id in found]


def list_assertions_page(session: Session, query: AssertionListQuery, *, user_id: str) -> dict:
    """``{"items", "total", "limit", "offset"}``; ``total`` counts every match."""
    f, limit, offset = query.filters, query.limit, query.offset
    page = _Derived(f.matter_id, user_id)
    conditions = _conditions(f, page)
    order = _order_by(query.sort, page, session)

    if f.q:
        needle = f.q.strip().lower()
        raw = page.proposition_raw()
        stmt = page.apply(select(Assertion.id, Assertion.proposition, raw).select_from(Assertion))
        matched = [
            assertion_id
            for assertion_id, proposition, raw_text in session.execute(stmt.where(*conditions).order_by(*order))
            # Track A, item A6: the raw text, so a term the sanitizer dropped
            # still finds the assertion.
            if needle in ((raw_text if raw_text is not None else proposition) or "").lower()
        ]
        total = len(matched)
        window = matched[offset:] if limit is None else matched[offset:offset + limit]
        rows = _assertions_by_id(session, f.matter_id, window) if window else []
    else:
        stmt = page.apply(select(Assertion).select_from(Assertion)).where(*conditions).order_by(*order)
        if limit is None and offset == 0:
            rows = list(session.scalars(stmt))
            total = len(rows)
        else:
            counting = _Derived(f.matter_id, user_id)
            count_conditions = _conditions(f, counting)
            total = session.scalar(
                counting.apply(select(func.count(Assertion.id)).select_from(Assertion)).where(*count_conditions)
            )
            rows = list(session.scalars(stmt.limit(limit).offset(offset)))

    context = _RowContext.load(session, f.matter_id, user_id, rows)
    return {
        "items": [context.list_item(a) for a in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def assertion_stats(session: Session, query: AssertionStatsQuery, *, user_id: str) -> dict:
    """Matter-level aggregates for the Analytics and Profile pages (spec §19),
    over the same filters as the list, in five queries whatever the size."""
    f = query.filters
    d = _Derived(f.matter_id, user_id)
    conditions = _conditions(f, d)

    def rows(*columns, group_by=()):
        # Each call registers the derived values it needs before the joins are
        # applied; all joins are one-to-one, so later queries may reuse them.
        stmt = d.apply(select(*columns).select_from(Assertion)).where(*conditions)
        return session.execute(stmt.group_by(*group_by) if group_by else stmt).all()

    by_status: dict[str, int] = defaultdict(int)
    by_origin: dict[str, int] = defaultdict(int)
    by_origin_status: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_type: dict[str, int] = defaultdict(int)
    authors: dict[str, dict] = {}
    confidence: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
    groups = (Assertion.status, Assertion.origin, Assertion.assertion_type, Assertion.author_user_id)
    for status, origin, assertion_type, author, n, n_confidence, sum_confidence in rows(
        *groups, func.count(Assertion.id), func.count(Assertion.confidence), func.sum(Assertion.confidence),
        group_by=groups,
    ):
        by_status[status] += n
        by_origin[origin] += n
        by_origin_status[origin][status] += n
        by_type[assertion_type] += n
        author_entry = authors.setdefault(author, {"user_id": author, "total": 0, "by_status": defaultdict(int)})
        author_entry["total"] += n
        author_entry["by_status"][status] += n
        if n_confidence:
            confidence[origin][0] += n_confidence
            confidence[origin][1] += float(sum_confidence)

    evidence_status = d.evidence_status()
    by_evidence_status = {status: n for status, n in rows(evidence_status, func.count(Assertion.id), group_by=(evidence_status,))}

    average_rating = d.average_rating()
    ((rated_assertions, n_ratings, average_of_averages),) = rows(
        func.count(average_rating), func.sum(d.rating_count()), func.avg(average_rating)
    )

    edges = query.created_bucket_edges
    buckets = []
    if edges:
        pairs = list(zip(edges, edges[1:]))
        (counts,) = rows(*(
            func.sum(case((and_(Assertion.created_at >= start, Assertion.created_at < end), 1), else_=0))
            for start, end in pairs
        ))
        buckets = [{"start": start, "end": end, "count": int(count or 0)} for (start, end), count in zip(pairs, counts)]

    return {
        "matter_id": f.matter_id,
        "total": sum(by_status.values()),
        "by_status": dict(by_status),
        "by_origin": dict(by_origin),
        "by_origin_status": {origin: dict(statuses) for origin, statuses in by_origin_status.items()},
        "by_type": dict(by_type),
        "by_evidence_status": by_evidence_status,
        "authors": [
            {**entry, "by_status": dict(entry["by_status"])}
            for entry in sorted(authors.values(), key=lambda e: (-e["total"], e["user_id"]))
        ],
        "confidence_by_origin": {
            origin: {"count": n, "average": total / n} for origin, (n, total) in confidence.items()
        },
        "ratings": {
            "rated_assertions": rated_assertions,
            "ratings": int(n_ratings or 0),
            # float(): PostgreSQL's avg() is numeric, i.e. a Decimal.
            "average_of_averages": float(average_of_averages) if average_of_averages is not None else None,
        },
        "created_buckets": buckets,
    }
