---
id: "2026-08-10-green-the-suite"
status: planned
current_role: developer
branch: claude/green-the-suite
locked_by: null
locked_at: null
last_agent: "claude-code:planner"
last_updated: "2026-08-10T19:40:19Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 3
lint: "PASS 157 2026-08-10T19:40:29Z"
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-08-04-defs-us-preamble"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
---

# Sprint: green the suite — restore `main` to a trustworthy gate

## Mandate

**CI has been red on `main` since at least 2026-08-05.** The last five runs on
`main` are `failure` or `cancelled`. Locally `main` @ `be4370b` runs
**23 failed / 979 passed**. PR #20 carries three failing checks
(`backend (py3.12)`, `backend (py3.13)`, `sprint contract lint`).

The 23 are RED defect-marker tests the markers panel committed and merged to
`main` at `7208dcf`. Marking a known defect with a red test is reasonable on a
panel branch; merging it to `main` turned the suite from a gate into a
noticeboard. Every panel since has worked against a baseline it could not
distinguish its own regressions from, which is a direct contributor to P-R17 and
P-R18 both costing real time.

Director standard **D-GREEN** (binding, program-wide): the test suite must
represent the intended final state of the repo, and CI must be green. No branch
merges to `main` while its CI is red.

## The triage rule — D-GREEN-TRIAGE (director, 2026-08-10)

Classify **each** of the 23 individually, citing evidence:

- **FIX** — the defect LOSES a definition or a term. D-RECALL-FP: a miss is the
  expensive defect. These get genuinely repaired.
- **XFAIL** — the defect only degrades CAPTURE QUALITY: a truncated citation
  tail, a stub where fuller text existed, a boundary overrun. D-MAP already
  classes byte-quality as informational. These get
  `pytest.mark.xfail(strict=True)` plus a tracked GitHub issue.

"Looks minor" is not a verdict. The question is whether an anchor `(row, term)`
is lost or merely captured imperfectly. Determine it by running the row, not by
reading the test name.

**Forbidden — this is the obvious cheat and it will be diff-checked:** deleting
tests, weakening assertions, broad `skip`, or non-strict `xfail`. `strict=True`
is required so the suite fails loudly if a defect is ever silently fixed.

## Acceptance gates (manager-defined)

1. **`main`'s CI goes green** — backend on py3.12 and py3.13, frontend
   typecheck + vitest, and `sprint contract lint`.
2. **Every one of the 23 is accounted for** with a written verdict (FIX or
   XFAIL) citing whether an anchor is lost, and an issue link for each XFAIL.
3. **No defect is hidden.** Each XFAIL is strict and traceable to an issue; a
   reader of the suite can enumerate every known defect.
4. **No regression.** Nothing that passes today may start failing.
5. **The contract lint passes** — the sprint contract is inside its size budget.

## Known scope

The 23 failures on `main`, by file (run
`PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python -m pytest backend/tests -q --tb=no -p no:randomly`
from the worktree root to reproduce):

- `test_us_markers_c5guard_class_b_boundary_defects.py` — 16 (ND/NJ/OK: citation
  tails truncated, lists cut mid-enumeration, next-entry marker chains leaking)
- `test_us_markers_ext_a_ok_gapidiom.py` — 1
- `test_us_markers_ext_b_nm.py` — 1
- `test_us_markers_ext_b_nv.py` — 2
- `test_us_markers_core3_fed_structural_sibling_live.py` — 1
- `test_us_markers_qa_q2_short_definitions.py` — 1
- `test_us_markers_qa_q3_tx_2009_003.py` — 1

Names suggest the c5guard cluster is largely capture-quality (XFAIL) and the
ext_a/ext_b "recovers ... definitions end_to_end" tests are anchor-losing (FIX),
but **that is a hypothesis, not the triage** — verify each by running the row.

## Next Steps

### FX1 — OK gap-idiom: bridge the interposed clause between quoted term and "shall mean" (US-OK)

`extract_quote_anchored_entries`'s tight-idiom gate (`us_markers_boundary.py`)
requires "means"/"shall mean" essentially immediately after a term's closing
quote, so it does not bridge OK's real `The term "person" as used in this
act shall mean ...` idiom (a clause interposed between subject and verb).
Verified live: today's real pipeline creates 0 `Definition` rows for
`STATE_OK_T47_S47-157.5` (anchor `person` entirely absent). Fix: a narrow,
scoped rule for this shape (same pattern as `us_markers_tn_idiom.py`'s TN
gap-bridge), not a corpus-wide loosening of the shared tight gate (false
positive risk, U-R1).
Gate: `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_ext_a_ok_gapidiom.py::test_real_pipeline_recovers_ok_gap_idiom_definition -q`

### FX2 — Register US-NM in `us_markers_inline_quote.py`'s `_JURISDICTIONS`

NM's dominant convention (lettered `A. "term" means ...` runs) is already
correctly parsed by the shipped `extract_quote_anchored_entries` engine when
simulated — NM is simply absent from the tuple wiring it into the live
pipeline. Verified live: today's real pipeline creates 0 `Definition` rows
for `STATE_NM_C13_A4B_S13-4B-2` (all 5 real terms absent). Registration-only
fix; re-verify against the fully-clean bucket before widening further (the
mixed means/includes bucket is out of scope here).
Gate: `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_ext_b_nm.py::test_real_pipeline_recovers_all_five_nm_lettered_definitions_end_to_end -q`

### FX3 — Register US-NV in `us_markers_inline_quote.py`'s `_JURISDICTIONS`

NV's dominant convention (bare digit-dot markers, curly-quoted terms with
internal padding spaces) is already correctly parsed by the shipped engine
when simulated — NV is absent from the same tuple as FX2. Verified live:
today's real pipeline creates 0 `Definition` rows for
`STATE_NV_T34_C396_S396.005` (all 5 real terms absent). Registration-only
fix. (NV's separate cross-reference classifier gap is tracked as XFAIL issue
#24, not part of this item.)
Gate: `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_ext_b_nv.py::test_real_pipeline_recovers_all_five_nv_higher_education_definitions_end_to_end -q`

## Stale-pin sweep

Roots checked: `backend/tests/unit/`, `backend/tests/integration/`,
`backend/tests/e2e/`, `frontend/src/components/__tests__/*.test.tsx`. This
sprint changes no production code and no assertions — only adds
`xfail(strict=True)` to 20 already-RED tests, leaving 3 RED as FIX gates —
so there is no behavior change that could strand a pin. `grep -rlE` for the
23 tests' own node ids and fixed row/term names hits only the tests' own
files plus the sibling GREEN c5guard regression-guard files, which already
document (in their own header comments) that these exact terms' defective
captures are pinned separately, RED, elsewhere — already correctly
cross-referenced, not stale. Result: **none**. Full detail: sprint log.

## Dev Complete

_(empty)_

## Completed

_(empty)_

## Context Dump

New sprint, opened by the program manager off `main` @ `be4370b`. Sibling sprint
`2026-08-10-core-g4-discriminator-perf` runs concurrently on
`claude/core-g4-discriminator-perf`, also off main; it touches only
`us_profile.py`'s citation discriminator and must not collide with this sprint's
markers-panel surface. D-GREEN sequences this sprint AHEAD of that one for merge
order. Program rulings live in the program log on `claude/defs-us-preamble`.
