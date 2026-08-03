---
id: "2026-08-04-defs-us-headings"
status: planning
current_role: planner
branch: claude/defs-us-headings
locked_by: null
locked_at: null
last_agent: "claude-code:program-manager"
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

# Sprint: US family 4 — heading variants the matcher never sees

## Mandate

Definitions sections whose HEADINGS defeat the first/last-word "Definitions"
rule (dossier §2 family 4 + §6 addendum):
- **Compound/mid-token headings**: `"Reciprocity — definitions — procedure —
  fees."` (MO, 20/300), `"Definition of Terms."` (NH), dash/semicolon-joined
  compounds (TN/SC/SD/PA/UT), `"APPLICABILITY OF DEFINITIONS."` (TX), NV/NY/
  MI variants. Includes the prior sprint's recorded WA 10.3% / FL 5.5% /
  NY 4.4% heading-miss rates.
- **NEW verb-form family**: `"X" defined` / `Employee defined` / `Words and
  phrases defined` — no "Definitions" token at all. VA 57, WA 279, WV 204,
  WI 16, WY 45, DC 38, FED 163 sampled instances — 0% captured everywhere.
The false-positive hazard is real (a heading MENTIONING definitions is not
always a definitions section — TX's "APPLICABILITY OF DEFINITIONS" needs
judgment): P-R2 escalation with examples when recall and precision collide.

## Acceptance gates (program manager-defined)

- **U1 — Every heading variant above is captured**, RED tests from real rows
  of the named states before implementation.
- **U2 — Scope stamped/enforced** where the heading or body names a scope
  unit, via the core seam, live-path both directions.
- **U3 — Rules ship as registry modules**; zero shared-module edits.
- **U4 — Zero-miss sweep (director bar)**: QA sweeps ALL 53 jurisdictions
  for def-signal headings (incl. `defin*` substrings and verb-form shapes);
  every hit captured or proven not-a-definitions-section.
- **U5 — Nothing regresses**: zero false positives held by the current
  matcher across 10 states must not break; baseline states hold; P-R2
  escalation on conflicts.
- **U6 — Measured before/after**: heading-recognition rates per
  jurisdiction (WA/FL/NY prior-known misses must move) on the full corpus.

## Coordination

Core sprint owns scope plumbing + registry; read its `## Seam spec` from
branch `claude/defs-core-scope`; merge after core. Note the interaction with the markers sprint: a newly
RECOGNIZED heading only helps if the extractor can parse the body — bodies
that then yield zero belong to the markers family; route them via the
program manager, do not fix extraction here. Registry registrations
append-only. Out-of-family misses route via program manager.

## Standing constraints

All program standing constraints apply (program doc): CodeGraph first;
red-before-green live-path tests; Planner owns tests; QA independent; no
test downloads the corpus; absolute zero-miss bar; P-R2.

## Next Steps

_Planner defines items._

## Dev Complete

_None._

## Completed

_None._

## Context Dump

New sprint. Planner: read program doc + dossier §2 family 4 + §6 addendum
(finding #2 verb-form table), re-confirm examples live, author RED tests.
