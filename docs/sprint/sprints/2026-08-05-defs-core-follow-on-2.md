---
id: "2026-08-05-defs-core-follow-on-2"
status: dev-complete
current_role: qa
branch: claude/defs-core-follow-on-2
worktree: /Users/nerya/LexGraph-wt/defs-core-follow-on-2
locked_by: "/root/core2_final_qa2"
locked_at: "2026-08-05T21:06:39Z"
last_agent: "/root/core2_final_qa2"
last_updated: "2026-08-05T21:06:39Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 2
previous_sprint: "2026-08-04-defs-core-dispatch"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
---

# Sprint: Core follow-on 2 — consolidated shared-module fixes

**Program role: the SHARED-MODULE OWNER.** Every family panel is fenced out
of shared modules (P-R1); this sprint is where their routed shared-module
defects get fixed. All six items below arrived with panel-measured evidence;
the Planner reads the program doc's "Core follow-on 2 candidates" entry
(sprint-roster table, `_program close_` row) as the authoritative worklist
and MUST NOT re-derive what panels already measured — verify, then build.

## Mandate

Fix the six accumulated shared-module defects, RED-first, with corpus
measurement per fix. Shared modules (`us_profile.py`, `pipeline.py`,
`matcher.py`, `registry.py`, unit-path resolver) are THIS sprint's exclusive
write-set. This sprint merges BEFORE the family panels' next merges — its
fixes unblock three panels' held state.

## Acceptance gates (program manager-defined)

- **G1 — MS padding strip.** `us_profile._leading_quote_candidate` strips
  padded quote contents consistently with the inline fallback. Padded terms
  (real MS rows, preamble evidence @ 92c2b1f on claude/defs-us-preamble)
  link their mentions. No existing capture regresses.
- **G2 — period-style markers.** `resolve_unit_path` recognizes
  period-style top-level markers (ME `2-A.`/`F.`, AZ `J.`, VA `A.`).
  Measured: the S-R16 empty-path degrade (full census 3,200/38,172 = 8.4%;
  ME 81.0%, AZ 69.7%, nine states ≥25% — scoped-inline pass-7 Planner data)
  drops to a measured, reported after-number. No regression on paren-style
  states (the 3-ladder selection stays intact).
- **G3 — FED unbounded-last-entry.** `_split_into_numbered_blocks`' last
  entry no longer runs to end-of-text. The markers panel's held RED
  (1 failed on claude/defs-us-markers) goes green on a merged tree; DC's
  27.3% zero-yield moves measurably; the preamble panel's 27,209
  fallback-affected rows become re-measurable (their `definition_text`
  boundary caveat).
- **G4 — citation pin-cite stack corruption.** `resolve_unit_path` no
  longer lets citation pin-cites reset/corrupt the marker stack. The three
  quote-verified cases fix: SC `Section 58-9-576(C)` (stack reset to [C],
  genuine `(c)(i)` skipped), TX `Section 37.007(a)(1)`, ME `(NEW)` revisor
  annotation (ladder misselection + path built from CFR/USC pin-cites).
  Also covers the Oregon S-R14-validation-row latch ("under subsection (1)
  of this section" — scoped-inline plan8 evidence). Post-QA newline scope
  is binding: only `Section`/lone-`§` + parenthesized candidates may use the
  measured cross-line exception; structural, full-USC, bare-code, and period
  forms stay unchanged. Tests must not import/pin the private context helper
  signature (`rg` stale-pin sweep: zero matches before Developer handoff).
- **G5 — RuleContext.unit_path.** No longer hardcoded `()`; rules receive
  the real unit path through the seam instead of importing
  `resolve_unit_path` directly. Existing rule modules keep working (their
  direct imports stay valid — this is additive plumbing, not a forced
  migration).
- **G6 — scope-VALUE seam.** A registrable path exists from a
  heading/body-derived scope VALUE (enumerated tuple or range) to the
  Definition — ScopeKindRule extension or a new seam kind, Planner's design
  call, documented in the seam doc as an append-only version. Headings
  panel's 8 non-expressible U2 rows (AK 9-chapter tuple, KY enumerations,
  TN dual-scope et al., plan5 item-14 evidence @ 8cd3829 on
  claude/defs-us-headings-plan5) become expressible; the headings panel
  builds the rules LATER on their side — this sprint delivers the seam plus
  one live-path proof.
- **G7 — nothing regresses.** Full suite green minus known cross-panel
  holds; the panels' certified numbers (markers' zero-yield table,
  preamble's 23,617, GA 2,794) re-reproduce on this branch after each fix
  that touches their code paths.

## Standing constraints

All program standing constraints (program doc): CodeGraph-first,
red-before-green with live-path REDs, Planner owns tests, QA independent,
D-CERT is the program close (these fixes shrink the certification's fix
loop), M18 denominator law, P-R10 probe sanity. Panel-held REDs that these
fixes target live on PANEL branches — the Planner vendors equivalent REDs
here rather than cherry-picking panel commits (authorship stays clean).
Merge-order: this sprint merges to main FIRST among pending program merges;
coordinate timing with the program manager.

## Next Steps

- Planner: verify the six candidates against the cited evidence, define
  items with RED tests, publish any seam change as an append-only seam-doc
  version, flag any candidate that should NOT be built (with evidence) back
  to the program manager instead of silently dropping it.

## Context Dump

Fresh sprint. Worktree needs creating (`git worktree add` off current main
@ 58162b2 or later) + its OWN backend venv (main venv imports main checkout
code). Git identity: verify `user.email` is the noreply address before
first commit. Never `git stash`; never `git add -A`. CodeGraph indexes main
only — fine here (this sprint works off main), but panel-branch evidence
needs Read/Grep on those branches.
