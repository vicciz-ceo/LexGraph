"""LexGraph MCP package (sprint 2026-07-26-local-first-platform, Track C, item C1).

A local stdio MCP server (official `mcp` Python SDK) that maps the
LexGraph database for agent sessions, CodeGraph-style: `explore`,
`search`, and `fetch` tools reading the local SQLAlchemy session/models
directly. Read-only (ruling R5) — no write/mutation tools. Zero network
I/O (ruling R6, gate G7's guardrail, item D3): this package imports none
of httpx/requests/urllib.request/aiohttp/socket/http.client.

See `app.mcp.server` for the implementation and `create_server`.
"""

from __future__ import annotations
