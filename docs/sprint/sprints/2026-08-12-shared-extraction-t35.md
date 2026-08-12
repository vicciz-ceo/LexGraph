---
id: "2026-08-12-shared-extraction-t35"
status: planning
current_role: developer
branch: claude/shared-extraction-t35
locked_by: null
locked_at: null
last_agent: "claude-code:planner"
last_updated: "2026-08-12T05:20:23Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python -m pytest backend/tests -q -p no:randomly && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 1
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
lint: "PASS 282 2026-08-12T05:20:39Z"
previous_sprint: "2026-08-10-green-the-suite"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
---

# Sprint: shared extraction — stop capturing section-label headings as terms

## Mandate

This is the **last failing test on PR #20**. Everything else is green: backend
1338 passed / 1 failed, frontend passing, contract lint passing across every
contract.

`USC_T35_C4_S41` persists a definition whose term is the section label
**`"SEC. 804. DEFINITION."`**, scope law-wide, carrying an **8,431-character**
bleed. The row's real content — a `Director means ...` clause — is not captured
at all.

So this row is wrong in both directions at once:

- **a phantom**: a heading is captured as a definiendum (D-MAP's blocking class —
  the anchor points at something that is not a defined term)
- **a miss**: the genuine definition is absent (D-RECALL-FP's expensive class)

Gate:
`backend/tests/integration/test_us_body_preamble_defining_verb_narrowing_red.py::test_usc_t35_c4_s41_wrong_tuple_needs_shared_extraction_p_fp_debt`

## Why it was deferred, and why that no longer applies

The test's own docstring calls it *"held shared-extraction/P-FP debt, not a
Developer gate in this bounded B1 sprint,"* and program ruling **P-R14** put this
class out of scope for the panel that found it. Both were correct at the time:
the B1 sprint could not edit shared extraction.

The director has now directed that it be fixed, in its own sprint, with its own
measurement. That is this sprint.

## The hazard on the record — read before proposing anything

A previous attempt at this class was **rejected under M-R64** for narrowing the
capture window in a way that dropped other genuine definitions. This file carries
10 passing guards that exist because of it.

The failure mode to avoid is precise: a fix that suppresses the phantom by
tightening what counts as a definiendum, and in doing so silently stops capturing
real definitions elsewhere in the corpus. That trade is not acceptable — it swaps
a visible defect for an invisible one, which is the pattern this program has been
correcting all week.

## Acceptance gates (manager-defined)

1. **The phantom is gone.** `USC_T35_C4_S41` no longer persists a section-label
   heading as a term.
2. **The real definition is captured.** The row's genuine `Director means ...`
   clause becomes an anchor. Gate 1 alone is satisfiable by suppression; this
   gate is what distinguishes a fix from a mute.
3. **Nothing else is lost.** Corpus-wide, measured: no term that is captured
   today may disappear. This is the M-R64 gate and it is the one that matters.
4. **No regression.** Backend stays at 1338 passed with this test flipping to
   green — 1339 passed / 0 failed. Frontend and contract lint stay green.
5. **Bounded.** Shared extraction only. Do not touch the citation-window perf
   fix, the #21 discriminator, or the compound-idiom guard — all three are
   QA-certified this week.

## Related, and worth checking for a common cause

Three open issues plausibly share this seam. If one change closes more than one,
that is a better outcome than four patches — but it must be shown, not assumed:

- **#19** — `refers to` missing from the defining-verb vocabulary, drops a
  definition
- **#26** — `classify_correctly_empty` has no production call-site
- **#27** — 41 definitions run to end-of-text because no boundary idiom
  (`shall include`) is recognised, then die on the length ceiling

## Next Steps

Single-track — one function, one root cause, both symptoms. See "Planner
findings" below for the full evidence; splitting this across two agents
would repeat the exact disconnect M-R64 rejected (a Developer fixing the
capture side without visibility into what else the same window touches).

### Item 1 (RED, both gates authored this pass) — fix `_extract_inline_quoted_definitions`'s quote handling in `us_profile.py`

**Root cause** (see "Planner findings"): `_QUOTE_TERM_RE`
(`backend/app/definition_links/us_profile.py:924`) pairs the first `"`/`"`
after a candidate start with the NEXT such character, with no awareness
that a multi-paragraph quoted excerpt re-opens `"` at the start of EVERY
paragraph (only the last one closes), and no support for a definiendum
delimited by single `'...'` quotes nested inside such a block. Both fix
this ONE regex/function's quote-pairing and quote-character handling —
do not add a second, narrower mechanism alongside it (that shape is
exactly what M-R64 rejected).

Acceptance criteria, in this order:
1. `PYTHONPATH=.:backend .venv/bin/python -m pytest backend/tests/integration/test_us_body_preamble_defining_verb_narrowing_red.py -q -p no:randomly`
   — all 12 tests green, including the two gate tests this Planner pass
   added/corrected (`test_usc_t35_c4_s41_wrong_tuple_needs_shared_extraction_p_fp_debt`,
   now asserting the phantom term specifically rather than an empty list —
   see "Planner findings" for why — and the new
   `test_usc_t35_c4_s41_director_definition_not_yet_captured_needs_shared_extraction_p_fp_debt`)
   and the 10 pre-existing M-R64 regression guards in the same file.
2. Corpus-wide blast radius (gate 3), using this Planner's tooling in
   `docs/sprint/sprints/2026-08-12-shared-extraction-t35-scripts/`:
   run `measure_inline_fallback_population.py --out before.jsonl` on
   pre-fix HEAD, implement the fix, run it again `--out after.jsonl`, then
   `diff_before_after.py before.jsonl after.jsonl` must exit 0 (no term
   present before and absent after for the same `(code, act_id)`). See the
   scripts' own docstrings for the two-stage cost design (full corpus,
   unoptimized, is many hours — the cheap Stage-1 prefilter narrows before
   the expensive real-pipeline gate runs). **Nuance**: a handful of OTHER
   rows already show this exact phantom shape today (e.g. `USC_T51_C203_S20301`,
   `USC_T31_C15_S1535` — a subsection heading or mid-clause fragment
   captured as a "term", found incidentally during this Planner's tooling
   validation, not investigated further — out of this sprint's bounded
   scope). If the fix's corpus-wide effect touches any of these, a
   disappearing term must be individually judged genuine-vs-phantom before
   counting it as a gate-3 regression — do not treat "term count identical"
   as the bar, and do not treat "some other row's term also changed" as
   automatic permission to wave it through either. Flag any such row to
   QA explicitly rather than silently absorbing it.
3. `PYTHONPATH=.:backend .venv/bin/python -m pytest backend/tests -q -p no:randomly`
   — 1340 passed / 0 failed (1338 baseline + the 2 tests this pass added
   to the narrowing-red file). Frontend (`npm --prefix frontend run test -- --run`,
   `npm --prefix frontend run typecheck`) and contract lint stay green
   (unaffected by this file, but part of the sprint's own evaluator
   command — verify, don't assume).
4. `git diff main -- backend/app/` touches only
   `backend/app/definition_links/us_profile.py`. Confirm no incidental
   edit to `_citation_or_xref_context`, the #21 discriminator machinery in
   `us_markers_boundary.py`, or the compound-idiom guard — all three
   QA-certified this week and out of bounds per the sprint's hard rules.

Files likely affected: `backend/app/definition_links/us_profile.py`
(`_QUOTE_TERM_RE`, `_extract_inline_quoted_definitions`) only.

Not this item's job: #19 (defining-verb vocabulary gap, `us_markers_
boundary.py`), #26 (`classify_correctly_empty` dead code, `correctly_
empty.py`), #27 (`MAX_CLEAN_DEFINITION_LENGTH` ceiling + idiom recognition,
`us_markers_boundary.py`) — none share this root cause; see "Planner
findings" for the evidence. FX7 (#27) was separately already ruled "not
buildable as framed" in `2026-08-10-green-the-suite`.

## Dev Complete

_None._

## Completed

_None._

## Planner findings (this pass, sprint `2026-08-12-shared-extraction-t35`)

**Root cause, read and run live** (not inferred from the docstring):
`_extract_inline_quoted_definitions` (`us_profile.py:995`) is the CA/GA/IL
"heading-was-derived" inline fallback, now also reached for this federal
row via B1's own `heading_was_derived=True` path
(`USProfile.derive_heading_from_body`, `us_profile.py:2545`). Its
`_QUOTE_TERM_RE` (`us_profile.py:924`, `["“]([^"”]{1,200})["”]`) finds the
row's real quoted historical note — `"SEC. 804. DEFINITION.\n\n"In this
title, the term 'Director' means the Under Secretary of Commerce...
Trademark Office."` — and pairs the OPENING `"` before `SEC. 804.
DEFINITION.` with the RE-OPENING `"` that starts the NEXT paragraph (the
standard legal convention: each paragraph of a multi-paragraph quotation
re-opens `"`, only the LAST one closes). That false pairing captures the
heading as `term`; the immediately-following text ("In this title, the
term 'Director' means...") then satisfies `_MEANS_IDIOM_GAP_RE`
(`us_profile.py:960`), so an entry starts right after "means ", and — since
this is the ONLY `_QUOTE_TERM_RE` match in the whole 89,380-char body that
passes the idiom-gap check (confirmed live: 157 quote-pair matches total,
1 passes) — its `definition_text` runs to end-of-body: the 8,431-char
bleed. Confirmed by direct call: `_extract_inline_quoted_definitions`
returns exactly one candidate, `('SEC. 804. DEFINITION.',)`, matching the
persisted row byte-for-byte.

The genuine `'Director'` clause is invisible for a SEPARATE reason inside
the SAME regex: `_QUOTE_TERM_RE` only recognizes `"`/curly-quote
delimiters. `'Director'` is delimited by single ASCII apostrophes — the
real, common convention for a term nested inside an already-double-quoted
block (using a double quote again would prematurely close the outer
quotation). One regex, one function, two symptoms: naive quote-pairing
produces the phantom; the same regex's double/curly-only quote-character
restriction produces the miss.

**Gate-2 RED test authored** (M-R107-compliant — see the test's own
docstring): `test_usc_t35_c4_s41_director_definition_not_yet_captured_
needs_shared_extraction_p_fp_debt` in `test_us_body_preamble_defining_
verb_narrowing_red.py`. Reads the row's own real sentence and the
unrelated editorial-note fragment that follows it directly off the
fixture text (not hardcoded/retyped), then asserts `'Director'` is
captured, the real sentence is in its `definition_text`, and the
unrelated `"[Pub. L. 111"` bleed marker is NOT — verified RED for the
right reason (assertion failure on `'Director' not in persisted`, no
exception).

**Gate-1 test corrected, also verified still RED for the right reason**:
the pre-existing `test_usc_t35_c4_s41_wrong_tuple_needs_shared_extraction_
p_fp_debt` asserted `created_definitions == []`. That is stricter than
this sprint's own gate-1 contract text ("no longer persists a
section-label heading as a term") and is logically UNSATISFIABLE together
with gate 2 once `'Director'` is genuinely captured from the same row —
`created_definitions` for `USC_T35_C4_S41` can never be empty AND contain
`'Director'` at the same time. Narrowed to check specifically that
`'SEC. 804. DEFINITION.'` is absent from the captured terms; still RED
today (same underlying defect, corrected assertion). No test was deleted,
skipped, or weakened — the corrected assertion is strictly what gate 1's
own contract text requires, documented in the test's own docstring with
the reasoning above.

**Shared-seam assessment (#19/#26/#27) — measured, not assumed, per the
director's ask**: none share this root cause.
- **#19** (`refers to` missing from the defining-verb vocabulary) lives in
  the compound-idiom/`_TIGHT_IDIOM_RE` machinery in `us_markers_
  boundary.py` — a vocabulary-breadth gap in a DIFFERENT file's idiom
  matcher, not a quote-pairing/quote-character defect.
- **#26** (`classify_correctly_empty` has no production call-site) is a
  standalone pure classifier in `correctly_empty.py` with zero pipeline
  wiring — confirmed via `grep`, its only callers are tests. Nothing to
  do with quote-term extraction at all.
- **#27** (41 definitions run to end-of-text, no `shall include` boundary
  idiom, die on the length ceiling) lives in `us_markers_boundary.py`'s
  `close_entries`/`MAX_CLEAN_DEFINITION_LENGTH` — a DIFFERENT function,
  DIFFERENT file, different mechanism (marker/digit-paren entry closing +
  a hard length ceiling, vs. this defect's naive quote-character pairing
  in the marker-free inline fallback). Already independently investigated
  and ruled "not buildable as framed" in `2026-08-10-green-the-suite`
  (FX7): QA reproduced live that any ceiling widening broad enough to
  recover the 41 lost terms is broad enough to break the guard's real
  purpose.

**Blast-radius spot-check (this Planner, bounded — NOT the gate-3
measurement itself)**: on the first 4,000 rows of `us_federal_statutes.
parquet` (54,853 rows total), 239 rows (5.98%) currently persist >=1 term
sourced from `_extract_inline_quoted_definitions` (950 terms total) via
the real, gated pipeline dispatch (mirrors `pipeline.py` lines 246-347
directly, not reimplemented). This is a real, non-trivial population, not
an edge case limited to one row — consistent with the M-R64 hazard's own
framing. Timing, measured live on the same sample: the real gated check
costs ~32ms/row (128.8s/4,000); a cheap, ungated direct call to the same
function costs ~0.4ms/row (1.5s/4,000) and is a provable superset. Full
corpus-wide (~2.05M rows, all 105 files) at the naive per-row rate is
tens of hours — not tractable as a single unoptimized pass. Tooling
built and validated this pass (see Item 1, criterion 2) applies the cheap
pass first, full corpus, before running the expensive real-pipeline check
only on the narrowed candidate set.

**Feasibility**: buildable. No evidence found that fixing this window
requires trading away other genuine captures — the phantom and the miss
share one narrow, well-understood mechanism (a quote-pairing/quote-
character defect in one regex), not a recognition-window tradeoff of the
M-R64 shape. The real cost is measurement TIME (multi-hour corpus-wide
gate-3 run), not a structural conflict between the two required
outcomes.

## Context Dump

Sprint opened by the program manager off PR #20's head `fe0ef30`; gate-1
test already RED/committed. This Planner pass read+ran the row live,
confirmed root cause (see "Planner findings"), authored gate-2's RED
test, corrected gate-1's stale `== []` assertion, ruled out #19/#26/#27
as sharing this seam, and built+validated a corpus-wide blast-radius
tool. Suite: 1338 passed / 2 failed (both gate tests, genuinely RED).
`backend/app/` untouched this pass. Handing off to `current_role:
developer`; full detail lives in "Planner findings", not here.
