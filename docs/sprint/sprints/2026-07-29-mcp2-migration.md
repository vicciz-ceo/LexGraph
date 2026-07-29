---
id: "2026-07-29-mcp2-migration"
status: review
current_role: planner
branch: sprint/2026-07-29-mcp2-migration
locked_by: "claude-code:planner"
locked_at: "2026-07-29T21:54:29Z"
last_agent: "claude-code:manager"
last_updated: "2026-07-29T21:54:29Z"
lint: "PASS 141 2026-07-29T18:38:21Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 2
completed_items: 2
dev_complete_items: 0
qa_cycles: 1
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
- R4 (merge-time, 2026-07-30): `origin/main` gained the `<2.0` stopgap via a
  DIFFERENT sprint (definition-links item DL10 @ 821a597), which explicitly
  deferred "mcp 2.x migration to a future sprint" — this sprint. DL10's
  `test_qa_regression_definition_links.py::test_installed_mcp_package_version_is_pinned_below_2_0`
  asserts `major < 2` and is the exact inverse of this sprint's floor test:
  a pre-existing GREEN pin our intended change breaks, i.e. a planning bug
  the Planner reconciles (SKILL.md Phase 2), not a Developer/manager edit.
  Ruled SUPERSEDED — the stopgap it guards no longer exists.
- R5 (merge rulings, `origin/main` → sprint branch): both textual conflicts
  take the SPRINT side whole, no hand-blending. `backend/pyproject.toml` —
  verified the only delta between sides is the `mcp` line, so taking ours
  drops nothing of main's. `docs/sprint/current-sprint.json` — this sprint is
  active; definition-links is `done`. `previous_sprint` re-pointed to
  `2026-07-29-definition-links` (manager bookkeeping).

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

## Completed

QA cycle 1 (2026-07-29), 2/2 PASS. Verdict = PASS, probe = one
live/independent check beyond the item's own tests, regression = new QA
test name (file: `backend/tests/integration/test_qa_regression_mcp2_migration.py`
unless noted).

- **Item 1** — Raise the `mcp` dependency floor (commit `3009266`).
  Verdict: PASS. Probe: independent fresh-venv rebuild (`rm -rf .venv`,
  `python3.13 -m venv .venv`, `pip install -e '.[dev]'`) resolves `mcp` to
  `2.0.0`; `grep -rn 'mcp<' backend --include='*.toml'` empty (no `<2.0`
  pin anywhere in the repo).
  Regression: existing `test_mcp_dependency_floor.py::test_installed_mcp_distribution_is_2x_or_newer`.
- **Item 2** — Port `app/mcp/server.py` to the mcp 2.0 server API (commit
  `3009266`). Verdict: PASS. Probe: `git diff a6c1efe..3009266 --
  backend/app/mcp/server.py` is exactly the import/class-name/docstring
  rename (5 lines changed), zero tool-body or payload-shape changes; live
  `call_tool`/`list_tools` dispatch tests (`test_mcp_tools_live.py`,
  `test_mcp_search_fetch_tools.py`) green against the real SDK.
  Regression: `test_create_server_exposes_the_list_tools_call_tool_and_run_surface_stdio_needs`
  and `test_call_tool_with_missing_required_query_argument_raises_tool_error[search|explore]`.

## Evaluation Notes

Fresh venv rebuilt from scratch resolves mcp to **2.0.0**. Full authoritative test pass: backend 291 passed (10 warnings), frontend 62 passed (11 test files). No flakes or single-file re-runs required. All six RED tests now green (no more ModuleNotFoundError for mcp.server.fastmcp). Gates G1–G4 satisfied: floor raised to >=2.0, server API migrated, full suite green in fresh venv, tool payload shapes unchanged.

## QA Notes

- 2026-07-29T18:33:33Z qa cycle 1: independent fresh-venv rebuild + full
  evaluator green — backend 291→294 (3 new regressions), frontend 62/62,
  zero flakes. Live-path PASS (real `call_tool`/`list_tools` dispatch,
  confirmed by reading the test files); G4 diff PASS (`a6c1efe..3009266`
  on `server.py` is a pure rename, verified via `git diff`); CI install
  path PASS (`.github/workflows/ci.yml` installs via plain `pip install
  -e '.[dev]'`, no pinned 1.x anywhere). 2/2 PASS. Full transcript in
  `-log.md`.

## Context Dump

- Sprint at `review` awaiting director/manager sign-off (review→done is
  director-only). Both items QA-verified in 1 cycle; suite: backend 291
  (294 incl. 3 QA regressions) / frontend 62, all green, branch pushed.
- G1–G4 all confirmed independently (fresh venv, real `git diff`, live
  SDK dispatch, clean CI install path) — see QA Notes / log for probes.
- Successor start here: gates + rulings above are durable; full research
  trail is in `2026-07-29-mcp2-migration-log.md`.
- No known deferred surfaces from this sprint (single-purpose floor-raise
  + rename; no new capability, nothing left on the table).
