---
id: "2026-08-10-green-the-suite"
status: planned
current_role: developer
branch: claude/green-the-suite
locked_by: null
locked_at: null
last_agent: "claude-code:developer"
last_updated: "2026-08-10T20:35:09Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 3
lint: "PASS 230 2026-08-10T20:34:56Z"
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

_(empty — FX2/FX3 verification below found blockers; NOT moved here, see
Escalation.)_

## Completed

_(empty)_

## Evaluation Notes — FX2/FX3 resumed verification (Developer, escalated, not shipped)

HEAD verified at `58019fc` (the handoff commit; code diff unchanged, not
redone). Verification found two blockers the handoff could not have known
about — reporting the measurement per the brief's "escalate with the numbers
instead of shipping it" instruction. FX2/FX3 are **NOT** moved to Dev
Complete pending director triage.

**Gate tests**: FX3 (NV) gate is GREEN. FX2 (NM) gate is still RED —
`test_us_markers_ext_b_nm.py::test_real_pipeline_...end_to_end` fails on its
own boundary-quality guard (`'fine art' in by_term["artist"].definition_text`),
but the captured `artist` text is verified byte-correct against the real
`STATE_NM_C13_A4B_S13-4B-2` source (ends cleanly at "...as a whole;", entry B
never leaks in) — "fine art" is legitimately mentioned inside entry A's own
prose ("...the rights of an artist with respect to the work of fine art as a
whole"). The test's own substring guard has no way to distinguish that from a
real swallow. This looks like a test-authoring defect, not an extraction
defect — but no test file may be touched under this item's hard boundary.

**Regression (new)**: `test_us_markers_g3_heal_priority_seam.py::
test_priority_opt_in_is_additive_default_false_and_registration_is_exactly_wa_only`
— previously GREEN, now RED. It pins the exact 11-code
`_OTHER_INLINE_QUOTE_CODES` tuple via `mi_rules[0].jurisdiction_codes ==
_OTHER_INLINE_QUOTE_CODES`; FX2/FX3's registration extends the live tuple to
13 codes (+US-NM, +US-NV), breaking the exact-equality pin. Full suite:
**3 failed** (FX1 unchanged + FX2 NM gate + this new regression), **979
passed**, **20 xfailed, 0 xpass** — same headline count as the sprint's
pre-FX2/FX3 baseline (`3 failed / 979 passed`), but the *set* of failures is
different: NV's fix is real, but it was masked by a new regression at the
same total.

**Blast radius** (real `USProfile.extract_definitions_from_section` /
`is_definitions_heading` / `determine_scope` called directly on post-ingest
body text — `\n`-unescaped `row["text"]` — across the full pinned corpus,
no DB; "before" simulated by suppressing only the NM/NV entries from
`registry.entry_splitter_rules_for` in-process):
- **NM** (`us_nm_statutes.parquet`, 34,455 rows, 1,625 Definitions-headed):
  before 47 rows/341 defs → after 1,556 rows/12,979 defs. **+1,509 rows,
  +12,638 definitions.** Matches the FX2 fixture docstring's own prior
  measurement exactly (1,509 rescued, 69 residual zero-candidate = 1,578).
- **NV** (`us_nv_statutes.parquet`, 48,190 rows, 1,262 Definitions-headed):
  before 0/0 → after 337 rows/1,580 defs. **+337 rows, +1,580 definitions.**
  Matches the FX3 fixture docstring's own prior measurement exactly.

**Spot-check** (22 individual definitions inspected against real source
text): **15 real / 7 artifact**, all 7 artifacts in 2 NV rows —
`STATE_NV_T8_C104_S104.1201` (NV's UCC Article 1 general definitions) and
`STATE_NV_T8_C104_S104.9102` (UCC Article 9). Root cause: NV's UCC drafting
convention `"Term," except as used in "excluded-phrase," means ...` /
`"Term," as distinguished from "other-term," means ...` double-quotes the
excluded phrase; the shared engine's tight-idiom gate has no guard against
this shape (unlike the existing `_preceded_by_references_to` guard for the
PA "References to X" shape), so it captures the LAST quoted phrase before
"means" as its own spurious entry carrying the PRECEDING term's real
definition text, verbatim. Confirmed real terms **lost** under their correct
name in these 2 rows: `Agreement`, `Contract`, `Party` (1201) and `Account`,
`Accounting`, `Assignee`, `Record` (9102) — each replaced by a wrongly-named
duplicate (`"contract ,"`, `"agreement ,"`, `"third party ,"`,
`"statement of account"`, `"accounting for ,"`,
`"assignee for benefit of creditors,"`, `"record owner,"`). NM shows the
same English phrases ("except as used in", "as distinguished from") in 5
newly-producing rows but never double-quotes the excluded phrase there —
0 confirmed artifacts in NM. Rate: 7/1,580 (0.44%) of NV's new definitions,
0/12,638 of NM's. Both jurisdictions' clean samples (15 checked, spanning
1-77-candidate rows) matched source text verbatim.

**Escalation** (see conversation for full detail; summary): both the new
regression and the confirmed artifacts are real, evidenced findings, not
noise — reported per this item's "STOP and escalate ... instead of shipping
it" instruction rather than judged shippable unilaterally.

## Context Dump

New sprint, opened by the program manager off `main` @ `be4370b`. Sibling sprint
`2026-08-10-core-g4-discriminator-perf` runs concurrently on
`claude/core-g4-discriminator-perf`, also off main; it touches only
`us_profile.py`'s citation discriminator and must not collide with this sprint's
markers-panel surface. D-GREEN sequences this sprint AHEAD of that one for merge
order. Program rulings live in the program log on `claude/defs-us-preamble`.
