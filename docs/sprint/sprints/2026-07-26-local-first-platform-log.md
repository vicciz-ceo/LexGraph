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
