# Sprint log — 2026-07-30-deterministic-assertions (append-only)

## Agent roster

- 2026-07-30T09:47Z recon-lexgraph (Explore, haiku low-med) → agentId a27fce9d54bda5693
- 2026-07-30T09:47Z recon-assertions-db (Explore, haiku low-med) → agentId a2cdba69477f1e939
- 2026-07-30T10:00Z shared-planner dual-repo (general-purpose, sonnet high) → agentId a72ec2b29e124ab90

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
