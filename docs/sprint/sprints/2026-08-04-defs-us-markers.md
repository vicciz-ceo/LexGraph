---
id: "2026-08-04-defs-us-markers"
status: planning
current_role: planner
branch: claude/defs-us-markers
worktree: /Users/nerya/LexGraph-wt/defs-us-markers
locked_by: "claude-code:planner"
locked_at: "2026-08-04T01:00:00Z"
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

# Sprint: US family 3 — entry-marker mismatch (highest corpus impact)

## Mandate

The heading IS recognized as a Definitions section, but the extractor's
expected entry shape rejects the real body and yields zero. Sub-cases, all
confirmed live (dossier §2 family 3 + §6 addendum):
- **No-marker inline-quote** — `"As used in this chapter… \"Term\" means…"`
  with no `(N)` before the quote. Dominates VA (97% of 1,117 Definitions
  sections yield 0), WA (98% of 2,007), FED (84% of 1,949 — largest raw
  miss in the corpus), WV/DC minority. The EXISTING
  `_extract_inline_quoted_definitions` fallback rescues 77-93% of these but
  is wired to fire only on body-derived headings (dossier §6 finding #1).
- **Bare `(N)` numeric markers** (SC), **bare digit-dot** (AZ), **unquoted
  ALL-CAPS terms** (AL), **mojibake curly quotes** `\x80\x9c/\x9d` (AK, RI —
  RI's leading cause at 15%), **nested lettered sub-clauses under numbered
  entries** (UT, 24.2%), **colon-then-list** (TN), **ALL-CAPS singular
  "DEFINITION." + single inline entry** (TX), **prose bodies under matched
  headings** (OR), **unquoted-term definitions** (DC: `A bond… means…`).
Also owns the prior sprint's recorded residual: entry-boundary bloat/
truncation (Open-space purposes 21,174 chars; TX 17.33% degenerate recovered
terms) — "captured" means captured CLEANLY (right term, right boundary).

## Acceptance gates (program manager-defined)

- **U1 — Every sub-case above is captured cleanly**, RED tests from the
  exact recon rows (incl. `STATE_VA_T23.1_SI_C3_S23.1-300`,
  `STATE_CA_..._S54221`'s residual) before implementation. Entry boundaries
  are precise: no swallowed neighbors, no sentence-fragment terms, no
  degenerate near-empty definitions.
- **U2 — Scope stamped/enforced** where bodies carry scope preambles, via
  the core seam, live-path both directions.
- **U3 — Rules ship as registry modules**; zero shared-module edits; the
  fallback-rewiring decision is designed WITH the core panel (it currently
  lives in pipeline.py, which core is moving behind the seam).
- **U4 — Zero-miss sweep (director bar)** across all 53 jurisdictions for
  detected-heading-zero-candidate sections: each is captured or proven
  correctly-empty (pure cross-reference sections are correctly empty —
  document the classifier).
- **U5 — Nothing regresses**: baseline states hold; existing tests green;
  P-R2 escalation on precision conflicts.
- **U6 — Measured before/after**: per-jurisdiction zero-candidate rates for
  Definitions-headed sections (VA 97%→?, WA 98%→?, FED 84%→?) reported
  honestly on the full corpus.

## Coordination

Core sprint owns scope plumbing + registry + the pipeline.py extraction
migration — THIS sprint's fallback-rewiring overlaps core's C3 gate: the two
Planners must agree the boundary in writing (both contracts) before either
Developer touches it; disagreement escalates. Read core's `## Seam spec`
from branch `claude/defs-core-scope`; merge after core. Registry
registrations append-only. Out-of-family misses route via program manager.

## Standing constraints

All program standing constraints apply (program doc): CodeGraph first;
red-before-green live-path tests; Planner owns tests; QA independent; no
test downloads the corpus; absolute zero-miss bar; P-R2.

## Manager rulings

Full text in `2026-08-04-defs-us-markers-log.md` §M1. Summary:
- **U-R1** — "captured" = captured CLEANLY (right term, right boundary);
  boundary quality is a measurable RED assertion, not prose.
- **U-R2** — the `_extract_inline_quoted_definitions` rewiring is a JOINT
  decision with the core panel; no Developer touches it before both Planners
  record the boundary in writing in both contracts.
- **U-R3** — the correctly-empty classifier is a Planner deliverable and is
  independently verified by QA.
- **U-R4** — P-R2 escalation per conflict class, with real statute rows.

## Boundary with core sprint (`2026-08-04-defs-core-scope`)

_Status: NOT YET AGREED. Core's `## Seam spec (published)` was absent as of
`origin/claude/defs-core-scope` @ `5b93ef8`. This section is filled in by the
Planner once both Planners agree; no work on shared modules until then._

## Next Steps

_Planner defines items._

## Dev Complete

_None._

## Completed

_None._

## Context Dump

New sprint. Planner: read program doc + dossier §2 family 3 + §6 addendum
(findings #1, per-jurisdiction detail), re-confirm examples live, author RED
tests. Largest-impact sprint in the program — plan waves accordingly.
