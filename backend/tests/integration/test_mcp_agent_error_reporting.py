"""MCP tools report anticipated failures to the agent (agent:0, review:0).

mcp >= 2.1 forwards only `ToolError` text to the client; any other exception
arrives as the bare "Error executing tool <name>". These tests use the real
client path (in-process `Client(server)`, plus one stdio session against
`python -m app.mcp.server`) because that is what an MCP client receives.
"""
from __future__ import annotations

import asyncio
import sys

import pytest
from mcp import Client, StdioServerParameters
from sqlalchemy import func, select

from app.db import make_engine, make_session_factory
from app.mcp.server import create_server
from app.models.assertion import Assertion
from tests.conftest import seed_document, seed_matter, seed_source_span
from tests.integration.agent_surface_helpers import agent_env, call_tool, tool_error


@pytest.fixture
def suggestion(db_session, matter_with_users):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"], title="Service agreement")
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"],
                            quote_text="Confidentiality shall survive termination.")
    return dict(repository_id=m["repository_id"], matter_id=m["matter_id"], assertion_type="SURVIVES_TERMINATION",
                proposition="The confidentiality obligation survives termination.",
                subject_entity={"type": "Document", "id": doc},
                evidence=[{"source_span_id": span, "evidence_role": "primary_basis"}],
                agent={"platform": "claude-code"}, confidence=0.8)


def _count(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(Assertion))


def test_duplicate_reports_409_with_the_existing_assertion_id(app, db_session, matter_with_users, suggestion):
    server = create_server(app.state.session_factory, agent_user_id=matter_with_users["contributor_id"])
    is_error, text = call_tool(server, "suggest_assertion", {"payload": suggestion})
    assert not is_error, text
    existing_id = db_session.scalar(select(Assertion.id))
    body = tool_error(server, "suggest_assertion", {"payload": suggestion})
    assert body["status"] == 409 and "duplicate" in body["error"] and existing_id in body["error"], body
    # Structured, like the REST 409 body (XREQ-33): no need to parse the text.
    assert body["existing_assertion_id"] == existing_id, body
    assert _count(db_session) == 1


@pytest.mark.parametrize(("change", "field"), [
    ({"confidence": 1.5}, "confidence"),
    ({"agent": None}, "agent"),
    ({"save_as": "accepted"}, "save_as"),
    ({"origin": "user_suggested"}, "origin"),
])
def test_schema_violations_report_422_and_the_failing_field(app, db_session, matter_with_users, suggestion, change, field):
    server = create_server(app.state.session_factory, agent_user_id=matter_with_users["contributor_id"])
    body = tool_error(server, "suggest_assertion", {"payload": {**suggestion, **change}})
    assert body["status"] == 422, body
    assert field in body["error"] and field in [issue["field"] for issue in body["issues"]], body
    assert _count(db_session) == 0


@pytest.mark.parametrize(("change", "fragment"), [
    ({"evidence": [{"source_span_id": "missing", "evidence_role": "supports"}]}, "Evidence must resolve"),
    ({"subject_entity": {"type": "Document", "id": "not-present"}}, "Entity must exist"),
    ({"jurisdiction": "Israel"}, "jurisdiction 'Israel'"),
    ({"assertion_type": "IMPLIES"}, "controlled vocabulary"),
])
def test_domain_validation_reports_422_and_the_reason(app, db_session, matter_with_users, suggestion, change, fragment):
    server = create_server(app.state.session_factory, agent_user_id=matter_with_users["contributor_id"])
    body = tool_error(server, "suggest_assertion", {"payload": {**suggestion, **change}})
    assert body["status"] == 422 and fragment in body["error"], body
    assert _count(db_session) == 0


def test_permission_failures_report_403(app, db_session, matter_with_users, suggestion):
    m = matter_with_users
    outsider = create_server(app.state.session_factory, agent_user_id=m["outsider_id"])
    body = tool_error(outsider, "suggest_assertion", {"payload": suggestion})
    assert body == {"error": "not permitted to suggest assertions", "status": 403}
    assert tool_error(outsider, "agent_context", {"matter_id": m["matter_id"]}) == {
        "error": "no access to matter", "status": 403}
    other_matter = seed_matter(db_session, repository_id=m["repository_id"])
    member = create_server(app.state.session_factory, agent_user_id=m["contributor_id"])
    assert tool_error(member, "agent_context", {"matter_id": other_matter})["status"] == 403
    assert _count(db_session) == 0


@pytest.mark.parametrize(
    "arguments", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 2**31}, {"offset": 10**20}]
)
def test_agent_context_reports_invalid_paging(app, matter_with_users, arguments):
    server = create_server(app.state.session_factory, agent_user_id=matter_with_users["contributor_id"])
    assert tool_error(server, "agent_context", arguments) == {
        "error": "limit must be 1..100 and offset 0..2147483647", "status": 422}


def test_unknown_actor_reports_401(app, matter_with_users):
    server = create_server(app.state.session_factory, agent_user_id="no-such-user")
    assert tool_error(server, "agent_context") == {"error": "unknown user", "status": 401}


@pytest.mark.parametrize("tool", ["search", "explore", "fetch"])
def test_database_failures_report_500_without_sql_text(tool):
    engine = make_engine("sqlite://")  # no schema: every query fails
    server = create_server(make_session_factory(engine))
    arguments = {"assertion_id": "x"} if tool == "fetch" else {"query": "termination"}
    body = tool_error(server, tool, arguments)
    engine.dispose()
    assert body["status"] == 500 and "no such table" in body["error"], body
    assert "SELECT" not in body["error"] and "sqlalche.me" not in body["error"], body


def test_stdio_server_reports_the_duplicate_to_a_real_client(app, client, matter_with_users, suggestion, tmp_path):
    """The registered entrypoint, driven over real stdio by the installed SDK."""
    m = matter_with_users
    assert client.post("/api/v1/agent/assertions", json=suggestion, headers=m["contributor_headers"]).status_code == 201
    params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp.server"], cwd=str(tmp_path),
                                   env=agent_env(str(app.state.engine.url), m["contributor_id"]))

    async def run():
        async with Client(params, read_timeout_seconds=60) as session:
            names = {tool.name for tool in (await session.list_tools()).tools}
            return names, await session.call_tool("suggest_assertion", {"payload": suggestion})

    names, result = asyncio.run(run())
    assert {"agent_context", "suggest_assertion"} <= names
    text = " ".join(block.text for block in result.content)
    existing_id = client.get("/api/v1/assertions", params={"matter_id": m["matter_id"]},
                             headers=m["reviewer_headers"]).json()["items"][0]["id"]
    assert result.is_error and '"status": 409' in text and existing_id in text, text
