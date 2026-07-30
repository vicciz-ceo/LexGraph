---
id: "2026-07-30-deterministic-assertions"
status: dev-complete
current_role: qa
branch: sprint/2026-07-30-deterministic-assertions
locked_by: "claude-code:qa"
locked_at: "2026-07-30T11:05:00Z"
last_agent: "claude-code:developer"
last_updated: "2026-07-30T13:20:00Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 1
completed_items: 0
dev_complete_items: 1
qa_cycles: 0
previous_sprint: "2026-07-29-mcp2-migration"
prd_sections: []
design_sections: []
---

# Sprint: Deterministic assertions — status semantics + article-mention links

## Mandate (director)

1. Remove the "proposed" status for deterministic assertions. "Proposed" is
   reserved for implicit AI-deduced assertions that still need a human
   rating; deterministically derived assertions must not carry it.
2. When an article mentions another article within a law, connect the two
   with a deterministic assertion.
3. At the end, verify the outcome on the DB in the `lexgraph-assertions-db`
   folder (POC builder at "/Users/nerya/AI for others/lexgraph-assertions-db",
   its own git repo).

## Acceptance gates (manager-defined, plain language)

Draft — pending recon; finalized before Planner spawn.

- **G1 — No deterministic assertion is "proposed":** everywhere an assertion
  is created by a deterministic derivation (not AI inference), its status is
  not "proposed"; "proposed" remains valid only for AI-deduced assertions
  awaiting human rating.
- **G2 — Article-mention links exist:** when one article's text mentions
  another article of the same law, the two are connected by a deterministic
  assertion.
- **G3 — Suites green:** full backend + frontend suites pass.
- **G4 — DB outcome verified:** the rebuilt `lexgraph_assertions.sqlite` in
  the POC builder shows (a) zero deterministic assertions with status
  "proposed" and (b) article→article mention assertions present, verified by
  direct SQL probes.

## Manager rulings

- R1: Sprint branch based on `origin/main` @ 3feaa41.
- R2 (resolved post-recon): dual-repo sprint. LexGraph receives the
  status-semantics fix for its deterministic definition-links pipeline
  (pipeline.py assigns "proposed" today) + test-estate sweep. The POC
  builder ("/Users/nerya/AI for others/lexgraph-assertions-db", own git
  repo, NO remote, own contract + lock, baseline `984593b`) receives the
  status fix AND the intra-law article-mention pass — the director's
  verification target is the POC DB. Mention derivation inside the
  LexGraph app pipeline is OUT of this sprint (possible follow-up).
- R3: Replacement status for deterministic assertions is **"accepted"**
  (no human rating needed per director's semantics; derivation stays
  encoded in origin=system_generated; reviewed_by/reviewed_at stay null).
- R4: User-suggested assertions (`routers/assertions.py`, save_as
  draft|proposed, origin=user_suggested) are NOT deterministic and stay
  unchanged; AI heuristics (origin=model_suggested) keep "proposed" — that
  is the reserved use. Surfaced to director for possible follow-up ruling
  on user-suggested semantics.
- R5: Recon dossier at
  `docs/sprint/sprints/2026-07-30-deterministic-assertions-review.md`;
  Planner briefs reference it by path, never re-inline it.

## Next Steps

## Stale-pin sweep

Roots checked: `backend/tests/unit/`, `backend/tests/integration/`,
`backend/tests/e2e/`, `frontend/src/components/__tests__/*.test.tsx`
(`grep -riE "proposed"`; full grep output logged).

- **Re-pointed (this sprint, fixed in this commit):**
  - `backend/tests/integration/test_definition_links_cli.py:41-63` — asserted
    all CLI-created deterministic assertions were `"proposed"`; now asserts
    `"accepted"` (test renamed to `..._creates_accepted_assertions_...`).
  - `backend/tests/integration/test_definition_links_pipeline_live.py:25,84`
    — same collision, NOT flagged by the recon dossier (recon only named
    the CLI test) — found during this sweep. Docstring + assertion
    re-pointed to `"accepted"`.
- **Left as-is, with reason:**
  - `backend/tests/unit/test_graph_projection.py:23-30,44-50` — `"proposed"`
    here is a synthetic fixture value for `InMemoryGraphProjection`'s
    generic show/hide-unreviewed filter; it exercises "any non-accepted
    status", is unrelated to the definition-links pipeline, and is
    unaffected by this sprint's status-semantics change. Left unchanged.
  - `backend/tests/integration/test_enrichment_pipeline_live.py:45` —
    `app/enrich/pipeline.py` uses `_MODEL_STATUS = "draft"` with
    `origin=model_suggested` (AI heuristic pipeline, ruling R4's reserved
    use) — a different pipeline entirely, not deterministic. Unchanged.
  - `backend/tests/integration/test_assertions_crud.py`,
    `test_rating_raw_text_fidelity.py`,
    `test_qa_regression_local_first_platform.py`, `test_length_cap_api.py`,
    `test_validation_duplicates_api.py`, `test_search_sort.py`,
    `test_ratings_api.py`, `test_hostile_input.py`,
    `test_graph_projection_api.py`, `test_review_workflow.py`,
    `e2e/test_local_first_platform_flow.py`, `e2e/test_full_flow.py` — all
    exercise the user-submission path (`save_as: "proposed"`,
    `origin=user_suggested`, `routers/assertions.py`) or generic
    default-view filtering — ruling R4: user paths unchanged. Left as-is.
  - `frontend/src/components/__tests__/AssertionCard.test.tsx`,
    `AssertionDetailPanel.test.tsx`, `AssertionReviewPanel.test.tsx`,
    `AssertionSuggestionForm.test.tsx` — all use `origin: "user_suggested"`
    fixtures or generic reviewer-panel/status props; none represent
    deterministic-pipeline output. Confirmed legitimate (ruling R4), left
    unchanged.

## Dev Complete

- [x] **L1 — deterministic definition-links status: "proposed" → "accepted".** Changes committed; status now "accepted" across all deterministic definition-linking assertions (pipeline.py:49, RUNBOOK.md:160 updated). Tests green: backend 423 passed, frontend 62 passed.

## Completed

## Evaluation Notes

Scoped tests (definition-links pipeline and CLI): 12 passed. Full suite: backend 423 passed, frontend 62 passed. All acceptance gates remain green. No pre-existing green tests broken.

## QA Notes

## Context Dump

- Sprint created 2026-07-30 by manager; recon pending on where "proposed"
  is set for deterministic assertions in each repo and what article-mention
  linking already exists (builder repo has a citation graph artifact).
