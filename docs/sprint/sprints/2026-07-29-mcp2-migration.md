---
id: "2026-07-29-mcp2-migration"
status: dev-complete
current_role: qa
branch: sprint/2026-07-29-mcp2-migration
locked_by: "claude-code:developer"
locked_at: "2026-07-29T18:20:17Z"
last_agent: "claude-code:developer"
last_updated: "2026-07-29T18:23:16Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 2
completed_items: 0
dev_complete_items: 2
qa_cycles: 0
previous_sprint: "2026-07-26-local-first-platform"
prd_sections: []
design_sections: []
---

# Sprint: Migrate backend MCP server to mcp 2.0

## Mandate (director)

PyPI `mcp` released 2.0.0, which removed `mcp.server.fastmcp` — the module
`backend/app/mcp/server.py` is built on. A fresh install of `mcp>=1.0` now
resolves to 2.0.0 and breaks 6 backend tests (and fresh CI runs). The
director rejected pinning to `<2.0` (PR #8 closed) and directed a real
migration to the latest mcp version.

## Acceptance gates (manager-defined, plain language)

- **G1 — On the latest SDK:** a fresh `pip install -e '.[dev]'` of the
  backend resolves `mcp` to 2.x (floor raised; no `<2.0` pin anywhere).
- **G2 — Server works on 2.x:** the LexGraph MCP server builds and registers
  its three tools (explore / search / fetch) on mcp 2.x, proven by the
  existing integration tests running green against the new API.
- **G3 — Full suite green in a fresh venv:** rebuild `backend/.venv` from
  scratch and the entire backend suite passes (currently 290 tests),
  including the 6 tests that fail today under mcp 2.0.0; frontend suite
  stays green (no frontend surface expected).
- **G4 — No behavior change:** explore/search/fetch tool payload shapes are
  unchanged (existing tests pin this; QA re-verifies).

## Manager rulings

- R1: Sprint branch is based on `origin/main` (a6c1efe). The rejected pin
  commit (39b602b on `claude/sad-almeida-75d671`) must NOT be carried over.
- R2: If migrating requires adding a NEW third-party dependency (e.g. the
  separate `fastmcp` package) because the 2.0 SDK has no equivalent
  high-level server API, that is an architectural fork — ESCALATE to the
  manager before adding it. Same if tool payload shapes cannot be preserved.
- R3: Known risk to investigate FIRST:
  `test_no_network_dependencies.py::test_mcp_package_imports_no_network_libraries`
  encodes a product constraint from the local-first sprint. If mcp 2.0's
  import graph unavoidably pulls network libraries at import time, ESCALATE —
  do not weaken or delete that test unilaterally.

## Next Steps

## Stale-pin sweep

Swept `grep -riE 'fastmcp|mcp\.server|mcp>=|mcp==|mcp<'` across
`backend/tests/{unit,integration,e2e}/` and `frontend/src/` (the four test
roots), plus a repo-wide pass for context. Re-pointed in the same commit as
the RED tests:

- `backend/tests/integration/test_mcp_tools_live.py` — module docstring
  and `_flatten_to_text`'s docstring named `mcp.server.fastmcp.FastMCP`
  concretely; generalized to cover both `FastMCP` (1.x) and
  `mcp.server.mcpserver.MCPServer` (2.x), and made the helper itself
  check `.content` first (version-agnostic public shape) instead of
  assuming a bare dict/sequence.
- `backend/tests/integration/test_qa_regression_local_first_platform.py`
  — same `.content`-first fix applied to its inline duplicate of the
  flatten logic; docstring's "real FastMCP" reference generalized to
  "real SDK".

No other test-root hits: neither file asserted against `FastMCP`/internals
via `isinstance`/import in executable code — both already dispatched only
through the public `call_tool`/`list_tools` API.

`backend/pyproject.toml:13` (`"mcp>=1.0"`, no `<2.0` pin) is Item 1 above,
not a stale pin to remove — there's nothing incorrect there, only a floor
to raise. `docs/mcp-registration.md` and `docs/RUNBOOK.md` hits are false
positives (`mcp\.server` matching inside `app.mcp.server`, our own module
path — unaffected by the rename). `docs/sprint/sprints/2026-07-26-local-first-platform*`
hits are closed-sprint historical record, out of scope. Full detail and
grep output in the sprint log.

## Dev Complete

### Item 1 — Raise the `mcp` dependency floor
Files touched: `backend/pyproject.toml`
Commit: `3009266`
Result: Changed `"mcp>=1.0"` to `"mcp>=2.0"` in pyproject.toml; floor enforcement prevents silent resolution to 1.x on fresh installs.

### Item 2 — Port `app/mcp/server.py` to the mcp 2.0 server API
Files touched: `backend/app/mcp/server.py`
Commit: `3009266`
Result: Renamed `FastMCP` → `MCPServer` across import, return annotation, and constructor; updated docstring; scoped tests (8 tests) and full suite (291 backend + 62 frontend) green in fresh venv at mcp 2.0.0.

## Completed

## Evaluation Notes

Fresh venv rebuilt from scratch resolves mcp to **2.0.0**. Full authoritative test pass: backend 291 passed (10 warnings), frontend 62 passed (11 test files). No flakes or single-file re-runs required. All six RED tests now green (no more ModuleNotFoundError for mcp.server.fastmcp). Gates G1–G4 satisfied: floor raised to >=2.0, server API migrated, full suite green in fresh venv, tool payload shapes unchanged.

## QA Notes

## Context Dump

`backend/.venv` is at mcp **2.0.0** now (left for you — don't revert).

RED set (6, all `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` from `app/mcp/server.py:39`): both tests in `test_mcp_search_fetch_tools.py` and `test_mcp_tools_live.py`, `test_qa_regression_local_first_platform.py::test_mcp_fetch_of_nonexistent_assertion_id_does_not_crash`, and `test_no_network_dependencies.py::test_mcp_package_imports_no_network_libraries`.

Run: `backend/.venv/bin/pytest backend/tests -v`. Do Item 1 then Item 2 (one-line `FastMCP`→`mcp.server.mcpserver.MCPServer` rename; planner log has the proof) — don't edit any test file. Rebuild the venv from scratch before declaring G3 done.
