---
id: "2026-08-10-core-g4-discriminator-perf"
status: planned
current_role: developer
branch: claude/core-g4-discriminator-perf
locked_by: null
locked_at: null
last_agent: "claude-code:planner"
last_updated: "2026-08-10"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "cd /Users/nerya/LexGraph-wt/core-g4-perf && PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python -m pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 1
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
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

### Item 1: bound `_citation_or_xref_context`'s five suffix-regex probes to a fixed lookback window

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

_(empty)_

## Completed

_(empty)_

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
