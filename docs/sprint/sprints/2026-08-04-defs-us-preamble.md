---
id: "2026-08-04-defs-us-preamble"
status: planning
current_role: planner
branch: claude/defs-us-preamble
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

# Sprint: US family 2 — body preambles without the word "Definitions"

## Mandate

Capture definitions sections whose only signal is a body preamble that never
uses the word "Definitions": GA's `"As used in this chapter, the term:"`
(173/400 sampled instances missed; GA capture is 0), MD and NE (0% capture,
no heading signal at all — strictly worse than GA), MS (0%), SD (dominant
miss type: `"For the purposes of this chapter, the term, X, means…"` under
term-name headings), plus low-volume instances in OR/PA/RI/SC/TN/TX/UT/VT.
This is the family the prior sprint deliberately skipped to protect zero
false positives — P-R2 escalation is EXPECTED here: bring the director real
conflict examples rather than silently choosing recall or precision.

## Acceptance gates (program manager-defined)

- **U1 — Every preamble variant is captured**, with RED tests from real GA/
  MD/NE/MS/SD rows before implementation.
- **U2 — Scope is stamped correctly and enforced** for scoped preambles
  ("As used in this chapter…" → chapter scope), live-path both directions,
  built on the core seam.
- **U3 — Rules ship as registry modules** per the core seam spec; zero edits
  to shared modules.
- **U4 — Zero-miss sweep (director bar)**: QA sweeps ALL 53 jurisdictions
  for preamble signals; every hit captured or proven not-a-definition.
- **U5 — Nothing regresses**: baseline states hold; all existing tests
  green; false-positive risk is the KNOWN hazard of this family — any
  precision/recall trade escalates per P-R2 with examples.
- **U6 — Measured before/after** full-corpus capture-rate report (GA must
  move from 5/28,154; report the new number honestly).

## Coordination

Core sprint owns scope plumbing + registry; read its published `## Seam
spec` from branch `claude/defs-core-scope`; merge after core. Registry
registrations are append-only. Out-of-family misses are reported to the
program manager for routing. Overlap warning: preamble detection feeds the
scoped-inline family (a preamble is often also a scope trigger) — the
boundary is: THIS sprint owns recognizing a definitions-bearing BLOCK with
no heading signal; the scoped-inline sprint owns scope-trigger parsing
inside otherwise-ordinary sections. Ambiguous cases escalate to the program
manager rather than being claimed by both panels.

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

New sprint. Planner: read program doc + dossier (§2 family 2, §6 addendum
SD/OR/PA sections), re-confirm recon examples live, then author RED tests.
