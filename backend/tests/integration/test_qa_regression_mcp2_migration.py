"""QA regression coverage — sprint 2026-07-29-mcp2-migration.

Independent QA pass (separate agent from the Developer who ported
`backend/app/mcp/server.py` from `FastMCP` to `mcp.server.mcpserver.MCPServer`
in commit 3009266, and raised the `mcp` floor to `>=2.0` in the same commit).
These tests close two edge-case gaps neither the Planner's RED tests nor the
Developer's per-item verification exercised, following the existing patterns
in test_mcp_tools_live.py / test_mcp_search_fetch_tools.py /
test_qa_regression_local_first_platform.py (real SDK dispatch, no
hand-written stand-in; `app` fixture only, since none of this needs seeded
data):

- The async/sync dispatch surface `_stdio_main` depends on. Every other MCP
  test in this repo drives `list_tools`/`call_tool` directly against a
  server built by `create_server`, but nothing pins that `create_server`'s
  *return value* actually carries the exact `list_tools`/`call_tool`/`run`
  surface `_stdio_main` (`# pragma: no cover`, hence untested by any other
  path) calls. A future SDK release renaming or reshaping any of these three
  — the same class of change the `FastMCP` -> `MCPServer` rename itself
  was — would break the stdio entrypoint silently, since nothing else in
  this suite imports or exercises `.run`.
- The missing-required-argument edge call. Every existing `search`/
  `explore`/`fetch` test — including
  `test_mcp_fetch_of_nonexistent_assertion_id_does_not_crash` — calls with a
  complete, valid `arguments` dict; that test's "not found" case is a
  *business-logic* error the tool body itself returns as a plain dict,
  which still flattens via `.content` like any successful call. None probe
  the SDK's own argument validation for a call missing a required field.
  Empirically verified against this exact server (not assumed): mcp 2.x's
  `call_tool` does NOT wrap a missing-argument call into a flattenable
  `CallToolResult` the way the not-found case is — it raises
  `mcp.server.mcpserver.exceptions.ToolError` before any `CallToolResult`
  is ever constructed. This pins that actual contract, so a future SDK
  version that silently swallowed the validation error into a
  malformed/empty success payload instead of raising (a worse failure mode
  for a stdio client than a clean exception) would be caught here.
"""

from __future__ import annotations

import asyncio
import inspect

import pytest

from mcp.server.mcpserver.exceptions import ToolError


# --- create_server's return value must expose _stdio_main's dependency surface --


def test_create_server_exposes_the_list_tools_call_tool_and_run_surface_stdio_needs(app):
    """`_stdio_main` calls `server.run(transport="stdio")` on whatever
    `create_server` returns, and every other MCP test in this repo drives
    `list_tools`/`call_tool` as coroutines via `asyncio.run(...)`. Pin all
    three directly so a future rename would fail here instead of only in an
    untested manual stdio run.
    """
    from app.mcp.server import create_server

    server = create_server(app.state.session_factory)

    assert inspect.iscoroutinefunction(server.list_tools)
    assert inspect.iscoroutinefunction(server.call_tool)
    assert callable(server.run) and not inspect.iscoroutinefunction(server.run)
    assert "transport" in inspect.signature(server.run).parameters


# --- Missing-required-argument edge call (distinct from the not-found case) ---


@pytest.mark.parametrize("tool_name", ["search", "explore"])
def test_call_tool_with_missing_required_query_argument_raises_tool_error(app, tool_name):
    """`search`/`explore` both require `query`; no existing test omits it.
    Confirms the SDK raises `ToolError` naming the missing field (caught and
    handled by callers, never silently producing a malformed/empty
    `CallToolResult`) rather than returning something that would flatten
    "cleanly" the way the business-logic not-found case does.
    """
    from app.mcp.server import create_server

    server = create_server(app.state.session_factory)

    with pytest.raises(ToolError, match="query"):
        asyncio.run(server.call_tool(tool_name, {}))
