# Sprint log — 2026-07-29-mcp2-migration (append-only, never auto-loaded)

Overflow sink for full test output, QA transcripts, per-round narration, and
the agent roster. See the contract for working state.

## Agent roster

(manager appends `role → agentId` at every spawn)

## Planner pass — 2026-07-29

Summary (≤10 lines): Installed `mcp==2.0.0` into `backend/.venv` and probed it
empirically. `mcp.server.fastmcp.FastMCP` was renamed in-package to
`mcp.server.mcpserver.MCPServer` (also re-exported as `mcp.server.MCPServer`)
— same constructor (`name=...`), same `.tool()`/`.list_tools()`/`.call_tool()`
(both still coroutines)/`.run(transport="stdio")` surface. No new third-party
dependency needed; not an architectural fork (R2: no escalation). One real
behavior change: `call_tool()` now returns a `CallToolResult` object exposing
`.content` (a list of blocks with `.text`) instead of a bare dict/sequence —
re-pointed the shared `_flatten_to_text` test helper (and its QA-file inline
duplicate) to check `.content` first, since a `CallToolResult` is itself
iterable as name/value pairs (pydantic model) and would otherwise silently
flatten to garbled-but-accidentally-matching text. R3 (network imports):
investigated and NOT escalating — see below.

### mcp 2.0 API research (empirical, in `backend/.venv`)

```
$ .venv/bin/pip install 'mcp==2.0.0'
...
Successfully installed httpcore2-2.9.1 httpx2-2.9.1 mcp-2.0.0 mcp-types-2.0.0 opentelemetry-api-1.44.0 truststore-0.10.4
```

Pip printed a resolver warning during this install:
`lexgraph-backend 0.1.0 requires mcp<2.0,>=1.0, but you have mcp 2.0.0 which
is incompatible.` This is stale **editable-install metadata** cached in
`.venv/lib/python3.13/site-packages/lexgraph_backend-0.1.0.dist-info` from
some earlier `pip install -e .` in this venv's history (consistent with R1's
note that a `<2.0` pin existed on the rejected branch/commit 39b602b) — it is
NOT read from the live `backend/pyproject.toml`, which I confirmed still
reads exactly `"mcp>=1.0"` (no upper bound) at HEAD 2b28c9a. Harmless local
artifact; a genuinely fresh venv (which the Developer/QA will build for G3)
has no such stale cache. No repo action needed.

API surface confirmed via direct inspection (`dir(mcp.server)`,
`inspect.signature`, and a throwaway in-process `MCPServer` instance with a
registered tool, run through `asyncio.run`):

- `from mcp.server.fastmcp import FastMCP` → `ModuleNotFoundError` (confirmed
  gone, matches the mandate).
- `mcp.server.mcpserver.MCPServer.__init__(name: str | None = None, ...)` —
  same as `FastMCP(name="lexgraph")`; drop-in constructor call.
- `.tool()` decorator: same no-arg `@server.tool()` call convention; a
  plain-dict-returning function still gets JSON-dumped into a `TextContent`
  block automatically (verified: a toy tool returning
  `{"hello": "world", "count": 1}` produced
  `TextContent(text='{\n  "hello": "world",\n  "count": 1\n}')`) — this is
  the concrete evidence for gate G4 (payload shapes unchanged): the JSON
  payload itself is identical in shape; only the outer wrapper object
  changed (see below).
- `.list_tools()` — still `async`, still returns objects with `.name`; the
  existing `test_mcp_server_registers_explore_search_fetch_tools` assertion
  (`{t.name for t in tools}`) needs no change.
- `.call_tool(name, arguments)` — still `async` (confirmed via
  `inspect.iscoroutinefunction`, matches existing `asyncio.run(...)` call
  sites), but now returns `mcp_types._types.CallToolResult`, not a bare dict
  or directly-iterable block sequence. `CallToolResult.content` is a
  `list[TextContent | ...]`, each block still carrying `.text`.
- `.run(transport="stdio")` — identical signature/default; `_stdio_main`'s
  `server.run(transport="stdio")` call needs no change.

**Conclusion for the port** (`backend/app/mcp/server.py`, Developer's item):
swap the one import line and the two `FastMCP` name occurrences
(constructor call + return-type annotation) for `MCPServer` /
`mcp.server.mcpserver`. No tool-body changes, no new dependency, no
transport-argument changes.

### R3 — network-library import investigation (no escalation)

`test_mcp_package_imports_no_network_libraries` (`test_no_network_dependencies.py`)
does a **static AST scan of `app.mcp`'s own submodule source files only**
(`ast.parse` + `ast.Import`/`ast.ImportFrom` node walk on each file opened
from `pkgutil.walk_packages`), checking for literal `import httpx` /
`requests` / `urllib.request` / `aiohttp` / `socket` / `http.client`
statements written in *our* code. It does not scan `sys.modules` and does
not recurse into what the third-party `mcp` package itself imports.

Empirically confirmed that `import mcp.server.mcpserver` DOES transitively
pull in real network-capable modules at import time — `httpx2` (mcp 2.0's
httpx replacement; `pip show mcp` lists it directly under `Requires:`),
plus stdlib `socket`, `http.client`, `urllib.request` (used internally by
`starlette`/`anyio`/`httpx2` for the SSE/streamable-http/auth transports
that ship in the same package even though we only use stdio). This is
**not new**: `pip show mcp` at 1.29.0 (captured before upgrading) already
listed `httpx, httpx-sse` under `Requires:` — mcp 1.x pulled in an HTTP
client transitively too, under the pre-rename name. Same shape, same kind
of transitive dependency, before and after this migration; only the
package name (`httpx` → `httpx2`) changed upstream.

Net effect: the test's assertion is scoped to `app/mcp/*.py`'s own literal
import statements. The one-line rename port (`mcp.server.fastmcp` →
`mcp.server.mcpserver`) introduces no new banned literal import name, so
the test passes post-port for the same structural reason it always did —
confirmed by running it now (RED only via `ModuleNotFoundError`, not via
any banned-import assertion; see RED evidence below). Per the brief's
precise trigger ("mcp 2.0 unavoidably imports network libraries at import
time, **conflicting with** test_mcp_package_imports_no_network_libraries"):
no conflict exists. Not escalating; test left untouched and unweakened.

### RED evidence — exact sequence

1. Baseline at mcp 1.29.0 (venv as handed off): full suite green.

   ```
   $ backend/.venv/bin/pytest backend/tests -q
   290 passed, 11 warnings in 5.67s
   ```

2. Wrote `backend/tests/unit/test_mcp_dependency_floor.py` (new; asserts
   installed `mcp` distribution major version >= 2, per gate G1). Ran it
   BEFORE upgrading, at mcp 1.29.0, to capture genuine RED:

   ```
   $ backend/.venv/bin/pytest backend/tests/unit/test_mcp_dependency_floor.py -v
   FAILED ...test_installed_mcp_distribution_is_2x_or_newer
   AssertionError: expected an installed `mcp` distribution >= 2.0 (gate G1), found 1.29.0
   assert 1 >= 2
   ```

3. Installed `mcp==2.0.0` (`backend/.venv/bin/pip install 'mcp==2.0.0'`).
   Left the venv at 2.0.0 for the Developer (not reverted).

4. Re-pointed `_flatten_to_text` (test_mcp_tools_live.py) and the inline
   duplicate in test_qa_regression_local_first_platform.py to the
   version-agnostic `.content`-first shape (see above). Verified the new
   helper against a real `CallToolResult` from a throwaway `MCPServer`
   probe (not against app code — `backend/app/mcp/server.py` was not
   touched): a `fetch`-shaped tool returning
   `{"error": "assertion not found: does-not-exist"}` flattened cleanly to
   `'{\n  "error": "assertion not found: does-not-exist"\n}'` — genuine
   substring match, not an accidental repr-string hit.

5. Ran the full suite at mcp 2.0.0 (server.py still unported — expected):

   ```
   $ backend/.venv/bin/pytest backend/tests -q
   6 failed, 285 passed, 10 warnings in 7.12s
   FAILED tests/integration/test_mcp_search_fetch_tools.py::test_search_finds_a_seeded_assertion_by_text
   FAILED tests/integration/test_mcp_search_fetch_tools.py::test_fetch_returns_full_assertion_detail_by_id
   FAILED tests/integration/test_mcp_tools_live.py::test_mcp_server_registers_explore_search_fetch_tools
   FAILED tests/integration/test_mcp_tools_live.py::test_explore_returns_assertion_evidence_and_relationships_in_one_bounded_call
   FAILED tests/integration/test_qa_regression_local_first_platform.py::test_mcp_fetch_of_nonexistent_assertion_id_does_not_crash
   FAILED tests/unit/test_no_network_dependencies.py::test_mcp_package_imports_no_network_libraries
   ```

   All 6 fail identically: `app/mcp/server.py:39: from mcp.server.fastmcp
   import FastMCP` → `ModuleNotFoundError: No module named
   'mcp.server.fastmcp'`. Legitimate RED (collection/execution-time import
   error from the removed 1.x module, not an assertion failure) — exactly
   the failure mode the mandate describes. 285 passed = 290 original +
   1 new floor test (now green at 2.0.0) - 6 newly-red = 285. Confirms no
   collateral damage beyond the named 6.

### Stale-pin sweep detail

`grep -riE 'fastmcp|mcp\.server|mcp>=|mcp==|mcp<'` across
`backend/tests/{unit,integration,e2e}` and `frontend/src` plus a
repo-wide pass (excluding `.venv`/`node_modules`):

- Test-root hits: docstring/comment prose only, in
  `backend/tests/integration/test_mcp_tools_live.py` (module docstring +
  `_flatten_to_text` docstring) and
  `backend/tests/integration/test_qa_regression_local_first_platform.py`
  (module docstring line, "through the real FastMCP"). No test asserted
  against `FastMCP`/`fastmcp` via `isinstance`/import in actual test code
  — both files already called only public dispatch (`call_tool`,
  `list_tools`). Re-pointed the prose (generalized to name both `FastMCP`
  under 1.x and `MCPServer` under 2.x, or dropped the class name entirely)
  in the same commit as the RED tests.
- `backend/pyproject.toml:13` `"mcp>=1.0"` — no `<2.0` pin present (R1's
  rejected pin is NOT carried over, confirmed by direct read at HEAD
  2b28c9a). Raising this to force the 2.x line is Developer item 1 — not
  a "stale pin" to fix now, since there is no incorrect pin to remove, only
  a floor to raise.
- `docs/mcp-registration.md`, `docs/RUNBOOK.md` hits are false positives —
  the regex's `mcp\.server` alternative matches inside the substring
  `app.mcp.server` (our own module path, e.g. `python -m app.mcp.server`),
  not the SDK's `mcp.server.*` namespace. These invocations are unaffected
  by the FastMCP→MCPServer rename (the `_stdio_main`/`__main__` entrypoint
  is untouched). No action; also outside the test-root scope of this
  sweep and outside Planner's editable scope regardless.
- `docs/sprint/sprints/2026-07-26-local-first-platform.md` and its
  `-log.md` are closed-sprint historical record — out of scope, left
  untouched.
