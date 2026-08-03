---
id: "2026-08-04-defs-us-scoped-inline"
status: planning
current_role: planner
branch: claude/defs-us-scoped-inline
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

# Sprint: US family 1 — scoped-inline definitions (no Definitions heading)

## Mandate

Capture the dominant US miss-class: definitions declared inside ordinary
substantive sections via `"As used in this section…"` / `"For purposes of
this section/subsection/chapter/part…"` — the English analog of the Hebrew
local-definitions path. 0% captured today in every state tested (dossier §2
family 1, §6 addendum). Lead states by measured frequency: OH 47%, UT 34.6%,
ME 39%, MO 33%, MT 27%, plus F1 presence in all 36 first-round states and
OR/TN/VT/RI/SC/PA/TX. These definitions are the canonical SCOPED case: the
scope unit named by the trigger (section/subsection/chapter/part) must be
stamped and enforced (assertions only within scope) via the core seam.

## Acceptance gates (program manager-defined)

- **U1 — Every convention variant in this family is captured**, with RED
  tests from real corpus rows of the lead states before implementation.
- **U2 — Scope is stamped correctly and enforced**: each captured definition
  carries the scope its trigger names; live-path proof both directions
  (in-scope mention links, out-of-scope does not) — built on the core seam.
- **U3 — Rules ship as registry modules** per the core seam spec; zero edits
  to shared modules.
- **U4 — Zero-miss sweep (director bar)**: QA sweeps ALL 53 jurisdictions
  for this family's signal patterns; every hit is captured or proven
  not-a-definition; any confirmed miss fails.
- **U5 — Nothing regresses**: baseline states (IN/CO/KY/LA/DE/ID/NJ/MI/MT/
  ND/NY/OK) capture rates hold; all existing tests green; zero-miss vs
  false-positive conflicts escalate per P-R2.
- **U6 — Measured before/after**: full-corpus capture-rate report for this
  family's signals (before vs after), same honesty standard as prior runs.

## Coordination

Core sprint `2026-08-04-defs-core-scope` owns scope plumbing + registry; read
its published `## Seam spec` from branch `claude/defs-core-scope` before
implementation; merge after core. Registry registrations are a
Planner-pre-declared append-only zone (program P-R5 merges). Misses found
outside this family's classes are REPORTED to the program manager for
routing, never fixed here. File-boundary conflicts escalate immediately.

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

New sprint. Planner: read program doc + dossier (§2 family 1, §6 addendum),
re-confirm recon examples against live code, then author RED tests.
