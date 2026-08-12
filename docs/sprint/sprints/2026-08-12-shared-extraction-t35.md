---
id: "2026-08-12-shared-extraction-t35"
status: planning
current_role: planner
branch: claude/shared-extraction-t35
locked_by: "claude-code:planner"
locked_at: "2026-08-12T03:00:00Z"
last_agent: "claude-code:program-manager"
last_updated: "2026-08-12T03:00:00Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python -m pytest backend/tests -q -p no:randomly && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-08-10-green-the-suite"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
---

# Sprint: shared extraction — stop capturing section-label headings as terms

## Mandate

This is the **last failing test on PR #20**. Everything else is green: backend
1338 passed / 1 failed, frontend passing, contract lint passing across every
contract.

`USC_T35_C4_S41` persists a definition whose term is the section label
**`"SEC. 804. DEFINITION."`**, scope law-wide, carrying an **8,431-character**
bleed. The row's real content — a `Director means ...` clause — is not captured
at all.

So this row is wrong in both directions at once:

- **a phantom**: a heading is captured as a definiendum (D-MAP's blocking class —
  the anchor points at something that is not a defined term)
- **a miss**: the genuine definition is absent (D-RECALL-FP's expensive class)

Gate:
`backend/tests/integration/test_us_body_preamble_defining_verb_narrowing_red.py::test_usc_t35_c4_s41_wrong_tuple_needs_shared_extraction_p_fp_debt`

## Why it was deferred, and why that no longer applies

The test's own docstring calls it *"held shared-extraction/P-FP debt, not a
Developer gate in this bounded B1 sprint,"* and program ruling **P-R14** put this
class out of scope for the panel that found it. Both were correct at the time:
the B1 sprint could not edit shared extraction.

The director has now directed that it be fixed, in its own sprint, with its own
measurement. That is this sprint.

## The hazard on the record — read before proposing anything

A previous attempt at this class was **rejected under M-R64** for narrowing the
capture window in a way that dropped other genuine definitions. This file carries
10 passing guards that exist because of it.

The failure mode to avoid is precise: a fix that suppresses the phantom by
tightening what counts as a definiendum, and in doing so silently stops capturing
real definitions elsewhere in the corpus. That trade is not acceptable — it swaps
a visible defect for an invisible one, which is the pattern this program has been
correcting all week.

## Acceptance gates (manager-defined)

1. **The phantom is gone.** `USC_T35_C4_S41` no longer persists a section-label
   heading as a term.
2. **The real definition is captured.** The row's genuine `Director means ...`
   clause becomes an anchor. Gate 1 alone is satisfiable by suppression; this
   gate is what distinguishes a fix from a mute.
3. **Nothing else is lost.** Corpus-wide, measured: no term that is captured
   today may disappear. This is the M-R64 gate and it is the one that matters.
4. **No regression.** Backend stays at 1338 passed with this test flipping to
   green — 1339 passed / 0 failed. Frontend and contract lint stay green.
5. **Bounded.** Shared extraction only. Do not touch the citation-window perf
   fix, the #21 discriminator, or the compound-idiom guard — all three are
   QA-certified this week.

## Related, and worth checking for a common cause

Three open issues plausibly share this seam. If one change closes more than one,
that is a better outcome than four patches — but it must be shown, not assumed:

- **#19** — `refers to` missing from the defining-verb vocabulary, drops a
  definition
- **#26** — `classify_correctly_empty` has no production call-site
- **#27** — 41 definitions run to end-of-text because no boundary idiom
  (`shall include`) is recognised, then die on the length ceiling

## Next Steps

_(Planner fills this in.)_

## Dev Complete

_(empty)_

## Completed

_(empty)_

## Context Dump

New sprint, opened by the program manager off PR #20's head `fe0ef30`. Nothing
implemented. The gate test is already RED and committed — red-before-green is
satisfied for free. Prior sprints this week: `2026-08-10-green-the-suite`
(23 failures to 1) and `2026-08-10-core-g4-discriminator-perf` (both merged into
PR #20). Program rulings live in the program log on `claude/defs-us-preamble`.
