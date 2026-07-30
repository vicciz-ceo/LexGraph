---
id: "2026-07-30-deterministic-assertions"
status: planning
current_role: planner
branch: sprint/2026-07-30-deterministic-assertions
locked_by: "claude-code:planner"
locked_at: "2026-07-30T09:46:17Z"
last_agent: "claude-code:manager"
last_updated: "2026-07-30T09:46:17Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 0
completed_items: 0
dev_complete_items: 0
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
- R2: Cross-repo scope (LexGraph vs lexgraph-assertions-db builder) to be
  ruled after recon; if both receive code, dual-repo mode applies (one
  contract + lock per repo).

## Next Steps

(Planner populates.)

## Stale-pin sweep

(Planner populates.)

## Dev Complete

## Completed

## Evaluation Notes

## QA Notes

## Context Dump

- Sprint created 2026-07-30 by manager; recon pending on where "proposed"
  is set for deterministic assertions in each repo and what article-mention
  linking already exists (builder repo has a citation graph artifact).
