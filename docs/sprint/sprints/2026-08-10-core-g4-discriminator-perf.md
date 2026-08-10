---
id: "2026-08-10-core-g4-discriminator-perf"
status: planning
current_role: planner
branch: claude/core-g4-discriminator-perf
locked_by: null
locked_at: null
last_agent: "claude-code:program-manager"
last_updated: "2026-08-10"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
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

## Next Steps

_(Planner fills this in.)_

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
