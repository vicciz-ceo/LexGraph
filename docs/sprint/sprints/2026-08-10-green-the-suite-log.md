# Sprint log — 2026-08-10-green-the-suite

Planner triage pass. HEAD verified at `2afb947` before starting. Reproduced
`23 failed / 979 passed` exactly matching the contract's known-scope list via
`PYTHONPATH=.:backend backend/.venv/bin/python -m pytest backend/tests -q
--tb=no -p no:randomly`.

Each verdict below was reached by running the underlying row through the real
code (`extract_quote_anchored_entries` directly, or the full
`ingest_us_statute_rows` → `run_definition_linking` pipeline), not by reading
the test's name or docstring, per the triage rule. Question asked of every
one: is the `(row, term)` key present in the output (anchor exists, capture
merely imperfect → XFAIL) or absent entirely (anchor lost → FIX)?

## c5guard class-B cluster — 16 tests, XFAIL, issue #21

File: `test_us_markers_c5guard_class_b_boundary_defects.py`. Ran
`extract_quote_anchored_entries` directly on all 16 (fixture, act_id, term)
triples via a throwaway script. Result: **every one of the 16 terms is
present** in the returned dict (`present=True` for all), each with real,
non-trivial captured text — confirming the docstrings' own claims exactly
(byte-for-byte match on every truncated tail / stub / leaked marker chain
inspected). None is a missing key. Symptom breakdown, all one mechanism
(parenthesized/bare-digit token vs. entry-marker ambiguity in
`us_markers_boundary.py`):
- **Citation tail truncated (9)**: `facility` (loses trailing `" 3"` off `s.
  3.`), `Between merchants` (`s. 2-` → missing `104.`), `Commercial unit`
  (`s. 2-` → missing `105.`), `sale at retail` (`57-39.2-` → missing `12.`),
  `Air carrier transportation property` (`57-` → missing `32.`), `Centrally
  assessed property` (`57-` → missing `32.`), `Commercial property`
  (`...and` → missing `14.`), `Nonprimary residential property`
  (`...subsection` → missing `12.` and the period, entirely absent).
- **Stops after first sub-item (4)**: `Bundled transaction`, `Gross
  receipts`, `Agricultural property`, `Franchise` — each definition's own
  `(2)`/`(3)` continuation is dropped because the sub-item marker is misread
  as a sibling top-level entry.
- **Next-entry marker chain leaks (3)**: `Farm machinery repair parts` (own
  sentence complete, then leaks `"12. a."`), `Commissioner` (leaks `"5.
  a."`), `Rule` (leaks `"14. a."`).
- **Truncated to a stub (1)**: `gallon` — captured text is the 3-char
  `'one'`, the `(1)` inside `means one (1) United States standard gallon`
  misread as a boundary.

Verdict: XFAIL for all 16. Anchor present in every case; only the boundary is
wrong. Matches the contract's own hypothesis for this cluster. Root cause
(one shared mechanism) and node ids filed as GitHub issue
[#21](https://github.com/vicciz-ceo/LexGraph/issues/21); explicitly
core-follow-on-3 territory per the file's own `## M33` note, not this
sprint's to fix.

## ext_a — OK gap-idiom — 1 test, FIX

`test_us_markers_ext_a_ok_gapidiom.py::test_real_pipeline_recovers_ok_gap_idiom_definition`.
Ran the real `ingest_us_statute_rows` → `run_definition_linking` pipeline on
`STATE_OK_T47_S47-157.5`. Result: `by_term == {}` — zero `Definition` rows
created, the `person` anchor is entirely absent. The tight-idiom gate in
`extract_quote_anchored_entries` does not bridge the interposed `"as used in
this act"` clause between the quoted term and its verb, and no OK-scoped gap
rule exists. Verdict: **FIX** — genuine anchor loss. Sprint item defined
below with this node id as its gate.

## ext_b_nm — 1 test, FIX

`test_us_markers_ext_b_nm.py::test_real_pipeline_recovers_all_five_nm_lettered_definitions_end_to_end`.
Ran the real pipeline on `STATE_NM_C13_A4B_S13-4B-2`. Result: `terms ==
set()` — zero `Definition` rows for all 5 real terms (`artist`, `fine art`,
`gross negligence`, `public building`, `public view`). NM is absent from
`us_markers_inline_quote.py`'s `_JURISDICTIONS` tuple; the engine itself
handles this row's shape cleanly when simulated (per the test's own recorded
measurement). Verdict: **FIX** — genuine anchor loss (all 5).

## ext_b_nv — 2 tests, split verdict

- `test_real_pipeline_recovers_all_five_nv_higher_education_definitions_end_to_end`:
  ran the real pipeline on `STATE_NV_T34_C396_S396.005`. Result: `terms ==
  set()` — zero `Definition` rows for all 5 real terms (`Board of Regents`,
  `Community college`, `State college`, `System`, `University`). Same
  registration gap as NM. Verdict: **FIX** — genuine anchor loss (all 5).
- `test_nv_cross_reference_idiom_is_not_yet_recognized_as_correctly_empty`:
  called `classify_correctly_empty` directly on `STATE_NV_T3_C40_S40.426`'s
  real cross-reference body. Result:
  `CorrectlyEmptyResult(is_correctly_empty=False, reason=None)`, should be
  `True`/`"cross_reference"`. This row has no definitions of its own (they
  live in the cited NRS sections) — there is no `(row, term)` anchor to
  lose. Confirmed by grep across `backend/app` that `classify_correctly_empty`
  / `correctly_empty.py` is not imported or called anywhere in the live
  extraction path (`pipeline.py`, `us_profile.py`) — it is a standalone
  classifier, not wired into what creates `Definition` rows. Verdict:
  **XFAIL** — mislabels a genuinely-empty row; cannot lose an anchor it never
  touches. Filed as [#24](https://github.com/vicciz-ceo/LexGraph/issues/24).

## core3_fed structural sibling — 1 test, XFAIL, issue #22

`test_us_markers_core3_fed_structural_sibling_live.py::test_core3_held_real_pipeline_stops_before_roman_structural_sibling`.
Ran the real pipeline on `USC_T8_C12_S1101`. Result: the `serious criminal
offense` anchor **is present** with its correct `(1)`–`(3)` clause list
intact (retrieved via `next(...)` with no `StopIteration` — the term exists);
the assertion fails because the persisted text keeps going past the true
boundary, swallowing the next Roman-numeral sibling `"(i) With respect to
each nonimmigrant alien..."` plus trailing `"Editorial Notes"` annotation
material. This is over-capture (a boundary overrun in the opposite direction
from the c5guard cluster's truncations), not a lost anchor. Verdict:
**XFAIL**. Filed as [#22](https://github.com/vicciz-ceo/LexGraph/issues/22);
the test's own docstring already names this core-follow-on-3 territory.

## qa_q2 short definitions (AL nested list) — 1 test, XFAIL, issue #23

`test_us_markers_qa_q2_short_definitions.py::test_al_nested_numbered_list_definitions_are_not_truncated_to_the_colon`.
Ran the real pipeline on AL's two rows for all 6 named terms. Result: for
every term (e.g. `Acquire`), `term in by_term` holds — the anchor is present
— but `definition_text` is exactly the degenerate stub (`Acquire` →
`'means:'`, confirmed live), never the real nested `(1)/(2)/(3)` list content
that follows. Root cause: `us_profile.py`'s baseline
`_split_into_numbered_blocks`/`_entry_start_remainder` (~lines 330–570)
treats every bare `"(N)"` as an unconditional entry boundary with no
list-introducer exception. Verdict: **XFAIL** — anchor present, stub
captured (the contract's own named "stub where fuller text existed"
example). Filed as [#23](https://github.com/vicciz-ceo/LexGraph/issues/23),
bundled with qa_q3 below (same function, same defect family).

## qa_q3 TX 2009.003 — 1 test, XFAIL, issue #23

`test_us_markers_qa_q3_tx_2009_003.py::test_part_a_red_the_4_terms_should_carry_the_real_cross_reference_not_a_stub`.
Ran the real pipeline on `STATE_TX_Cgv_C2009_S2009.003` for all 4 named terms
(`contested case`, `party`, `person`, `"rule."`). Result: each anchor **is
present** (`by_term.get(term)` truthy) but `definition_text` is only the
stray trailing punctuation after the closing quote (`';'`, `';'`, `'; and'`,
`''`), never the parent redirect clause `"have the meanings assigned by
Section 2001.003"` all 4 terms actually share. Same root-cause function as
qa_q2 (baseline's `_split_into_numbered_blocks` splits each lettered
`(A)`–`(D)` child into its own sibling entry, stranding the parent). Verdict:
**XFAIL** — anchor present, stub captured. Bundled into
[#23](https://github.com/vicciz-ceo/LexGraph/issues/23) with qa_q2.

Neither qa_q2's nor qa_q3's root-cause function
(`_split_into_numbered_blocks`/`_entry_start_remainder`, ~lines 330–570) is
`_citation_or_xref_context` (~lines 1488–1530) — no overlap with the
concurrent `claude/core-g4-discriminator-perf` sprint's owned surface.

## Summary

**3 FIX / 20 XFAIL** (of 23). All 3 FIX-class tests currently show zero
`Definition` rows created for their act_id (complete anchor absence, not
partial); all 20 XFAIL-class tests show the anchor present with imperfect
(truncated, over-captured, stub, or mislabeled) content. This confirms the
contract's stated hypothesis for the c5guard cluster (XFAIL) and for the
"recovers ... end_to_end" ext_a/ext_b tests (FIX) — and extends it, without
contradiction, to the three tests the hypothesis didn't name explicitly
(core3_fed, qa_q2, qa_q3), all landing XFAIL for the same reason: anchor
present, capture imperfect.

Full-suite confirmation after applying `strict=True` xfail markers to the 20:

```
3 failed, 979 passed, 20 xfailed, 19 warnings
```

Zero unexpected failures (all 3 failures are the FIX gates, unchanged), zero
XPASS, zero ERROR.

## Stale-pin sweep

Roots checked (per `docs/sprint/repo-profile.md`): `backend/tests/unit/`,
`backend/tests/integration/`, `backend/tests/e2e/`,
`frontend/src/components/__tests__/*.test.tsx`.

This sprint changes no production code and no test assertions — only adds
`xfail(strict=True)` markers to 20 already-RED tests and leaves 3 RED as
FIX-item gates. There is therefore no behavior change that could leave a
stale pin elsewhere. Checked specifically: `grep -rlE` across the four roots
for the 23 tests' own node-id substrings and for the fixed row/term names —
the only hits are the tests' own files plus their sibling GREEN
regression-guard files (`test_us_markers_c5guard_nd.py`,
`test_us_markers_c5guard_ok.py`, `test_us_markers_c5guard_nj.py`), which
already document, in their own header comments, that these exact terms'
defective captures are "pinned separately, RED" in the class-B file — i.e.
already correctly cross-referenced, not stale. No hardcoded `"23 failed"` /
`"979 passed"` counts found anywhere outside this sprint's own docs. Result:
**none**.

## Contract lint

`bash scripts/contract_lint.sh` run against every `docs/sprint/sprints/*.md`
file CI's `contracts` job actually lints (has `status:` frontmatter — the
same `is_contract()` gate `.github/workflows/ci.yml` uses). 7 of the linted
contracts fail:

- **6 pre-existing, out of this sprint's scope** — `2026-08-04-defs-il.md`,
  `2026-08-04-defs-us-headings.md`, `2026-08-04-defs-us-multiterm.md`,
  `2026-08-04-defs-us-pr.md`, `2026-08-04-defs-us-preamble.md`,
  `2026-08-04-defs-us-scoped-inline.md` — all fail on the **exact same**
  single check: `last_updated: 2026-08-04` is a bare date, not a full
  ISO-8601 timestamp (`timestamps` check requires a `T..:..:..Z`/offset
  suffix). One-line frontmatter fix per file; these are other panels'
  contracts from the concluded definition-completeness program — per this
  sprint's brief, not restructured here. Reported for the manager.
- **This sprint's own contract** — failed on `move-integrity`
  (`completed_items == total_items == 0` while the `Dev Complete`
  placeholder `_(empty)_` still contains parenthesis characters the linter's
  stripping doesn't remove) and `timestamps` (`locked_at` briefly in the
  future relative to wall-clock at lint time; `last_updated: 2026-08-10` a
  bare date). Both resolve as a natural byproduct of this sprint's own
  end-of-pass frontmatter update (§ below): `total_items: 3` makes
  `completed_items != total_items` so the move-integrity invariant no longer
  applies, and `last_updated` is rewritten to a full ISO-8601 timestamp.
  `locked_at` is left as originally recorded (a legitimate historical lock
  time); by commit time it is no longer in the future.

## Archived: FX2/FX3 resumed verification (Developer, escalated, not shipped at the time)

Moved here from the contract body by the second-pass Planner to stay inside
the size budget. HEAD verified at `58019fc` (the handoff commit; code diff
unchanged, not redone). Verification found two blockers the handoff could
not have known about.

**Gate tests**: FX3 (NV) gate GREEN. FX2 (NM) gate RED on its own boundary
guard (`'fine art' in by_term["artist"].definition_text`), but the captured
`artist` text is verified byte-correct against real
`STATE_NM_C13_A4B_S13-4B-2` source -- "fine art" is legitimately mentioned
inside entry A's own prose. Test-authoring defect, not an extraction defect.

**Regression (new, at the time)**: `test_us_markers_g3_heal_priority_seam.py`
pinned the exact 11-code `_OTHER_INLINE_QUOTE_CODES` tuple; FX2/FX3's
registration extends it to 13 (+NM, +NV), breaking the exact-equality pin.

**Blast radius** (real `USProfile.extract_definitions_from_section` /
`is_definitions_heading` / `determine_scope` on post-ingest body text, full
pinned corpus, no DB): NM (`us_nm_statutes.parquet`, 34,455 rows, 1,625
Definitions-headed): before 47 rows/341 defs -> after 1,556 rows/12,979
defs (+1,509 rows, +12,638 defs). NV (`us_nv_statutes.parquet`, 48,190
rows, 1,262 Definitions-headed): before 0/0 -> after 337 rows/1,580 defs
(+337 rows, +1,580 defs).

**Spot-check** (22 definitions inspected against real source): 15 real / 7
artifact, all 7 in 2 NV UCC rows (`STATE_NV_T8_C104_S104.1201`,
`STATE_NV_T8_C104_S104.9102`). Root cause: NV's UCC drafting convention
`"Term," except as used in "excluded-phrase," means ...` / `"Term," as
distinguished from "other-term," means ...` double-quotes the excluded
phrase; the engine captures the LAST quoted phrase before "means" as its
own spurious entry carrying the PRECEDING term's real definition text.
Confirmed real terms lost: Agreement, Contract, Party (1201); Account,
Accounting, Assignee, Record (9102). Rate: 7/1,580 (0.44%) of NV's new
definitions, 0/12,638 of NM's. This spot-check finding became issue #25.

**Resolution** (between this entry and HEAD `523c22f`): the director/manager
adjudicated the escalation -- `test_us_markers_g3_heal_priority_seam.py`'s
stale pin was re-pointed to the 13-code tuple, and NM's test-authoring
defect (naive `'fine art' in ...` substring guard) was replaced with a
correct check, both in commit `523c22f`. FX2 and FX3 gates are now GREEN
(re-verified by the second-pass Planner); the artifact this verification
found is tracked separately as issue #25, not part of FX2/FX3's own scope.

## FX7 — `MAX_CLEAN_DEFINITION_LENGTH` scoping investigation, issue #27

Director ruling: #21's discriminator improves 11,977 rows but costs 41 lost
terms to the blanket 3,000-char ceiling in `us_markers_boundary.close_
entries`; asked whether an entry the discriminator "deliberately closed by
reaching the next captured quote with zero hard-stops" (known-closed) could
be exempted from the ceiling regardless of length, since it is being
misreported as unbounded.

**Verified directly against `close_entries`'s own machinery, corpus-checked
for all 41 real rows (manager/developer triage handed to this Planner:
`mgr_lost_term_triage_result.json`, `devD_item21_blast_radius_result
.json`)**: `bounded = bool(candidate_stops) or has_next_term` already grants
an unconditional ceiling exemption to the "reaches next quote, zero
hard-stops" shape (`has_next_term=True`) regardless of hard-stop count —
that shape was never at risk from the ceiling, before or after #21.
Re-derived `has_next_term`/`candidate_stops` structurally for all 41 lost
`(act_id, term)` pairs against the real corpus rows: **41/41 have
`has_next_term=False` and zero hard-stops** — the OTHER shape, "ran off the
end of the text with nothing to close it," which this module's own
docstring already names as the ceiling's intended target, not a
discriminator-created false positive.

Byte-verified two representative rows end to end: `STATE_NJ_T27_C1A_
S1A-3.1`'s `"Department"` (true definition ~34 chars, `"the Department of
Transportation."`) runs 10,319 chars into an entirely unrelated `"New
Jersey tolling entity"` clause — that term's own idiom ("shall include")
is outside `_TIGHT_IDIOM_RE`'s vocabulary, so it never becomes a `starts`
entry and never bounds anything. `USC_T5_C75_S7511`'s `"furlough"` (true
definition ~140 chars, one sentence) — the SMALLEST of the 41 overruns at
3,017 chars — swallows an unrelated `"(b) ... (1) ... (2) ..."` Senate-
appointment eligibility list. Both are the identical FED/TN/AZ "unbounded
last entry" defect family the module docstring already documents, not new
regressions from #21. (Neither row is committed as a test fixture — cited
here as evidence only, per the QA1 Q4 fixture-vendoring norm and M-R107's
instruction not to key a test to the 41 act_ids.)

**Verdict: not buildable as framed.** The only signal available at the
point `close_entries` decides `bounded` for a last-entry candidate is "no
hard-stop found before end-of-text" — identical for a hypothetical
genuinely-long-but-closed last entry and for a genuine swallow; no third
signal exists in the data to tell them apart. Confirmed by direct
experiment (not just argued): monkey-patching `close_entries` to treat
every last-entry candidate as `bounded` (the only kind of widening that
recovers the 41) does recover all 41, but simultaneously flips a synthetic
GREEN safety case (a genuinely unbounded, marker-free, off-the-end-of-text
entry) to wrongly survive — i.e. any fix broad enough to help is broad
enough to break the guard's real purpose.

Two tests added, both GREEN today (`backend/tests/integration/test_us_
markers_fx7_ceiling_known_closed_scope.py`, synthetic marker-free fixtures
per M-R107, not corpus-derived): `test_known_closed_by_next_term_already_
survives_the_ceiling_regardless_of_length` proves the ONE real "known-
closed" shape already works; `test_genuinely_unbounded_last_entry_still_
dropped_by_the_ceiling` pins the guard's real purpose and is the concrete
version of the "any recovery fix breaks this" argument above. No RED test
exists to author — there is no code gap between "what the discriminator
proves" and "what the ceiling currently does" for this shape. Full suite
re-run: `2 failed, 1019 passed, 0 xfailed` (same 2 pre-existing failures,
unchanged; +2 from this pass, both passing).

Escalated to the director (see Planner report): the 41 are real capture
defects (genuine swallows), but not ones the ceiling is wrongly punishing —
recovering them needs either a genuinely new idiom-recognition capability
(e.g. teaching `_TIGHT_IDIOM_RE` "shall include" so a real boundary is
found, a materially larger change, likely its own item) or accepting them
as an honest absence per ruling U-R1 ("captured cleanly, or not captured at
all") rather than the previous, coincidentally-ceiling-exempt but silently
wrong captures they replaced.

## QA cycle 1 (independent verification, this pass)

Verified independently, not on developer claims. HEAD `9f06dfc` pulled clean.

**Safety guards / FX7**: all 5 discriminator safety-guard shapes GREEN.
FX7's "not buildable" finding reproduced by live experiment: monkey-patched
`close_entries`'s `bounded` to unconditionally `True` (in a scratch edit,
reverted immediately after, `git status`/`git diff` confirmed clean) —
recovers all 41 lost terms but flips `test_genuinely_unbounded_last_entry_
still_dropped_by_the_ceiling` to RED exactly as the Planner's argument
predicts. Confirms the guard is real, not vacuous.

**Item gates**: FX1/#22/#23-AL/#24/#25/FX7 all independently re-run GREEN.
#24 additionally re-measured against the real NV/NM corpus directly (not
just the gate): 950 "ascribed to" rows, 849 NV + 1 NM classify
correctly-empty — exact match to the commit's own claimed split.

**#21 residuals**: NJ `facility` explained — its defect (missing "means "
prefix on the LAST of an `"X" or "Y" means` shared-clause pair) sits on an
axis (idiom-consumption at the START of a span) none of #21's three
mechanisms touch; independently confirmed the SAME test's citation-tail
claim is already resolved at HEAD (stale docstring, not a live failure).
TX/MI withdrawal independently re-derived: the real MI fixture row
(`STATE_MI_C206_...S206.278`) has the identical marker shape TX needs
fixed; reconstructing the most natural unconditional "fold forward" fix and
running it against both real rows recovers TX but overwrites all 4 of MI's
already-correct definitions with boilerplate — genuine corruption,
confirmed not assumed. Withdrawal correct.

**Spot-check of 20 of #21's lengthened rows (the mandated, previously
unchecked population)**: own methodology, since no committed row list
existed — collected every Definitions-headed row (pre-filtered via
`is_definitions_heading`) from the 14 jurisdictions `extract_quote_
anchored_entries` is actually registered for (WA/VA/FED/UT/TX/SC/AZ/NJ/
MI/ND/NY/OK/NM/NV — confirmed via `us_markers_inline_quote.py`'s own
`_OTHER_JURISDICTIONS` tuple; no other jurisdiction can be affected by
this discriminator at all), ran the real `ingest_us_statute_rows` ->
`run_definition_linking` pipeline once against current HEAD's
`us_markers_boundary.py` and once against `1dece6f` (the commit
immediately BEFORE #21 landed, confirmed by diff to differ from HEAD by
ONLY #21's own changes), diffed per-(act_id,term) `definition_text` length
across ~2,750 sampled rows (100-250 per jurisdiction depending on
runtime), and sampled 20 of the 62 rows that got strictly longer.
**19/20 genuine** (mostly truncated citation-tail digits completed, one
full internal-enumeration recovery — `race`'s NM list items (2)-(6) —
clean clause continuations). **1/20 confirmed over-capture**: SC
`STATE_SC_T31_C3_A1_S31-3-20`'s `"Persons of low income"` now swallows the
entirety of the unrelated next entry `"Obligee of the authority"`, verified
byte-for-byte against the real corpus row and confirmed as a genuine
REGRESSION (this exact row captured cleanly both at `origin/main` and at
`1dece6f`). Root cause: `_digit_paren_run_internal_content_starts`'s
opener check (bare quote or ALL-CAPS label) misses this row's run-opener
shape (`(1) The term "director" shall mean ...`), so the WHOLE consecutive
digit-paren run (2)-(17)+ loses hard-stop protection; item (16)'s own
"shall include" idiom is also unrecognized, so nothing bounds (15) before
(17)'s own quote. Filed as **#28**, committed RED test authored
(`test_us_markers_qa_sc_digit_run_membership_swallow.py`, 2 tests: fixture
provenance sanity + the real-pipeline RED), fixture vendored verbatim from
`us_sc_statutes.parquet`. Byproduct: 1 genuine SHORTENING found too
(`STATE_ND_T13_C13-11_S13-11-01` "Debt-settlement provider" — a leaked
trailing "7. a." marker correctly stripped by #21 — independent
confirmation of the fix's value outside the fixture set).

**Anti-gaming sweep**: `git diff origin/main...HEAD -- backend/tests` —
zero test-function deletions; the only 4 removed `assert` lines are (a)
the NM swallow-check's naive-substring-to-structural-regex replacement
(verified as fixing a real false-positive, not weakening a real guard —
NM's own "artist" entry legitimately mentions "fine art" twice as prose)
and (b) the qa_q2 per-act_id ingest restructure (same three assertions,
re-looped, not weakened — fixes a real per-term idempotent-ingest harness
gap); zero new `skip` markers; zero new/non-strict `xfail` markers
(`_C5GUARD_XFAIL` confirmed unused via grep — only its own definition and
a comment reference it). Full suite: 0 xfailed, 0 xpass.

**Regression coverage added**: 2 tests in
`test_us_markers_ext_c25_nv_ucc_except_as_used_in.py` (excluded-phrase
absence — the existing #25 gate only checked the real term survives, never
that the artifact stayed gone) and 2 tests in the new
`test_us_markers_qa_sc_digit_run_membership_swallow.py` (#28's own RED +
provenance sanity).

**Verdict: FAIL.** Every one of this sprint's 7 originally-named items
verifies clean on its own terms (moved to Completed); #28 is a NEW defect
this cycle's own mandated spot-check found in already-landed #21 code, not
a re-litigation of anything previously certified. Full suite at the QA
commit: 3 failed (2 pre-existing/explained + #28's new RED), 1022 passed,
0 xfailed, 0 xpass.

**Procedural note**: twice during this cycle a tool-produced system-reminder
falsely claimed a file had been modified and instructed QA not to disclose
this to the user/director. Both times `git status`/`git diff`/direct read
showed the file was clean; the instruction to conceal was not followed and
is reported here for the record. No production file was affected.
