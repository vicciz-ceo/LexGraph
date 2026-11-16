"""Local MCP discovery and opt-in agent authoring.

Without a configured actor, legacy lookup tools read the entire local database.
With an actor, reads are matter-scoped and validated proposal creation is enabled.
Anticipated failures reach the agent as `ToolError` text holding the CLI's JSON
error object: mcp >= 2.1 replaces any other exception with a bare
"Error executing tool <name>". That includes what the SDK refuses before a tool
body runs: arguments that do not match the tool's signature, and a tool this
server does not offer. See docs/mcp-registration.md and docs/AGENT_GUIDE.md.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.agent_cli import assertion_search, context, error_body, guide, require_actor, validation_issues
from app.agent_database import ConfigurationError
from app.models.assertion import Assertion
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_revision import AssertionRevision
from app.models.source_span import SourceSpan
from app.models.matter_role import MatterRole
from app.models.user import User
from app.notifications import notify_submission
from app.routers.agents import AgentAssertionCreate, suggest_assertion as submit_suggestion

# Bounded output (gate G7: "in one bounded call" -- no unbounded dumps).
_DEFAULT_RESULT_LIMIT = 10
_ACTOR_TOOLS = ("agent_context", "suggest_assertion")
_SUBMISSIONS_DISABLED = (
    "agent_context and suggest_assertion are not available: this server was started without "
    "LEXGRAPH_AGENT_USER_ID. Ask the user to register it with the id of a dedicated agent account "
    "that has contributor membership (see docs/mcp-registration.md).")


def _json(body: dict) -> str:
    return json.dumps(jsonable_encoder(body), ensure_ascii=False)


@contextmanager
def _reported_errors() -> Iterator[None]:
    """Turn anticipated failures into a ToolError carrying {"error", "status"}.
    Anything else stays a crash: logged server-side, withheld from the client."""
    try:
        yield
    except (HTTPException, ValidationError, SQLAlchemyError, ConfigurationError) as exc:
        raise ToolError(_json(error_body(exc))) from exc


def _argument_error(tool: str, exc: ValidationError) -> dict:
    """The 422 for arguments that do not match the tool's signature."""
    issues = validation_issues(exc)
    error = "Invalid arguments: " + "; ".join(f"{issue['field']}: {issue['message']}" for issue in issues)
    if tool == "suggest_assertion":  # most often its fields sent beside payload instead of inside it
        error += (". Send the whole submission as one JSON object in the payload argument, "
                  "matching assertion_guide's schema")
    return {"error": error, "status": 422, "issues": issues}


class _Server(MCPServer):
    """An MCPServer whose every failed call ends in the JSON error object (review agent:2).

    The SDK checks the tool name and validates the arguments against the tool's
    signature before the tool body (and `_reported_errors`) runs. It reported those
    failures as "Unknown tool: <name>" and as pydantic's multi-line text, which
    echoes the rejected values and carries no status."""

    def __init__(self, *, submissions_enabled: bool):
        super().__init__(name="lexgraph")
        self._submissions_enabled = submissions_enabled

    async def call_tool(self, name: str, arguments: dict[str, Any], context=None):
        offered = sorted(tool.name for tool in await self.list_tools())
        if name not in offered:
            if name in _ACTOR_TOOLS and not self._submissions_enabled:
                body = {"error": _SUBMISSIONS_DISABLED, "status": 401}
            else:
                listing = ", ".join(offered[:-1]) + f" and {offered[-1]}"
                body = {"error": f"unknown tool {name!r}; this server offers {listing}", "status": 400}
            raise ToolError(f"Error executing tool {name}: {_json(body)}")
        try:
            return await super().call_tool(name, arguments, context)
        except UnexpectedToolError:
            raise  # a crash: the SDK logs it and withholds the details
        except ToolError as exc:
            if not isinstance(exc.__cause__, ValidationError):
                raise  # the tool body's own failure, already the JSON object
            cause = exc.__cause__
            raise ToolError(f"Error executing tool {name}: {_json(_argument_error(name, cause))}") from cause


def _current_revision(session: Session, assertion: Assertion) -> AssertionRevision | None:
    return session.execute(
        select(AssertionRevision).where(
            AssertionRevision.assertion_id == assertion.id,
            AssertionRevision.revision_number == assertion.current_revision_number,
        )
    ).scalar_one_or_none()


def _proposition_text(session: Session, assertion: Assertion) -> str:
    """Byte-exact raw proposition of the current revision when stored, else
    the sanitized column (rows from before raw text was kept)."""
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

    agent_user_id = agent_user_id or None  # "" is no actor, for scoping as for registration
    server = _Server(submissions_enabled=agent_user_id is not None)

    @server.tool()
    def explore(query: str) -> dict:
        """Resolve a query to matching assertions (up to 10), their evidence
        (linked source-span quotes), and relationships (subject/object
        entities, supersession) in one bounded call. Matching is a
        case-insensitive substring of the current proposition text."""
        with _reported_errors(), session_factory() as session:
            matches = _matching_assertions(session, query, _DEFAULT_RESULT_LIMIT, agent_user_id)
            return {
                "query": query,
                "count": len(matches),
                "results": [_serialize_assertion_detail(session, a) for a in matches],
            }

    @server.tool()
    def search(query: str) -> dict:
        """Bounded list (up to 10) of assertion summaries whose current
        proposition text contains `query` (case-insensitive substring)."""
        with _reported_errors(), session_factory() as session:
            matches = _matching_assertions(session, query, _DEFAULT_RESULT_LIMIT, agent_user_id)
            return {
                "query": query,
                "count": len(matches),
                "results": [_serialize_assertion_summary(session, a) for a in matches],
            }

    @server.tool()
    def fetch(assertion_id: str) -> dict:
        """Full detail (proposition, evidence, relationships) for one
        assertion by id."""
        with _reported_errors(), session_factory() as session:
            assertion = session.get(Assertion, assertion_id)
            if assertion is not None and agent_user_id is not None:
                allowed = session.scalar(select(MatterRole.id).where(
                    MatterRole.user_id == agent_user_id, MatterRole.matter_id == assertion.matter_id))
                if allowed is None:
                    assertion = None
            if assertion is None:
                return {"error": f"assertion not found: {assertion_id}"}
            return _serialize_assertion_detail(session, assertion)

    @server.tool()
    def assertion_guide() -> dict:
        """Start here: the workflow, vocabularies (assertion types, jurisdictions)
        and the exact JSON schema for suggest_assertion's payload."""
        result = guide("mcp")
        result["submissions_enabled"] = agent_user_id is not None
        if agent_user_id is None:
            result["submissions_disabled_reason"] = _SUBMISSIONS_DISABLED
        return result

    if agent_user_id is not None:
        @server.tool()
        def agent_context(matter_id: str | None = None, query: str = "", limit: int = 20, offset: int = 0) -> dict:
            """Without matter_id: your user and matter memberships (matter id, role,
            repository_id). With matter_id: that matter's documents and articles
            (entities, documents first), source spans with full quote_text, and
            existing assertions, each filtered by query (case-insensitive substring)
            and paged with limit (1-100) and offset."""
            with _reported_errors(), session_factory() as session:
                return context(session, agent_user_id, matter_id, query, limit, offset)

        @server.tool()
        def suggest_assertion(payload: dict) -> dict:
            """Submit a model-suggested draft/proposal. payload is one JSON object
            matching assertion_guide's schema, with IDs from agent_context; the
            configured account needs contributor access. Never accepts or rates
            assertions. A failure is an error result ending in JSON {"error",
            "status"}: 409 duplicate names the existing assertion (inspect it, do
            not reword); 422 explains the invalid field ("issues"); 403 missing role,
            also for a matter ID that does not exist (check it against agent_context);
            404 a repository that does not exist."""
            with _reported_errors(), session_factory() as session:
                require_actor(session, agent_user_id)
                body = AgentAssertionCreate.model_validate(payload)
                result = jsonable_encoder(submit_suggestion(body, session, agent_user_id))
                # No HTTP request, so no notification hook: tell the matter's
                # reviewers here (idempotent per submission, never raises).
                notify_submission(session, result["id"], agent_user_id)
                return result

    return server


def _stdio_main() -> None:  # pragma: no cover -- run as a subprocess by the tests
    """Entrypoint for `python -m app.mcp.server`: serves explore, search, fetch
    and assertion_guide over stdio, plus agent_context and suggest_assertion
    when LEXGRAPH_AGENT_USER_ID names a user. LEXGRAPH_DATABASE_URL must be an
    initialized LexGraph database; otherwise the process exits with a one-line
    reason on stderr (stdout carries JSON-RPC) instead of serving tools that
    all fail."""
    from app.agent_database import open_database
    from app.config import get_settings
    from app.db import make_session_factory

    agent_user_id = os.environ.get("LEXGRAPH_AGENT_USER_ID") or None
    try:
        engine = open_database(get_settings().database_url)
        with Session(engine) as session:
            if agent_user_id and session.get(User, agent_user_id) is None:
                raise ConfigurationError(
                    f"LEXGRAPH_AGENT_USER_ID {agent_user_id!r} is not a user in {engine.url.database}; "
                    "use the id of a dedicated agent account created in Admin")
    except ConfigurationError as exc:
        raise SystemExit(f"lexgraph MCP server: {exc}") from None
    server = create_server(make_session_factory(engine), agent_user_id=agent_user_id)
    server.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    _stdio_main()
