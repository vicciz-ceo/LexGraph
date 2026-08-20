---
id: "2026-08-20-defs-boundary-idioms"
status: planning
current_role: planner
branch: claude/defs-boundary-idioms
locked_by: "claude-code:planner"
locked_at: "2026-08-20T21:50:00Z"
last_agent: "claude-code:manager"
last_updated: "2026-08-20T21:50:00Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python -m pytest backend/tests -q -p no:randomly && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
lint: "PASS 120 2026-08-20T21:52:25Z"
previous_sprint: "2026-08-12-defs-b1-refers-to"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
---

# Sprint: boundary-idiom widening — recover the 41 ceiling-tripped losses (issue #27)

## Mandate

GitHub issue #27. Forty-one (row, term) anchors produce no definition at all:
each is the LAST entry in its section with zero hard-stops found, because the
NEXT term's defining idiom (e.g. "shall include") is not in `_TIGHT_IDIOM_RE`
(`backend/app/definition_links/rules/us_markers_boundary.py:295` — currently
means | shall mean | has the meaning). With no boundary, capture runs to
end-of-text, exceeds `MAX_CLEAN_DEFINITION_LENGTH` (3,000 chars, line ~497),
and is correctly dropped by `close_entries` (~lines 640-693). The issue
owner's adjudication: all 41 are genuine runaway captures; the ceiling works;
the recovery path is idiom-vocabulary widening so a genuine closing boundary
is recognized. Raising the ceiling and scoping the guard are BOTH ruled out
(FX7 ruling, sprint 2026-08-10-green-the-suite: any guard-scoping broad
enough to recover the 41 flips the safety test RED — proven by QA).

Known examples: `USC_T5_C75_S7511` "furlough" (real def ~135 chars, captured
3,017), `STATE_NJ_T27_C1A_S1A-3.1` "Department" (real def one sentence,
captured 10,319). 2026-08-11 manager triage of all 66 affected rows:
41 ceiling-tripped / 25 present-but-shorter / 0 discriminator errors;
uncapped lengths min 3,017 / median 4,342 / max 11,730.

Director decisions taken: idiom list must be DERIVED from the 41 rows' actual
next-entry verbs (Planner enumerates the evidence; no guessed vocabulary).
Issue #26 stays deferred to its own sprint.

## Acceptance gates (manager-defined, director-approved 2026-08-20)

1. **Recovery with correct text.** The 41 ceiling-tripped anchors are
   captured with text bounded at the true end of each definition. Any
   unrecoverable one is individually adjudicated with a stated reason —
   never silently skipped.
2. **Certified by execution (P-R11).** One full all-53 run; 100%
   anchor-granularity adjudication of the ACTUAL delta; measurement runs
   under the corrected convention — `--current` on BOTH sides of
   `measure_actual_production.py` (see Known traps).
3. **No collateral damage.** No existing correct capture is split by an
   idiom occurring INSIDE a definition body; every ADDED anchor in the delta
   is adjudicated genuine; P-R15 deletion-side screen clean.
4. **The ceiling guard still works.** FX7 safety test
   (`backend/tests/integration/test_us_markers_fx7_ceiling_known_closed_scope.py`)
   stays GREEN — genuinely unbounded runaways are still dropped.
5. **No regression.** Full backend/frontend/lint green, explicitly including
   the boundary-engine guard estate: 16 c5guard class-B tests, the 5
   discriminator safety guards, the SC #28 run-membership test, the NV #25
   exclusion-bridge tests, and the module-docstring-pinned fixtures (AZ
   qualified actuary, UT Insolvent, VA sell, NV UCC, FED new drug).
6. **Red before green.** RED tests reproducing representative losses +
   novel structural controls (M-R107 — no jurisdiction/term/section keying;
   controls use unseen identifiers).
7. **Bounded.** `git diff -- backend/app/` touches only
   `us_markers_boundary.py`. No edits to `us_profile.py`,
   `_citation_or_xref_context`, or any B1 module.

## Rulings in force

P-R11, P-R12, P-R15, M-R107, D-RECALL-FP, D-MAP (see program doc and
handoff). FX7 prior ruling: ceiling-scoping not buildable as framed —
recovery goes through idiom vocabulary only.

## Known traps (do not rediscover)

- **Harness flags are part of the certificate**: `measure_actual_production.py`
  gates `recognized_by_registered_rule` on `--current`; production computes it
  unconditionally. Baseline runs MUST pass `--current` too, or the diff
  manufactures phantom deltas (proven in the #19 sprint — see
  `docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/investigation.md`;
  reusable corrected runner: that sprint's `run_gate2.sh`).
- "shall include" (and kin) commonly appear INSIDE definition bodies
  ("'X' means ... and 'Y' shall include ...") — this is exactly why the gate
  was kept tight. New idioms create new `starts` entries corpus-wide.
- `extract_quote_anchored_entries` returns (term, definition_text) tuples;
  a try/except-swallowing probe once manufactured a false "66/66
  discriminator errors" catastrophe — never swallow exceptions in probes.
- `qa_g7_common.INTEGRATION_SHA` re-pin + evidence regeneration whenever
  `backend/app` moves.
- Worktree venv: main checkout's venv with `PYTHONPATH=.:backend` from the
  worktree root; no `git stash`; raw-vs-ingest (escaped-\n) on raw parquet.

## Next Steps

_To be defined by the Planner._

## Dev Complete

_None._

## Completed

_None._

## Context Dump

Sprint opened 2026-08-20 by the manager off main tip `69fb425` (issue #19
sprint merged and closed; backend suite baseline now includes its 11 QA
regression tests). Planner to enumerate the 41 rows' actual next-entry
idioms, define item(s), and author RED tests per gate 6.
