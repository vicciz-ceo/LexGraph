---
id: "2026-08-04-defs-core-dispatch"
status: planned
current_role: planner
branch: claude/defs-core-dispatch
worktree: /Users/nerya/LexGraph-wt/defs-core-dispatch
locked_by: "claude-code:dispatch-manager"
locked_at: "2026-08-04T12:26:23Z"
last_agent: "claude-code:dispatch-manager"
last_updated: "2026-08-04T13:32:23Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 9
lint: "PASS 167 2026-08-04T13:32:23Z"
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
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

- [ ] **I1 — `HeadingRule` consumed by `is_definitions_heading`** (both
  profiles). Detection kind, first-positive-wins, tried after the profile's
  own baseline.
- [ ] **I2 — `BodyPreambleRule` consumed by `derive_heading_from_body`, and
  the `_is_placeholder_heading` GATE REMOVED.** Seam v2 §4/M6 — "registered
  `BodyPreambleRule`s are ALWAYS tried next if nothing was found yet" — is
  director-confirmed (**D-PREAMBLE-ALL**) and NOT implemented: manager
  verified `us_profile.py:517` early-returns `None` when the heading is not
  a placeholder, so registered rules can never run. Baseline (placeholder
  gate + body scan) still runs FIRST; the rules run when it yields nothing.
- [ ] **I3 — `EntrySplitterRule` + `TermClauseRule` consumed by
  `extract_definitions_from_section`.** Both are UNION kinds (M1 moved
  `EntrySplitterRule` off the first-wins side) — every matching rule's
  candidates are kept; rules never suppress each other (zero-miss).
- [ ] **I4 — `StructuralUnitRule` consumed as ARTICLE-METADATA enrichment**
  (**manager ruling M-D1**, seam v2.6 §1 — NOT a `UnitPath` producer, no
  relation to `resolve_unit_path`). Shape reverts to M11's
  `derive: (StructuralContext) -> tuple[ScopeUnit, ...]`; UNION; core keeps
  stamping `ScopeUnit("chapter", ...)` itself and rules ADD, never replace.
  Consumption point: where article structural metadata is populated, feeding
  **`matcher._in_scope`'s generic-kind branch** (`getattr(article,
  "structural_units", ())`) — dead today because nothing populates it.
  US parquet breadcrumb availability is RESOLVED (verified on a real file);
  do not re-escalate it.
- [ ] **I5 — new `ScopeKindRule` kind behind `determine_scope`** (**manager
  ruling M-D2**, seam v2.6 §2). `(jurisdiction_codes, detect: (str) -> str |
  None)`; `register_scope_kind_rule`; **baseline-first, then
  first-non-None-wins** in filename-sort order — NOT a union (a body has
  exactly one scope kind). Baseline still wins when it matches, so the 7
  working US states are untouched. Planner refused to coerce
  `ScopeTriggerRule` into a boolean detector — correctly; that would
  mis-scope definitions against the director's constraint.
- [ ] **I6 — D-DF enablement: additive optional `body_confirms` on
  `HeadingRule`.** `body_confirms: Callable[[str], bool] | None = None`,
  consumed as `matches(heading) and (body_confirms is None or
  body_confirms(body))`. The headings panel verified `body` is already in
  scope at the detection site (`pipeline.py:198/215`), so this is
  **seam-shape only, no new plumbing**. MUST stay backward-compatible with
  every already-written `HeadingRule`.
- [ ] **I8 — `ScopeKindRule` RED tests** (Planner round-trip after M-D2).
- [ ] **I7 — PER-KIND live-path dispatch tests, all SEVEN kinds.** The
  mandatory new test class. For each kind: register a probe rule, call the
  profile method `pipeline.py` actually calls, and assert **the answer
  CHANGES**. Includes the two already-live kinds — the point is a permanent
  guard, not a patch. This is the class whose absence let the gap survive two
  QA cycles.

- [ ] **I9 (NEW, scoped-inline panel finding) — `resolve_unit_path`
  mis-parses inline legislative-history annotations as sub-article markers.**
  Maine carries `(NEW)` / `(AMD)` / `(AFF)` editorial parentheticals inline
  and pervasively. **Manager reproduced on the live seam** — for a real-shaped
  ME body, offsets after an `(AMD)` annotation resolve to
  `(UnitStep('lower_alpha','b'), UnitStep(kind='sub', value='AMD'))`: a garbage
  step appended to the true path, degrading subsection-scope enforcement.
  Under zero-miss this is **wrong-path data, not missing data** — the same
  severity class as the M12 citation truncation.
  **Sequencing:** NOT folded into the in-flight Developer batch (its RED does
  not exist yet, and red-before-green is not negotiable). Planner authors the
  RED from REAL Maine rows first; a Developer fixes after the current batch
  merges. Fixture material: `claude/defs-us-scoped-inline` @ `4909afb`.
  **Also required:** determine whether other states carry similar editorial
  parentheticals, with a P-R7-compliant (signal-agnostic) denominator — a
  Maine-only fix would be a guess, not a finding.
  Fix shape is the Developer's choice against the RED (exclusion set vs
  uppercase-alpha-token guard), not specified here.

## Completed

_None._

## Context Dump

**Fresh sprint, planning.** Branch `claude/defs-core-dispatch` from main
`0f4e8fc`. Implementation only — behavior is already specified in
`2026-08-04-defs-core-scope-seam.md` (**v2.5 authoritative**).
**Root cause to internalize:** a one-kind live proof was generalized to seven;
the registry test stops at registration+lookup. I7 closes that permanently.
**Traps:** CodeGraph indexes `main`, not branches — Read/Grep branch-divergent
files. Never `git stash` (stack shared across worktrees). One writer per
worktree; each needs its OWN backend venv. No test may read the corpus.
