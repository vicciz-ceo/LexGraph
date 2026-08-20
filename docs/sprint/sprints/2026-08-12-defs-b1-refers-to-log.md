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

**Developer-pass correction (2026-08-12, post gate-2 execution):** the
`--members`-restricted baseline invocation above is WRONG and must not be
re-run as recorded. `measure_actual_production.py`'s `capture()` gates
`recognized_by_registered_rule` on its own `--current` flag, but real
production (`pipeline.py:262-266`) computes that value unconditionally --
running BASELINE without `--current` invokes a calling convention no
production commit ever executed, and produced a 4,255-record artifact
delta (3,584 anchors) that was 99.97% measurement noise, not the fix's
effect. Full mechanism, verification, and the corrected single-record
delta: `docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/investigation.md`.
Corrected recipe: both CURRENT and BASELINE run with `--current`; the
script's own CLI forbids combining `--current` with `--members`, so
BASELINE determines its own membership via `--current`'s
`registered_b1_winner()` path (enforced against the same
`EXPECTED_MEMBERS_HASH` the script already certifies under `--current`)
rather than being restricted to CURRENT's `members.jsonl`. See the
corrected `run_gate2.sh` under the same scripts directory.

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

## Developer pass 2 — escalation resolution, corrected gate-2, G7 re-pin (2026-08-20/21)

Manager relayed the completed investigation (`a6eae82`,
`docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/investigation.md`):
the 4,255-record delta was a measurement-tool artifact, not the fix's
effect. `measure_actual_production.py`'s `capture()` gates
`recognized_by_registered_rule` on its own `--current` CLI flag; real
production (`pipeline.py:262-266`) computes the same value
unconditionally. `run_gate2.sh` ran CURRENT with `--current` but BASELINE
without it — a calling convention no production commit ever executes.
Verified corpus-wide (all 2,953 touched rows): 2,952/2,953 byte-identical
under the true `--current` convention on both source trees; the sole
exception is the intended `US-IN` row 80161 "loan" recovery. Verdict
checked against the investigation's own evidence before acting (matched
independent reading of `capture()`'s source during the original gate-2
run).

Actions taken, in order:

1. `git reset --hard origin/claude/defs-b1-refers-to` to `a6eae82` (worktree
   sync per the resume instructions).
2. Corrected `run_gate2.sh`: BASELINE now also passes `--current`. The
   script's own CLI forbids `--current` + `--members` together
   ("current run needs no --members; baseline run requires it"), so
   BASELINE determines its own membership via `--current`'s
   `registered_b1_winner()` path instead of being restricted to CURRENT's
   `members.jsonl`; the script's built-in `EXPECTED_MEMBERS_HASH` check
   (enforced only under `--current`) would fail loudly if that membership
   ever diverged — it did not (`851e85dc...` identical both runs).
   Log-doc recipe above annotated with a correction note citing
   investigation.md (does not rewrite the Planner's original recorded
   text).
3. Re-ran ONLY the baseline side under the corrected convention (CURRENT's
   existing output, produced WITH `--current` in the original run, was
   reused unchanged). Corrected diff: **exactly 1 changed record** —
   `US-IN us_in_statutes.parquet row 80161 "loan"`, added, `definition_text`
   identical to the Planner's original simulation transcript. Matches the
   contract's original "expected shape" exactly, once measured correctly.
4. Replaced `run/compare/{changed.jsonl,summary.json}` in place (old
   4,255-record version preserved in git history at `75c030a`); appended a
   correction entry to `run/run.log`. Committed `dc5faed`.
5. `qa_g7_common.INTEGRATION_SHA` re-pinned `5c3e751...` → `86fccfb`
   (the fix commit itself; `git diff 86fccfb..HEAD -- backend/app` empty,
   confirmed ancestral) — verified this points at the actual production-code
   commit, not a bookkeeping commit, per the resume instructions' explicit
   check. Ran `run_g7_certification.py` (Q-D1 → independent Q-D2 → Q-D3)
   into a scratch `--out`, then `export_compact_evidence()` into the
   checked-in `g7-certification-evidence/`. Result: **G7 CERTIFICATION
   PASS**, `qd3_crosscheck.json` `status: "PASS"`,
   `summary_hash=2057f6dc79df615bc0591d5b112757ed109add34e1bf2002e432724c8fa1a76c`,
   both G7 minimum gates pass (`ga_after_pass`, `new_primary_pass`).
   Committed `816f63d`. (Wall-clock for this step read ~1h28m in `ps`
   because the machine slept mid-run; actual CPU time was ~10 min per full
   pass — process was never dead, contra a stale manager status snapshot
   taken during the sleep window; confirmed alive via direct `ps` check
   before re-arming the monitor rather than restarting the run.)
6. Contract: Item 1 moved to Dev Complete, `status: dev-complete`,
   `current_role: qa`, `dev_complete_items: 1`; lock fields untouched.

**Not yet done — explicitly QA's next step, not Developer's:** gate 3's
deletion-side relation re-screen has not been re-run against the corrected
1-record delta (trivial at this size, but out of Developer scope per the
brief — Developer produces the raw delta, does not adjudicate). Full
gate-by-gate sign-off is QA's.

Full backend/frontend re-verification this pass: unchanged from the
original developer pass (86fccfb already had 1347/0 backend, 165/165
frontend, clean typecheck before the escalation; no backend/app or
frontend source changed since, only docs/scripts) — not re-run, since
nothing in scope for full-suite results changed.

- developer → (same worktree session, resumed after escalation + 2 machine
  sleeps, exited clean @ 816f63d)
- investigator (read-only recon, Sonnet high) → a734e9b202e545ee7 (spawned 2026-08-12, delivered investigation.md @ a6eae82)
- lock handover developer→qa 2026-08-21T00:35Z by manager after diff verification (production hunk = 1 line in us_body_preamble_b1.py, module 298 lines, zero test files in dev commits)

## QA pass 1 (2026-08-21) — full gate-by-gate independent re-verification

Independent agent from Planner/Developer. Ran every gate from scratch
rather than reusing recorded numbers, per the QA brief.

**Gate 4 (evaluator).** `PYTHONPATH=.:backend .../python -m pytest
backend/tests -q -p no:randomly`: **1347 passed, 0 failed, 1347 collected**
(29.69s). `npm --prefix frontend run test -- --run`: **165/165 passed**.
`npm --prefix frontend run typecheck`: clean, zero output. All green on
first run — no flakes to report.

**Gate 6 (red-before-green provenance).** `git show --stat f9961c9`
confirms both new test files (`test_us_body_preamble_b1_refers_to_
relation_red.py`, `test_us_body_preamble_b1_refers_to_relation_
persistence_red.py`) were committed there, before the fix; `git show
--stat 86fccfb` confirms the fix touches zero test files;
`git merge-base --is-ancestor f9961c9 86fccfb` holds. Read the persistence
test: it imports and drives the real production seam
(`ingest_us_statute_rows` + `run_definition_linking`, reading back
`Definition` rows via `db_session.get`) — not a mock. Independently
**re-ran the actual regression**: backed up
`us_body_preamble_b1.py`, overwrote it with the f9961c9 (pre-fix) content
via `git show f9961c9:<path>`, ran both new test files —
**5 failed / 2 passed**, matching the Developer's own claimed transcript
exactly (2 passes = the two "referring to" gerund negative controls, one
per altitude). Restored the file via `git checkout --`, byte-diffed
against the backup to confirm a clean restore, then re-ran the same two
files against current (post-fix) HEAD: **7 passed**. M-R107: all CASES use
novel jurisdictions (US-WY/US-NM/US-VT) and terms never seen elsewhere.

**Gate 5 (boundedness).** `git show --stat 86fccfb`: exactly 1 file
(`us_body_preamble_b1.py`), 1 line changed (adds `refers?\s+to|` to the
verb alternation, nothing else). Module is 298 lines (≤300). No commit
after `86fccfb` touches `backend/app` at all (`git log --oneline
86fccfb..HEAD -- backend/app` empty). Note: the brief's literal
`git diff f9961c9..86fccfb` spans 3 commits (2 docs-only lock-handover
commits sit between the RED-test commit and the fix commit), so that
2-dot diff shows 3 files total — but the FIX commit itself (`86fccfb`
alone) is exactly the 1 allowed file / 1 line, and the 2 intervening
commits (`4b00fc7`, `362d4db`) touch only `docs/sprint/sprints/*.md`.
Gate 5's substance (module scope + line budget + no post-fix backend/app
drift) holds regardless of this minor brief imprecision.

**Gate 2 (executed certificate).** Read `run_gate2.sh`: both CURRENT and
BASELINE now pass `--current`, per the corrected convention.
`run/run.log` ends `GATE2_CORRECTED_RUN_COMPLETE`; the corrected baseline
re-run reports `members_sha256` identical to current's
(`851e85dc81d6f9657a80cd2ae6d94d2c6289068932d9274288a45c926236af5a`),
confirming dispatch/membership is unchanged by the fix. Read
`run/compare/summary.json` (`added:1, removed:0, changed:1`) and
`changed.jsonl` (single row: `US-IN us_in_statutes.parquet row 80161
"loan"`, added). **Independently recomputed** the diff myself, reading
only `run/current/records.jsonl` and `run/baseline/records.jsonl`
(read-only, no regeneration) with a standalone script using the same
`key()` tuple as `diff_gate2.py` — got the identical result (0 removed, 1
added, same record). **Adjudicated the record**: loaded the real Indiana
row 80161 directly from the ratified snapshot parquet
(`us_in_statutes.parquet`) — `act_id` and `section_title` match, and the
raw text is exactly `Sec. 3. As used in this chapter, "loan": (1) refers
to a loan made by the corporation...; and (2) includes a loan guarantee
made by the corporation. As added by P.L.222-2007, SEC.1.` — the
certified `definition_text` ("a loan guarantee made by the corporation.
As added by P.L.222-2007, SEC.1.") is a faithful substring of the row's
own limb-(2) text, term "loan" is the row's own quoted term. Cross-checked
`investigation.md`'s central claim (the `capture()` `current`-flag
asymmetry vs. `pipeline.py`'s unconditional computation) by reading both
functions directly — confirmed byte-for-byte: `pipeline.py:262-266`
computes `recognized_by_registered_rule` unconditionally,
`measure_actual_production.py:151-153` gates it on `current`. Convention
correction trusted; did not re-run the full corpus.

**Gate 3 (deletion-side screen).** Corrected delta has 0 removed records
(confirmed above, both from the committed certificate and my own
recomputation) — but RAN the recorded screen anyway rather than assuming:
wrote a standalone script that iterates the corrected delta's removed set
(empty), confirms the loan row is present in ADDED and absent from
REMOVED (i.e. it "cleared"), and tests `_POST_RELATION`/`_ENUM_RELATION`
against any removed row's quoted-term tail. Result: 0 removed, 0
suspects, loan row confirmed cleared — script printed
`GATE3_RESCREEN_COMPLETE`.

**Gate 1.** Confirmed via gates 2+4: the live-persistence RED test
(`test_state_in_loan_refers_to_relation_recovered_live_persistence`) is
GREEN post-fix (I re-ran it directly, see gate 6), and the gate-2
certified corpus-wide run shows exactly the Indiana "loan" row recovered,
matching the mandate's SINGLE genuine loss.

**G7 re-pin check.** `qa_g7_common.INTEGRATION_SHA ==
"86fccfb1d2d6e3bcf93899b67ac97b71ed30d425"` (grep-confirmed). Ran
`validate_integration()` directly (the fast, bounded runnable check named
in the contract's "known trap") — **PASS** (SHA is ancestral, `backend/app`
unchanged since). Did NOT re-run the full `run_g7_certification.py`
Q-D1→Q-D2→Q-D3 corpus pass (53 files / 2M rows; the Developer's own pass
logged ~10min CPU but risked long wall-clock due to unpredictable machine
sleep) — instead verified the committed evidence: `git log` confirms
`g7-certification-evidence/` was regenerated by commit `816f63d`, and
`qd3_crosscheck.json` reads `"status":"PASS"`,
`"integration_sha":"86fccfb1d2d6e3bcf93899b67ac97b71ed30d425"`,
`"summary_hash":"2057f6dc79df615bc0591d5b112757ed109add34e1bf2002e432724c8fa1a76c"`
— matching the log doc's claimed values exactly.

**Regression tests.** Added
`backend/tests/integration/test_qa_regression_defs_b1_refers_to.py` (11
tests, 3 altitudes: direct `_POST_RELATION` regex pins including two new
negative guards — "with reference to" and a partial-word "refers toon" —
not covered by the Developer's own tests; direct-profile altitude with
fresh jurisdictions US-OR/US-ME and terms "credit voucher"/"service
credit"/"audit referral"; live-persistence altitude for the "credit
voucher" recovery and the "audit referral" gerund negative control).
Every case verified empirically against post-fix production code before
being committed. Full backend suite with the new tests: **1358 passed, 0
failed**. Committed `7718f7b`, pushed.

**Verdict: Item 1 PASS.** All 6 gates independently confirmed, no defects
found. Contract updated: Item 1 → Completed, `status: review`,
`current_role: planner`, `completed_items: 1`, `dev_complete_items: 0`,
`qa_cycles: 1`. `locked_by`/`locked_at` left untouched (manager-owned).

- qa (Sonnet high) → this session, exited clean
