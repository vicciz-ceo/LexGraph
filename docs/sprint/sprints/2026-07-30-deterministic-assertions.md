---
id: "2026-07-30-deterministic-assertions"
status: review
current_role: planner
branch: sprint/2026-07-30-deterministic-assertions
locked_by: null
locked_at: null
last_agent: "claude-code:qa"
last_updated: "2026-07-30T10:45:06Z"
lint: "PASS 166 2026-07-30T10:45:06Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 1
completed_items: 1
dev_complete_items: 0
qa_cycles: 1
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

## Completed

- [x] **L1 — deterministic definition-links status: "proposed" → "accepted".**
  QA-verified (independent full run, commit 6a0c0f5): `pipeline.py:49`
  `_STATUS == "accepted"`, `_ORIGIN` unchanged (`system_generated`);
  `docs/RUNBOOK.md` synced (:160 by the Developer in 6a0c0f5, :140 by a
  separate doc-sync commit 731fb25). Both re-pointed live tests
  (`test_definition_links_cli.py`, `test_definition_links_pipeline_live.py`)
  confirmed to drive the REAL CLI entrypoint / `run_definition_linking`
  pipeline against real `Article`/`Definition`/`Assertion` ORM rows — no
  mocking. Diff audit (`git diff --stat 3feaa41..73f52f3`): only
  `pipeline.py`, the two owned test files, `RUNBOOK.md`, and sprint
  bookkeeping changed — no leakage. Full evaluator (from repo root,
  `backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run
  test -- --run`): **backend 423 passed, frontend 62 passed**, 0 failures,
  0 flakes. Regression: 1 new test added,
  `backend/tests/integration/test_qa_regression_deterministic_assertions.py::test_definition_links_pipeline_never_persists_proposed_status_across_all_edge_subtypes`
  — reads the persisted `Assertion.status` column (not the pipeline's
  summary dict) for every sub-type in one run (`USES_DEFINITION`,
  `DERIVES_FROM_LAW` resolved AND unresolved — the resolved-derivation case
  had never had its `status` checked by any prior test) and pins
  `status == "accepted"` / `status != "proposed"` explicitly. Verified RED
  against a reverted `_STATUS = "proposed"` (sabotage-and-revert via `git
  checkout`, no residual diff) before being committed green.

## Evaluation Notes

Scoped tests (definition-links pipeline and CLI): 12 passed. Full suite: backend 423 passed, frontend 62 passed. All acceptance gates remain green. No pre-existing green tests broken.

## QA Notes

- 2026-07-30T10:40Z (UTC; earlier stamp 14:10 was local-time error) — QA
  cycle 1, independent agent. Verdict **PASS**. Evaluator: backend 423 +
  frontend 62 passed, 0 failed, no flakes. Live-path confirmed on both
  re-pointed tests (real CLI + real pipeline, no mocks). Diff audit
  3feaa41..73f52f3: no leakage. Regression added: 1 (sabotage-verified
  RED then green). Full transcript in `-log.md`.

## Context Dump

- Both repos at `review`, QA cycle 1 full PASS (this repo L1 @6a0c0f5,
  QA @251e7db; POC P1+P2 @23edbe9, QA @a319d99, local-only, no remote).
- Rebuilt POC DB manager-verified by direct SQL: 164,237 assertions all
  "accepted", 0 "proposed"; REFERENCES_PROVISION 63,891→65,492 (+1,601
  same-document bare-mention edges); all other type counts unchanged;
  backup lexgraph_assertions.pre-status-accepted-20260730.sqlite kept.
- Awaiting director: merge sprint branch to main (PR) + close sprint.
