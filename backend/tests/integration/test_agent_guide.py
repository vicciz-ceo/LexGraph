"""The submission guide matches the interface that serves it (agent:8, agent:9).

MCP `assertion_guide` names MCP tools and parameters, CLI `schema` keeps the
CLI wording, and both expose the jurisdiction vocabulary the validator
enforces, so an agent need not call the web API or guess codes.
"""
from __future__ import annotations

import asyncio
import re

import pytest

import app.mcp as mcp_package
from app.agent_cli import guide
from app.mcp.server import _stdio_main, create_server
from app.services.jurisdiction import JURISDICTION_CODES, validate_jurisdiction
from tests.integration.agent_surface_helpers import agent_env, cli_json, run_cli, tool_json


def _tools(server) -> dict:
    return {tool.name: tool for tool in asyncio.run(server.list_tools())}


def test_mcp_guide_names_only_mcp_tools_and_their_parameters(app, matter_with_users):
    server = create_server(app.state.session_factory, agent_user_id=matter_with_users["contributor_id"])
    result = tool_json(server, "assertion_guide")
    tools = _tools(server)
    text = " ".join(result["workflow"] + result["notes"])
    assert "agent_context" in text and "suggest_assertion" in text, text
    assert {"agent_context", "suggest_assertion"} <= set(tools)
    assert "--" not in text and not re.search(r"\b(use|with) (context|suggest)\b", text, re.I), text
    assert {"matter_id", "query", "limit", "offset"} <= set(tools["agent_context"].input_schema["properties"])
    assert "payload" in tools["suggest_assertion"].input_schema["properties"]
    assert "payload" in text and "offset" in text and "matter_id" in text, text
    assert result["submissions_enabled"] is True and "submissions_disabled_reason" not in result


@pytest.mark.parametrize("actor", [None, ""])
def test_mcp_guide_without_an_actor_explains_how_to_enable_submissions(app, actor):
    result = tool_json(create_server(app.state.session_factory, agent_user_id=actor), "assertion_guide")
    assert result["submissions_enabled"] is False
    reason = result["submissions_disabled_reason"]
    assert "LEXGRAPH_AGENT_USER_ID" in reason and "agent_context" in reason and "suggest_assertion" in reason


def test_mcp_tool_descriptions_document_parameters_and_errors(app, matter_with_users):
    tools = _tools(create_server(app.state.session_factory, agent_user_id=matter_with_users["contributor_id"]))
    assert all(word in tools["agent_context"].description for word in ("matter_id", "offset", "query"))
    assert "payload" in tools["suggest_assertion"].description and "409" in tools["suggest_assertion"].description
    assert "case-insensitive" in tools["search"].description


def test_cli_schema_keeps_the_cli_workflow(app):
    result = cli_json(run_cli("schema", env=agent_env()))
    text = " ".join(result["workflow"])
    assert "context --matter-id" in text and "--offset" in text and "suggest" in text
    assert "agent_context" not in text and "submissions_enabled" not in result
    assert result["workflow"] == guide()["workflow"] == guide("cli")["workflow"]


def test_cli_and_mcp_guides_share_schema_and_vocabularies(app):
    mcp_guide = tool_json(create_server(app.state.session_factory), "assertion_guide")
    cli_guide = cli_json(run_cli("schema", env=agent_env()))
    for key in ("schema", "assertion_types", "entity_types", "jurisdictions"):
        assert mcp_guide[key] == cli_guide[key], key
    with pytest.raises(ValueError):
        guide("http")


def test_guide_lists_the_jurisdiction_vocabulary_in_canonical_order():
    result = guide()
    assert result["jurisdictions"] == list(JURISDICTION_CODES)
    for code in result["jurisdictions"]:
        validate_jurisdiction(code)


def test_schema_constrains_jurisdiction_but_keeps_it_optional():
    schema = guide()["schema"]
    field = schema["properties"]["jurisdiction"]
    assert "jurisdiction" not in schema.get("required", [])
    branches = field["anyOf"]
    assert {"type": "null"} in branches
    assert [b for b in branches if b.get("type") == "string"][0]["enum"] == list(JURISDICTION_CODES)
    assert "IL" in field["description"] and "US-IL" in field["description"]


def test_package_and_entrypoint_docstrings_describe_the_authoring_tools():
    assert "no write/mutation tools" not in mcp_package.__doc__
    assert "suggest_assertion" in mcp_package.__doc__ and "agent_context" in mcp_package.__doc__
    assert "suggest_assertion" in _stdio_main.__doc__ and "agent_context" in _stdio_main.__doc__
