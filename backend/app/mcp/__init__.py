"""LexGraph MCP package (sprint 2026-07-26-local-first-platform, Track C, item C1).

A local stdio MCP server (official `mcp` Python SDK) that maps the
LexGraph database for agent sessions, CodeGraph-style: `explore`,
`search`, `fetch` and `assertion_guide`, reading the local SQLAlchemy
session/models directly. Read-only by default (ruling R5). With
`LEXGRAPH_AGENT_USER_ID` set, every read is scoped to that account's
matters and two more tools are registered: `agent_context` (discovery) and
`suggest_assertion`, which creates draft/proposed model suggestions only,
through the same validated transaction as the CLI and REST API (spec
"Local agent authoring and lawyer completion"). Zero network I/O (ruling R6,
gate G7's guardrail, item D3): this package imports none of
httpx/requests/urllib.request/aiohttp/socket/http.client.

See `app.mcp.server` for the implementation and `create_server`.
"""

from __future__ import annotations
