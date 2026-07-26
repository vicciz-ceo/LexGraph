"""Track C, item C1 (continued) — LexGraph MCP `search` and `fetch` tools
(gate G7). See test_mcp_tools_live.py's module docstring for the shared
fidelity/no-network rationale; this file exercises the other two tools
through the same real `call_tool` dispatch.
"""

from __future__ import annotations

import asyncio

from tests.conftest import assertion_payload
from tests.integration.test_mcp_tools_live import _flatten_to_text


def test_search_finds_a_seeded_assertion_by_text(app, client, matter_with_users):
    from app.mcp.server import create_server

    m = matter_with_users
    payload = assertion_payload(
        m["matter_id"],
        m["repository_id"],
        proposition="A uniquely identifiable MCP search fixture proposition.",
    )
    created = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assertion_id = created.json()["id"]

    server = create_server(app.state.session_factory)
    result = asyncio.run(server.call_tool("search", {"query": "MCP search fixture"}))
    text = _flatten_to_text(result)
    assert assertion_id in text


def test_fetch_returns_full_assertion_detail_by_id(app, client, matter_with_users):
    from app.mcp.server import create_server

    m = matter_with_users
    payload = assertion_payload(
        m["matter_id"], m["repository_id"], proposition="A fetchable MCP fixture proposition."
    )
    created = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assertion_id = created.json()["id"]

    server = create_server(app.state.session_factory)
    result = asyncio.run(server.call_tool("fetch", {"assertion_id": assertion_id}))
    text = _flatten_to_text(result)
    assert "A fetchable MCP fixture proposition." in text
