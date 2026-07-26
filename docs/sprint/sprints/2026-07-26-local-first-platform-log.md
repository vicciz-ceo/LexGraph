# Sprint log — 2026-07-26-local-first-platform

Append-only overflow sink for the sprint contract (never auto-loaded).
Full test output, QA transcripts, per-round narration, superseded rulings,
and the agent roster live here.

## Agent roster

- 2026-07-26T08:51Z manager: claude-code (Fable 5) — sprint opened.
- 2026-07-26T09:xxZ planner: claude-code (Sonnet 5) — planning pass.
  Preflight: HEAD matched `a96a659`. Built backend venv
  (`python3.13 -m venv .venv && pip install -e '.[dev]'`) and
  `npm --prefix frontend ci`. Baseline green: `backend/.venv/bin/pytest
  backend/tests -q` -> 238 passed; `npm --prefix frontend run test -- --run`
  -> 60 passed (11 files).

  Mid-planning, the director sent a scope amendment (relayed via the
  coordinator channel) removing document-acquisition/ingest-CLI work from
  Track B: enrichment now operates only on documents already in the DB
  (existing APIs/fixtures), never on files. Applied verbatim to the
  contract's mandate paragraph, G5, G6, G8, and a new ruling R7 — see the
  contract body. No ingest-related test was authored before the amendment
  arrived, so nothing needed to be deleted.

  17 items defined across 4 tracks (A sequential/first — schema, write
  paths, read-path classification, length cap, frontend raw rendering,
  stale-pin sweep; B — enrichment CLI, suggester, pluggable enricher; C —
  MCP explore/search/fetch + registration docs; D — runbook, G8 E2E,
  zero-network guardrail). Full item text, parallelization plan, and
  Expected-RED census live in the contract's `## Next Steps`.

  Design decisions worth recording (none rose to a full ESCALATION —
  each had a clear, low-risk default consistent with the manager's
  contract text):
  - Raw columns land only on `assertion_revisions.proposition_raw`,
    `assertion_comments.comment_text_raw`, `assertion_ratings.rationale_raw`
    (exactly the contract's Track A list) — NOT on `assertions.proposition`
    itself. `GET /assertions/{id}` and search both derive raw text via a
    join to the assertion's *current* revision, since every write path
    already keeps a revision in lockstep with the assertion row. This
    avoids a 4th raw column while still satisfying G1's "create -> fetch"
    round trip.
  - No Alembic this sprint — a hand-rolled `app.migrations.
    add_raw_text_columns.upgrade(engine)/downgrade(engine)` module (raw
    DDL) is proportionate to "add 3 nullable columns + backfill" and
    matches the codebase's existing raw-SQL style (`conftest.py`'s seed_*
    helpers); repo-profile.md already treats Alembic adoption as optional
    ("if Alembic is adopted"). Flagged under Deviations in the final
    report.
  - No new "export" endpoint invented — issue #2 mentions exports in
    passing but neither the sprint contract's gates nor Track A's bullet
    list require one, and no export code exists today. Read-path
    classification (A6) covers the read paths that DO exist: fetch,
    revision history, comments, ratings, search.
  - MCP tools (C1) are tested via the real `mcp` SDK's `FastMCP.call_tool`
    dispatch (the actual registered-handler path), with a
    version-tolerant text-flattening helper in the test itself rather
    than pinning the exact `Sequence[ContentBlock] | dict` return shape,
    since that envelope is a legitimate Developer implementation choice.

  RED confirmed: `backend/.venv/bin/pytest backend/tests -q
  --continue-on-collection-errors` -> 238 passed (unchanged baseline),
  41 failed + 1 collection ERROR (the length-cap unit module, ImportError
  for `validate_text_length`) — every failure inspected and is
  ModuleNotFoundError / ImportError / KeyError / AssertionError /
  FileNotFoundError for the right reason, none an accidental existing-test
  regression. Frontend: `npm --prefix frontend run test -- --run` -> 60
  passed (unchanged baseline) + 2 new RED (AssertionError: DOM shows the
  sanitized `proposition`, not the new `propositionRaw`, since neither
  component reads that field yet).

  Stale-pin sweep: `grep -riE "browser-faithful|accepted limitation|browser
  faithful"` across backend/tests/{unit,integration,e2e} and
  frontend/src/components/__tests__ found exactly 2 files (both R18,
  2026-07-25 sprint) — see the contract's `## Stale-pin sweep` section for
  the full disposition (1 re-pointed integration test, 3 unit pins left
  behaviorally unchanged with docstrings updated). Also swept
  `grep -rn "json() =="` across backend/tests for exact-dict-equality
  assertions the new `_raw` response keys could break — only hit is an
  unrelated empty-list assertion in test_notifications.py.
- 2026-07-26T08:55Z planner: agentId a88133499a5ca2e77 (Sonnet, high) — spawned on a96a659.
- 2026-07-26T09:35Z manager: planner handoff verified (diff containment PASS,
  risk-grep clean, wiring-test gate PASS, stale-pin sweep PASS). Census
  corrected from measured run: search_raw 2→1, length_cap_api 7→6 (+1 green
  companion), mcp_tools_live 3→2, added missing mcp_search_fetch_tools row
  (2). Measured: backend 41 failed / 238 passed / 1 collection error;
  frontend 60 passed + 2 new RED. Lock → claude-code:developer; Dev-A
  (Track A bundle, Sonnet medium, solo mode) next.
- 2026-07-26T09:38Z developer (Track A): agentId a7443d93d43ec195c (Sonnet,
  medium) — spawned on 017c9d7, solo mode, items A1–A9.
- 2026-07-26T10:35Z manager: Track A verified — containment PASS (owned
  files only, zero test files), full 499-line diff read PASS (reversible
  migration, raw carry-forward on untouched-proposition revisions, privacy
  gate nulls rationale_raw, cap pre-sanitization, text-node-only frontend),
  risk-grep clean, manager probe run matches: backend 20 failed / 263
  passed (all B/C/D), frontend 62/62. Parallel fan-out: devB agentId
  ae34128728ec0c470 (Sonnet, medium, items B1–B3, worktree lexgraph-devB,
  branch …-devB @ eb38032); devC agentId a2bd8cf490d122d0d (Sonnet, medium,
  item C1, worktree lexgraph-devC, branch …-devC @ eb38032). Dev-D
  (C2+D1–D3) sequenced after B+C merge.
- 2026-07-26T10:45Z manager: devC verified (containment PASS — 2 new files
  only; full 220-line diff read PASS — read-only, no network imports,
  bounded, raw precedence; LEXGRAPH_DATABASE_URL env name confirmed real in
  config.py) and ff-merged → a578477. devB verified (containment PASS — 5
  new enrich files only; full 430-line read PASS — raw/sanitized mirror,
  draft-only, idempotent, offline) and merged → c836154. Manager combined
  evaluator on merged tree: backend 281 passed / 2 failed (only the two
  Track D doc tests); e2e D2 + guardrail D3 green with no code; frontend
  green. dev_complete_items → 13. Dev-D next: doc-only scope → Haiku low
  per model policy.
- 2026-07-26T10:05Z developer (Track A): all 9 items dev-complete, 7
  commits (47507b3 A1, d11324c A2, b14abe3 A3, 820a4b4 A4, c281ed6 A6,
  cb2546b A7, a0bf1f6 A8 — A5/A9 needed no code, verified green as
  consequences of A1/A2). Full authoritative pass: backend 20 failed / 263
  passed (reconciles exactly with the Track B/C/D expected list, no
  test_validation_length_cap collection error); frontend 62 passed.
  sanitize_for_storage untouched; no dangerouslySetInnerHTML introduced.
  dev_complete_items → 9. Pushed sprint/2026-07-26-local-first-platform @
  a0bf1f6 (+ this bookkeeping commit). status/current_role/lock fields left
  untouched for the manager.
- 2026-07-26T11:22Z manager: Dev-D anti-gaming diff check PASS (only
  docs/RUNBOOK.md + docs/mcp-registration.md + sprint docs; zero test
  files). Docs read by manager: commands verified truthful (uvicorn
  app.main:app + /healthz confirmed in main.py; editable install makes
  `-m app.mcp.server` valid from any cwd); one known doc defect handed to
  QA — RUNBOOK intro calls the frontend "Vue.js" (it is React+Vite). Lock →
  claude-code:qa; QA agentId aa67eeaff8c07ba6d (Sonnet, high) spawned on
  d746e99.
- 2026-07-26T13:50Z manager: QA cycle-1 verdicts checked — QA commit
  containment PASS (e450010 test-only, 5ba7374 sprint-docs-only);
  RED-provenance gate satisfied for D1 via explicit prose-pin-impossible
  line. Haiku qa-fail fix agent a572548e82a2dbd33 (Haiku, low) fixed
  RUNBOOK line 6 (Vue.js → React) @ 0e66b73; manager anti-gaming check
  PASS (1 file / 1 line, zero "Vue" remains, no test touched). Scoped
  QA-2 agent a00bafd49eaa1b279 (Sonnet, high) spawned on 6da2d13 to
  re-verify D1 and take the sprint to review.
- 2026-07-26T13:00Z developer (Track D): doc-only items C2+D1+D2+D3 (Haiku
  low). Scoped RED preflight: 2 failed (test_mcp_registration_docs 1,
  test_local_first_runbook_docs 1). C2: `docs/mcp-registration.md` written
  — Claude Code `claude mcp add` command + config snippets for Codex,
  Cursor, Antigravity (1/1 green). D1: `docs/RUNBOOK.md` written — fresh-clone
  to working local-first: DB init/migration/backfill, backend serve
  (uvicorn app.main:app), grading-app serve (npm run dev), MCP registration,
  E2E workflow, troubleshooting (1/1 green). D2/D3 verify-only: no code
  required; both tests already green from prior dev work (B1/C1). Full
  authoritative pass: backend 283 passed (all green, zero regressions
  across all 17 items A1–A9+B1–B3+C1+C2+D1–D3); frontend 62 passed.
  dev_complete_items → 17. Pushed sprint/2026-07-26-local-first-platform @
  48caf40 (docs commit) + bookkeeping commit.

- 2026-07-26T13:35Z qa: agentId (this session, Sonnet, high) — spawned on
  d746e99 (HEAD matched expected, no reset needed). Note: this log file
  already carried an uncommitted manager entry at handoff time (the
  2026-07-26T11:22Z "Dev-D anti-gaming diff check" entry above, including
  the "known doc defect... Vue.js" note) — committed together with this
  entry since it predates QA's own findings and both belong in the
  permanent record.

  **Independent full evaluator** (own run, not reused from Developer):
  `backend/.venv/bin/pytest backend/tests -v` → 283 passed, 0 failed, 0
  flakes. `npm --prefix frontend run test -- --run` → 62 passed (11
  files), 0 failed.

  **Per-item verification** — files present on disk (22/22 checked) and
  commit hashes found in `git log` for all 17 (47507b3 A1, d11324c A2,
  b14abe3 A3, 820a4b4 A4, c281ed6 A6, cb2546b A7, a0bf1f6 A8, 9acd0f9 B1,
  be82651 B2, e3598a8 B3, a578477 C1, 48caf40 C2+D1, plus merge/bookkeeping
  commits c836154/9b9c60b/017c9d7/eb38032). Scoped run of all 17 items'
  test files together: 45/45 green.

  **Live-path traces**:
  - `app.enrich`: seeded a real SQLite file DB via `create_app()` +
    `Base.metadata.create_all` + raw-SQL seed helpers (mirroring
    `conftest.py`), ran `backend/.venv/bin/python -m app.enrich.cli
    --matter-id … --triggered-by-user-id …` as a genuine subprocess. Run 1
    created 1 draft `model_suggested` assertion for a
    "survives termination" span (confirmed via `GET /api/v1/assertions`
    showing `proposition_raw` byte-exact); run 2 was idempotent (stdout
    "0 draft assertion(s) created", DB still held exactly 1 row); run 3
    against `--matter-id does-not-exist` exited 1 with stderr
    `enrichment failed: matter 'does-not-exist' does not exist`.
  - `app.mcp`: read `test_mcp_tools_live.py`/`test_mcp_search_fetch_tools.py`
    line-by-line — both dispatch via `asyncio.run(server.call_tool(...))`,
    the real FastMCP registered-handler path, not raw Python function
    calls. Booted `backend/.venv/bin/python -m app.mcp.server` as a
    subprocess against a schema-created file DB with stdin held open
    (`subprocess.PIPE`, no EOF): still alive after the full 5s bound, no
    stdout/stderr, no traceback; terminated cleanly. A second run with
    stdin from `/dev/null` (immediate EOF) also exited 0 with empty
    stderr — confirms clean shutdown on stream close, not a crash.
  - Frontend A7: `npm --prefix frontend run test -- --run
    AssertionRevisionHistory AssertionComparisonView` → 9/9 green via
    real RTL `render()`/`screen.getByText()`. `grep -rn
    dangerouslySetInnerHTML frontend/src` → zero hits in component code
    (one hit is a comment string inside a `.test.tsx` file).

  **Gate sweeps**:
  - G1/G2: grepped every `proposition_raw`/`comment_text_raw`/
    `rationale_raw` call-site in `backend/app` (13/6/6 hits respectively)
    — all are FastAPI JSON dict responses; `grep -rln
    "Jinja2Templates\|render_template\|HTMLResponse" backend/app` found
    nothing, so the backend has no HTML-templating surface at all (JSON
    API only, text-safe by construction). Frontend consumers of
    `propositionRaw` are exactly the two A7 components, both via
    `{revision.propositionRaw ?? revision.proposition}` JSX text-node
    interpolation. `git show db203ce -- backend/tests/integration/
    test_hostile_input.py backend/tests/unit/test_validation.py` confirms
    the stale-pin sweep's claimed diff is exact: only docstring/comment
    edits plus the one documented `proposition_raw` assertion addition;
    the sanitized-column assertions and all 3 browser-faithful unit pins
    are byte-identical to their pre-sprint text.
  - G3: wrote and ran a standalone script (not the test suite) against a
    throwaway file DB: created full current schema via
    `Base.metadata.create_all`, manually dropped the 3 `_raw` columns to
    simulate a pre-migration DB, seeded one pre-existing revision/comment/
    rating row with sanitized-only text, ran `upgrade()` → columns added +
    backfilled correctly for all 3 tables, ran `downgrade()` → columns
    dropped, sanitized data untouched, ran `upgrade()` again → round trip
    repeatable. All assertions passed.
  - G4: `routers/ratings.py::list_ratings` nulls both `rationale` and
    `rationale_raw` together when `not can_see_rationales and r.user_id
    != user_id`; `has_permission` grants `assertion:view_rating_rationales`
    to reviewer/admin only. Searched the ENTIRE test suite (both this
    sprint and the prior 2026-07-25 sprint) for a test exercising an
    unauthorized viewer hitting someone else's rating — found none; every
    existing `.../ratings` GET test in the repo uses `reviewer_headers`
    (which HAS the permission) or the rater's own headers. Live-probed
    the real API directly: a peer contributor (no role relationship to
    the rating) sees `rationale`/`rationale_raw` both `None` (strength
    stays visible); the rater's own view and the reviewer's view both see
    the full text. Behavior is correct; only the test coverage was
    missing — closed with a new regression test.
  - G7/G8: booted `backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0
    --port 8123` per the runbook's exact command, `curl
    http://localhost:8123/healthz` → `{"status":"ok"}`, killed cleanly.
    Verified `frontend/package-lock.json` exists (so `npm ci` is valid),
    `.venv/bin/python --version` → 3.13.12 (matches `requires-python
    >=3.12`), the `mcp` package is actually installed
    (`pip show mcp` → 1.28.1). `docs/mcp-registration.md` read in full:
    no factual defects. `docs/RUNBOOK.md` read in full: **line 6, "3. A
    Vue.js grading application"**, is false — `frontend/package.json`
    has no Vue dependency at all; it lists `react`/`react-dom`/
    `@vitejs/plugin-react`, every component is `.tsx`, tests use
    `@testing-library/react`. `grep -n -i "vue\|react"
    docs/RUNBOOK.md docs/mcp-registration.md` confirms this is the ONLY
    Vue/React mention in either doc — a single, unambiguous factual
    error, not an isolated typo lost among correct mentions elsewhere.
    `test_local_first_runbook_docs.py` only checks for keyword presence
    (migration/backfill/backend/grading/mcp), so it cannot and does not
    catch this — confirmed by reading the test file. No test pin is
    possible for a prose factual claim; filed as `[QA-FAIL: ...]` in the
    contract's D1 item instead, quoting the exact wrong text. Every other
    command/path in both docs (uvicorn invocation, `/healthz`, `.venv/
    bin/python -m app.mcp.server`, `claude mcp add lexgraph -- ...`,
    `LEXGRAPH_DATABASE_URL`, migration upgrade/downgrade snippets, test
    run commands) was cross-checked against the actual code and is
    correct.

  **Regression tests added** (7, all in
  `backend/tests/integration/test_qa_regression_local_first_platform.py`,
  following the existing per-item test files' style):
  `test_proposition_raw_round_trips_unicode_emoji_and_crlf_byte_exact`,
  `test_comment_raw_round_trips_unicode_emoji_and_crlf_byte_exact`,
  `test_proposition_at_cap_boundary_containing_angle_brackets_round_trips_raw`,
  `test_enrich_cli_on_matter_with_zero_spans_creates_nothing_and_exits_zero`,
  `test_run_enrichment_on_matter_with_zero_spans_returns_empty_list`,
  `test_mcp_fetch_of_nonexistent_assertion_id_does_not_crash`,
  `test_rating_list_nulls_rationale_for_unauthorized_peer_but_not_for_rater_or_reviewer`.
  Full suite re-run with these included: backend 290 passed, 0 failed;
  frontend unchanged at 62 passed.

  **Deviation noted (not a QA-FAIL)**: `## Dev Complete`'s prose swaps the
  D2/D3 labels relative to this contract's own `## Next Steps` item
  definitions — Next Steps defines D2 as the G8 E2E flow test
  (`test_local_first_platform_flow.py`) and D3 as the zero-network
  guardrail (`test_no_network_dependencies.py`), but Dev Complete's prose
  calls the zero-network guardrail "D2" and the E2E flow "D3". Both
  underlying deliverables are correct, tested, and green — this is a
  bookkeeping label swap only, not a functional defect. QA's `##
  Completed` entries use the Next Steps (authoritative) labels and note
  the swap inline.

  **Verdict**: 16/17 PASS (A1–A9, B1–B3, C1, C2, D2, D3). D1 FAILED
  (RUNBOOK.md "Vue.js" factual defect — prose, no test pin possible; see
  contract's D1 item for the exact quote and reasoning).
  `status: qa-fail`, `current_role: developer`, `qa_cycles: 1`,
  `completed_items: 16`. Pushed after each commit.

## Pre-compression contract snapshot (fea7de7, archived at Phase 6 close)

```markdown
---
id: "2026-07-26-local-first-platform"
status: review
current_role: planner
branch: sprint/2026-07-26-local-first-platform
locked_by: "claude-code:qa"
locked_at: "2026-07-26T11:20:00Z"
last_agent: "claude-code:qa"
last_updated: "2026-07-26T11:00:17Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 17
completed_items: 17
dev_complete_items: 17
qa_cycles: 2
prd_sections:
  - docs/specs/collaborative-assertions.md
design_sections: []
previous_sprint: "2026-07-25-collaborative-assertions"
---

# Sprint: Local-first platform — authored-text fidelity, ingest pipeline, LexGraph MCP, packaging

Director mandate (2026-07-26): LexGraph is a three-part local-first open-source
system usable from Claude Code, Codex, Cursor, or Antigravity: (1) an
enrichment stage that suggests assertions from documents already stored in
the database (document acquisition/scraping is explicitly out of scope);
(2) the grading app (exists) that edits the database; (3) a LexGraph MCP
server that maps the database for agent sessions (CodeGraph-style: fewer
tokens, less time, better output). Everything local — no cloud deploy;
installable from a terminal. Also resolve GitHub issue #2 (store raw +
sanitized text separately), including its length-cap sub-item.

Director scope amendment (2026-07-26, mid-planning): scraping/document
acquisition is OUT of scope this sprint — no file-ingest CLI, no txt/md/html
parsing pipeline, no document-loader modules. Documents arrive in the
database by the existing means only (the current API/fixtures). Enrichment
is the only pipeline surface this sprint: it runs over documents already
stored in the local DB and suggests assertions as proposal drafts. See
ruling R7.

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

Planner pass complete 2026-07-26. 17 items across 4 tracks. Track A is
sequential and lands first (schema + fidelity); Tracks B/C/D are
parallel-eligible once Track A's schema item (A1) is dev-complete, since B2
writes propositions through the same revision-creation path A1/A2 touch.

### Track A — text fidelity, sanitizer pins, length cap (G1–G4) — sequential, FIRST

**DEV COMPLETE (all 9 items, Sonnet medium, solo) — see `## Dev Complete`
below for files/commits/results per item.** Item specs kept here as
reference for QA and for the Track B/C/D items below, which build on this
track's schema/routes.

**A1. Raw-text columns + reversible migration + backfill**
Add `proposition_raw` (assertion_revisions), `comment_text_raw`
(assertion_comments), `rationale_raw` (assertion_ratings) columns (ORM +
a hand-rolled reversible migration module, no Alembic — see Deviations).
Migration backfills sanitized value into raw for pre-existing rows;
downgrade drops the columns. Document the backfill in `docs/RUNBOOK.md`
(D1). Files: `backend/app/models/assertion_revision.py`,
`assertion_comment.py`, `assertion_rating.py`, new
`backend/app/migrations/add_raw_text_columns.py`.
Test: `backend/tests/integration/test_migration_raw_text_columns.py`.

**A2. Write paths (assertions) store raw + sanitized**
`POST /assertions`, `PATCH /assertions/{id}`, `POST
/assertions/{id}/revisions` store `body.proposition` verbatim into the new
revision's `proposition_raw`, sanitized value unchanged in `proposition`.
`GET /assertions/{id}` exposes the current revision's raw text as
`proposition_raw`. Files: `backend/app/routers/assertions.py`.
Test: `backend/tests/integration/test_assertion_raw_text_fidelity.py`.

**A3. Write paths (comments) store raw + sanitized**
Comment create/update store `comment_text_raw` verbatim; list/get expose
it. Files: `backend/app/routers/comments.py`.
Test: `backend/tests/integration/test_comment_raw_text_fidelity.py`.

**A4. Write paths (ratings) store raw + sanitized**
Rating PUT stores `rationale_raw` verbatim; get/list expose it (same
rationale-visibility permission gate as today). Files:
`backend/app/routers/ratings.py`.
Test: `backend/tests/integration/test_rating_raw_text_fidelity.py`.

**A5. G1 acceptance: named examples round-trip byte-exact**
The three issue-#2 example strings (`<Title>`, `<appendix A>`, `<img
plaintail <b>Y</b> Z`) round-trip byte-exact through create → fetch →
PATCH (new revision) → revision history, via the raw columns from
A2–A4. Depends on A1+A2. Test:
`backend/tests/integration/test_g1_fidelity_round_trip.py`.

**A6. Search reads raw, not sanitized (read-path classification)**
`GET /assertions?q=...` matches against the current revision's raw
proposition (joined), not the lossy sanitized column — so a search term
lost by the sanitizer (e.g. "appendix A") still finds the assertion. No
export/diff endpoint exists in this codebase to classify separately; audit
already stores only short status strings (spec §16), never proposition
text. Files: `backend/app/routers/assertions.py`.
Test: `backend/tests/integration/test_search_raw_text_classification.py`.

**A7. Frontend: revision history + comparison render raw as text nodes**
`AssertionRevisionHistory` and `AssertionComparisonView` render the raw
proposition (never `dangerouslySetInnerHTML` — plain JSX text nodes, which
neither component uses today) so angle-bracket prose is visible
byte-exact in the diff/compare surfaces. Files:
`frontend/src/components/AssertionRevisionHistory.tsx`,
`AssertionComparisonView.tsx`.
Tests (edited in place, new cases added):
`frontend/src/components/__tests__/AssertionRevisionHistory.test.tsx`,
`AssertionComparisonView.test.tsx`.

**A8. Length cap: 100,000 chars enforced at the API (G4)**
New `validate_text_length(text, *, label, max_length=100_000)` in
`app/services/validation.py`; called for proposition (create/patch/
revision-create), comment_text (create/update), rationale (rating put).
Rejects with a clear 422 detail; boundary (exactly 100,000) is accepted.
Files: `backend/app/services/validation.py`, `routers/assertions.py`,
`comments.py`, `ratings.py`. Tests:
`backend/tests/unit/test_validation_length_cap.py`,
`backend/tests/integration/test_length_cap_api.py`.

**A9. Stale-pin sweep: supersede the R18 "accepted limitation" framing**
`sanitize_for_storage` itself is UNCHANGED (still browser-faithful, still
lossy for tag-attribute-shaped prose) — the sweep does not weaken it. Only
the one test that treated the sanitized column as the sole fidelity story
is re-pointed to also assert byte-exact `proposition_raw`; see `## Stale-pin
sweep` below for the exact hit list.

### Track B — enrichment only (G5, G6) — parallel-eligible after A1

**B1. Enrichment CLI command**
`python -m app.enrich.cli --matter-id <id>` runs the enrichment pass over
documents/spans already in the DB (seeded via existing conftest
fixtures/API — no file parsing). Idempotent re-run (no duplicate draft
assertions for a span already suggested); clear non-zero-exit failure for
an unknown matter. Files: `backend/app/enrich/cli.py`.
Test: `backend/tests/integration/test_enrich_cli.py`.

**B2. Offline heuristic suggester + live pipeline**
`app/enrich/suggester.py`: pure heuristic function, span text → candidate
proposal(s) (type, proposition, evidence span). Live pipeline writes real
`Assertion`/`AssertionRevision`/`AssertionEvidence` rows (origin
`model_suggested`, status `draft`/`proposed`, never `accepted`) against
real spans, visible via the existing `GET /assertions` list. Files:
`backend/app/enrich/suggester.py`, `pipeline.py`. Tests:
`backend/tests/unit/test_enrichment_suggester.py`,
`backend/tests/integration/test_enrichment_pipeline_live.py`.

**B3. Pluggable enricher interface (R4 boundary seam)**
`app/enrich/base.py` defines the `Enricher` protocol; the pipeline accepts
an injected enricher (declared boundary seam — a fake enricher is allowed
here only), defaulting to the real built-in `HeuristicEnricher` when none
is given. Files: `backend/app/enrich/base.py`.
Test: `backend/tests/unit/test_enricher_interface.py`.

### Track C — LexGraph MCP (G7) — parallel-eligible after A1

**C1. MCP stdio server: explore/search/fetch tools, no network**
`app/mcp/server.py` (official `mcp` SDK, stdio transport) registers
`explore` (query → assertions + evidence + relationships in one bounded
call), `search`, `fetch` tools reading the local SQLAlchemy session
directly; zero network I/O. Files: `backend/app/mcp/server.py`,
`backend/pyproject.toml` (add `mcp` dependency).
Test: `backend/tests/integration/test_mcp_tools_live.py`.

**C2. MCP registration docs**
`docs/mcp-registration.md`: one command to register with Claude Code;
config snippets for Codex, Cursor, Antigravity.
Test: `backend/tests/unit/test_mcp_registration_docs.py`.

### Track D — local-first install + E2E (G8) — parallel-eligible after A1+B1

**D1. Local-first install runbook**
`docs/RUNBOOK.md`: DB init/migration (incl. A1's backfill note), backend
serve, grading-app serve, MCP registration (points to C2).
Test: `backend/tests/unit/test_local_first_runbook_docs.py`.

QA cycle 1 bounced D1 (`docs/RUNBOOK.md` mislabeled the frontend
"Vue.js"); fixed in `0e66b73` and re-verified PASS in QA cycle 2 — see
`## Completed` and `## QA Notes`.

**D2. G8 E2E: seed → enrich → review → grade, fully local**
Seed a matter/document/source_span via existing fixtures, run the
enrichment pipeline (B2), submit for review, reviewer accepts via the
existing API, assert the accepted assertion appears in
`GET /matters/{id}/graph` — one process, one local SQLite file, no
network. Test: `backend/tests/e2e/test_local_first_platform_flow.py`.

**D3. Zero-network guardrail**
Static test asserting `app.enrich` and `app.mcp` import none of
`httpx`/`requests`/`urllib.request`/`aiohttp`/`socket`.
Test: `backend/tests/unit/test_no_network_dependencies.py`.

### Parallelization plan (write-sets, zero overlap)

- **Track A** (sequential, first): `backend/app/models/assertion_revision.py`,
  `assertion_comment.py`, `assertion_rating.py`; new
  `backend/app/migrations/`; `backend/app/routers/assertions.py`,
  `comments.py`, `ratings.py`; `backend/app/services/validation.py`;
  `frontend/src/components/AssertionRevisionHistory.tsx`,
  `AssertionComparisonView.tsx`. Owner of `proposition_raw`/
  `comment_text_raw`/`rationale_raw` persistence (new repository-level
  columns) and every write call-site listed above.
- **Track B** (after A1): new `backend/app/enrich/` package only
  (`cli.py`, `suggester.py`, `pipeline.py`, `base.py`). Owner of the new
  `run_enrichment(...)` dispatcher call-site and the `Enricher` protocol.
  Reads `app.routers.assertions`/`app.models` but does not edit them.
- **Track C** (after A1): new `backend/app/mcp/` package only
  (`server.py`); `backend/pyproject.toml` (dependency line only, additive).
  Owner of the `explore`/`search`/`fetch` tool registrations. Reads
  `app.models` but does not edit routers.
- **Track D** (after A1+B1): `docs/RUNBOOK.md`, `docs/mcp-registration.md`
  (new docs only); `backend/tests/e2e/test_local_first_platform_flow.py`
  (new test only, no app code). No shared file with A/B/C.

### Expected-RED census

| Test file | Expected failing | Failure mode |
|---|---|---|
| `integration/test_migration_raw_text_columns.py` | 2 | ModuleNotFoundError (`app.migrations`) |
| `integration/test_assertion_raw_text_fidelity.py` | 4 | KeyError/AssertionError (no `proposition_raw` key) |
| `integration/test_comment_raw_text_fidelity.py` | 2 | KeyError/AssertionError |
| `integration/test_rating_raw_text_fidelity.py` | 2 | KeyError/AssertionError |
| `integration/test_g1_fidelity_round_trip.py` | 3 | KeyError/AssertionError |
| `integration/test_search_raw_text_classification.py` | 1 | AssertionError (search misses raw-only match) |
| `AssertionRevisionHistory.test.tsx` (new cases) | 1 | AssertionError (raw text not in DOM) |
| `AssertionComparisonView.test.tsx` (new cases) | 1 | AssertionError |
| `unit/test_validation_length_cap.py` | 4 | ImportError (`validate_text_length`) |
| `integration/test_length_cap_api.py` | 6 | AssertionError (no 422 / no cap); +1 GREEN companion (at-cap accepted) stays green |
| `integration/test_hostile_input.py` (edited) | 1 | KeyError/AssertionError (`proposition_raw` missing) |
| `integration/test_enrich_cli.py` | 3 | ModuleNotFoundError (`app.enrich`) |
| `unit/test_enrichment_suggester.py` | 3 | ModuleNotFoundError |
| `integration/test_enrichment_pipeline_live.py` | 2 | ModuleNotFoundError |
| `unit/test_enricher_interface.py` | 3 | ModuleNotFoundError |
| `integration/test_mcp_tools_live.py` | 2 | ModuleNotFoundError (`app.mcp`) |
| `integration/test_mcp_search_fetch_tools.py` | 2 | ModuleNotFoundError (`app.mcp`) |
| `unit/test_mcp_registration_docs.py` | 1 | FileNotFoundError/AssertionError |
| `unit/test_local_first_runbook_docs.py` | 1 | FileNotFoundError/AssertionError |
| `e2e/test_local_first_platform_flow.py` | 1 | ModuleNotFoundError (`app.enrich`) |
| `unit/test_no_network_dependencies.py` | 2 | ModuleNotFoundError |

Census corrected by the manager 2026-07-26 from a measured full run
(`41 failed, 238 passed, 1 collection error` — reconciles exactly with the
table above; the length-cap unit file's 4 tests surface as 1 collection
ERROR until `validate_text_length` exists).

## Stale-pin sweep

`grep -riE "browser-faithful|accepted limitation|browser faithful"` across
`backend/tests/{unit,integration,e2e}` and `frontend/src/components/__tests__`
found exactly two hits, both from ruling R18 (2026-07-25 sprint):

- `backend/tests/unit/test_validation.py` — 3 pins on `sanitize_for_storage`
  directly (`test_sanitize_drops_text_parsed_as_tag_attributes_browser_faithful_*`).
  **Not re-pointed**: these test the pure sanitizer function, which issue #2
  explicitly requires stay unweakened; their assertions remain correct and
  unchanged. Docstrings amended in place to replace the stale "(proposed
  for a future sprint)" note with a pointer to this sprint's raw-storage
  resolution.
- `backend/tests/integration/test_hostile_input.py::test_proposition_text_parsed_as_tag_attributes_dropped_browser_faithful_via_real_api`
  — **re-pointed**: added `assert r.json()["proposition_raw"] == text`
  (byte-exact) alongside the existing (unchanged) sanitized-column
  assertion, since the raw column now supersedes "permanently lost" as the
  fidelity story for this shape. This is the one hit that changes behavior
  the Developer must satisfy (A2/A5).

No other hits for "single-column" storage assumptions or `r.json() ==`
exact-dict-equality patterns that would break from the new `_raw` response
keys (verified via `grep -rn "json() =="` across `backend/tests` — the only
hit is an unrelated empty-list assertion in `test_notifications.py`).

## Dev Complete

Developer pass (Track A solo, Sonnet medium), spawned on 017c9d7, all 9
items dev-complete:

- **A1** Raw-text columns + reversible migration + backfill. Files:
  `backend/app/models/assertion_revision.py`, `assertion_comment.py`,
  `assertion_rating.py`, `backend/app/migrations/__init__.py`,
  `add_raw_text_columns.py`. Commit `47507b3`. Result: `upgrade`/`downgrade`
  green (2/2); ORM columns added nullable, backfilled by the migration.
- **A2** Assertion write paths (create/patch/create-revision) store raw +
  sanitized. Files: `backend/app/routers/assertions.py`. Commit `d11324c`.
  Result: 4/4 green.
- **A3** Comment write paths store raw + sanitized. Files:
  `backend/app/routers/comments.py` (+ `assertions.py`'s embedded comment
  summary, for read-path consistency). Commit `b14abe3`. Result: 2/2 green.
- **A4** Rating write paths store raw + sanitized rationale, same
  rationale-visibility gate applied to `rationale_raw`. Files:
  `backend/app/routers/ratings.py`. Commit `820a4b4`. Result: 2/2 green.
- **A5** G1 named-example round-trip. No new code — green as a direct
  consequence of A1+A2 (verified, no commit of its own). Result: 3/3 green.
- **A6** Search matches the current revision's raw proposition, not the
  sanitized column. Files: `backend/app/routers/assertions.py`. Commit
  `c281ed6`. Result: 1/1 green.
- **A7** Frontend revision-history + comparison render
  `propositionRaw ?? proposition` as plain JSX text nodes (no
  `dangerouslySetInnerHTML` introduced). Files:
  `frontend/src/components/AssertionRevisionHistory.tsx`,
  `AssertionComparisonView.tsx`. Commit `cb2546b`. Result: 2/2 new cases
  green; full frontend suite 62/62 green.
- **A8** `validate_text_length(text, *, label, max_length=100_000)` added
  to `app/services/validation.py`; wired into every proposition/
  comment_text/rationale write path (create/patch/create-revision,
  comment create/update, rating put), checked against the raw submitted
  text before sanitization. `sanitize_for_storage` untouched. Files:
  `backend/app/services/validation.py`, `routers/assertions.py`,
  `comments.py`, `ratings.py`. Commit `a0bf1f6`. Result: unit 4/4, API
  6/6 (+1 at-cap companion stayed green) — 11/11.
- **A9** Stale-pin sweep. No code change: `sanitize_for_storage` is
  byte-identical to before this sprint; the Planner-edited
  `test_hostile_input.py` pin (which asserts `proposition_raw == text`
  alongside the unchanged sanitized-column assertion) went green as a
  direct consequence of A2's `proposition_raw` exposure on
  `_serialize_assertion`. Verified: full `test_hostile_input.py` 40/40
  green, including the 17-shape hostile battery and all 3
  `test_validation.py` browser-faithful pins untouched.

Parallel pass (devB enrichment / devC MCP, both Sonnet medium, spawned on
eb38032 in isolated worktrees; manager merged devC ff → a578477, devB
merge → c836154; entries applied by the manager per parallel-mode rule):

- **B1** Enrichment CLI (`python -m app.enrich.cli --matter-id <id>
  --triggered-by-user-id <id>`; reads `LEXGRAPH_DATABASE_URL`; non-zero
  exit + stderr on unknown matter). Files: `backend/app/enrich/cli.py`.
  Commit `9acd0f9`. Result: 3/3 green.
- **B2** Offline heuristic suggester + live pipeline: deterministic
  precision-first rule set → real Assertion/AssertionRevision/
  AssertionEvidence rows, origin `model_suggested`, status `draft`, never
  accepted; raw/sanitized split mirrors `routers/assertions.py`;
  idempotent re-runs. Files: `backend/app/enrich/suggester.py`,
  `pipeline.py`. Commit `be82651`. Result: 3/3 + 2/2 green.
- **B3** Pluggable `Enricher` protocol, default `HeuristicEnricher`
  (declared R4 boundary seam). Files: `backend/app/enrich/base.py`,
  `__init__.py`. Commit `e3598a8`. Result: 3/3 green.
- **C1** LexGraph MCP stdio server (`FastMCP`, tools explore/search/fetch,
  read-only per R5, zero network, bounded results, raw-text precedence,
  runnable `python -m app.mcp.server`). Files: `backend/app/mcp/__init__.py`,
  `server.py`. Commit `a578477`. Result: 4/4 green.

Developer pass (Track D solo, doc-only, Haiku low), spawned on 9b9c60b:

- **C2** MCP registration docs. Files: `docs/mcp-registration.md`. Commit
  `48caf40`. Result: 1/1 green. Covers Claude Code registration (`claude mcp
  add lexgraph`), plus config snippets for Codex, Cursor, and Antigravity.
- **D1** Local-first install runbook. Files: `docs/RUNBOOK.md`. Commit
  `48caf40`. Result: 1/1 green. Covers DB init/migration/backfill, backend
  serve, grading-app serve, MCP registration, E2E workflow, environment
  variables, and troubleshooting.
- **D2** Zero-network guardrail (no code). Test: `backend/tests/unit/test_no_network_dependencies.py`. Result: 2/2 green with no code — verified in full pass.
- **D3** Local-first E2E flow (no code). Test: `backend/tests/e2e/test_local_first_platform_flow.py`. Result: 1/1 green with no code — verified in full pass.

Developer-verified on the dev tree (48caf40): backend 283 passed /
0 failed; frontend 62 passed / 0 failed. Scoped doc tests 2/2 green
before commit; full pass confirms zero regressions across all 17
completed items (A1–A9, B1–B3, C1–C2, D1–D3).

Owned-file conditional grants (`backend/app/routers/history.py`,
`backend/app/models/repository.py`): not exercised. No Track A test reads
`GET /assertions/{id}/history` (audit-only, stores short status strings
per spec §16, never proposition text) or a repository-pattern write layer
(`app/models/repository.py` is the `Repository` ORM model, not a write
layer); every write path in this app goes directly through routers via
`Session`. Both files left untouched.

## Completed

QA cycle 1 (2026-07-26), 16/17 PASS — D1 bounced (now fixed, see below).
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
  `backend/tests/e2e/test_local_first_platform_flow.py`, per this
  contract's Track D item list — labeled "D3" in `## Dev Complete`'s prose,
  see `## QA Notes`). PASS — 1/1 green; test body read in full and matches
  gate G8 exactly against the real API, one local SQLite file, no network.
  Regression: n/a (E2E-level, exhaustive by design).
- **D3** (zero-network guardrail;
  `backend/tests/unit/test_no_network_dependencies.py`, per this
  contract's Track D item list — labeled "D2" in `## Dev Complete`'s prose,
  see `## QA Notes`). PASS — manually grepped every import in `app/enrich/`
  and `app/mcp/`; zero network-capable modules, matching the AST-based
  test's verdict. Regression: n/a (static-analysis-level, exhaustive).

## Evaluation Notes

Track A (A1–A9), Developer solo pass, dev-complete 2026-07-26 (see `## Dev Complete` for per-item detail):

**Previous evaluation (Track A summary)**:

- Scoped RED confirmed before work started: 21 failed across the 8 Track A
  integration/hostile-input files + 4-test collection error in
  `test_validation_length_cap.py` — matched the contract's corrected
  census exactly.
- Per-item scoped runs, all green: A1 2/2, A2 4/4, A3 2/2, A4 2/2, A5 3/3,
  A6 1/1, A7 2/2 (+ full frontend suite), A8 11/11 (4 unit + 6 API + 1
  at-cap companion), A9 verified via full `test_hostile_input.py` 40/40
  (no code change required for A5 or A9 — both went green as direct
  consequences of A1/A2's `proposition_raw` plumbing).
- One full authoritative pass:
  `backend/.venv/bin/pytest backend/tests -v` → **20 failed, 263 passed**;
  `npm --prefix frontend run test -- --run` → **62 passed**. The 20
  backend failures reconcile exactly against the contract's expected
  Track B/C/D RED list (test_enrich_cli 3, test_enrichment_suggester 3,
  test_enrichment_pipeline_live 2, test_enricher_interface 3,
  test_mcp_tools_live 2, test_mcp_search_fetch_tools 2,
  test_mcp_registration_docs 1, test_local_first_runbook_docs 1,
  test_local_first_platform_flow 1, test_no_network_dependencies 2) — no
  failure outside that list. `test_validation_length_cap.py`'s collection
  error is gone.
- `sanitize_for_storage` is byte-identical to before this sprint (not
  edited); all 3 `test_validation.py` browser-faithful pins and the
  17-shape hostile battery in `test_hostile_input.py` remain green.
- No `dangerouslySetInnerHTML` introduced anywhere in the frontend diff.
- Conditional grants (`routers/history.py`, `models/repository.py`) not
  exercised/edited — no Track A test reads either surface; every write
  path goes directly through routers via `Session`.

Track D (C2+D1+D2+D3), Developer solo pass (doc-only items), dev-complete
2026-07-26. Summary counts only (see `## Dev Complete` for per-item detail):

- Scoped RED confirmed before work: 2 failed (doc-tests for C2, D1 only).
- Doc files written: `docs/mcp-registration.md` (covers Claude Code + 3
  client config snippets) and `docs/RUNBOOK.md` (fresh-clone to working
  local-first system in one doc: DB init/migration/backfill, backend serve,
  grading-app serve, MCP registration, E2E workflow, troubleshooting).
- Scoped run: C2+D1 both pass 1/1 each.
- D2 and D3 are verify-only (no code): `test_local_first_platform_flow` and
  `test_no_network_dependencies` are already green from prior dev work
  (B1/C1). Verified in full pass: both remain green.
- Full authoritative pass: backend 283/283 green, frontend 62/62 green. Zero
  regressions across all 17 completed items (A1–A9 from prior dev, B1–B3
  from prior devB/devC, C1 from prior devC, C2+D1+D2+D3 this pass).
- Deviations from brief: none.

## QA Notes

- 2026-07-26T13:35Z qa: Independent evaluator green — backend 283→290
  passed (7 new QA regressions), frontend 62/62, zero flakes. Live-path
  PASS: enrich CLI subprocess (idempotent, clean unknown-matter failure),
  MCP stdio boot (5s, stdin held open, no crash), FastMCP real
  `call_tool` dispatch confirmed, frontend raw-text rendering + zero
  `dangerouslySetInnerHTML`. Gate sweeps PASS: G1/G2 classification
  (JSON-only backend + 2 text-node React components), G3 migration
  round-trip (live, throwaway DB), G4 privacy (live — closed a real
  untested gap). D1 FAILED: `docs/RUNBOOK.md` calls the frontend
  "Vue.js" — it's React+Vite (manager's own pre-handoff log already
  flagged this). 16/17 PASS. Full transcript: see `-log.md`.
- 2026-07-26T11:00:17Z qa (cycle 2, D1 scoped re-verify): fix commit
  `0e66b73` confirmed in history; `git diff f4b656a..0e66b73` touches only
  `docs/RUNBOOK.md`, 1 line. `grep -in vue docs/RUNBOOK.md` zero hits;
  `grep -in react docs/RUNBOOK.md` names the app correctly. Doc tests
  (`test_local_first_runbook_docs.py`, `test_mcp_registration_docs.py`)
  2/2 passed. Full re-run: backend 290 passed, frontend 62 passed — matches
  cycle 1 exactly, zero regressions. D1 PASS. 17/17 items PASS; sprint
  moved to `review`.

## Context Dump

- New sprint opened by manager 2026-07-26. Planner defines items + RED tests
  per the gates above. Issue #2 body is authoritative for G1–G4 detail:
  https://github.com/vicciz-ceo/LexGraph/issues/2
```
