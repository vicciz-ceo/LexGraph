---
id: "2026-08-10-green-the-suite"
status: planned
current_role: developer
branch: claude/green-the-suite
locked_by: null
locked_at: null
last_agent: "claude-code:planner"
last_updated: "2026-08-11T22:48:35Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 7
lint: "PASS 236 2026-08-11T22:49:28Z"
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

### FX1 — OK gap-idiom: bridge the interposed clause between quoted term and "shall mean" (US-OK)

Unimplemented, unchanged from first pass. Owns `us_markers_boundary.py`
(narrow OK-scoped rule, pattern of `us_markers_tn_idiom.py`'s TN gap-bridge —
NOT a corpus-wide loosening of the shared tight gate).
Gate: `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_ext_a_ok_gapidiom.py::test_real_pipeline_recovers_ok_gap_idiom_definition -q`

### #21 — c5guard class-B: 16 NJ/ND/OK boundary defects (citation-tail truncation, premature stop, marker-chain leak)

XFAIL marker removed, now RED (16 tests). Fix: a citation-vs-entry-marker
discriminator in `us_markers_boundary.py`. **Caution**: issue #21's own text
routes this to "core-follow-on-3" (a different initiative) and forbids
extending `us_profile.py`'s `_citation_or_xref_context`. Director should
confirm this sprint may implement it before a Developer is spawned (see
Escalations in Planner report).
Gate: `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_c5guard_class_b_boundary_defects.py -q`

### #22 — FED `USC_T8_C12_S1101` over-captures next Roman-numeral structural sibling

XFAIL marker removed, now RED (1 test). Fix lives in `us_profile.py`'s
marker-hierarchy logic (`resolve_unit_path`, ~lines 1533-1708) — **directly
adjacent to** `_citation_or_xref_context` (~1488-1532), the exact function
the concurrent `claude/core-g4-discriminator-perf` sprint is actively
editing (confirmed: its live diff vs `origin/main` starts at
`us_profile.py:1485`). HOLD — do not spawn until coordinated with that
sprint. See Parallelization plan.
Gate: `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_core3_fed_structural_sibling_live.py -q`

### #23 — Baseline splitter truncates nested numbered/lettered-list definitions to a punctuation stub (AL x6, TX x4)

XFAIL markers removed, now RED (2 tests, 10 real terms). Fix: list-introducer
exception in `us_profile.py`'s `_entry_start_remainder`/
`_split_into_numbered_blocks` (~lines 330-573) — far from #22's territory and
from `_citation_or_xref_context`, but same FILE; sequence vs #22, safe in
parallel with Track A/C. Anchor check (director asked): `term in by_term`
holds for all 10 — key survives — but captured `definition_text` is a 1-8
char punctuation/colon stub (`';'`, `'means:'`) carrying zero real content.
Verified live, both files. Practically this is closer to content loss than
the other XFAILs in this batch; flagged, not reclassified unilaterally (see
Planner report).
Gate: `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_qa_q2_short_definitions.py backend/tests/integration/test_us_markers_qa_q3_tx_2009_003.py -q`

### #24 — NV cross-reference idiom not recognized by `classify_correctly_empty`

XFAIL marker removed, now RED (1 test). Fix: extend `correctly_empty.py`'s
`_CROSS_REFERENCE_RE`. Fully isolated file, not imported into the live
extraction path at all (confirmed by issue #24's own grep) — zero collision
risk with any other item in this batch.
Gate: `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_ext_b_nv.py::test_nv_cross_reference_idiom_is_not_yet_recognized_as_correctly_empty -q`

### #25 — NV UCC "except as used in" disambiguation loses the real term

NEW RED test authored this pass (2 tests, 7 real terms across 2 rows).
FIX-class per D-RECALL-FP (anchor loss, not quality). Fix: a guard in
`us_markers_boundary.py`'s `extract_quote_anchored_entries` for the
`"TERM," (as distinguished from|except as used in) "excluded...," means`
shape, so the excluded phrase is not treated as the definiendum. Same file
as FX1 and #21 — sequence, do not parallelize.
Gate: `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_ext_c25_nv_ucc_except_as_used_in.py -q`

### FX7 — issue #27: scope `MAX_CLEAN_DEFINITION_LENGTH` for discriminator-closed entries

Investigated this pass, **not buildable as framed** — evidence, not opinion.
All 41 of #21's lost terms have `has_next_term=False` + zero hard-stops (the
"ran off the end of text" shape the ceiling already targets), not the
"reaches next quote, zero hard-stops" shape the ruling named — that shape
is *already* unconditionally exempt (`bounded = bool(candidate_stops) or
has_next_term`). Byte-verified spot checks (NJ "Department", USC "furlough")
show genuine swallows, not clean closures. Two GREEN tests pin the finding;
no production fix exists to gate. Director decision needed — see Planner
report Escalation.
Gate: `PYTHONPATH=.:backend backend/.venv/bin/pytest backend/tests/integration/test_us_markers_fx7_ceiling_known_closed_scope.py -q`

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

_(none yet — first Developer pass not run)_

## Context Dump

Manager: spawn Track A (FX1→#21→#25, sequenced, one worktree,
`us_markers_boundary.py`), Track B (#23, `us_profile.py:330-573`), Track C
(#24, `correctly_empty.py`) as up to 3 parallel Developers now. HOLD #22 —
resolve the `core-g4-discriminator-perf` collision first (Parallelization
plan + Planner's ESCALATION). Confirm #21 belongs in this sprint at all —
its issue text names it "core-follow-on-3 territory"; D-GREEN2 may
supersede that, but ask before Track A touches #21 (FX1/#25 unaffected).
