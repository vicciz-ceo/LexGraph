# Sprint log — 2026-08-10-core-g4-discriminator-perf (Planner)

Rationale that doesn't belong in the contract itself, per the brief's
"Rationale goes to the log, not the contract."

## Why the work-count shape (over complexity-ratio or wall-clock)

Verified directly against this branch (`1b7d910`, off `main` `be4370b`)
before writing any test, using a throwaway probe script
(`/private/tmp/.../probe_windowsize.py`, not committed):

```
body length: 177600
_STRUCTURAL_UNIT_WORD_SUFFIX_RE n_calls=1 max_window=177595
_FULL_USC_CITATION_SUFFIX_RE    n_calls=1 max_window=177595
_SECTION_CITATION_SUFFIX_RE     n_calls=1 max_window=177595
_LONE_SECTION_CITATION_SUFFIX_RE n_calls=1 max_window=177595
_BARE_STATE_CODE_CITATION_SUFFIX_RE n_calls=1 max_window=177595
frac=0.1 pos=17760  time_for_20_calls=0.0156s
frac=0.5 pos=88800  time_for_20_calls=0.0792s
frac=0.9 pos=159840 time_for_20_calls=0.1513s
frac=0.99 pos=175824 time_for_20_calls=0.1581s
```

This confirms two things at once: (a) the `search(body, 0, trimmed_end)`
call passes a LITERAL `0` as `pos`, so the recorded window IS `trimmed_end`
-- an exact, deterministic, non-timing-based signal -- and (b) wall-clock
scales with it too (10x more work at frac=0.99 vs frac=0.1, matching
position growth), confirming the recorder isn't measuring a fluke.

Work-count (shape 1) was chosen over complexity-ratio (shape 2) because the
window-arg recording gives a DIRECT causal measurement (the exact number of
characters a probe was told to search) rather than an indirect proxy
(elapsed wall-clock, which is also sensitive to machine load, Python
version, and regex engine internals unrelated to this defect). It was
chosen over an absolute wall-clock bound (shape 3) because no timeout
plugin is installed in this repo's venv (`backend/pyproject.toml`'s `dev`
extras: `pytest`, `pytest-cov`, `httpx` only -- no `pytest-timeout`), and
the Planner brief says not to pip install; a hand-rolled `time.perf_counter`
bound would also need generous slack for a slow CI machine, which is
exactly the kind of "weakened assertion" risk the brief warns against for a
Developer trying to make a RED test pass without truly fixing the defect.

The window-recorder technique itself does not stub any acceptance target:
it wraps the FIVE SUFFIX-REGEX OBJECTS (`_STRUCTURAL_UNIT_WORD_SUFFIX_RE`
etc.), which are private implementation details `_citation_or_xref_context`
happens to call, not `_citation_or_xref_context`/`_is_citation_or_xref_
context`/`resolve_unit_path` themselves. The wrapper always forwards to the
real compiled pattern's `.search()` and returns its real result unmodified
-- it is a spy, not a stub. Confirmed this compiles down correctly by
re-running each new test file and inspecting that recorded windows always
match `_citation_or_xref_context`'s own `trimmed_end` (which the function
computes and returns), i.e. the instrumentation observes reality rather
than substituting a fake.

## Bound choice: 4096 characters

The five patterns' own match spans are all short by construction:
`_STRUCTURAL_UNIT_WORD_SUFFIX_RE` matches one word (<= ~11 chars,
"subdivision"); `_FULL_USC_CITATION_SUFFIX_RE`'s longest realistic instance
is something like `"47 United States Code, Section 522(13)"` (well under
100 chars, and the pattern doesn't even require the "United States Code"
words -- just digits, "U.S.C.", "§", digits); `_SECTION_CITATION_SUFFIX_RE`/
`_LONE_SECTION_CITATION_SUFFIX_RE`/`_BARE_STATE_CODE_CITATION_SUFFIX_RE` are
all similarly short. 4096 gives roughly 40x headroom over the longest of
these, while every position probed in the new tests is >= 10,000 chars in
(17-40x the bound itself), so the bound cannot be satisfied by accident on
a small test body -- it only passes once the implementation genuinely stops
scanning from position 0.

## Why the equivalence test is GREEN today (and why that's correct, not a gap)

Gate 1 says output must not change. Nothing has changed yet on this branch
-- the defect is a SPEED problem, not a correctness problem, so there is no
existing output difference for an equivalence test to detect today. Forcing
it to also fail today (e.g. by mixing in a wall-clock assertion) would
conflate two different failure modes in one assertion, which is exactly the
ambiguity the brief's "gate 1 must not be traded away for gate 2" line
warns against -- if the Developer sees ONE test failing for two possible
reasons, they might "fix" the wrong one. Keeping it a pure characterization
test (P-R11: baseline captured by running today's code, not hand-authored)
means: if it's green after the Developer's change, gate 1 holds; if it goes
red, the Developer changed behavior, full stop, no other explanation
possible. The RED evidence for this sprint's defect lives entirely in the
other two test files (5 of 6 new tests currently fail); this one is the
tripwire for the fix, not evidence of the current bug.

## Corpus row extraction for the real-evidence case

Extracted `USC_T17_C1_S115` from `us_federal_statutes.parquet` in the pinned
corpus snapshot via `pyarrow.parquet.read_table`, confirmed `len(text) ==
150551` (exact match to the contract's measured-evidence table), and wrote
the full row (all original parquet columns, unmodified) to
`backend/tests/fixtures/us_statutes/core_g4_perf_pathological_federal_row.json`
-- following this test suite's own established convention (every other
`us_statutes/*.json` fixture is a committed extraction, not a live corpus
read) rather than reading the HuggingFace cache path at test time, which
would make the test depend on that exact cache being present on whatever
machine/CI runs it later. Verified the extracted row reproduces the SAME
unbounded-window defect (window=150093 at the last of 1,165 marker tokens)
before committing to using it.

## Deviations from the brief

- Bundled the "real corpus row" case into the SAME integration test file
  as the synthetic live-path test, rather than a fourth separate file/item.
  The brief names exactly three required test tracks (unit bounded-window,
  integration live-path, equivalence); this is an ADDITIONAL case within
  the second track, added because gate 2 names "the rows that used to
  hang" and the sprint contract's own measured-evidence table already
  names three specific rows on THIS branch (no panel needed, since G4 is
  already on `main`) -- using one of them grounds gate 2 in real, already-
  cited evidence rather than only a synthetic proxy, at near-zero extra
  cost (one more test function, ~35 lines, <10ms to run).
- Structured Next Steps as exactly ONE item. Gate 5 ("bounded change ...
  the lookback window, and only the lookback window") describes a
  single-scope fix; splitting it into multiple items would have implied a
  multi-part change that doesn't exist here.
- Fixed two stale values encountered while working (worktree venv path in
  `evaluator_command`; the "16" vs measured "23" pre-existing-failure
  count) -- both explicitly permitted by the brief's Hard Rules ("update
  the contract and repo-profile.md if a value there is stale"). Did not
  touch `docs/sprint/repo-profile.md`'s general recipe, since the venv
  issue is worktree-specific, not a repo-wide fact.

No escalations were needed -- no gate conflicted with the code, and no
architectural call had to be made without evidence. The riskiest judgment
call (equivalence test green vs. forced-red) is documented above rather
than escalated, since it's a test-design decision squarely inside the
Planner's authority ("you are the ONLY role permitted to write or modify
test files this sprint") and the brief's own escalation bar ("a gate
conflicts with the code, or you would have to make an architectural call
without evidence") wasn't met -- this was a interpretation-of-instructions
call I could resolve and justify directly.

## Archived from contract (2026-08-12)

Moved verbatim from the sprint contract (`2026-08-10-core-g4-discriminator-perf.md`)
during a contract-hygiene pass to bring the contract under the 400-line
lint budget. Nothing summarized or dropped — each section below is the
exact prior contract text, moved because CI's `sprint contract lint`
lints every contract with frontmatter, not just the active one. The
contract now carries a short summary + pointer to each section here.

### Evaluation Notes

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

### QA Verification Notes (2026-08-10, PASS)

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

### Context Dump (pre-compression, superseded 2026-08-12)

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
