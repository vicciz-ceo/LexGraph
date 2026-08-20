# Log: `2026-08-12-defs-b1-refers-to`

## Planner pass (2026-08-12)

### Loss reproduction, verified against current HEAD (`7af67d8`)

Pulled the real row from the ratified snapshot
(`/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/us_in_statutes.parquet`,
`source_row=80161`, `act_id=STATE_IN_T5_A28_C28_S5-28-28-3`) and ran it
through the real production seam directly (`get_profile("US-IN")`,
`derive_heading_from_body`, `extract_definitions_from_section`,
`extract_local_scope_definitions`). Confirmed:

- `_b1_trigger_colon_or_quote_means(body)` returns `"Definitions"` (the
  colon-list branch matches the row's own `As used in this chapter,
  "loan":` intro) -- B1 recognizes the SHAPE.
- `_extract_inline_quoted_definitions` (a `us_profile.py` function, out of
  this sprint's scope) DOES create a `("loan",)` candidate, but with
  `definition_text = "a loan guarantee made by the corporation."` --
  `_MEANS_IDIOM_GAP_RE`'s own 200-char lazy scan skips past the `(1)
  refers to...` clause (excluded because it contains a `;` the gap regex's
  own `[^;.\n]`-adjacent boundary logic in `_candidate_is_substantive`
  cannot cross) and lands on the `(2) includes` clause instead.
- `preserve_substantive_b1_candidates` then DROPS this candidate entirely:
  `_POST_RELATION.match(tail)` and `_ENUM_RELATION.match(tail)` both
  return `None` on the tail starting `:\n\n(1) refers to...` (no verb in
  either alternation matches "refers to"), and `_bounded_payload` --
  `_candidate_is_substantive`'s fallback path -- stops at the bare `:`
  immediately after the quoted term (the colon precedes a blank line, so
  the "wrapped means/includes on the next line" exception does not apply),
  yielding a non-substantive `":"` payload.
- Net effect: `derive_heading_from_body`'s own B1-winner gate in
  `us_profile.py` (`if not local_candidates and not section_candidates:
  return None`) then returns `None` for the WHOLE row -- today this row
  is not recognized as a Definitions body at all, and persists zero
  definitions, not merely a "loan"-shaped miss among others.
- Confirmed at live-persistence altitude too:
  `ingest_us_statute_rows` + `run_definition_linking` on this exact row
  produces `created_definitions == []`.

### What the fix will actually recover (verified by local simulation only, no repo file touched)

Monkeypatched a plausible widened `_POST_RELATION` in-process only
(`r'...|refers?\s+to)\b'` appended to the verb alternation) and re-ran the
SAME real seam. `derive_heading_from_body` returns `"Definitions"`;
`extract_definitions_from_section` returns exactly one candidate:
`terms=("loan",)`,
`definition_text = "a loan guarantee made by the corporation.\n\nAs added by P.L.222-2007, SEC.1."`,
`scope = "chapter"`. This is because `_POST_RELATION` only decides
KEEP/DROP in `_candidate_is_substantive` -- it does not touch
`definition_text`, which was already fixed by `_extract_inline_quoted_
definitions`'s own (untouched) idiom-gap match on the `(2) includes`
clause. Any reasonable phrasing of the `_POST_RELATION` widening
(`refers?\s+to`, `refers\s+to|refer\s+to`, etc.) produces the SAME
resulting `definition_text`, since the widening only flips the keep/drop
decision, never the boundary. The RED acceptance test
(`test_state_in_loan_refers_to_relation_recovered_live_persistence`)
asserts exactly this text; if a Developer's fix produces a different
`definition_text`, re-verify against this transcript before assuming the
test is wrong.

### Stale-pin sweep: full grep transcript and per-hit disposition

Ran `grep -rniE "refers?\s+to|_POST_RELATION"` across
`backend/tests/unit/`, `backend/tests/integration/`, `backend/tests/e2e/`
(no hits), and `frontend/src/components/__tests__/` (no hits). Every
pre-existing hit outside this pass's own two new files was individually
traced to confirm it either never reaches `_POST_RELATION`/
`_candidate_is_substantive`, or empirically still produces the same
result after the widening:

1. `test_definition_links_core_follow_on_2_g13_pub_l_targeted_guard.py`
   (`test_ar_term_that_itself_contains_amendments_survives_the_guard`,
   AR row whose own defined term is followed directly by "refers to the
   Community Right-to-Know Act..."). SAFE: the file's own
   `test_all_four_rows_raw_headings_are_directly_recognized_not_derived`
   pins `heading_was_derived=False` for this row (raw `section_title` is
   directly `is_definitions_heading`-True) -- `preserve_substantive_b1_
   candidates`/`_POST_RELATION` are gated behind `if heading_was_derived:`
   in `us_profile.py` and are never invoked for this row at all. Confirmed
   the test itself calls `extract_definitions_from_section(text,
   scope="law-wide")` with the default `heading_was_derived=False`.
2. `test_us_core_g3_guard_states_no_regression.py` (NJ "facility" fixture,
   `"means and refers to the real property..."`). SAFE: same
   `extract_definitions_from_section(text, scope="law-wide")` call,
   default `heading_was_derived=False`; also the verb group already
   matches `means` first regardless.
3. `test_mr121_b1_source_truth_red.py`, case
   `R3_dotted_term_ignores_normalized_ordinary_reference` (`'..."cerulean
   savings bank.".\nThis section refers to the term "cerulean savings
   bank" in ordinary prose...'`, asserted `absent`). This ONE goes through
   the real B1 `b1_winner=True` path (`heading_was_derived=True`,
   `preserve_substantive_b1_candidates` IS invoked) -- the closest call in
   the sweep. Verified EMPIRICALLY, not just by regex reasoning: ran this
   exact fixture through `direct_candidates()` (the test file's own
   helper) both unwidened (today) and with the same simulated `refers?\s+
   to` widening in-process. Both produce `candidates == []`. Reason: the
   tail immediately after the closing quote is `.\nThis section refers to
   the term...` -- `_POST_RELATION`'s optional `[^;.\n]{1,160}?,\s*`
   prefix requires a literal comma before the verb group, and there is no
   comma between "This section" and "refers to" in this sentence, so
   neither the widened nor the unwidened regex can bridge the gap. Stays
   correctly `absent`.
4. `test_definition_links_us_heading_variants_d_df.py` line 108: an
   informational docstring line ("Misses defining verbs other than
   means/mean/is defined as, e.g. includes, shall include, refers to, is
   a -- NOT pinned either direction") -- explicitly states no test asserts
   a verdict for "refers to" in that module (a DIFFERENT recognizer,
   `us_heading_variants`, out of this sprint's scope entirely). No
   assertion to break.
5. `test_us_body_preamble_shape7_ca_idiom_other_states_red.py`
   (`test_indiana_winning_rule_is_ca_rule_not_some_other_rule` asserts
   `_b1_trigger_colon_or_quote_means(body) is None` for an Indiana row
   whose text contains `"Board" refers to...`/`"Fund" refers to...`).
   SAFE: `_b1_trigger_colon_or_quote_means` is the bare
   trigger/colon-list/quote-means recognizer -- it never references
   `_POST_RELATION` or `_ENUM_RELATION` (those live one layer up, in
   `_candidate_is_substantive`, called only from `preserve_substantive_
   b1_candidates`). This function's return value is structurally
   independent of the widening; also moot in practice since the CA
   wide-window rule is registered ahead of B1 and already wins first.
6. `test_us_markers_c5guard_class_b_boundary_defects.py`: imports
   `extract_quote_anchored_entries` directly from
   `app.definition_links.rules.us_markers_boundary` -- a different module
   entirely (also the module gate 5 forbids touching).
7. `test_us_markers_c5guard_nj.py`: same NJ "facility" fixture as #2, live
   pipeline path, verb group already matches `means` first.

**Verdict: none re-pointed.** No pre-existing GREEN test pins the current
loss behavior in a way this sprint's widening would break.

### Full backend suite baseline (gate 4)

`PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python -m
pytest backend/tests -q -p no:randomly` (2026-08-12, HEAD `7af67d8` plus
this pass's two new RED test files, nothing else changed):

**1342 passed, 5 failed, 1347 collected.** The 5 failures are exactly this
pass's own new RED tests (2 unit + 3 integration) -- zero pre-existing
tests broke by adding these files. Post-fix, the gate-4 target is **1347
passed / 0 failed** (same collection count; the 5 REDs flip to green).

### Gate 2: executed all-53 acceptance run -- exact commands for the Developer/QA

Tooling: `docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/qa/
measure_actual_production.py` (fixed post P-R16 -- calls the real
production seam, not a hand-copy; see `us_profile.py:capture()`'s own
`registered_b1_winner`/`b1_winner=True` mirroring of pipeline dispatch).
Recipe adapted from the M-R121 acceptance run documented in
`mr118/DEVELOPER_READY.md` (same tool, same three-phase shape: measure
current, measure an archived pre-fix baseline restricted to current's own
membership, then diff).

**This sprint's baseline commit is `qa_g7_common.INTEGRATION_SHA`
(`5c3e75130c9e1d26c8e3448dc85691d12478889c`)**, NOT the old `5753e11`/
`5753e11` M-R121 pin -- production has not moved since that SHA merged
(confirmed: `git merge-base --is-ancestor 5c3e751 HEAD` holds and
`git diff 5c3e751..HEAD -- backend/app` is empty on this Planner's HEAD),
so it is exactly this sprint's pre-fix state, already certified at mr124
(345 changed = 341 removed + 4 added, `db52f060...bb1778`).

```bash
(
set -euo pipefail
REPO=$(git rev-parse --show-toplevel); cd "$REPO"
BASE_SHA=5c3e75130c9e1d26c8e3448dc85691d12478889c   # qa_g7_common.INTEGRATION_SHA, pre-fix
git cat-file -e "${BASE_SHA}^{commit}"

PY=/Users/nerya/LexGraph/backend/.venv/bin/python
MEASURE=docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/qa/measure_actual_production.py
SNAPSHOT=/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad

RUN=$(mktemp -d /tmp/b1-refers-to-acceptance.XXXXXX)
mkdir -p "$RUN/current" "$RUN/baseline-src" "$RUN/baseline" "$RUN/compare"
printf 'artifacts: %s\n' "$RUN"

git archive "$BASE_SHA" | tar -x -C "$RUN/baseline-src"

# CURRENT = post-fix working tree (run this AFTER the Developer's one-file change)
PYTHONPATH=.:backend "$PY" "$MEASURE" --snapshot "$SNAPSHOT" --source-root "$REPO" \
  --out "$RUN/current" --current

# BASELINE = archived pre-fix source, restricted to CURRENT's own membership
PYTHONPATH=.:backend "$PY" "$MEASURE" --snapshot "$SNAPSHOT" --source-root "$RUN/baseline-src" \
  --members "$RUN/current/members.jsonl" --out "$RUN/baseline"

cat "$RUN/current/summary.json"
cat "$RUN/baseline/summary.json"
)
```

Note what this recipe deliberately does NOT do: it does not invoke
`measure_actual_production.py --compare`, because that mode enforces a
HARD-CODED certified hash (`EXPECTED_CHANGED`/`EXPECTED_CHANGED_HASH`
constants in the script) baked in from the LAST executed M-R124 run --
there is no pre-existing certified ledger for THIS sprint's incremental
delta, and P-R11/this sprint's own gate 2 forbid hand-authoring one. QA
must instead diff `$RUN/current/records.jsonl` against
`$RUN/baseline/records.jsonl` directly (same `key()` tuple the script's
own `compare()` uses: `jurisdiction, source_file, source_row, term,
definition_text, scope`) to produce the actual changed set, THEN
adjudicate every changed key at ANCHOR granularity (decompose remove+add
pairs on the same `(row, term)` first per gate 2's own text) rather than
comparing against any pre-written expectation. Expected shape per the
mandate: exactly one net anchor gain (`STATE_IN_T5_A28_C28_S5-28-28-3`,
"loan") and nothing else changed, since `_POST_RELATION` widening only
flips keep/drop decisions for candidates that were ALREADY being computed
identically before and after.

### Gate 3: deletion-side relation screen -- re-run methodology

No script for `removal_relation_screen.jsonl` was committed (it was an
ad hoc one-off at the time of the `00b5b5c` fix, per that commit's own
message: "Screening all 364 certified removals found 26 where the quoted
term is immediately followed by an explicit defining relation"). Re-derive
the same check against gate 2's new "removed" set: for each removed
`(row, term)`, locate the quoted term's occurrence in the row's raw
source text and test whether `_POST_RELATION.match(tail)` or
`_ENUM_RELATION.match(tail)` (POST-FIX vocabulary) matches the text
immediately following the quote. Zero should match; any match is a
suspect requiring the same adjudication `removal_relation_screen_
summary.json`'s schema already models (`removals_relation_adjacent_
SUSPECT`, `suspects_never_adjudicated`).

### INTEGRATION_SHA re-pin trap (named in the contract, restated here)

Once the fix commit lands, `qa_g7_common.INTEGRATION_SHA` MUST be re-pinned
to a SHA that is ancestral to the fix and has `backend/app` unchanged after
it (i.e., the fix commit itself, or later), and all G7 evidence under
`docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/g7-certification-
evidence/` regenerated. Skipping this makes `validate_integration()`
fail-close on every subsequent G7/D-PFP-400 run without measuring
anything -- the exact trap the program handoff already names.

## Agent roster (manager bookkeeping, append-only)

- planner → ad62ef5b860ca7578 (spawned 2026-08-12T10:26Z, exited clean @ f9961c9)

## Gate-2 escalation + director ruling (2026-08-12, manager)

Developer completed the fix (86fccfb; gates 1/4/5/6 green) and executed the
all-53 run per the recorded recipe. Raw delta: 4,255 changed records /
3,584 distinct (row,term) anchors / 42 jurisdictions (3,542 added, 713
removed; 671 anchors remove+add on the same key, 586 of the 713 removals in
US-MI; ~42 removal-only records). Developer escalated per the >dozen-keys
stop rule without adjudicating or committing gate-2 bookkeeping.

DIRECTOR RULING (AskUserQuestion, 2026-08-12): **Investigate before QA** —
diagnose WHY US-MI captures got their text replaced and sample the
additions for genuineness BEFORE any QA cycle runs. INTEGRATION_SHA re-pin
and contract advancement stay on hold. Manager committed the compare
artifacts + scripts as evidence (full 376M/398M corpus outputs gitignored,
preserved on disk under run/current + run/baseline).

- developer → a4af3fdce965b77ed (spawned 2026-08-12T10:55Z, escalated clean @ 86fccfb)
