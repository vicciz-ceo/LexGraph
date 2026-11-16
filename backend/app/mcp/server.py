"""Local MCP discovery and opt-in agent authoring.

Without a configured actor, legacy lookup tools read the entire local database.
With an actor, reads are matter-scoped and validated proposal creation is enabled.
See docs/mcp-registration.md and docs/AGENT_GUIDE.md.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.agent_cli import assertion_search
from app.models.assertion import Assertion
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_revision import AssertionRevision
from app.models.source_span import SourceSpan
from app.models.matter_role import MatterRole

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


def _matching_assertions(session: Session, query: str, limit: int, user_id: str | None = None) -> list[Assertion]:
    stmt = assertion_search(query)
    if user_id is not None:
        stmt = stmt.where(Assertion.matter_id.in_(select(MatterRole.matter_id).where(MatterRole.user_id == user_id)))
    return list(session.scalars(stmt.order_by(Assertion.id).limit(limit)))


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
        "origin": assertion.origin,
        "repository_id": assertion.repository_id,
        "current_revision_number": assertion.current_revision_number,
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


def create_server(session_factory: sessionmaker[Session], *, agent_user_id: str | None = None) -> MCPServer:
    """Build local tools; a configured actor enables validated, scoped suggestions."""

    server = MCPServer(name="lexgraph")

    @server.tool()
    def explore(query: str) -> dict:
        """Resolve a query to matching assertions (up to 10), their evidence
        (linked source-span quotes), and relationships (subject/object
        entities, supersession) in one bounded call. Matching is a
        case-insensitive substring of the current proposition text."""
        session = session_factory()
        try:
            matches = _matching_assertions(session, query, _DEFAULT_RESULT_LIMIT, agent_user_id)
            return {
                "query": query,
                "count": len(matches),
                "results": [_serialize_assertion_detail(session, a) for a in matches],
            }
        finally:
            session.close()

    @server.tool()
    def search(query: str) -> dict:
        """Bounded list (up to 10) of assertion summaries whose current
        proposition text contains `query` (case-insensitive substring)."""
        session = session_factory()
        try:
            matches = _matching_assertions(session, query, _DEFAULT_RESULT_LIMIT, agent_user_id)
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
            if assertion is not None and agent_user_id is not None:
                allowed = session.scalar(select(MatterRole.id).where(
                    MatterRole.user_id == agent_user_id, MatterRole.matter_id == assertion.matter_id))
                if allowed is None:
                    assertion = None
            if assertion is None:
                return {"error": f"assertion not found: {assertion_id}"}
            return _serialize_assertion_detail(session, assertion)
        finally:
            session.close()

    @server.tool()
    def assertion_guide() -> dict:
        """Learn how to create evidence-backed suggestions and retrieve the exact JSON schema."""
        from app.agent_cli import guide
        result = guide()
        result["submissions_enabled"] = agent_user_id is not None
        return result

    if agent_user_id:
        @server.tool()
        def agent_context(matter_id: str | None = None, query: str = "", limit: int = 20, offset: int = 0) -> dict:
            """Discover authorized matters, real entity IDs, source quotes and existing assertions."""
            from app.agent_cli import context
            with session_factory() as session:
                return context(session, agent_user_id, matter_id, query, limit, offset)

        @server.tool()
        def suggest_assertion(payload: dict) -> dict:
            """Submit a model-suggested draft/proposal. Call assertion_guide for schema, agent_context for IDs.
            The configured account must have contributor access. Never accepts assertions or rates them.
            """
            from app.routers.agents import AgentAssertionCreate, suggest_assertion as submit
            from fastapi.encoders import jsonable_encoder
            with session_factory() as session:
                return jsonable_encoder(submit(AgentAssertionCreate.model_validate(payload), session, agent_user_id))

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
    import os
    server = create_server(session_factory, agent_user_id=os.environ.get("LEXGRAPH_AGENT_USER_ID") or None)
    server.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    _stdio_main()
