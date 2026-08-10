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
