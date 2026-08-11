---
id: "2026-08-10-green-the-suite"
status: qa-fail
current_role: developer
branch: claude/green-the-suite
locked_by: null
locked_at: null
last_agent: "claude-code:qa"
last_updated: "2026-08-11T23:31:13Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 8
lint: "PASS 263 2026-08-11T23:31:38Z"
completed_items: 5
dev_complete_items: 0
qa_cycles: 1
previous_sprint: "2026-08-04-defs-us-preamble"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
---

# Sprint: green the suite — restore `main` to a trustworthy gate

## Mandate

Director standard **D-GREEN** (binding, program-wide): the test suite must
represent the intended final state of the repo, and CI must be green. First
pass classified 23 real defects (3 FIX, shipped as FX1/FX2/FX3; 20 XFAIL,
tracked as issues #21-#24). **Second pass, director standard D-GREEN2**: the
20 XFAILs are scaffolding, not the destination — every open defect issue gets
resolved, not just marked.

## The triage rule — D-GREEN-TRIAGE (director, 2026-08-10)

- **FIX** — the defect LOSES a definition or a term (D-RECALL-FP: a miss is
  the expensive defect).
- **XFAIL** — the defect only degrades CAPTURE QUALITY (truncated tail,
  stub, boundary overrun). `pytest.mark.xfail(strict=True)` + tracked issue.

## Second pass — status and what this Planner did

FX2 (NM) and FX3 (NV) are now DONE: registration landed at `58019fc`, the
Developer's escalation (stale `g3_heal_priority_seam` pin + NM test-authoring
defect) was resolved by the director/manager at `523c22f` (HEAD before this
pass). Both gates re-verified GREEN by this Planner. Full detail: log
`## Archived: FX2/FX3 resumed verification`. FX1 remains open/unimplemented.

That same FX2/FX3 spot-check surfaced a NEW defect — NV UCC's
`"Term," except as used in "excluded," means ...` idiom loses the real term
under its correct name (7/1,580 new NV defs, 0/12,638 NM). Filed as **issue
#25, FIX-class** (anchor loss, not capture-quality) — no test existed for it
before this pass; this Planner authored one (M-R107: derived from the row's
own structure, not a hardcoded term list — see the test file's docstring).

This Planner removed the `xfail(strict=True)` marker from all 20 tests
tracked at issues #21-#24 (16 + 1 + 2 + 1), restoring them to RED. The tests
themselves are untouched beyond the decorator (plus one now-unused
`_C5GUARD_XFAIL` object left defined, and `import pytest` left in place,
in each file — minimal diff, no logic changed). See `## Parallelization
plan` for file ownership and sequencing before any Developer is spawned.

## Acceptance gates (manager-defined)

1. `main`'s CI goes green (backend py3.12/py3.13, frontend typecheck+vitest,
   contract lint).
2. Every one of the 7 items below (FX1 + #21-#25 + FX7) is either genuinely
   fixed (test goes GREEN) or the director explicitly re-classifies it — no
   re-marking as xfail without a fresh, argued reason.
3. No regression: nothing passing today may start failing.
4. Contract lint passes.

## Next Steps

### #28 (QA-FAIL, found this cycle) — #21's digit-paren run-membership heuristic swallows a sibling entry when a run's item 1 opens `The term "X" shall mean` instead of a bare quote

Discovered during this QA cycle's mandated spot-check of 20 rows the #21
discriminator lengthened (the brief's own "discriminator's main risk" —
over-capture — the one nobody had hand-checked). 19/20 spot-checked rows
were genuine recoveries (mostly citation-tail digits, one full internal-
enumeration recovery). This ONE is a confirmed, real over-capture,
byte-verified against the real corpus row `STATE_SC_T31_C3_A1_S31-3-20`
(`us_sc_statutes.parquet`).

**Root cause**: `us_markers_boundary._digit_paren_run_internal_content_starts`
derives a whole consecutive digit-paren run's sibling-vs-internal status
from what item 1 of the run opens with — a bare quote or an ALL-CAPS label.
This row's run opens `(1) The term "director" shall mean the Secretary of
Commerce; (2) "Authority" ...; ... (15) "Persons of low income" means ...;
and (16) "Obligee of the authority" or "obligee" shall include ...; (17)
"Persons of moderate to low income" means ...`. Item 1's `The term "` prefix
is neither a bare leading quote nor an ALL-CAPS label, so the WHOLE run
(2)-(17)+ loses its digit-marker hard-stop protection. Item (16)'s own
idiom ("shall include") is not one `_TIGHT_IDIOM_RE` recognizes either, so
it never becomes its own bounding `starts` entry — with both boundaries
gone, `"Persons of low income"` (item 15) runs straight through the whole
of (16) and only stops at (17)'s own quote. **Confirmed regression, not a
pre-existing gap**: `"Obligee of the authority"` was never captured as its
own term before or after (its idiom is simply unrecognized — a separate,
pre-existing issue), but `"Persons of low income"` captured CLEANLY (ending
`'...\"beneficiary class\"; and'`, no swallow) both at `origin/main` and at
the pre-#21 commit `1dece6f` — #21's run-membership fix broke a row that
worked before it landed.

Verified genuine via an independent 20-row spot-check methodology (real
`ingest_us_statute_rows` -> `run_definition_linking` pipeline, OLD-vs-NEW
`us_markers_boundary.py` diffed across ~2,750 sampled Definitions-headed
rows spanning all 13 registered jurisdictions + WA; see QA report for the
full method). Not filed as xfail: `"Persons of low income"`'s own
`definition_text` now contains another term's entire unrelated definition —
a content-quality defect in the SAME family #21 itself targets, not a new
bug class, so it belongs in #21's own fix scope, not a separate xfail
ledger entry.

Committed RED test (2 tests, one provenance sanity + the real-pipeline RED):
Gate: `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_qa_sc_digit_run_membership_swallow.py -q`

### #21 residual — NJ `"facility"` (1 of 16) still resists; TX qa_q3 fix-attempt withdrawal confirmed correct

The c5guard class-B gate is 15/16 GREEN (QA-reverified). The one resisting
test, `test_nj_facility_missing_means_prefix_and_truncated_citation_tail`,
fails on an axis #21's fixes never touch: `"facility"` is the LAST of an
`"X" or "Y" means ...` shared-clause pair (module's own documented rule:
only the last quote is recognized), and per the engine's UNIFORM idiom-
consumption convention (`idiom_m.end()` becomes the definition start —
confirmed identical for EVERY other entry in this same fixture: Department,
Commissioner, Cost, etc. all have their own "means"/"shall mean" stripped
too), the captured text correctly starts right after "means " is consumed.
#21's three mechanisms (marker-chain walking, digit-paren sentence-boundary
check, run-membership) are all about where a captured span ENDS; this
defect is about where a span STARTS — an orthogonal axis, never in #21's
scope. QA independently re-verified live that the test's OWN second claim
(truncated citation tail) is already resolved at HEAD — `entries["facility"]`
now correctly ends `'...s. 3.'` — the test's docstring is stale on that
point (cosmetic, not a new failure); only the means-prefix half remains
open.

Separately, `test_us_markers_qa_q3_tx_2009_003.py`'s TX half of #23 (the
"orphaned digit-marked redirect clause folds into lettered quote-anchored
children" shape) was attempted and withdrawn as corrupting real MI
definitions. QA independently reconstructed the withdrawal's own claim (not
assumed): the real MI fixture row (`STATE_MI_C206_AAct-281-of-1967_S206.278`)
has the IDENTICAL marker shape TX needs fixed — `(8) As used in this
section:` followed by lettered quote-anchored children `(a) "Board" means
...`, `(b) "Michigan strategic fund" means ...`, etc., each already
carrying real, correct, substantial content. Reconstructing the most
natural "fold forward" mechanism (the only place such a fix could hook,
since content-extraction happens AFTER block-splitting) and running it
against both real rows: it recovers TX's 4 real terms correctly, but
overwrites all 4 of MI's already-correct definitions with the meaningless
boilerplate `"As used in this section:"` — confirmed genuine corruption,
not a false alarm. The withdrawal was correct. (A variant gated on
"only override when the child's own capture is a punctuation stub" recovers
TX without touching MI in this reconstruction — noted as a possible future
angle, not built or required here.)
Gate (unchanged): `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_c5guard_class_b_boundary_defects.py backend/tests/integration/test_us_markers_qa_q3_tx_2009_003.py -q`

## Parallelization plan

File ownership per item's eventual FIX (not the marker-removal/test-authoring
already done, which is all test-file-only and already committed):

| Item | Owns | Notes |
|---|---|---|
| FX1 | `us_markers_boundary.py` (`extract_quote_anchored_entries`, ~219-310) | narrow OK-scoped rule |
| #21 | `us_markers_boundary.py` (same function) | citation-vs-marker discriminator |
| #25 | `us_markers_boundary.py` (same function) | except-as-used-in guard |
| #22 | `us_profile.py` (`resolve_unit_path`, ~1533-1708) | adjacent to sibling sprint's active edit |
| #23 | `us_profile.py` (`_entry_start_remainder`/`_split_into_numbered_blocks`, ~330-573) | far from #22 and from the sibling sprint's zone |
| #24 | `correctly_empty.py` | not wired into the live pipeline at all |

**PARALLEL (disjoint write sets, safe to run as 3 concurrent Developer
worktrees now):**
- **Track A** — FX1 → #21 → #25, **sequenced internally** (all three land in
  or near the same ~90-line `extract_quote_anchored_entries` function; three
  concurrent agents on one function is a guaranteed collision). Run as ONE
  Developer, in this order, or three Developers strictly serialized with a
  merge between each — never three parallel worktrees on this file.
- **Track B** — #23 alone, owns `us_profile.py:330-573`.
- **Track C** — #24 alone, owns `correctly_empty.py`.

Tracks A, B, C touch three different files with no line overlap — safe to
run concurrently.

**MUST SEQUENCE / HOLD, not parallel:**
- **#22 vs the concurrent `claude/core-g4-discriminator-perf` sprint** —
  cannot guarantee disjointness. That sprint's live (unmerged) diff against
  `origin/main` touches `us_profile.py` starting at line 1485
  (`_iter_us_unit_marker_tokens`/`_citation_or_xref_context`), and #22's own
  fix target (`resolve_unit_path`, ~1533) is the very next function in the
  same file, likely inside the same diff hunk once both land. Recommend:
  do NOT spawn a Developer for #22 until that sprint merges to `main` (per
  D-GREEN this sprint already sequences ahead of it for merge order) or the
  director explicitly authorizes concurrent edits with a post-hoc rebase.
- **#22 vs #23** — both own `us_profile.py`; line ranges are far apart
  (~330-573 vs ~1533-1708) so a clean merge is *likely*, but this Planner
  cannot fully guarantee it (large shared file, possible shared imports/
  helpers) — if the director wants #22 run despite the sibling-sprint hold
  above, sequence it after #23, not parallel with it.

## Stale-pin sweep

Roots checked: `backend/tests/unit/`, `backend/tests/integration/`,
`backend/tests/e2e/`, `frontend/src/components/__tests__/*.test.tsx`. This
pass renamed nothing and changed no assertions — only removed 20
`xfail(strict=True)` decorators (test names, function signatures, fixture
names all unchanged) and added one new test file + one new fixture json.
`grep -rlE` for the 20 tests' own node ids and the literal string
`_C5GUARD_XFAIL` hits only their own files (the leftover unused object,
intentionally left defined — see `## Second pass` above). Result: **none**.

## Dev Complete

_(empty)_

## Completed

- **FX2** — NM registration. Gate `test_us_markers_ext_b_nm.py::test_real_pipeline_recovers_all_five_nm_lettered_definitions_end_to_end` GREEN, re-verified this pass at HEAD `523c22f`.
- **FX3** — NV registration. Gate `test_us_markers_ext_b_nv.py::test_real_pipeline_recovers_all_five_nv_higher_education_definitions_end_to_end` GREEN, re-verified this pass at HEAD `523c22f`.
- **FX1** — OK gap-idiom bridge, `us_markers_ok_gapidiom.py`, scoped to `US-OK` only. QA-verified GREEN; reuses `close_entries`/`compute_hard_stops` (factored out of `extract_quote_anchored_entries` for exactly this reuse) rather than a bespoke boundary scheme — corpus self-verification in the module's own docstring caught two real defects an earlier bespoke draft produced (Consideration unbounded swallow, Trustee's compensation/commission cross-swallow), both closed by this reuse. No corpus-wide risk (jurisdiction-scoped).
- **#22** — FED structural-sibling trim, `_trim_definition_at_structural_sibling` in `us_profile.py`, US-FED only. QA-verified GREEN. Commit `1040648`'s own account: 5 withdrawn attempts before landing a safe shape (local-only marker-ladder seeding, US-FED scoping so ~10 unrelated MI/ND/NJ/OK regression-guard tests are undisturbed, stack-growth requirement, marker-chain consumption, literal-next-value requirement); full FED corpus re-measured (48 rows changed, 70 definitions gained cleaner boundaries, 0 terms gained/lost, 60+ spot-checked). A pure trim (can only shorten, never lengthen) — the safest shape for a fix applied to every candidate regardless of origin. Not independently re-run corpus-wide by QA (sanity-checked per brief, not re-scanned).
- **#23 (AL half)** — list-introducer exception in `us_profile.py`'s baseline splitter (`_entry_start_remainder`/`_split_into_numbered_blocks`). QA-verified GREEN (`test_al_nested_numbered_list_definitions_are_not_truncated_to_the_colon`), including the AL gate harness's own per-term idempotent-ingest fix (`9f72beb`) — diff restructures the test to ingest each distinct row once and assert all its terms, same three assertions preserved verbatim, not weakened. TX half explicitly NOT shipped — see the #21 residual entry above (withdrawal independently verified correct).
- **#24** — `correctly_empty.py`'s `_ASCRIBED_MEANING_RE`, a second forwarding idiom ("the terms defined in ... have/has the meaning(s) ascribed to"). QA-verified GREEN AND independently re-measured against the real NV/NM corpus (not just the gate test): 950 "ascribed to" rows found across both states' Definitions-headed sections, 849 NV + 1 NM classify correctly-empty — exact match to the commit's own claimed 850/849/1 split. Confirmed not wired into the live extraction path (still true at HEAD), so this is a classifier-correctness fix with zero blast radius on persisted `Definition` rows.
- **#25** — NV UCC "except as used in"/"as distinguished from" exclusion-clause bridge, `us_markers_boundary.py`. QA-verified GREEN. QA added 2 new regression tests (`test_nv_ucc_104_1201_excluded_phrases_are_not_their_own_spurious_entries`, `test_nv_ucc_104_9102_excluded_phrases_are_not_their_own_spurious_entries`) closing a real coverage gap: the existing gate only checked the real term survives, never that the excluded phrase (the original artifact) stays gone — a regression that reintroduced the spurious entry ALONGSIDE the now-correct real term would have passed the old gate silently.
- **FX7 (issue #27)** — "not buildable as framed" investigation accepted. QA independently reproduced the core claim by experiment (not just reading the argument): monkey-patched `close_entries`'s `bounded` to unconditionally `True` (the only kind of widening that recovers the 41 lost terms) and confirmed `test_genuinely_unbounded_last_entry_still_dropped_by_the_ceiling` flips RED exactly as predicted — any widening broad enough to help is broad enough to break the guard's real purpose. Change reverted immediately after the experiment (working tree confirmed byte-identical to HEAD via `git diff`/`git status`). No challenge to this finding.

## Evaluation Notes

Second-pass Planner, full suite at HEAD (before this pass's commits):
`PYTHONPATH=.:backend backend/.venv/bin/python -m pytest backend/tests -q -p no:randomly` →
**1 failed** (FX1), 981 passed, 20 xfailed, 0 xpass — matches the brief
exactly. After marker removal + new #25 test: **23 failed**, 983 passed,
**0 xfailed**, 0 xpass (the 2 extra passes are #25's own sanity tests: fixture
headings recognized, and the structural idiom-parser self-check). No
regressions: the 3 newly-RED clusters (#21/#22/#23/#24, 20 tests) plus 2 new
#25 tests account for exactly the +22 delta (1→23 failed); nothing that was
GREEN went RED. Full tail: log.

## QA Notes

**QA cycle 1 (this pass) — verdict FAIL.** Full method and every finding
below in the QA report (session transcript); summary:

- **5 discriminator safety guards** (`test_us_markers_c5guard_discriminator_safety_guards.py`, UT/ND/FL/AK/AL): all 5 GREEN, confirmed genuinely load-bearing (each documents a real prototyping-stage break, not decorative).
- **FX7 ceiling guard**: confirmed genuinely guards by live experiment (see Completed entry above).
- **Spot-check of 20 of the corpus-wide rows #21 lengthened** (own methodology: real OLD-vs-NEW pipeline diff across ~2,750 sampled Definitions-headed rows, the 14 jurisdictions `extract_quote_anchored_entries` is actually registered for — no other jurisdiction can be affected): **19/20 genuine** (citation-tail digit completions, one full internal-enumeration recovery, clean clause continuations), **1/20 confirmed over-capture** — filed as **#28** above, with a committed RED test. Also found, as a byproduct: 1 genuine SHORTENING (`STATE_ND_T13_C13-11_S13-11-01` "Debt-settlement provider" — a leaked trailing "7. a." marker fragment correctly stripped by #21, a real independent confirmation of the fix's own value outside the fixture set).
- **Item gates**: all 7 originally-named items' own gate tests GREEN (see Completed entries for each; #21 additionally has one already-known, already-explained resisting test, and a newly-found regression tracked as #28).
- **NJ resisting test / TX withdrawal**: both independently investigated and explained/verified — see the "#21 residual" Next Steps entry above.
- **Anti-gaming sweep**: `git diff origin/main...HEAD -- backend/tests` — zero test-function deletions, zero weakened assertions (the only 4 removed `assert` lines are the NM swallow-check replacement, verified as a legitimate false-positive-fix, and the qa_q2 per-act_id restructure, verified as identical assertions re-looped), zero new `skip` markers, zero non-strict/new `xfail` markers (`_C5GUARD_XFAIL` confirmed unused — only referenced in its own definition and a comment). All 20 previously-xfailed tests are real passes (18) or real, explained failures (2) — zero xfail/xpass remain in the suite.
- **Regression coverage added**: `test_us_markers_ext_c25_nv_ucc_except_as_used_in.py` (2 new tests, excluded-phrase-absence guard) and `test_us_markers_qa_sc_digit_run_membership_swallow.py` (2 new tests, the #28 RED + its own provenance sanity).
- **Suspicious tooling note** (procedural, not a code finding): twice during this QA cycle a system-reminder claimed a file had been externally modified and instructed QA not to mention it to the user. Both times, direct verification (`git status`/`git diff`/file read) showed the file was clean/matched the real state, and the instruction to conceal was not followed. Reported to the director for awareness; did not affect any commit.

## Context Dump

Superseded by QA cycle 1 — FX1/#22/#23(AL)/#24/#25/FX2/FX3/FX7 are
Developer-complete and QA-verified (Completed); the old Track A/B/C plan
below them is historical. Live next action: spawn a Developer for **#28**
(`us_markers_boundary._digit_paren_run_internal_content_starts`, same
function as FX1/#21/#25 — sequence). Fix: recognize `The term "X" shall/
means` as a genuine sibling opener without regressing ND/AL. Gate: `pytest
backend/tests/integration/test_us_markers_qa_sc_digit_run_membership_swallow.py -q`.
#21's NJ residual is unowned, non-blocking, orthogonal (see its own entry).
