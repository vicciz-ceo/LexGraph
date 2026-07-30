---
id: "2026-07-30-ratings-grade"
status: planning
current_role: planner
branch: sprint/2026-07-30-ratings-grade
locked_by: "claude-code:planner"
locked_at: "2026-07-30T20:35:12Z"
last_agent: "claude-code:manager"
last_updated: "2026-07-30T20:35:12Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-07-30-deterministic-assertions"
prd_sections: []
design_sections: []
---

# Sprint: Ratings-driven grade — proposed until rated, then weak/probable/strong

## Mandate (director, 2026-07-30)

"Proposed" covers user-submitted AND AI-deduced assertions until they are
rated by other users; a rated assertion carries a 1-5 grade
(weak-probable-strong) instead. Director confirmed via batched gate
questions: (a) first rating by a non-author user ends "proposed"; (b) grade
= median of ratings, banded weak (1-2) / probable (3) / strong (4-5);
(c) the reviewer accept/reject workflow stays and overrides the grade.

## Acceptance gates (manager-defined, director-confirmed)

- **G1 — Proposed until rated:** a proposed assertion (user-submitted or
  AI-deduced) with zero ratings from non-author users still presents as
  "proposed" everywhere it is shown.
- **G2 — Grade after first outside rating:** once ≥1 non-author user has
  rated it, the assertion's standing is its grade — median strength banded
  weak (1-2) / probable (3) / strong (4-5) — visible via the assertions
  API and in the frontend wherever status is shown today.
- **G3 — Author ratings don't count:** the author's own rating never moves
  an assertion out of "proposed" (whether authors can rate at all follows
  current API rules — Planner characterizes; if currently allowed, it
  simply doesn't count toward G2).
- **G4 — Reviewer override intact:** explicit reviewer decisions
  (accept/reject/dispute/…) keep working unchanged and take precedence
  over the grade presentation.
- **G5 — Deterministic assertions untouched:** origin=system_generated
  assertions stay born-accepted (previous sprint) and never enter the
  proposed→grade flow.
- **G6 — Suites green:** full backend + frontend suites pass.

## Manager rulings

- R1: Sprint branch based on `main` @ 13c3484 (includes PR #13).
- R2: Scope is the LexGraph app only — the POC builder emits deterministic
  (accepted) assertions and has no ratings surface.
- R3: Manager lean, Planner may confirm or escalate with evidence: the
  grade/standing is DERIVED at read time from existing AssertionRating
  rows (services/ratings.py already computes median + distribution) and
  exposed as a field alongside `status` — no schema migration, no
  persisted status mutation on rating. Any schema/migration alternative is
  an ESCALATION, not a Planner decision.
- R4: "weak"/"probable"/"strong" are the only band names; band edges are
  weak ≤2, probable =3, strong ≥4 (median may be fractional, e.g. 2.5 —
  Planner pins the edge rule in tests: weak <3, probable =3, strong >3;
  fractional medians between 3 and 4 exclusive of 3 count per that rule —
  i.e. 3.5 → strong; 2.5 → weak).

## Next Steps

(Planner populates.)

## Stale-pin sweep

(Planner populates.)

## Dev Complete

## Completed

## Evaluation Notes

## QA Notes

## Context Dump

- Sprint opened 2026-07-30 after director confirmed grading semantics.
  Prior sprint (deterministic-assertions) closed done; ratings service
  already aggregates 1-5 strengths (average/median/distribution);
  assertion status transitions currently happen only in routers/review.py.
