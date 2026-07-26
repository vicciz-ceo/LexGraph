"""Track C, item C1 — LexGraph MCP stdio server: explore tool, no network
(gate G7, ruling R6: official `mcp` Python SDK).

`app.mcp.server` does not exist yet -- ModuleNotFoundError is the expected
RED signal. `create_server(session_factory)` must return a real
`mcp.server.fastmcp.FastMCP` instance with an `explore` tool registered;
this test invokes it through the SDK's own `call_tool` dispatch (the real
registered handler), not a hand-written stand-in, against a local SQLite DB
seeded via the existing API -- no network I/O anywhere in the call.
"""

from __future__ import annotations

import asyncio

from tests.conftest import assertion_payload


def _flatten_to_text(result) -> str:
    """`FastMCP.call_tool` may return a dict (structured output) or a
    sequence of MCP content blocks (each carrying a `.text` attribute) --
    flatten either shape to one string for content assertions, since the
    exact envelope is an implementation choice this test does not pin."""
    if isinstance(result, dict):
        return str(result)
    parts = []
    for block in result:
        parts.append(getattr(block, "text", str(block)))
    return " ".join(parts)


def _seed_assertion_with_evidence(client, db_session, m: dict) -> tuple[str, str]:
    from tests.conftest import seed_document, seed_source_span

    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(
        db_session,
        document_id=doc_id,
        matter_id=m["matter_id"],
        quote_text="Clause 8.4 governs the notification exception.",
    )
    payload = assertion_payload(
        m["matter_id"],
        m["repository_id"],
        proposition="Clause 8.4 creates a distinctive exception for the MCP explore probe.",
        evidence=[{"source_span_id": span_id, "evidence_role": "primary_basis"}],
    )
    created = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert created.status_code == 201
    return created.json()["id"], span_id


def test_mcp_server_registers_explore_search_fetch_tools(app):
    from app.mcp.server import create_server

    server = create_server(app.state.session_factory)
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert {"explore", "search", "fetch"} <= names


def test_explore_returns_assertion_evidence_and_relationships_in_one_bounded_call(
    app, client, db_session, matter_with_users
):
    from app.mcp.server import create_server

    m = matter_with_users
    assertion_id, span_id = _seed_assertion_with_evidence(client, db_session, m)

    server = create_server(app.state.session_factory)
    result = asyncio.run(
        server.call_tool("explore", {"query": "distinctive exception for the MCP explore probe"})
    )
    text = _flatten_to_text(result)

    assert assertion_id in text
    assert span_id in text
    assert "evidence" in text.lower()
