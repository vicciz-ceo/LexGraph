---
id: "2026-08-10-core-g4-discriminator-perf"
status: review
current_role: planner
branch: claude/core-g4-discriminator-perf
locked_by: null
locked_at: null
last_agent: "claude-code:qa"
last_updated: "2026-08-10"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "cd /Users/nerya/LexGraph-wt/core-g4-perf && PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python -m pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 1
completed_items: 1
dev_complete_items: 0
qa_cycles: 1
previous_sprint: "2026-08-04-defs-us-preamble"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
---

# Sprint: core — bound the G4 citation/cross-reference discriminator's lookback

## Mandate

`_citation_or_xref_context` (`backend/app/definition_links/us_profile.py:1488`)
runs up to five regex probes as `PATTERN.search(body, 0, trimmed_end)` — each
unanchored from document position 0 — and is called once per candidate marker
token from inside `resolve_unit_path`'s loop (`us_profile.py:1654`). Cost per
token is therefore O(document position), and `resolve_unit_path` as a whole is
O(tokens x position).

This is **already on `main`** (`be4370b`), owned by neither active panel. It is
latent here because nothing on main drives `resolve_unit_path` per-trigger over
large bodies; the scoped-inline panel does, via `_resolve_subsection_scope`, and
that is what exposed it. **It blocks all four remaining panel merges**
(scoped-inline, multiterm, IL, PR), not just one.

Make it fast. Do not make it different.

## Measured evidence (program manager, 2026-08-10)

Same function, same three federal rows, 30s cap, raw and normalized input alike:

| row | bytes | scoped-inline tree (no G4) | merged tree (G4 present) |
|---|---|---|---|
| `USC_T17_C1_S115` | 150,551 | 0.02s | 4.07s |
| `USC_T26_C1_S72` | 187,145 | 0.04s | >30s |
| `USC_T42_C7_S405` | 225,928 | 0.02s | >30s |

Bisected by runtime monkeypatch: neutralizing `_US_PERIOD_UNIT_MARKER_RE` alone
changes nothing (3.41s -> 3.37s); additionally neutralizing the discriminator
restores 0.02s/0.04s. cProfile attributes 3.401s of 3.438s to 6,800
`re.Pattern.search` calls, all from `_citation_or_xref_context`. Growth curve
across five body sizes holds `time / (tokens x offset)` constant at 3.5-4.2e-8
over a 200x range, while `time/tokens^2` and `time/offset^2` each drift ~3x —
the signature of O(M*N), not exponential backtracking.

Corpus cost, measured over all 53 files / 2,038,247 rows on the merged tree:
**230 rows across 21 jurisdictions cannot be processed at all**, and a
corpus-wide deletion screen attributes **4,097 genuine anchor losses** to them —
**100% of the merge's total anchor loss, with zero losses on any row where both
panels complete.**

## Acceptance gates (manager-defined, plain language)

1. **Nothing changes except speed.** For every input, `resolve_unit_path` and
   `_is_citation_or_xref_context` return exactly what they returned before.
   This is the gate that matters most: a faster wrong answer is a failure.
2. **The rows that used to hang now finish.** All 230 known-pathological rows
   process well inside the guard threshold and produce their definitions.
3. **The lost definitions come back.** Corpus-wide genuine anchor losses on the
   merged tree fall from 4,097 to zero (or every remaining loss is explained and
   shown not to be a timeout).
4. **No regression anywhere else.** The backend suite holds its accepted ledger.
   The 16 known merge-interference failures are NOT this sprint's to fix and
   must not be "fixed" by touching them.
5. **Bounded change.** The lookback window, and only the lookback window. Do not
   touch the G2 ladder-defer logic (`us_profile.py:1665-1672`) or
   `_US_PERIOD_UNIT_MARKER_RE` — those are the separate Family C correctness
   causes, and bundling them merges two unrelated rulings.

## Known planning risk — resolve this before authoring tests

The defect is **latent on `main`**: B1 and scoped-inline both live on panel
branches, so no test on this branch alone will be slow by default. The Planner
must decide, and record, how to build a RED test that fails here and passes
after the fix, without being a wall-clock flake. Candidate shapes, in preference
order — the Planner picks and justifies:

- **Work-count assertion** (preferred): instrument or count the discriminator's
  regex probe work for a synthetic large body with many marker tokens, and
  assert it does not grow with document position. Deterministic, no timing.
- **Complexity-ratio assertion**: run at two body sizes and assert the ratio is
  sub-quadratic. Timing-based but far more robust than an absolute bound.
- **Absolute wall-clock bound**: last resort, and only with generous headroom.

Plus, mandatory regardless of shape: an **equivalence test** proving output is
unchanged across a corpus sample — gate 1 is the one that must not be traded
away for gate 2.

**Planner resolution (2026-08-10).** Chose the work-count assertion (shape 1).
Both `_citation_or_xref_context` and `resolve_unit_path` call the five suffix
regexes as literal `search(body, 0, trimmed_end)` -- `pos` is always `0`, so
the search window (`endpos - pos`) equals `trimmed_end` itself today,
regardless of token position. A thin recorder wrapped around each of the five
module-level regex objects (NOT the three named acceptance targets) forwards
to the real `.search` while recording the `(pos, endpos)` args actually used
-- this is instrumentation of a dependency, not a stub of the discriminator's
decision, so it does not trip the self-mock ban. Verified directly against
this branch before committing to the shape: a body with no matchable
citation/structural-word content forces every probe to genuinely scan to
`trimmed_end`, confirmed by wrapping the five regexes and reading back the
recorded windows (see the RED confirmation run below) -- deterministic, no
wall-clock, cannot flake. Three test files implement this:
- `backend/tests/unit/test_definition_links_core_g4_perf_bounded_window.py` --
  calls `_citation_or_xref_context` directly at isolated far/near positions in
  a synthetic 177,600-char body; asserts window size stays under a
  4096-char bound (~40x headroom over the longest real branch match) and
  does not grow between a near and a far token.
- `backend/tests/integration/test_definition_links_core_g4_perf_resolve_unit_path_live.py`
  -- drives the real `resolve_unit_path` entry point (not the helper
  directly) over 220 marker tokens across ~98,000 chars; asserts the same
  per-probe bound holds through the live per-token loop, that total probe
  work does not roughly quadruple when token count merely doubles, AND (a
  third case, grounded in the sprint contract's own cited evidence) that the
  real federal row `USC_T17_C1_S115` (150,551 bytes, contract-measured
  4.07s) shows the same unbounded window at its last marker token today.
- `backend/tests/unit/test_definition_links_core_g4_perf_equivalence.py` --
  the mandatory gate-1 guard. P-R11 compliant: the baseline JSON fixture
  (`backend/tests/fixtures/us_statutes/core_g4_perf_equivalence_baseline.json`)
  was produced by literally running today's code (see the module's
  `_regenerate_baseline`), not hand-authored. **This test is GREEN today by
  design** -- gate 1 is not broken yet, so there is nothing for it to fail
  on; its job is to start failing the moment the Developer's speed change
  alters any output, which is exactly gate 1's contract. The RED evidence
  for this sprint comes from the other two files (5 of 6 new tests fail
  today; this one intentionally does not).

**Gate 3 -- corpus-wide anchor-loss delta -- is explicitly OUT of this
sprint's scope.** It can only be observed on a merged probe tree this branch
does not have; the manager verifies it post-merge. No sprint item targets it.

## Next Steps

### Item 1 (DEV COMPLETE, commit `4c0ff01`) -- bound `_citation_or_xref_context`'s five suffix-regex probes to a fixed lookback window

Description: `us_profile.py:1496-1509` calls each of the five suffix regexes
as `PATTERN.search(body, 0, trimmed_end)` -- `pos` is the literal constant
`0`, not a function of `trimmed_end`. Change the call site(s) only, so each
probe searches `search(body, max(0, trimmed_end - WINDOW), trimmed_end)`
for a `WINDOW` generously larger than the longest real branch match (a
full-U.S.C. cite is the longest, well under 100 chars) -- e.g. a few
hundred characters. Do not touch matching semantics, branch order, or the
five patterns themselves; do not touch `us_profile.py:1665-1672` (G2
ladder-defer) or `_US_PERIOD_UNIT_MARKER_RE`.

Acceptance criteria (all currently RED, must go GREEN, in this order of
priority):
1. `test_definition_links_core_g4_perf_equivalence.py` -- stays GREEN
   (gate 1; captured via P-R11 against today's code, do not regenerate the
   baseline as part of this fix).
2. `test_definition_links_core_g4_perf_bounded_window.py` -- both tests GREEN.
3. `test_definition_links_core_g4_perf_resolve_unit_path_live.py` -- all
   three tests GREEN, including the real-evidence `USC_T17_C1_S115` case.
4. Full `backend/tests` run: no NEW failures beyond the 23 pre-existing
   ones already present before this item (see Stale-pin sweep note below on
   the "16" figure) -- gate 4.

Files likely affected: `backend/app/definition_links/us_profile.py`
(`_citation_or_xref_context`, lines ~1488-1509) only.

Not this item's job: gates 2's full 230-row corpus sweep and gate 3's
corpus-wide anchor-loss delta are both post-merge manager checks against a
merged tree this branch does not have -- see the note directly below.

## Stale-pin sweep

Checked every test root named in `docs/sprint/repo-profile.md` for anything
Item 1 changes (the five suffix-regex names, `_citation_or_xref_context`,
`_is_citation_or_xref_context`, `resolve_unit_path`, `_iter_us_unit_marker_
tokens`):
- `backend/tests/unit/` and `backend/tests/integration/`: no test besides
  this sprint's three new files references the five suffix-regex names or
  `_citation_or_xref_context` directly (`grep -rl` confirmed). Every
  pre-existing test that exercises this code path goes through the public
  `profile.resolve_unit_path(...)` seam, whose signature and return shape
  Item 1 does not change -- nothing to re-point.
- `backend/tests/e2e/`: no hits for `resolve_unit_path`/`_citation_or_xref_
  context`/`us_profile` at all.
- `frontend/src/components/__tests__/*.test.tsx`: no hits (Python-internal
  names, not applicable).

**Two stale values found and fixed in this pass (both permitted under "update
the contract and repo-profile.md if a value there is stale"):**
1. This sprint contract's `evaluator_command` and the frontmatter above
   referenced `backend/.venv/bin/pytest`, which does not exist in this
   worktree (`/Users/nerya/LexGraph-wt/core-g4-perf/backend/.venv` is
   absent -- confirmed by `ls`). Updated to the verified worktree invocation
   from the Planner brief's Environment section (main checkout's venv +
   `PYTHONPATH=.:backend`, `cd`-scoped to this worktree). Not touching
   `docs/sprint/repo-profile.md`'s own general `evaluator_commands`/
   `venv_setup` recipe, which is presumably accurate for checkouts that DO
   build their own venv (e.g. the main checkout) -- this is a worktree-
   specific carve-out, not a repo-wide correction, so I did not overwrite the
   general recipe based on one worktree's setup.
2. Gate 4's "16 known merge-interference failures" is stale: a full
   `backend/tests` run on this branch today (verified twice -- once with
   this sprint's new files present, once with them moved aside) shows
   **23** pre-existing failures, all in `test_us_markers_*` files, none
   touching `us_profile.py`'s G4 discriminator. Recorded here as a factual
   correction, not a rewrite of the manager's gate language; Item 1's
   acceptance criteria above use the measured 23, not the stale 16.

## Dev Complete

_(empty -- Item 1 moved to Completed after QA PASS, see below)_

## Completed

- [x] **Item 1 (COMPLETED, commit `4c0ff01`, QA-verified 2026-08-10) --
  bound the G4 discriminator's five suffix-regex probes to a fixed
  512-char lookback window.** `_citation_or_xref_context`
  (`us_profile.py:1488-1552`) now calls each of the five suffix regexes as
  `PATTERN.search(body, max(0, trimmed_end - _SUFFIX_PROBE_WINDOW),
  trimmed_end)` instead of `PATTERN.search(body, 0, trimmed_end)` -- `pos`
  is no longer the literal constant `0`. Only the call site and a new
  module-level `_SUFFIX_PROBE_WINDOW = 512` constant changed; matching
  semantics, branch order, and the five patterns themselves are untouched,
  as is everything outside `_citation_or_xref_context` (G2 ladder-defer
  logic at 1665-1672 and `_US_PERIOD_UNIT_MARKER_RE` not touched).

  **Window derivation (512 chars), not copied from any test constant:**
  `_STRUCTURAL_UNIT_WORD_SUFFIX_RE` is a closed, finite word alternation
  with no quantifier -- longest member "subdivision" = 11 chars, already
  bounded. The other four patterns all end in the same
  `\d+(?:[.\-]\d+)*\Z` numeric pin-cite tail; the longest,
  `_FULL_USC_CITATION_SUFFIX_RE`
  (`\d+\s+U\.S\.C\.\s+§\s*\d+(?:[.\-]\d+)*\Z`), has 7 fixed literal chars
  ("U.S.C." + "§") plus four variable spans that are only ever a
  citation's own digits/whitespace in real statute text: a leading US Code
  title number (titles run 1-54, budgeted 4 chars), three inter-token
  whitespace runs (ordinarily one space, budgeted 8 each), and the
  trailing numeric chain (real citations chain at most a handful of
  dot/hyphen-separated components, e.g. "115-6-2"; budgeted 10 components
  x 5 chars = 50) -- sum 85 chars. The other three citation-suffix
  patterns are strict subsets of that shape, so none exceeds 85 either.
  512 is ~6x that derived 85-char bound, independently corroborated by
  this contract's own "well under 100 chars" measurement and the RED
  tests' 4096-char ceiling (~40x that same ~100-char figure), while
  staying 8x under that 4096 ceiling.

  Files touched: `backend/app/definition_links/us_profile.py` only (54
  insertions, 7 deletions -- the probe call sites plus the derivation
  comment and docstring update). No test file touched. Sprint contract
  updated in this same pass.

  See Evaluation Notes below for the before/after suite numbers, the
  measured timing improvement, and the QA Verification Notes for
  independent gate-by-gate confirmation.

## Evaluation Notes

**Developer pass (2026-08-10).** HEAD verified at `283cf21` before any
writes. Full `backend/tests` run before the fix: **28 failed / 980
passed** (23 pre-existing `test_us_markers_*` failures, already recorded
in the Stale-pin sweep above, plus this sprint's 5 committed RED tests).
After the fix (commit `4c0ff01`): **23 failed / 985 passed** -- the exact
same 23 test names failing (diffed by name, not just count), and all 5 RED
tests now green. The mandatory equivalence guard
(`test_definition_links_core_g4_perf_equivalence.py`) stayed green
throughout, never went red at any point in this pass.

**Timing improvement, measured directly (not just via the RED tests'
work-count proxy):** `resolve_unit_path` against the real
`USC_T17_C1_S115` row (150,551 bytes, the sprint contract's own named
pathological row) -- measured by temporarily reverting
`us_profile.py` to the pre-fix `HEAD` content, timing, then restoring the
fix and timing again, both via the same script against the row already
vendored in
`backend/tests/fixtures/us_statutes/core_g4_perf_pathological_federal_row.json`:
before **4.996s**, after **0.097s** (~51x), with **byte-identical
returned `UnitPath`** in both runs -- direct evidence for gate 1
(unchanged output) alongside the equivalence test, and direct evidence for
the speedup alongside the RED tests' work-count assertions.

Full suite wall time also dropped, 45.10s -> 23.27s, consistent with other
tests in the suite that drive `resolve_unit_path` over non-trivial bodies
also benefiting, though this was not individually attributed per-test.

## QA Verification Notes (2026-08-10, PASS)

Independently verified all five gates against this branch (`3f4b980`) and the
merged probe tree `/Users/nerya/LexGraph-wt/probe-precedence-a` @ `baf184d`
(preamble + scoped-inline + this fix). Nothing in `backend/app/**` was
touched by this pass; two new test files were added (see below).

**Gate 1 (behavior identical) -- PASS, dominant margin.** Ran the 6
committed acceptance tests (5 RED-turned-GREEN + the equivalence guard):
all green. Beyond that: scanned the ENTIRE pinned corpus (105 parquet
files, 2,046,009 rows -- every statute and constitution row, not a sample)
for the longest REAL match of each of the five suffix patterns
(`_STRUCTURAL_UNIT_WORD_SUFFIX_RE`, `_FULL_USC_CITATION_SUFFIX_RE`,
`_SECTION_CITATION_SUFFIX_RE`, `_LONE_SECTION_CITATION_SUFFIX_RE`,
`_BARE_STATE_CODE_CITATION_SUFFIX_RE`, `\Z` stripped so the search finds
the match content anywhere, not just where it happens to anchor). Longest
real match found anywhere in the corpus: **24 characters** (a
`bare_state_code`-shaped match with odd whitespace). Full-U.S.C. citations
topped out at 22 chars (`"42 U.S.C. §12131-12165"`). `_SUFFIX_PROBE_WINDOW`
(512) has a **21x+ margin** over the worst real citation in the entire
corpus -- no real row anywhere can have a citation clipped by the window.
Zero matches exceeded the window (`count_over_window: 0` for all five
patterns).

**Gate 2 (230 pathological rows complete) -- 228/230 comfortably fast,
2/230 slow-but-finite (escalated, not a fail).** Loaded all 230 rows named
in the handed-off `precedence_d3_pathological_rows.jsonl` directly from the
pinned corpus by `act_id` match (all 230 found), and ran each through the
real Stage2/Stage3 mirror (`precedence_m2_stage2.extract_row_definitions`,
byte-identical call sequence to `pipeline.py`) against the merged+fix tree,
one row per isolated worker process (persistent worker over a pipe,
killed and respawned on a per-row deadline -- per this program's own
SIGALRM-can't-bound-a-runaway-regex lesson). At a 15s per-row deadline:
**228/230 complete, most in well under 1s** (median ~0.4s; slowest of the
228 was 7.8s). **2/230 exceeded 15s**: `USC_T42_C7_S1395ww` (839,700
bytes) and `STATE_HI_D2_T24_C431_S431` (2,404,155 bytes) -- the 3rd- and
**1st**-largest bodies in the entire 230-row set (median body_len 128,960;
next-largest below these two is 873,879 and it completed in 5.4s). Given a
generous 60s ceiling, both DO complete: 24.7s and 30.5s respectively --
neither hangs. cProfile on both shows `_citation_or_xref_context` is still
the dominant cost (13.5s and 14.7s of the totals), but NOT because any
individual probe is unbounded: 372,402 and 414,790 discriminator calls
respectively (i.e. that many candidate marker tokens in one document),
each now paying only the bounded ~512-char-window cost -- O(1) per call,
confirmed -- but the sheer per-document token count on these two extreme
outliers still sums to double-digit seconds. This is categorically
different from the pre-fix defect (O(position), unbounded, would never
terminate): it is O(tokens x window) with an unusually large token count,
a separate scaling axis the sprint's own scope note explicitly excludes
("the lookback window, and only the lookback window"). **Escalating, not
failing on this**: 1 of the 2 (30.5s) is a hair over the 30s cap the
contract's own "Measured evidence" table used, on the single largest
document in the 230-row set (19x the median, and 10.6x the largest body
the contract's own evidence table cited). Recommend the Planner/manager
decide whether a follow-up item (bounding total per-document discriminator
work, not just per-probe window) is warranted -- out of THIS item's scope
as written.

**Gate 3 (lost anchors recovered) -- PASS, 4,097-ish -> 0 on the actual
denominator verified.** Ran the same base-vs-cmp anchor-diff methodology
the manager's own M2 screen used
(`precedence_m2_anchor_diff.py`, unmodified), with: base = preamble-alone
tree (`defs-us-preamble` @ `e410bf0`, no G4 defect, all 230 rows complete
natively) and cmp = merged+fix tree's ACTUAL completed output for all 230
rows (the 228 fast completions plus the 2 slow-but-completed stragglers
above -- no `pathological_total_loss` stand-ins used, since all 230 now
produce a real result). Result: **`genuine_anchor_losses: 0`** across all
230 rows (1,162 raw anchor-tuples were removed, but all 1,162 survive
under the term-presence check -- the term is still there, sometimes
reattached to a different scoped-inline-derived text/scope, which is
expected: scoped-inline can now finish and contribute its own refined
candidates instead of being blocked entirely). Cross-checked with a
**300-row representative control sample** (random sample of
`precedence_m2_candidate_rows.jsonl`, i.e. already-completing, non-
pathological rows that already exercise the G4 discriminator) run through
the same two trees: also **`genuine_anchor_losses: 0`** -- no new
regression introduced elsewhere by the fix. **Denominator stated
explicitly, not extrapolated**: 230 (100% of the handed-off pathological
list) + 300 control = 530 of 2,038,247 corpus rows measured directly; this
is not a full corpus re-screen.

**Data-provenance note (does not affect the PASS verdict):** the handed-off
`precedence_d3_pathological_rows.jsonl` (230 rows, all `timed_out_in:
"scoped_inline"`) is NOT the same row set as this program's own
`precedence_m2_pathological_rows.jsonl` (279 rows) that generated the
cited "4,097 genuine anchor losses" figure -- 36 of the 230 handed-off rows
are absent from the 279-row set entirely, and only 3,508 of the 4,097
losses trace structurally to the 230-row set (the other 589 trace to 72
rows in the 279-set not present in the 230-list). This looks like two
different measurement passes from earlier in the program, not a defect in
this pass. QA measured directly against the exact 230-row denominator
handed off in this brief (0 losses) rather than trying to reconcile the two
historical lists -- flagged here per P-R11 (report the real delta, don't
paper over a discrepancy in inherited data).

**Gate 4 (no regression) -- PASS.** Full `backend/tests` run (independently,
not trusting the Developer's numbers): **23 failed / 985 passed** before
QA's own additions, same 23 test names as the Developer's reported
baseline (all `test_us_markers_*`, none touching `us_profile.py`'s G4
code). After adding QA's 2 new regression tests: **23 failed / 987
passed**, same 23 names, both new tests green. Zero xpass.

**Gate 5 (anti-gaming) -- PASS, verified by mutation, not inspection.** Two
mutations applied directly to `us_profile.py` (never committed, reverted
via `git checkout` immediately after each, worktree confirmed clean before
and after): (1) reverting `probe_start` to always `0` (simulating a silent
revert to unbounded lookback) correctly turned all 5 of the Developer's
window/work-count tests RED (equivalence guard correctly stayed GREEN --
behavior is genuinely unchanged, only speed regresses); (2) shrinking
`_SUFFIX_PROBE_WINDOW` to 5 (simulating a window too small to catch real
citations) correctly turned the equivalence guard RED immediately (`GATE 1
VIOLATION` on the `chain_continuation_or_connector` case). Both non-vacuity
guards (`assert windows, "expected at least one suffix-regex probe to
run"`) are present in every window-recording test and are load-bearing,
not decorative -- confirmed they fire real recorded windows, not an empty
list, in every passing run.

**Regression tests added (QA's own, on top of the Planner's three files):**
`backend/tests/unit/test_definition_links_core_g4_perf_qa_window_regression.py`
-- two tests: (a) a TIGHTER independent ceiling (1024 chars vs the
Planner's 4096) that catches a moderate silent widening (e.g. to 2000
chars) the Planner's own looser bound would miss -- verified by mutation;
(b) a corpus-grounded floor check using a synthetic ~60-char realistic
full-U.S.C. citation (M-R107 compliant -- no literal corpus content, just
the same pattern shape) placed immediately before a marker token at both a
near and a ~200,000-char-deep far position, asserting the citation is
still recognized as citation context at both -- catches the window being
shrunk below what real citations need. Both mutation-tested to confirm
they fail on the two directions they claim to guard against.

## Context Dump

New sprint, created by the program manager off `main` @ `be4370b`. Nothing
implemented yet. Program rulings P-R19 (perf defects are invisible to the test
estate; time the merged tree against the largest real corpus rows) and P-R20
(this fix routes to core, ahead of the panel merge queue) are the governing
context; both are in the program log on `claude/defs-us-preamble`.

**Planner pass complete (2026-08-10).** Full rationale (why the work-count
shape over the other two, how the window-recorder instrumentation was
validated against the real branch before being written into tests, the exact
probe-window numbers observed) is in
`docs/sprint/sprints/2026-08-10-core-g4-discriminator-perf-log.md` -- not
repeated here per the brief. Four RED test files committed (one item, four
files: two RED tracks plus the real-evidence case bundled into the
integration file, plus the equivalence guard which is intentionally GREEN
today). HEAD verified at `1b7d910` before any writes; all work is additive
(no existing file under `backend/app/` touched).

**Developer pass complete (2026-08-10, commit `4c0ff01`).** Item 1
implemented exactly as scoped -- see Dev Complete and Evaluation Notes
above for the window derivation, files touched, and before/after numbers.
No test file touched, no line written outside
`backend/app/definition_links/us_profile.py`'s discriminator probe
mechanism. No escalation needed: all five patterns' maximum match lengths
were derivable from the patterns themselves once the trailing numeric
pin-cite chain is read as a bounded real-world citation shape rather than
an unbounded formal regex length (see the Dev Complete entry's derivation
walkthrough). Ready for QA; gates 2 (230-row corpus sweep) and 3
(corpus-wide anchor-loss delta) remain explicitly out of this sprint's
scope per the manager's own note above and are not re-litigated here.
