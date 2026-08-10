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
