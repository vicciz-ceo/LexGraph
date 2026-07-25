---
id: "2026-07-25-collaborative-assertions"
status: planning
current_role: planner
branch: sprint/2026-07-25-collaborative-assertions
locked_by: "claude-code:planner"
locked_at: "2026-07-25T20:02:25Z"
last_agent: "claude-code:manager"
last_updated: "2026-07-25T20:02:25Z"
lint: null
evaluator: custom
evaluator_command: null   # TBD-by-Planner (fresh repo — Planner builds the harness)
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
prd_sections:
  - docs/specs/collaborative-assertions.md
design_sections: []
---

# Sprint: Collaborative assertion assessment & user-suggested assertions

Authoritative spec: `docs/specs/collaborative-assertions.md` (20 sections + 16-point definition of done).
Acceptance gates: `docs/sprint/sprints/2026-07-25-collaborative-assertions-log.md` § Acceptance gates.

## Manager rulings

- R1 Stack: backend Python 3.12 + FastAPI + SQLAlchemy 2 + Pydantic v2 + pytest; SQLite for test runs on a Postgres-compatible schema (PostgreSQL is the declared production authority per spec §11); frontend React 18 + TypeScript + Vite + Vitest + Testing Library. No live Neo4j here: graph projection goes behind a `GraphProjection` interface with an in-memory adapter; a Neo4j adapter may be stubbed but is not required to run.
- R2 Greenfield scaffold: the Planner MAY commit build/config scaffolding and empty package skeletons (pyproject, package.json, configs, bare app factory with no routes/handlers) so RED tests fail on assertions (404/missing behavior), never collection errors. All business logic and route handlers remain Developer work.
- R3 Auth: in-DB users + per-matter roles (viewer/contributor/reviewer/admin) with a test-friendly token scheme; no external IdP this sprint. All permission checks server-side (spec §12).
- R4 Notifications: in-app only (spec §15 MVP). No email/push.
- R5 Ratings are revision-scoped (spec §10 MVP): AssertionRating carries assertion_id + assertion_revision_id; one current rating per user per revision; prior-revision ratings preserved, never auto-copied.

## Next Steps

(Planner defines items here.)

## Dev Complete

## Completed

## Evaluation Notes

## QA Notes

## Context Dump

Fresh sprint, greenfield repo (README + spec only, no code). Planner: read the spec and the acceptance gates in the log file, honor Manager rulings R1–R5, define items with RED tests per the planner brief, and produce a parallelization plan with non-overlapping write sets.
