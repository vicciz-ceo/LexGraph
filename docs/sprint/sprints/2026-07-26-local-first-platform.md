---
id: "2026-07-26-local-first-platform"
status: review
current_role: planner
branch: sprint/2026-07-26-local-first-platform
locked_by: null
locked_at: null
last_agent: "claude-code:manager"
last_updated: "2026-07-26T11:03:06Z"
lint: "PASS 228 2026-07-26T11:04:23Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 17
completed_items: 17
dev_complete_items: 0
qa_cycles: 2
prd_sections:
  - docs/specs/collaborative-assertions.md
design_sections: []
previous_sprint: "2026-07-25-collaborative-assertions"
---

# Sprint: Local-first platform — authored-text fidelity, enrichment, LexGraph MCP, packaging

Director mandate (2026-07-26): LexGraph is a three-part local-first
open-source system usable from Claude Code, Codex, Cursor, or Antigravity:
(1) an enrichment stage that suggests assertions from documents already
stored in the database (document acquisition/scraping explicitly out of
scope — director amendment mid-planning, ruling R7); (2) the grading app
(exists) that edits the database; (3) a LexGraph MCP server that maps the
database for agent sessions (CodeGraph-style). Everything local — no cloud
deploy; installable from a terminal. Also resolve GitHub issue #2 (raw +
sanitized text split) including its length-cap sub-item.

## Acceptance gates (manager-defined)

- G1 Fidelity (issue #2): text containing angle-bracket prose (`<Title>`,
  `<appendix A>`, `<img plaintail <b>Y</b> Z`) round-trips byte-exact through
  create → fetch → revision history → audit/diff paths. Raw stored alongside
  sanitized; `sanitize_for_storage` is not weakened in any way.
- G2 No XSS regression: the 17-shape hostile-input battery still yields no
  live markup on any rendering path; every read site explicitly classified
  raw-vs-sanitized, with tests pinning that HTML paths never receive raw.
- G3 Reversible migration; backfill (sanitized value copied into raw for
  historical rows) documented in a runbook entry.
- G4 Length cap: proposition / comment_text / rationale capped at 100,000
  chars (director may override), enforced at the API with a clear error.
- G5 Enrich command: a local CLI command runs the enrichment pass over
  documents already stored in the local DB; re-running it is idempotent (no
  duplicate suggestions); failures are reported clearly. Document
  acquisition/scraping is out of scope — documents enter the DB via
  existing APIs/fixtures only.
- G6 Suggest: an enrichment pass produces suggested assertions as proposal
  drafts with evidence linked to real document spans already stored in the
  DB; never auto-accepted; they enter the existing review workflow;
  authored text preserved byte-exact. Enricher pluggable; built-in enricher
  fully offline.
- G7 MCP: a local stdio MCP server exposes the graph against the local DB
  with no network: an explore-style tool returns assertions + evidence +
  relationships for a query in one bounded call, plus search/fetch tools.
  One documented command registers it in Claude Code; config snippets for
  Codex, Cursor, Antigravity.
- G8 Local-first install: a documented terminal sequence takes a fresh clone
  to a working system (DB init, backend, grading app, MCP) with zero cloud
  dependencies; the grading app edits the DB end-to-end locally (E2E proves
  seed a document via the existing API → enrich/suggest → review → grade).

## Manager rulings

- R1 Prior sprint advanced review→done: PR #1 was merged to main by the
  director (vicciz-ceo) — treated as explicit approval; the new mandate
  supersedes it.
- R2 Local-first default DB is SQLite (file on disk); schema stays
  Postgres-compatible (spec §11 authority unchanged for server deployments).
- R3 Length cap defaults to 100,000 characters per issue #2's
  recommendation; flagged to the director as a product decision.
- R4 Enrichment: heuristic/rule-based suggester in core (fully offline);
  LLM enrichers behind a pluggable interface, optional and off by default —
  preserves the no-cloud guarantee.
- R5 MCP v1 is read-only (explore/search/fetch); write/suggest tools are
  deferred pending director direction.
- R6 MCP implemented in Python with the official `mcp` SDK (stdio
  transport), living in the backend package so it reuses the SQLAlchemy
  models directly.
- R7 Director correction (2026-07-26): scraping/document acquisition
  removed from scope; enrichment operates only on documents already present
  in the DB. Any ingest-CLI work is out of scope.

## Next Steps

(Empty — all 17 items verified and moved to `## Completed`. The full item
specs, parallelization plan/write-sets, Expected-RED census, and the
detailed `## Stale-pin sweep` disposition are archived verbatim in
`2026-07-26-local-first-platform-log.md` § "Pre-compression contract
snapshot".)

## Stale-pin sweep

Swept backend/tests/{unit,integration,e2e} + frontend `__tests__` for
R18/browser-faithful pins and `_raw`-key dict-equality breaks: 2 files hit;
3 `test_validation.py` sanitizer pins kept byte-identical (docstrings
updated only), 1 `test_hostile_input.py` API pin re-pointed to also assert
byte-exact `proposition_raw`. Full disposition in the log snapshot.

## Dev Complete

## Completed

QA cycle 1 (2026-07-26), 16/17 PASS — D1 bounced (fixed in cycle 2).
QA cycle 2 (2026-07-26), 17/17 PASS. Verdict = PASS, probe = one
live/independent check beyond the item's own tests, regression = new QA
test name (file:
`backend/tests/integration/test_qa_regression_local_first_platform.py`
unless noted).

- **A1** Raw-text columns + reversible migration + backfill. PASS — ran
  `upgrade()`/`downgrade()`/`upgrade()` myself against a throwaway file DB
  with a simulated pre-existing (pre-migration) row; backfill and column
  drop/restore verified byte-exact. Regression: none needed (G3 fully
  covers this).
- **A2** Assertion write paths store raw + sanitized. PASS — live API
  probe: create + PATCH with an `<appendix A>`-shaped proposition;
  `proposition_raw` byte-exact, sanitized column correctly altered.
  Regression: `test_proposition_raw_round_trips_unicode_emoji_and_crlf_byte_exact`.
- **A3** Comment write paths store raw + sanitized. PASS — live API probe:
  comment create + list expose `comment_text_raw` byte-exact. Regression:
  `test_comment_raw_round_trips_unicode_emoji_and_crlf_byte_exact`.
- **A4** Rating write paths store raw + sanitized rationale. PASS — live
  API probe of PUT rating plus the visibility gate (peer/rater/reviewer).
  Regression: `test_rating_list_nulls_rationale_for_unauthorized_peer_but_not_for_rater_or_reviewer`
  (closes a real coverage gap — no prior test exercised the unauthorized
  path for this gate).
- **A5** G1 named-example round trip. PASS — 3/3 green; confirmed the
  fixture strings are issue #2's exact quoted examples. Regression: n/a
  (covered by A2/A8 boundary regression).
- **A6** Search reads raw proposition, not sanitized. PASS — live API
  probe: `q=appendix A` (a sanitizer-dropped term) finds the assertion via
  the real endpoint. Regression: covered by
  `test_proposition_at_cap_boundary_containing_angle_brackets_round_trips_raw`.
- **A7** Frontend revision history + comparison render raw text nodes.
  PASS — scoped vitest run (9/9) via real React Testing Library render;
  `grep -rn dangerouslySetInnerHTML frontend/src` returns zero code hits
  (one unrelated comment string in a test file). Regression: none needed
  (component tests already exhaustive for this surface).
- **A8** Length cap (100,000 chars) enforced at the API. PASS — 11/11
  suite green. Regression:
  `test_proposition_at_cap_boundary_containing_angle_brackets_round_trips_raw`
  (boundary size composed with raw-fidelity in one case).
- **A9** Stale-pin sweep. PASS — `git show db203ce` on both edited test
  files confirms only the documented docstring updates + the one added
  `proposition_raw` assertion; the sanitized-column assertions and all 3
  `test_validation.py` browser-faithful pins are byte-identical to before.
  Regression: n/a (historical-diff verification, not new behavior).
- **B1** Enrichment CLI. PASS — ran the real CLI as a subprocess against a
  seeded SQLite file DB: run 1 creates 1 draft `model_suggested` assertion
  (confirmed via `GET /assertions`), run 2 is idempotent (0 created, DB
  still holds exactly 1), unknown matter exits 1 with a clear stderr
  message. Regression:
  `test_enrich_cli_on_matter_with_zero_spans_creates_nothing_and_exits_zero`.
- **B2** Offline heuristic suggester + live pipeline. PASS — same
  subprocess trace confirms real `Assertion`/`AssertionRevision`/
  `AssertionEvidence` rows, `origin=model_suggested`, `status=draft`,
  never `accepted`. Regression:
  `test_run_enrichment_on_matter_with_zero_spans_returns_empty_list`.
- **B3** Pluggable `Enricher` protocol. PASS — 3/3 green; read
  `pipeline.py`'s `enricher if enricher is not None else
  HeuristicEnricher()` wiring directly. Regression: n/a (interface-level,
  already exhaustive).
- **C1** LexGraph MCP stdio server. PASS — confirmed
  `test_mcp_tools_live.py`/`test_mcp_search_fetch_tools.py` dispatch
  through the real `server.call_tool(...)` (not raw functions); booted
  `python -m app.mcp.server` as a subprocess against a schema'd file DB
  with stdin held open — stayed alive the full 5s bound, no traceback, no
  crash. Regression: `test_mcp_fetch_of_nonexistent_assertion_id_does_not_crash`.
- **C2** MCP registration docs. PASS — content read in full: `claude mcp
  add` command matches `server.py`'s actual module path; Codex/Cursor/
  Antigravity snippets present; no factual defects found. Regression: n/a
  (doc-only, no behavior to pin).
- **D1** Local-first install runbook. PASS cycle 2 — probe = grep sweep
  (`grep -in vue docs/RUNBOOK.md` zero hits, `grep -in react` names the
  app correctly) + doc test rerun. Fix commit `0e66b73`.
- **D2** (G8 E2E: seed → enrich → review → grade;
  `backend/tests/e2e/test_local_first_platform_flow.py`; labeled "D3" in
  the archived Dev Complete prose). PASS — 1/1 green; test body read in
  full and matches gate G8 exactly against the real API, one local SQLite
  file, no network. Regression: n/a (E2E-level, exhaustive by design).
- **D3** (zero-network guardrail;
  `backend/tests/unit/test_no_network_dependencies.py`; labeled "D2" in
  the archived Dev Complete prose). PASS — manually grepped every import
  in `app/enrich/` and `app/mcp/`; zero network-capable modules, matching
  the AST-based test's verdict. Regression: n/a (static-analysis-level,
  exhaustive).

## Evaluation Notes

Final verified state (QA cycle 2, fea7de7): backend 290 passed / 0 failed
(283 dev + 7 QA regressions), frontend 62 passed / 0 failed. Track A full
pass reconciled exactly against the corrected census (20 expected
other-track RED at that point); parallel devB/devC trees reconciled
exactly; Track D full pass 283/283. `sanitize_for_storage` byte-identical
to pre-sprint; zero `dangerouslySetInnerHTML` in frontend code. Full
per-track evaluation narratives archived in the log snapshot.

## QA Notes

- 2026-07-26 qa cycle 1: independent evaluator green — backend 283→290
  (7 new regressions), frontend 62/62, zero flakes. Live-path PASS (enrich
  CLI subprocess, MCP stdio boot, real FastMCP dispatch, frontend
  text-node rendering); gate sweeps PASS (G1/G2 classification, G3 live
  migration round-trip, G4 privacy — closed an untested gap). D1 FAILED:
  RUNBOOK called the React app "Vue.js". 16/17 PASS. Full transcript in
  `-log.md`.
- 2026-07-26 qa cycle 2 (D1 scoped): fix `0e66b73` confirmed 1-file/1-line;
  `grep -in vue` zero hits; doc tests 2/2; full re-run backend 290 /
  frontend 62 — matches cycle 1, zero regressions. D1 PASS. 17/17; sprint
  → `review`.

## Context Dump

- Sprint at `review` awaiting director sign-off (review→done is
  director-only). All 17 items QA-verified across 2 cycles; suite: backend
  290 / frontend 62, all green, branch pushed.
- Successor start here: gates + rulings above are durable; full item
  specs/census/narratives are in the log's pre-compression snapshot.
- Known deferred surfaces: document acquisition/scraping (R7), LLM enricher
  adapters (R4), MCP write tools (R5), Alembic adoption, frontend wiring of
  `proposition_raw` into remaining components (only history/comparison
  consume it today).
