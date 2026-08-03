---
id: "2026-08-04-defs-us-multiterm"
status: planning
current_role: planner
branch: claude/defs-us-multiterm
worktree: /Users/nerya/LexGraph-wt/defs-us-multiterm
locked_by: "claude-code:planner"
locked_at: "2026-08-04T00:00:00Z"
last_agent: "claude-code:sprint-manager"
last_updated: "2026-08-04"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
---

# Sprint: US families 5+6 — multi-term shared clauses + inline parentheticals

## Mandate

Two lower-volume but confirmed miss-classes (dossier §2 families 5-6 + §6):
- **F5 multi-term shared-clause**: `The term(s) "X", "Y", and "Z" mean(s)…`
  — one clause defines several terms; the splitter assumes one term per
  entry. MT(7/300), MI, NH, ND, NY, OK; VT's `"mail," "mails," "mailing,"
  and "mailed" mean…` (simultaneously an F3 zero-yield case); SD's 4-term
  clause under a proper heading (extractor yield unconfirmed — verify);
  TX-style parent-clause lists from the prior sprint's known limitations
  (13/75 degenerate recovered terms).
- **F6 inline parentheticals**: apposition abbreviations `("Term")` with no
  means-idiom following — rejected even by the inline fallback's idiom-gap
  check. MI/MT/NH/ND/NY/OK (~1-2/300 each), OR's cross-reference-style
  `"X" has the meaning given that term in ORS…` variant.
Each term in a shared clause must become its OWN definition row linked to
the shared definition text, with correct scope.

## Acceptance gates (program manager-defined)

- **U1 — Every variant is captured**, RED tests from real rows (incl. the
  VT/SD flagged rows and a TX parent-clause list) before implementation;
  every term in a multi-term clause resolves individually.
- **U2 — Scope stamped/enforced** where applicable via the core seam,
  live-path both directions.
- **U3 — Rules ship as registry modules**; zero shared-module edits.
- **U4 — Zero-miss sweep (director bar)**: QA sweeps ALL 53 jurisdictions
  for multi-term/parenthetical signals; every hit captured or proven
  not-a-definition.
- **U5 — Nothing regresses**: baseline states hold; existing tests green;
  P-R2 escalation on precision conflicts (parentheticals are FP-prone —
  expected escalation surface).
- **U6 — Measured before/after** full-corpus report for these signals.

## Coordination

Core sprint owns scope plumbing + registry; read its `## Seam spec` from
branch `claude/defs-core-scope`; merge after core. Boundary with markers
sprint: rows that are BOTH zero-yield and multi-term (VT case) — splitting
mechanics belong to markers, per-term fan-out belongs here; the two Planners
agree the boundary in writing before Developers start; disagreement
escalates. Registry registrations append-only. Out-of-family misses route
via program manager.

## Standing constraints

All program standing constraints apply (program doc): CodeGraph first;
red-before-green live-path tests; Planner owns tests; QA independent; no
test downloads the corpus; absolute zero-miss bar; P-R2.

## Manager rulings

Full text in `2026-08-04-defs-us-multiterm-log.md`. Summary:
- **M-R1** — CodeGraph queries run against the index in the main checkout
  (`codegraph explore` with cwd `/Users/nerya/LexGraph`, read-only) because
  worktrees carry no `.codegraph/`; all edits/tests/commits stay in the
  worktree.

## Next Steps

_Planner defines items._

## Dev Complete

_None._

## Completed

_None._

## Context Dump

Manager setup done 2026-08-04: worktree `/Users/nerya/LexGraph-wt/defs-us-multiterm`
on `claude/defs-us-multiterm` from `origin/main` 83532fe; own backend venv
built and verified importing worktree code. Core seam spec NOT yet published
(checked `origin/claude/defs-core-scope`) — panel plans + authors RED tests
meanwhile. Next: Planner (Sonnet/high) spawn — re-confirm F5/F6 examples live,
agree the VT boundary in writing with the markers Planner, author RED tests.
