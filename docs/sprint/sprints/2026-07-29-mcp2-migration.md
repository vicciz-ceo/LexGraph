---
id: "2026-07-29-mcp2-migration"
status: planning
current_role: planner
branch: sprint/2026-07-29-mcp2-migration
locked_by: "claude-code:planner"
locked_at: "2026-07-29T18:02:43Z"
last_agent: "claude-code:manager"
last_updated: "2026-07-29T18:02:43Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 0
completed_items: 0
dev_complete_items: 0
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

(Planner defines items here.)

## Dev Complete

## Completed

## Evaluation Notes

## QA Notes

## Context Dump

New sprint. Planner: research the mcp 2.0 server API from the installed
package (install mcp==2.0.0 into backend/.venv to establish the RED
baseline), define items, author/re-point RED tests, prove RED, hand off.
