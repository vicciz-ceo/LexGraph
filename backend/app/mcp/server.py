"""LexGraph MCP stdio server (sprint 2026-07-26-local-first-platform, Track
C, item C1; gate G7; rulings R5, R6).

Registers three read-only tools against the local SQLAlchemy session,
built with the official `mcp` Python SDK's `MCPServer` (stdio transport):

- `explore(query)` -- a query resolves to matching assertions plus their
  evidence (linked source-span quotes) and relationships (subject/object
  entities, supersession) in ONE bounded call -- CodeGraph-style: fewer
  tokens, less time, better output than crawling the REST API.
- `search(query)` -- bounded list of assertion summaries matching `query`.
- `fetch(assertion_id)` -- full detail for one assertion by id.

Read-only (ruling R5): no write/mutation tool is registered here, and none
of these functions call `session.add`/`session.delete`/`session.commit`.
Zero network I/O (ruling R6, gate G7, item D3's static guardrail): this
module imports none of httpx/requests/urllib.request/aiohttp/socket/
http.client -- only the local `mcp` SDK, SQLAlchemy, and this app's own
models.

Text preference (raw-text awareness, Track A): every proposition surfaced
here is the current revision's byte-exact `proposition_raw` when present,
falling back to the sanitized `proposition` only for rows without a raw
value (e.g. pre-Track-A data) -- the same precedence
`app.routers.assertions` uses for search (`_matches`) and detail
(`_serialize_assertion`) responses, since `proposition_raw` is the system
of record for legal text.

Runnable standalone against a local SQLite file:

    python -m app.mcp.server

(reads `LEXGRAPH_DATABASE_URL` the same way `app.main.create_app` does;
see `docs/mcp-registration.md` for client registration commands.)
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.assertion import Assertion
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_revision import AssertionRevision
from app.models.source_span import SourceSpan

# Bounded output (gate G7: "in one bounded call" -- no unbounded dumps).
_DEFAULT_RESULT_LIMIT = 10


def _current_revision(session: Session, assertion: Assertion) -> AssertionRevision | None:
    return session.execute(
        select(AssertionRevision).where(
            AssertionRevision.assertion_id == assertion.id,
            AssertionRevision.revision_number == assertion.current_revision_number,
        )
    ).scalar_one_or_none()


def _proposition_text(session: Session, assertion: Assertion) -> str:
    """Byte-exact raw proposition when available, sanitized fallback
    otherwise -- see module docstring's "Text preference" note."""
    revision = _current_revision(session, assertion)
    raw = revision.proposition_raw if revision else None
    return raw if raw is not None else assertion.proposition


def _matching_assertions(session: Session, query: str, limit: int) -> list[Assertion]:
    needle = (query or "").strip().lower()
    assertions = session.execute(select(Assertion)).scalars().all()
    if not needle:
        return list(assertions[:limit])
    matched = [a for a in assertions if needle in _proposition_text(session, a).lower()]
    return matched[:limit]


def _evidence_rows(session: Session, assertion_id: str) -> list[AssertionEvidence]:
    return (
        session.execute(
            select(AssertionEvidence).where(AssertionEvidence.assertion_id == assertion_id)
        )
        .scalars()
        .all()
    )


def _span_quote(session: Session, source_span_id: str) -> str | None:
    span = session.get(SourceSpan, source_span_id)
    return span.quote_text if span is not None else None


def _serialize_evidence(session: Session, evidence: AssertionEvidence) -> dict:
    return {
        "id": evidence.id,
        "source_span_id": evidence.source_span_id,
        "evidence_role": evidence.evidence_role,
        "quote_text": _span_quote(session, evidence.source_span_id),
    }


def _serialize_assertion_summary(session: Session, assertion: Assertion) -> dict:
    return {
        "id": assertion.id,
        "matter_id": assertion.matter_id,
        "assertion_type": assertion.assertion_type,
        "proposition": _proposition_text(session, assertion),
        "status": assertion.status,
    }


def _serialize_relationships(assertion: Assertion) -> dict:
    return {
        "subject_entity": {
            "type": assertion.subject_entity_type,
            "id": assertion.subject_entity_id,
        },
        "object_entity": (
            {"type": assertion.object_entity_type, "id": assertion.object_entity_id}
            if assertion.object_entity_type is not None
            else None
        ),
        "superseded_by_assertion_id": assertion.superseded_by_assertion_id,
    }


def _serialize_assertion_detail(session: Session, assertion: Assertion) -> dict:
    detail = _serialize_assertion_summary(session, assertion)
    detail["evidence"] = [
        _serialize_evidence(session, e) for e in _evidence_rows(session, assertion.id)
    ]
    detail["relationships"] = _serialize_relationships(assertion)
    return detail


def create_server(session_factory: sessionmaker[Session]) -> MCPServer:
    """Build a `MCPServer` instance with `explore`/`search`/`fetch` tools
    registered, reading through a fresh `Session` (from `session_factory`)
    per call. No tool here mutates the database (ruling R5: MCP v1 is
    read-only)."""

    server = MCPServer(name="lexgraph")

    @server.tool()
    def explore(query: str) -> dict:
        """Resolve a query to matching assertions, their evidence (linked
        source-span quotes), and relationships (subject/object entities,
        supersession) in one bounded call."""
        session = session_factory()
        try:
            matches = _matching_assertions(session, query, _DEFAULT_RESULT_LIMIT)
            return {
                "query": query,
                "count": len(matches),
                "results": [_serialize_assertion_detail(session, a) for a in matches],
            }
        finally:
            session.close()

    @server.tool()
    def search(query: str) -> dict:
        """Bounded list of assertion summaries whose current proposition
        text matches `query`."""
        session = session_factory()
        try:
            matches = _matching_assertions(session, query, _DEFAULT_RESULT_LIMIT)
            return {
                "query": query,
                "count": len(matches),
                "results": [_serialize_assertion_summary(session, a) for a in matches],
            }
        finally:
            session.close()

    @server.tool()
    def fetch(assertion_id: str) -> dict:
        """Full detail (proposition, evidence, relationships) for one
        assertion by id."""
        session = session_factory()
        try:
            assertion = session.get(Assertion, assertion_id)
            if assertion is None:
                return {"error": f"assertion not found: {assertion_id}"}
            return _serialize_assertion_detail(session, assertion)
        finally:
            session.close()

    return server


def _stdio_main() -> None:  # pragma: no cover -- exercised via manual local run
    """Entrypoint for `python -m app.mcp.server`: wires a session factory
    from this app's usual settings (`LEXGRAPH_DATABASE_URL`, defaulting to
    an in-memory SQLite DB) and serves `explore`/`search`/`fetch` over
    stdio."""
    from app.config import get_settings
    from app.db import make_engine, make_session_factory

    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    server = create_server(session_factory)
    server.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    _stdio_main()
