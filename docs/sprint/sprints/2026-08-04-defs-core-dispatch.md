---
id: "2026-08-04-defs-core-dispatch"
status: review
current_role: qa
branch: claude/defs-core-dispatch
worktree: /Users/nerya/LexGraph-wt/defs-core-dispatch
locked_by: null
locked_at: null
last_agent: "claude-code:dispatch-manager"
last_updated: "2026-08-04T17:05:00Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 11
lint: "PASS 154 2026-08-04T17:05:01Z"
completed_items: 11
dev_complete_items: 0
qa_cycles: 1
previous_sprint: "2026-08-04-defs-core-scope"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/sprints/2026-08-04-defs-core-scope-seam.md
---

# Sprint: Core dispatch completion — make all seven rule kinds live

**Program role: BLOCKING.** Four family panels are parked on this. Per
program ruling **P-R8** (main @ `0f4e8fc`), core owns the fix: option B
(panels editing `us_profile.py`) is REJECTED, and option C (mis-scoping via
`ScopeTriggerRule`) violates the director's scoped-definitions constraint.

**This is IMPLEMENTATION, not design.** Every behavior below is already
specified in the seam spec of the previous sprint
(`2026-08-04-defs-core-scope-seam.md`). Do not redesign; build what is
written. The spec is the contract.

## The defect

Two panels independently proved with positive controls that **5 of the 7
registry rule kinds are DEAD on the live path**. They register and look up
correctly, but nothing in `backend/app` ever CONSUMES them.

Manager re-verified independently before opening this sprint — non-registry
reference counts in `backend/app` at `0f4e8fc`:

```
HeadingRule 0 | BodyPreambleRule 0 | EntrySplitterRule 0
TermClauseRule 0 | StructuralUnitRule 0
ScopeTriggerRule 9 | CitationRule 5
```

`rules/registry.py` is honest about this (its own docstring: "This module
owns registration/lookup only"). The gap is the consumption side.

**Why it survived two QA cycles — read this before planning.** The previous
sprint's C4 gate was proven live with a `ScopeTriggerRule` — one of the two
kinds that ARE live — and that single-kind proof was generalized to all
seven. The registry's own test asserts registration and lookup, never that a
registered rule **changes a profile's answer**. That is the exact hole item
I7 exists to close permanently.

Evidence branches (read-only): `claude/defs-us-pr` @ `5b177b7`,
`claude/defs-us-headings` @ `341fb50` — contract + log carry the probe tables.
The two panel managers' positive-control probes are the Planner's blueprints.

## Acceptance gates

- **G1 — every kind is consumed.** Each of the seven kinds is reached from
  the profile method `pipeline.py` actually calls, per the seam spec's
  **"Consumption contract — baseline-first, registry-second, per kind"**
  (v1) and **v2 §4/M6**. Baseline behavior runs FIRST; registered rules are
  consulted second, with the per-kind order the spec states (first-wins for
  detection kinds, union for the rest).
- **G2 — a registered rule CHANGES the answer.** For every kind, on the live
  path, registering a probe rule provably alters what the profile returns.
  Registration + lookup is NOT sufficient evidence and never was.
- **G3 — both profile surfaces.** `USProfile` AND `HebrewProfile`, per the
  spec. A kind live in one and dead in the other is a FAIL.
- **G4 — nothing regresses.** Full evaluator green; all IL/Hebrew tests green
  UNCHANGED (prior R2: editing one to fit is a planning bug — escalate).
- **G5 — zero shared-file edits required of family panels.** A panel ships a
  rule as a new module plus a registration, and it takes effect. This is C4
  restated and actually proven this time.

## Next Steps

_None — all 11 items dev-complete and QA-verified (cycle 1). Merge to main is
the program manager's (P-R5)._

## Completed

- **I1** — `HeadingRule` consumed by `is_definitions_heading`, both profiles.
  Live-path dispatch proven; QA mutation-verified US+IL.
- **I2** — `BodyPreambleRule` consumed by `derive_heading_from_body`,
  placeholder gate removed (D-PREAMBLE-ALL). QA mutation-verified US+IL.
- **I3** — `EntrySplitterRule` + `TermClauseRule` consumed by
  `extract_definitions_from_section` as UNION kinds. QA mutation-verified
  US+IL.
- **I4** — `StructuralUnitRule` as article-metadata enrichment (M-D1);
  population site `pipeline.py:212-228`. QA replaced the stub test with a
  live-path probe.
- **I5** — New `ScopeKindRule` behind `determine_scope` (M-D2), baseline-first
  then first-non-None. QA mutation-verified US+IL.
- **I6** — Additive optional `body_confirms` on `HeadingRule` (D-DF).
  Backward-compatible with every existing rule; pinned green.
- **I7** — Per-kind live-path dispatch tests, all seven kinds x both profiles.
  QA re-proved each is falsifiable (7x2 grid, all RED->GREEN).
- **I8** — `ScopeKindRule` RED tests (Planner round-trip after M-D2). Green.
- **I9** — ME editorial annotations no longer parsed as markers:
  unclassifiable tokens SKIPPED, not pushed as `kind='sub'`. The unproven
  word-list guard was removed (P-E3) after mutation proved it dead weight.
- **I10** — Subsection scope LEVEL semantics (M-D3/seam v2.7): defensive paren
  normalization + additive `scope_unit_kind`, containment compares at the
  matching-kind step, outermost fallback, declared-kind-absent = not covered.
- **I11** — Resolver kind correctness: per-call ladder selection across THREE
  measured conventions - federal lower_alpha, digit-outermost (OR),
  upper_alpha-outermost (OH, 99.4% of 17,951 structured rows). Follow-on

## QA Notes

**Cycle 1 — PASS on every gate except C, which was a claim-accuracy failure,
not a functional one; corrected in code and re-verified.** Independent QA
(own worktree/venv) ran: 7x2 dispatch mutation grid (all 14 genuinely
load-bearing); live `StructuralUnitRule` probe replacing the stub test; IL
parity (zero IL tests touched + 4 new Hebrew probes on the new code paths);
32/32 containment cells on REAL OR/FED/OH rows plus 2 live `run_definition_
linking` scenarios. Evaluator: 770 backend / 165 frontend / tsc clean.

**Gate C FAIL and its resolution.** QA's full-census scan (all 53 parquet
files, 2,038,247 rows, signal-agnostic denominator) disproved the
"upper_roman-outermost has zero corpus presence" justification: 5 real rows
(0.00025%). Manager verified all 5 are in-sentence PROSE enumerations, not a
jurisdiction convention, and measured the effect as exactly ONE spurious
`upper_alpha` step, non-cascading. Fixed by correcting the code's honesty
note (AST-verified comment-only); kept as a named limitation.

**Findings carried forward, not blockers.** (a) Ladder selection reads only
the FIRST parenthesized token, so citation noise picks the ladder — measured
prevalence of rows whose first marker is noise: OH 6.51%, FED 1.60%, OR 0.20%
(of rows having any marker). Pre-existing, byte-identical before/after, but
amplified; program-level. (b) Two subsection-scoped definitions at DIFFERENT
levels tie at `scope_rank` 0 and both link — zero-miss-safe, but QA argues it
is distinct from M10's kind-ties because a principled narrowest answer exists
here. (c) Single-char roman siblings (`(iv)`→`(v)`) collapse the stack via the
outermost-first ancestor match — pre-existing, byte-identical before/after,
unmeasured. (d) `heading_breadcrumbs=()` remains a named limitation.

## Context Dump

**SPRINT COMPLETE — awaiting program-manager merge.** Branch `claude/defs-core-dispatch` @ HEAD, clean, pushed. Evaluator: backend 770 passed / 0 failed, frontend 25 files / 165 tests, `tsc --noEmit` clean. Production surface: `us_profile.py`, `matcher.py`, `extract.py` ONLY. Zero existing tests modified (all test changes are additions).
**All 7 rule kinds are live and mutation-proven on BOTH profiles** — P-R8's "proven for 2 of 7" is closed.
**Three ladder conventions now handled** (federal lower_alpha / digit-outermost / upper_alpha-outermost OH, the last measured at 99.4% of OH's structured rows). It is an ENUMERATED set of three, deliberately not a per-depth-learned mechanism — a 4th convention falls through to federal.
**Named limitations, all in QA Notes and in code docstrings:** ladder selection keys on the first parenthesized token (OH 6.51% noise-first); upper_roman-outermost yields one spurious step (5 corpus rows); single-char roman sibling collapse (pre-existing); subsection-level ties both link; `heading_breadcrumbs=()`.
**Traps:** CodeGraph indexes `main` — read branch-divergent files directly. Never `git stash` (shared stack). One writer per worktree, each its OWN venv. No test reads the corpus.