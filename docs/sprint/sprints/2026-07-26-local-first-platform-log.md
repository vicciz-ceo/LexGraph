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
