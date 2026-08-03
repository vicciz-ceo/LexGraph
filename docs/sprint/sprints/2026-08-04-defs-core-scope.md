---
id: "2026-08-04-defs-core-scope"
status: planning
current_role: planner
branch: claude/defs-core-scope
worktree: /Users/nerya/LexGraph-wt/defs-core-scope
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

# Sprint: Core scope seam — scoped definitions + rule registry

**Program role: CRITICAL PATH.** Every other program sprint builds behind this
sprint's seam and merges after it. The Planner must publish the seam spec (a
`## Seam spec (published)` section in this contract, committed and pushed on
the sprint branch) as its FIRST deliverable so family panels can plan against
it before this sprint's code lands.

## Mandate

From the program (read `design_sections` first — do not re-derive recon):
make scope a first-class, profile-dispatched concept so that a definition
declared for a specific article/subsection/chapter creates USES_DEFINITION
assertions ONLY for mentions within that scope, in every jurisdiction; and
give per-jurisdiction convention rules a registry seam so family sprints ship
rules as NEW modules without editing shared files.

Recon facts to build on (dossier §1): enforcement already exists and works
(`matcher._in_scope`, matcher.py:104-110; `Definition.scope`,
definition.py:35); production of scoped rows is Hebrew-only
(`_CHAPTER_SCOPE_TRIGGERS` pipeline.py:62-68; `_LOCAL_TRIGGER_RE`/`_ADHOC_RE`
extract.py:28-33); US fallback extraction lives inline in pipeline.py
(:106-289), not in USProfile.

## Acceptance gates (program manager-defined)

- **C1 — Scope is enforced everywhere, at every granularity.** A definition
  scoped to an article, subsection, chapter/part/siman creates assertions
  only for mentions within that scope — proven live-path in BOTH directions
  (in-scope mention links; out-of-scope mention does not), for IL AND US test
  cases. Subsection granularity is new design work: mentions must be
  scope-checked below article level.
- **C2 — Scope triggers dispatch through the profile.** No Hebrew-only (or
  English-only) scope literals in shared pipeline/matcher/extract code;
  English triggers ("As used in this section/subsection/chapter", "For
  purposes of this section/part") produce correctly-scoped definitions.
- **C3 — Extraction lives behind the seam.** The inline-quote fallback,
  body-heading derivation, and preamble detection move from pipeline.py into
  profile-owned code; pipeline.py retains no jurisdiction-specific literals.
- **C4 — Rule registry.** A new convention rule ships as a new module plus a
  registration, with zero edits to shared modules; the seam interface is
  documented in this contract for the family sprints.
- **C5 — Nothing regresses.** All existing IL tests green unchanged (prior
  R2: editing one is a planning bug — escalate); US baseline states
  (IN/CO/KY/LA/DE/ID/NJ/MI/MT/ND/NY/OK) capture rates do not drop.

## Standing constraints

All program standing constraints apply (program doc §Standing constraints):
CodeGraph first for all code work; red-before-green with live-path RED tests;
Planner owns tests; QA independent; absolute zero-miss bar (director
decision 3); zero-miss vs false-positive conflicts escalate (P-R2), never
silently resolved.

## Next Steps

_Planner defines items._

## Dev Complete

_None._

## Completed

_None._

## Context Dump

New sprint. Planner starts here: read the program doc + recon dossier
(§1 code map has every file:line), then publish the seam spec before
authoring RED tests.
