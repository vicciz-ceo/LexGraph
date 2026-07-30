# Sprint log — 2026-07-30-deterministic-assertions (append-only)

## Agent roster

- 2026-07-30T09:47Z recon-lexgraph (Explore, haiku low-med) → agentId a27fce9d54bda5693
- 2026-07-30T09:47Z recon-assertions-db (Explore, haiku low-med) → agentId a2cdba69477f1e939
- 2026-07-30T10:00Z shared-planner dual-repo (general-purpose, sonnet high) → agentId a72ec2b29e124ab90
- 2026-07-30T10:30Z dev-lexgraph L1 (general-purpose, haiku low — bounded mechanical, RED committed) → agentId ac455da9693c8fa9e
- 2026-07-30T10:30Z dev-poc P1+P2 (general-purpose, sonnet medium — real parsing logic) → agentId adc828830226cc4c7

## Planner rationale (LexGraph side)

- Environment preflight: worktree had no `backend/.venv`. Built one
  (`python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`, python 3.13.12);
  `backend/.venv/bin/pytest backend/tests --collect-only -q` confirmed 423
  tests collected FROM THE WORKTREE tree (not the main checkout).
- L1 scope is narrow and well-isolated: `_STATUS = "proposed"` at
  `pipeline.py:49` is the single choke point (confirmed by reading the
  whole file — every `_create_assertion(...)` call goes through it, no
  second status literal anywhere in the module). No new unit-test file was
  needed/added: `run_definition_linking` has no pure, DB-free surface to
  unit-test in isolation (it's a thin function requiring a live session
  end-to-end), so re-pointing its existing live-path integration coverage
  IS the correct-weight RED proof, per the sprint's "no new heavyweight
  tests where an existing live test already pins the behavior" spirit.
- Sweep found a SECOND real collision the recon dossier missed:
  `test_definition_links_pipeline_live.py:25,84` also pinned
  `status == "proposed"` on `USES_DEFINITION` edges from the live pipeline
  — re-pointed in the same commit as the CLI test fix, per the hard rule
  ("re-point it in the same commit as your RED tests").
  `test_graph_projection.py` was the one recon flagged as ambiguous;
  reading it confirmed it is a pure `InMemoryGraphProjection` unit test with
  synthetic fixtures unrelated to the definition-links pipeline (generic
  accepted-vs-not filtering) — correctly left alone.
- Frontend fixtures (`AssertionCard`, `AssertionDetailPanel`,
  `AssertionReviewPanel`, `AssertionSuggestionForm`) were all read in full;
  every `"proposed"` occurrence there is either `origin: "user_suggested"`
  or a generic reviewer-panel prop with no tie to deterministic-pipeline
  output — confirmed legitimate per ruling R4, left unchanged.
- `docs/RUNBOOK.md:140,151,160` documents "draft/proposed" /
  "status=proposed" for both deterministic passes (enrichment AND
  definition-linking, described together in one paragraph at line 140).
  Only the definition-linking sentence (line 151/160) needs to change to
  "accepted" — the enrichment pass genuinely stays "draft"/"proposed"
  (`app/enrich/pipeline.py::_MODEL_STATUS = "draft"`, origin=model_suggested,
  out of scope). Flagged in the L1 item for the Developer to sync in the
  same commit as the code change; the Planner does not edit RUNBOOK.md
  (implementation-adjacent documentation, not a test file).

## QA log

- 2026-07-30T14:10:00Z qa-lexgraph L1 (independent verification agent,
  separate from the Developer) → verdict PASS.
- Preflight: confirmed worktree at expected HEAD `73f52f3`, clean tree,
  `backend/.venv/bin/pytest` present and functional (pytest 9.1.1, Python
  3.13.12).
- Read `backend/app/definition_links/pipeline.py` in full: `_ORIGIN =
  "system_generated"` (:48), `_STATUS = "accepted"` (:49), both consumed by
  the single `_create_assertion(...)` closure (:206-254) used for every
  `USES_DEFINITION` and `DERIVES_FROM_LAW` emission — no second status
  literal anywhere in the module.
- `git show 6a0c0f5` reviewed line-by-line: 2-line `pipeline.py` diff
  (`"proposed"` → `"accepted"`), 1-line `RUNBOOK.md` diff (:160,
  `status=proposed` → `status=accepted`); a separate commit `731fb25`
  ("manager doc-sync") fixed the OTHER occurrence at `RUNBOOK.md:140`
  (the "draft/proposed" summary sentence covering both offline pipelines
  together) → "draft/accepted" (draft = enrichment/model_suggested,
  unchanged per R4; accepted = definition-links, this sprint's change).
- `git diff --stat 3feaa41..73f52f3` audited for leakage: only
  `pipeline.py`, `test_definition_links_cli.py`,
  `test_definition_links_pipeline_live.py`, `RUNBOOK.md`, and sprint
  bookkeeping files changed. No implementation code outside
  `pipeline.py`; no non-owned test files touched.
- Read both re-pointed tests in full to confirm live-path: the CLI test
  calls `app.definition_links.cli.main([...])` directly (real entrypoint,
  not subprocess) then asserts via the real, already-registered
  `GET /api/v1/assertions` route; the pipeline-live test calls
  `run_definition_linking(db_session, ...)` against real ingested
  `Article` rows via `ingest_wiki_law`. Neither mocks the acceptance
  target.
- Full evaluator run (repo root, redirected to scratch, tail inspected):
  `backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run
  test -- --run` → `======================= 423 passed, 10 warnings in
  6.03s =======================` then ` Test Files  11 passed (11)` /
  `Tests  62 passed (62)`. Exit code 0. Single run, no flakes.
- Identified a genuine coverage gap while reading
  `test_definition_links_pipeline_live.py`: the RESOLVED
  `DERIVES_FROM_LAW` test
  (`test_run_definition_linking_resolves_a_cross_law_derivation_to_a_known_document`)
  never asserts anything about `status` — only the `USES_DEFINITION` test
  does. Wrote
  `backend/tests/integration/test_qa_regression_deterministic_assertions.py`
  (1 test): ingests all three vendored laws needed to hit
  `USES_DEFINITION` + `DERIVES_FROM_LAW` unresolved + `DERIVES_FROM_LAW`
  resolved in ONE matter/run, reads every created `Assertion` row straight
  off the DB via the ORM (`db_session.get(Assertion, id)`, not the
  pipeline's returned summary dict), and asserts `status == "accepted"`
  AND `status != "proposed"` for all of them, plus `origin ==
  "system_generated"` and `reviewed_by`/`reviewed_at` both `None`.
- Verified the new test is a real regression pin, not vacuous: ran
  `sed -i.bak 's/_STATUS = "accepted"/_STATUS = "proposed"/'
  backend/app/definition_links/pipeline.py`, re-ran the new test — failed
  with `AssertionError: assert 'proposed' == 'accepted'` — then
  `git checkout -- backend/app/definition_links/pipeline.py` and removed
  the `.bak` file; `git status --short` confirmed only the new test file
  remained untracked (implementation file byte-identical to HEAD).
  Re-ran the new test green afterward.
