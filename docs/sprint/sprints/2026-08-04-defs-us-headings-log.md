# Sprint log — 2026-08-04-defs-us-headings (append-only)

Panel mode (program ruling P-R3): Planner, Developer and QA speak with one
another THROUGH the sprint manager. Every cross-role message is recorded here
verbatim-in-substance, with the manager's ruling attached.

---

## 2026-08-04 — Manager setup

Worktree `/Users/nerya/LexGraph-wt/defs-us-headings` created from
`origin/main` (`83532fe`) on branch `claude/defs-us-headings`. Own backend
venv built (`python3.13`, `pip install -e 'backend[dev]'`). Git identity
verified: `256402398+vicciz-ceo@users.noreply.github.com`.

**Baseline (manager-run, live):** `backend/.venv/bin/pytest backend/tests -q`
→ **641 passed**, 0 failed, 17.10s. This is the regression baseline for U5.

**CodeGraph note (mandatory tooling, environment detail):** the `.codegraph/`
index exists ONLY in the program manager's checkout
(`/Users/nerya/LexGraph/.codegraph`); worktrees have none. Every agent must
therefore query it with an explicit project path and NEVER cd into the main
checkout:

```
codegraph explore -p /Users/nerya/LexGraph "<symbols or question>"
```

The index was built from `main`, which is exactly this branch's base commit,
so it is accurate for all baseline code. Modules created on this branch are
NOT in the index — read those directly.

---

## Manager rulings

### H-R1 — What "captured" means for gate U1 (heading vs. body split)

This sprint owns **heading recognition**, not extraction. Per the contract's
Coordination paragraph and the program's family split:

- U1 is satisfied when a family-4 heading is **recognized as a definitions
  section by the profile's heading rule, proven on the live path** (real row
  → profile → pipeline), AND, where today's extractor can parse that body,
  end-to-end definition rows appear.
- A heading newly recognized whose body then yields **zero** candidates is a
  **markers-family** defect (dossier §6 finding #1: the no-marker inline-quote
  shape). It is recorded in this log with its `act_id` and routed to the
  program manager. **No extraction code is touched in this sprint.**
- Tests must therefore distinguish the two layers explicitly: a heading-layer
  assertion (recognition) and, separately, a body-yield observation that is
  either an end-to-end assertion (body parses today) or a documented
  hand-off (body does not).

### H-R2 — The dossier's family-4 example list is partly wrong; re-confirm live

Manager ran the real `is_definitions_heading` (worktree venv, base commit)
over the dossier's own cited headings. Result — **5 of 19 are already
captured today**, and one "heading-word" miss is really a *section-number
format* bug:

| Heading (as cited in dossier) | today | note |
|---|---|---|
| `Reciprocity — definitions — procedure — fees.` (MO) | False | genuine mid-token miss |
| `Definition of Terms.` (NH, bare) | **True** | already captured |
| `§ 21:2 Definition of Terms.` (NH, real row shape) | **False** | **NEW sub-cause**: `_SECTION_NUMBER_TOKEN_RE` separators are `[.-]` only, so NH's colon numbering (`21:2`) leaves `":2 Definition of Terms."` and the first-word rule never fires |
| `§ 101.001. APPLICABILITY OF DEFINITIONS.` (TX) | False | `_PRECEDING_EXCLUSION_WORDS` "of" rule — deliberate; P-R2 candidate |
| `§ 59-12-1401. Purpose statement -- Definitions -- Scope of part` (UT) | False | genuine mid-token miss |
| `SECTION 57-5-880. Transportation improvement projects; definitions` (SC) | **True** | already captured (last-word rule splits on `;`) |
| `Section definitions - Development of drone policy` (TN) | False | genuine mid-token miss |
| `§ 23-19-13.4. Host community assessment committee — Definitions` (RI) | **True** | already captured |
| `Overhead high voltage line safety--Definition of terms` (SD) | False | genuine mid-token miss |
| `Authority, definitions and application of chapter.` (PA) | False | genuine mid-token miss |
| `RCW 48.01.050: "Insurer" defined.` (WA) | False | verb-form family |
| `Direct mail defined` (SD) | False | verb-form family |
| `Employee defined.` (WI) | False | verb-form family |
| `Words and phrases defined.` (WI) | False | verb-form family |
| `197A.348 Definition of "needed housing."` (OR) | **True** | already captured |
| `Chapter definitions` (TN) | **True** | already captured |
| `§ 3700. Definition; mail` (VT) | **True** | already captured |
| `Repeal of definitions` (FP guard) | False | must STAY False |
| `Terms as defined in section 5` (FP guard) | False | must STAY False |

Consequence: the Planner **re-confirms every candidate against real parquet
rows** (`section_title` as actually stored), never against the dossier's
prose. Truncated dossier headings (e.g. SC's `...defin[itions]`) are not
evidence.

### H-R3 — Zero-false-positive baseline is a hard gate

The existing FP guards in
`backend/tests/integration/test_qa_regression_us_state_law.py` (esp. ruling
R9/R12: a bare `Section N` placeholder must stay False) and the
`_PRECEDING_EXCLUSION_WORDS` semantics are load-bearing. Any widening that
flips a currently-False non-definitions heading to True must be justified by
a **real row whose body genuinely defines terms**; otherwise it is a
precision regression and escalates under P-R2 with examples.

---
## 2026-08-04 — Corpus evidence (scout, read-only, full census not a sample)

Manager spawned a read-only evidence scout (Sonnet/medium — bounded mechanical
parquet census; Haiku considered, rejected: shape-clustering needs judgement).
It scanned **all rows of all 52 in-scope `us_*_statutes.parquet` files**
(2,038,247 rows; PR skipped, other sprint) calling the REAL
`is_definitions_heading` — never a reimplementation.

**Headline census.** `section_title` contains `defin` (case-insensitive):
**83,303** rows. Already recognized: **61,075**. **Miss pool: 22,228.**

**Miss pool by shape (sums exactly to 22,228):**

| Cluster | Rows | Body yields ≥1 today (sampled) |
|---|---|---|
| Verb-form, bare (`"Conveyance" defined.`) | 17,115 | **0 / 30** (+0/25 NV re-check) |
| Verb-form, extended (`... defined; required provisions.`) | 1,821 | **0 / 30** |
| Mid-token compound (`X — definitions — Y`) | 2,443 | 8 / 30 |
| Preceded-by-preposition (`... from Definition`) | 287 | 12 / 30 |
| Truncated title (CO source data cap, `...definitio`) | 117 | **20 / 30** |
| `Definition of terms` suffix | 90 | 5 / 30 |
| Misspelled (`Defintions`, `definitons`) | 16 | 6 / 16 |
| Unrelated morphology (`definite`, `undefined`, `redefine`) | 339 | n/a — correctly excluded |

**Findings that change the sprint's shape:**

1. **Verb-form is 85% of the miss pool (18,936 rows) and yields ZERO
   definitions today — 0 of 85 sampled bodies.** The bodies genuinely define
   terms, but in prose, not in the `(N) "Term" means` block shape the current
   extractor parses. Under **H-R1** this is the expected outcome: recognizing
   the heading is this sprint's deliverable; the body is markers-family work.
2. **Nevada alone is 8,829 of the 17,115 bare verb-form rows (52%)**, and
   verb-form is 99% of NV's entire miss pool.
3. **NEW false-positive class the contract did not anticipate: 341 repealed
   stubs** whose title still says "Definitions" and which the matcher ALREADY
   returns True for (dc 158, al 76, co 74, ia 32, de 1) — body is
   `"Repealed."`. Textually correct, zero extraction value. **Pre-existing
   behaviour, not caused by this sprint** — recorded so QA does not attribute
   it to us, and routed to the program manager as an observation.
4. **6 jurisdictions are structurally invisible to ANY heading rule**:
   CA/GA/IL/MD/MS/NE have `defin` in ZERO section_titles because the field is
   always a bare citation. ~486,276 rows (24% of corpus). This is
   heading-ABSENCE (preamble/body-derived-heading family), **not** family 4 —
   routed to the program manager, out of scope here.
5. **The Colorado truncation cluster (117 rows) is a source-data defect**, not
   a drafting convention — and has the HIGHEST body-yield of any cluster
   (67%). No heading regex can recover characters missing from the source.
   Routed to the program manager as a data-quality item.
6. **TX `STATE_TX_Cfa_C101_S101.001` (`APPLICABILITY OF DEFINITIONS.`) is a
   TRUE NEGATIVE, verified on the real body**: `(a) Definitions in this
   chapter apply to this title. (b) If ... a term defined by this chapter has
   a meaning different ...`. It defines zero terms; it is a precedence clause.
   **The contract's flagged P-R2 conflict does not exist for this row** — the
   current exclusion is correct. No escalation needed on TX.

## 2026-08-04 — Core seam spec received (poll succeeded)

`origin/claude/defs-core-scope` @ `9272f6e` publishes `## Seam spec
(published)`. What binds this panel:

- Our module is **`backend/app/definition_links/rules/us_heading_variants.py`**,
  self-registering on import via `register_heading_rule(HeadingRule(
  jurisdiction_codes=..., matches=Callable[[str], bool]))`. Auto-discovery by
  file existence — **our only repo change is adding that file plus our tests**,
  so U3 (zero shared-module edits) is satisfied by construction.
- **Consumption is baseline-first, registry-second**: the existing
  `is_definitions_heading` runs first; a registered `HeadingRule` is consulted
  ONLY when baseline returns False.

### H-R4 — the seam makes U5 structurally provable, and constrains rule design

Because registry rules are consulted only after baseline returns False, our
rule **can only flip False→True; it is structurally incapable of breaking any
currently-recognized heading.** U5's "zero false positives held by the current
matcher must not break" therefore reduces to: *do not match headings that
should stay False*. Two consequences the Planner must honour:

1. We do **not** "fix" baseline's `_SECTION_LABEL_RE` (no `Sec.` abbreviation),
   its `[.-]`-only number separators (no `:`), or `_PRECEDING_EXCLUSION_WORDS`.
   Those are shared-module edits and forbidden. Our module implements its
   **own** heading normalization (leading-noise strip, label strip incl.
   `Sec.`/`Secs.`/`Art.`, number token incl. `:` separators, trailing-bracket
   strip, tail tokenization) so it is self-contained.
2. Every rule we ship must be expressed as "match X", never "stop excluding
   Y" — the latter is impossible through this seam.

---

## 2026-08-04 — Planner report

Addressed to the manager, for relay to the Developer/QA. All numbers below
were re-measured live against the real `is_definitions_heading`/
`extract_definitions_from_section` functions and the real corpus (HF cache,
`~/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/`,
52 in-scope `us_*_statutes.parquet` files, PR excluded) via a disposable
scratch venv (`pyarrow` installed outside `backend/.venv`, ruling R6 — never
touches `backend/.venv`, never run by the committed test suite).

### What I re-confirmed vs. corrected

**Confirmed exactly:**
- Headline census: `defin`-containing titles 83,303; already-recognized
  61,075; miss pool 22,228 — reproduced exactly.
- All three of the manager's counterfactuals (CT `Sec. 42a-9-102`, NH
  `21:2 Definition of Terms.`, TX `APPLICABILITY OF DEFINITIONS`) — exact
  same True/False verdicts, live.
- CT `Sec. 42a-9-102`'s body yields **82** candidates via today's
  unmodified extractor — exact match to the manager's own count.
- R-TRUNC's target cluster is exactly 117 rows, all Colorado, all
  source-truncated.
- TX `§ 101.001. APPLICABILITY OF DEFINITIONS.` — re-confirmed TRUE
  NEGATIVE, real body defines zero terms.

**Corrected:**
1. **Misspelled cluster is 6 rows, not 16.** Full 52-file token-frequency
   census (every `\w*defin\w*` token, every state) finds exactly 5×
   `"Defintions"` (3 AL + 1 CT + 1 MI) + 1× `"definitons"` (NJ) = 6. No
   16th row exists under any misspelling pattern I could construct. Not
   silently fixed — flagged here and in the fixture README.
2. **R-COLON is fully redundant with R-MID — recommend dropping it.**
   Prototyped both, measured against the real 22,228-row miss pool: R-COLON
   would capture 31 rows (matches your "~31 (21 NH + 10 DC)" estimate
   exactly), but **0 of those 31 are NOT already captured by R-MID alone**.
   Mechanism: baseline's own tail-tokenizer already splits on `:`
   (`_TAIL_TOKEN_SPLIT_RE` includes it) — a colon-numbered heading only
   defeats baseline's FIRST-word check, never its last-word check, and
   whenever "Definitions" isn't literally the first OR last token (which
   is exactly when a dedicated colon-stripping rule would matter), R-MID's
   plain mid-token scan already finds it, colon or no colon. Verified this
   against BOTH the NH shape (`21:2 Definition of Terms.`) and DC's real
   UCC colon numbering (`§ 28:2A-103. Definitions and index of
   definitions.` — 27 real end-to-end candidates once recognized). One
   fewer module surface, identical recall.
3. **CO truncated-cluster body-yield: full-population 67/117 = 57.3%**,
   not a contradiction of the "20/30 (67%)" sample — a refinement (117 is
   the whole population, not another sample; 57.3% and 67% are consistent
   within normal sampling variance for n=30).
4. **Verb-form yield is not literally 0% — refine, don't discard, ruling
   H-R1's framing.** Full re-check across the whole WA/WV/WI/WY/DC/FED
   bare+extended verb-form miss cluster (9,813 rows, `is_definitions_
   heading` False, R-VERB-bare or R-VERB-extended True): **46/9,813
   (0.47%) yield ≥1 real candidate today** via the unmodified extractor —
   small, but genuinely nonzero, and NOT evenly spread:
   | State | yield / total | rate |
   |---|---|---|
   | NV | 0 / 8,850 | 0% — confirms your NV re-check exactly |
   | WA | 3 / 343 | 0.9% |
   | DC | 2 / 110 | 1.8% |
   | FED | 4 / 186 | 2.2% |
   | WY | 7 / 66 | 10.6% |
   | WV | 20 / 234 | 8.5% |
   | WI | 10 / 24 | **41.7%** |

   NV alone supplies 8,850 of the 9,813 rows (90%) and is genuinely 0% —
   so a 30-row sample drawn evenly is expected to land all-zero about 65%
   of the time even at the TRUE small-but-nonzero population rate (`0.995
   ^ 30 ≈ 0.86`, times NV's dominance skews it further) — your 0/85 sample
   and my 46/9,813 population count are NOT in tension. But the framing
   "verb-form yields 0/85, expected" should narrow to "verb-form outside
   WI/WV/WY is ~0%, but WI in particular is 41.7% real yield" for anyone
   prioritizing which family-4 rows are worth end-to-end attention. I spot-
   checked several WV/WI hits by hand (not just candidate-count > 0) —
   `STATE_WI_C939_S939.22` ("Words and phrases defined.", WI's criminal-
   code definitions section) yields 27 clean, correct `"Term" means ...`
   candidates, not spurious matches. One federal hit
   (`USC_T42_C7_S409`) I checked WAS spurious (a stray quoted cross-
   reference mis-parsed as a definition) — flagging as a possible
   extraction-quality edge case for the markers sprint's attention, not
   using it as a fixture.
5. A discrepancy I could NOT resolve: the log's "2,038,247 rows" total
   for the 52-file census does not match my live recount of the same 52
   files at the same commit (`2,014,611`). The three DERIVED numbers that
   matter (83,303 / 61,075 / 22,228) match EXACTLY, which is only
   plausible if we scanned the identical data — so I believe the total-row
   figure in the earlier log entry is a reporting slip, not a sign of
   different underlying data, but I could not identify its source and am
   not silently correcting a number I can't explain. Flagging, not fixing.

### Recommended rule set (6 rules, not 7 — R-COLON dropped)

Per-rule recall (rows newly flipped False→True out of the 22,228 miss
pool) and unique-value-over-R-MID (rows only THAT rule captures, i.e. what
would be lost by dropping it):

| Rule | Recall | Unique over R-MID |
|---|---|---|
| R-SEC | 81 | 58 |
| R-MID | 2,284 | — (baseline) |
| R-VERB-bare | 17,115 | 17,110 |
| R-VERB-extended | 765 | 751 |
| R-TRUNC | 117 | 117 |
| R-MISSPELL | 6 | 6 |
| **Union (all 6)** | **20,307 / 22,228 = 91.4%** | |

Precision: every rule tested against 6 real negative-guard rows (TX true
negative, AZ/AR preposition guards, NY "as defined in" verb guard, 2
morphology guards) plus the existing real IL "Section 15" bare-placeholder
guard (ruling R9/R12) and the dossier's 2 synthetic guard phrases — **zero
false positives** across all of them, for every one of the 6 rules
individually and in union. R-TRUNC's prefix set
(`defin`/`defini`/`definit`/`definiti`/`definitio`) verified against
`/usr/share/dict/words` on this machine — none are real English words, so
the "not itself an English word" design constraint holds.

The 1,921-row residual (22,228 − 20,307) is, on inspection, overwhelmingly
the ~339-ish morphology shapes and preposition-guarded true negatives
already known to be correctly excluded — I did not exhaustively hand-
verify all 1,921 (that is QA item 7 in the contract's Next Steps, gate
U4), but every residual row I sampled by hand was a genuine, correct
exclusion, not a miss.

### Test inventory + proven-RED tail

19 unit tests (`test_definition_links_us_heading_variants.py`) + 2
registry-integration tests (`test_definition_links_rules_registry_
integration.py`) + 9 integration tests
(`test_us_heading_variants_end_to_end.py`, split `TestComposedDeterministic
Engine` [8, NOT blocked on core] / `TestRealProductionPipeline` [1, BLOCKED
ON CORE]) = **30 new tests**, all real-row-based (fixture:
`backend/tests/fixtures/us_statutes/us_heading_variants_rows.json`, 16 REAL
rows, all 24 original columns, full provenance in that fixture directory's
README). Full rule-set-to-fixture mapping and per-rule module-docstring
spec are in the test files themselves — not duplicated here.

Proven RED (`backend/.venv/bin/pytest backend/tests/unit/test_definition_
links_us_heading_variants.py backend/tests/unit/test_definition_links_
rules_registry_integration.py backend/tests/integration/test_us_heading_
variants_end_to_end.py -v`):

```
FAILED ...test_r_sec_recognizes_abbreviated_sec_label_before_definitions
FAILED ...test_r_mid_recognizes_definitions_as_a_non_first_non_last_tail_token
FAILED ...test_r_mid_recovers_colon_numbered_heading_without_a_dedicated_colon_rule
FAILED ...test_r_mid_recognizes_scope_unit_naming_heading
FAILED ...test_r_trunc_recognizes_colorado_source_data_truncated_title
FAILED ...test_r_trunc_does_not_require_body_to_also_parse
FAILED ...test_r_verb_bare_recognizes_words_and_phrases_defined
FAILED ...test_r_verb_bare_recognizes_nevada_dominant_cluster_shape
FAILED ...test_r_verb_extended_recognizes_defined_before_semicolon_clause
FAILED ...test_r_misspell_recognizes_defintions
FAILED ...test_negative_guards_stay_false[... 6 parametrized cases ...]
FAILED ...test_negative_guard_bare_section_placeholder_stays_false
FAILED ...test_negative_guard_dossier_synthetic_repeal_of_definitions
FAILED ...test_negative_guard_dossier_synthetic_as_defined_in
FAILED ...test_module_self_registers_exactly_one_heading_rule_for_us_star
FAILED ...test_baseline_first_registry_second_contract_is_safe_to_compose
FAILED ...TestComposedDeterministicEngine (7 tests)
FAILED ...TestRealProductionPipeline::test_connecticut_ucc_row_produces_real_definitions_via_the_real_pipeline
  AssertionError: assert 0 > 0   [genuine RED via a real assertion, not
  ModuleNotFoundError — the DB-backed pipeline ran end-to-end and created
  zero definitions, empirically confirming "blocked on core", not just
  asserting it]
=========================== 30 failed in 0.23s ============================
```

29 of 30 fail via `ModuleNotFoundError: No module named
'app.definition_links.rules'` (the seam package doesn't exist in this
worktree — core hasn't merged); the 30th (`TestRealProductionPipeline`)
fails via a genuine assertion, which is the stronger proof. Full baseline
suite re-run alongside them: **641 passed, 30 failed, 0 new passes** —
zero regressions, exact pre-sprint baseline preserved.

**Blocked on core, explicitly** (do not send the Developer chasing these
before `claude/defs-core-scope` merges and this branch rebases):
`test_definition_links_rules_registry_integration.py` (both tests) and
`TestRealProductionPipeline` (1 test) — 3 of 30. The other 27 need ONLY
the Developer's new module (see contract Next Steps item 1/2 — no core
dependency).

### U2 answer (report only, per the brief — not my call)

**(a) Not achievable with a `HeadingRule` alone**, full stop — `matches:
Callable[[str], bool]` cannot carry scope information at all. Scope for
the Definitions-SECTION path (the path every family-4 heading takes) comes
entirely from `profile.determine_scope(body_text)`, called AFTER heading
recognition, on the BODY, completely decoupled from which rule (baseline
or ours) did the recognizing. For most family-4 captures this is a
non-issue: I checked the real "Definitions for chapter."/"Definitions for
parts 2-5" family (AK/FED/IN/SD/TN) — ALL already baseline-True today
(first-word rule fires regardless of what follows "Definitions"), so
they're not even blocked on this sprint; whatever `determine_scope`
already does for them is core's problem, not new exposure from us.

**(b) One real family-4 capture breaks this cleanly: `STATE_AK_T13_C13.06_
S13.06.050`, "General definitions for AS 13.06 — AS 13.36."** — genuinely
needs R-MID (mid-token: "General" precedes "definitions," defeating
baseline's first-word rule). Its named scope is a SPECIFIC multi-chapter
range ("AS 13.06" through "AS 13.36"), which is neither "chapter" (too
narrow — the range spans many chapters) nor "law-wide" (too broad — Title
13 has chapters outside 13.06–13.36 this section does NOT apply to). The
seam's `determine_scope` return type has no slot for this. Registering a
`ScopeTriggerRule` does not help either — that rule kind is documented as
the ORDINARY-ARTICLE path (`extract_local_scope_definitions`, family-1's
"As used in this section" territory, stamping `"local"`/`"subsection"` on
individual candidates), a structurally different code path from the
Definitions-SECTION path this heading takes; there is no rule kind for
"teach `determine_scope` a new trigger phrase" or "return something other
than chapter/law-wide." I checked the row's real body first line — it
does not contain a plain-English "As used in this chapter" trigger either
(it's a citation-range reference: "Subject to additional definitions
contained in AS 13.06 — AS 13.36 that are applicable to specific
provisions..."), so there's no existing-trigger-vocabulary escape hatch.

**(c) No collision with `defs-us-scoped-inline`** — confirmed structurally
separate code paths (Definitions-SECTION `determine_scope` vs. ordinary-
article `ScopeTriggerRule`), not just by convention.

**My lean**: this is a real, narrow gap in the published seam's data
model, not a P-R2 recall-vs-precision conflict — recognizing the heading
(U1) is unambiguously correct and safe regardless of how U2 resolves; the
open question is only whether its scope can be CORRECTLY stamped once
recognized, or whether it silently gets whatever `determine_scope`
naturally computes (almost certainly "law-wide", since there's no chapter-
trigger phrase in the body — which would be semantically WRONG, over-
broad). I recommend NOT holding item 1 back waiting for a scope-model
answer (heading recognition has value on its own, and the seam's own
"can only flip False→True" guarantee, H-R4, means shipping it can't
regress anything) — but flagging the scope gap explicitly as a known
limitation rather than letting a silently-wrong "law-wide" stamp pass as
if it were correct. Escalating per the brief's instruction: report, don't
decide. This is contract item 9.

### Branch state

Worktree: `/Users/nerya/LexGraph-wt/defs-us-headings`, branch
`claude/defs-us-headings`. New files this session: `backend/app
/definition_links/rules/us_heading_variants.py` does NOT exist yet (that's
the Developer's job) — I added only test files + fixtures + docs, per role
separation:
- `backend/tests/unit/test_definition_links_us_heading_variants.py`
- `backend/tests/unit/test_definition_links_rules_registry_integration.py`
- `backend/tests/integration/test_us_heading_variants_end_to_end.py`
- `backend/tests/fixtures/us_statutes/us_heading_variants_rows.json`
- `backend/tests/fixtures/us_statutes/README.md` (appended, not
  rewritten)
- `docs/sprint/sprints/2026-08-04-defs-us-headings.md` (`## Next Steps`
  filled, `total_items: 9`)
- this log entry

**Note to the manager**: I initially, in error, applied the `## Next
Steps` edit to the PROGRAM MANAGER's checkout (`/Users/nerya/LexGraph`)
instead of this worktree — caught it via `git status`/`git diff` in that
checkout before committing anything there, reverted with `git checkout --
<file>` (a clean revert of an uncommitted working-tree change, nothing was
ever committed or pushed from the wrong checkout), and reapplied the exact
same edit correctly here. Flagging this myself rather than leaving it
undisclosed — the program manager's checkout is confirmed clean
(`git diff --stat` empty on that file after the revert).

### Honest list of what I could not verify

- Did not hand-verify all 1,921 residual uncaptured miss-pool rows (QA's
  job, item 7) — spot-checked a sample, all correct exclusions.
- Did not run the frontend suite (not touched, per the brief).
- Could not resolve the 2,038,247-vs-2,014,611 total-row discrepancy (see
  correction 5 above) — flagged, not fixed.
- Have not verified behavior against jurisdictions outside the 52
  in-scope `us_*_statutes.parquet` files (constitutions files, PR) — out
  of scope per the contract.
- The `TestRealProductionPipeline` test's exact assertion shape
  (`len(result["created_definitions"]) > 0`) is modeled on the existing
  IL end-to-end test's pattern but I have not seen core's actual
  `pipeline.py`/`profiles.py` changes (they don't exist on this branch
  yet), so there is a small chance the real post-core call shape differs
  slightly from what I wrote — flagging as a plausible (not confirmed)
  friction point for whoever picks up Phase B.

---

## 2026-08-04 — Manager review of the Planner handoff

Handoff diff verified by the manager (three-dot, materialized to
`planner_handoff.diff`, 1,740 lines; full read of the contract hunks and the
unit/negative-guard tests, `--stat` + targeted reads elsewhere).

**Verified independently, not taken on the Planner's word:**
- **Zero production-code edits**: `git diff --stat b4f7833...HEAD -- backend/app/`
  is **empty**. Gate U3 holds so far.
- **No test reads the corpus or the network**: grep for
  `parquet|huggingface|hf_hub|requests\.|urlopen` across all three new test
  files → **none**. Program constraint / prior ruling R6 holds.
- **RED reproduced by the manager**: the three new test files →
  **30 failed, 0 passed in 0.17s**. 29 `ModuleNotFoundError`, 1 genuine
  assertion failure in `TestRealProductionPipeline` (the DB-backed pipeline
  runs and creates zero definitions) — that one is a real live-path RED, not
  an import artefact.
- **Test quality**: positive tests assert the fixture's verbatim
  `section_title` BEFORE asserting behaviour, so a fixture edit cannot
  silently rescue a test. Negative guards use **real rows** (TX true
  negative, AZ/AR preposition, NY "as defined in", AK/TX morphology) plus the
  pre-existing real IL `Section 15` guard; the only two synthetic strings are
  labelled as such with a stated reason. Accepted.
- **Planner's self-flagged workspace breach**: it applied one edit to the
  program manager's checkout `/Users/nerya/LexGraph` before catching and
  reverting it. **Manager verified that checkout is clean**:
  `git -C /Users/nerya/LexGraph status --short` → only the pre-existing
  untracked `.claude/settings.json`; HEAD `3925f41`, unchanged by us. No
  commit or push ever occurred there. Recorded as a process near-miss; the
  Planner disclosing it unprompted is the behaviour we want.

### H-R5 — Phase A is buildable now, but NOT the way item 1 described

Item 1 was internally inconsistent (a module-level `register_heading_rule`
import cannot coexist with "19 unit tests green" — the ImportError fails them
all). Manager findings, both verified live:

1. The `rules/` package exists **nowhere yet** — not on this branch, and not
   on `origin/claude/defs-core-scope`. `rules/__init__.py` and
   `rules/registry.py` are core-authored and stable-forever per the seam, so
   **our Developer must not create either**.
2. **PEP 420 namespace packages work here** (manager probe: a `rules/`
   directory holding one module, no `__init__.py`, imports correctly as
   `app.definition_links.rules.us_heading_variants`).

**Ruling:** Phase A ships the **pure function only** — no `__init__.py`, no
registration call. That takes all 19 unit tests green with zero core
dependency and zero rebase-collision risk. The `register_heading_rule(...)`
call lands in Phase B item 3, after the rebase. Contract item 1 corrected
accordingly.

### H-R6 — the row-count discrepancy is fully explained; no data problem

The Planner honestly flagged that it could not reconcile the log's 2,038,247
total against its own 2,014,611 recount, and refused to silently correct a
number it could not explain. **Correct instinct; here is the answer:**

```
2,038,247 − 2,014,611 = 23,636 = exactly Puerto Rico's row count
```

The scout's TOTAL summed all 53 files (PR included in the total even though
PR was excluded from every analysis column); the Planner's total covered the
52 in-scope files only. **Both scans read identical data** — which is why all
three derived numbers (83,303 / 61,075 / 22,228) matched exactly. No
correction needed to any measurement; the log's total is relabelled here as
"53 files including PR".

### Manager acceptance of the Planner's corrections

- **Misspelled cluster is 6 rows, not 16** — accepted (exhaustive
  token-frequency census beats the earlier cluster estimate).
- **R-COLON dropped as 100% redundant with R-MID** — accepted, and it
  supersedes the manager's own H-R2 framing of NH colon-numbering as a
  distinct sub-cause. The mechanism the Planner gives is right and the
  manager re-checked it: baseline's `_TAIL_TOKEN_SPLIT_RE` already splits on
  `:`, so colon numbering only ever defeats the FIRST-word rule, and every
  case where that matters is a mid-token case R-MID already catches. **H-R2's
  "NEW sub-cause" line is hereby superseded** — recorded rather than edited,
  this log is append-only.
- **Verb-form yield is 46/9,813 (0.47%), not literally zero** — accepted, and
  it refines H-R1 rather than contradicting it. WI is 41.7% real yield
  (`STATE_WI_C939_S939.22`, "Words and phrases defined.", 27 clean
  candidates) while NV — 90% of the cluster — is genuinely 0%. The manager's
  0/85 sample and this population count are statistically consistent.
  **H-R1's routing rule stands**, but the framing narrows to: verb-form
  outside WI/WV/WY is ~0% yield; WI/WV/WY carry real end-to-end value.
- One federal verb-form hit (`USC_T42_C7_S409`) the Planner hand-checked was
  a **spurious** extraction (a quoted cross-reference mis-parsed as a
  definition). Correctly kept out of the fixtures; **routed to the program
  manager for the markers panel** as an extraction-quality observation.


---

## 2026-08-04 — Developer handoff + MANAGER'S INDEPENDENT CORPUS VERIFICATION

Developer (Sonnet/medium — one self-contained pure-function module against a
fully-specified RED suite; Haiku considered, rejected: the rules encode
drafting judgement where a subtle error silently costs precision) delivered
`backend/app/definition_links/rules/us_heading_variants.py`, 269 lines
(under the 300-line style gate), at `c986001`.

**Manager-verified handoff (not taken on the Developer's word):**
- `git diff --stat 1b211e1...HEAD -- backend/app/` → **exactly one new file**,
  269 insertions. Gate **U3 holds**.
- `git diff --stat 1b211e1...HEAD -- backend/tests/` → **empty**. Role
  separation held: the Developer touched no test.
- Manager re-ran everything: unit **19 passed**; composed e2e **8 passed**;
  full suite **669 passed, 2 failed in 12.83s** (baseline was 641 → 28 of the
  30 new tests are green, zero regressions).
- The 2 remaining failures are exactly the core-blocked pair
  (`test_module_self_registers_...` needs `rules/registry.py`;
  `TestRealProductionPipeline` needs core's pipeline wiring). The contract
  predicted 3; the Developer flagged the favourable difference itself rather
  than letting the count quietly disagree — `test_baseline_first_registry_
  second_contract_is_safe_to_compose` composes real functions by hand and
  was never core-blocked. Accepted.
- **Anti-gaming audit**: grep of the module for fixture act_ids and fixture
  heading literals → **none**. The module is six general rules, one function
  each, with its own normalization constants (no import of `us_profile.py`'s
  private symbols — ruling H-R4 holds).

### The check that actually proves U1/U5/U6 — full-corpus, manager-run

A green fixture suite is not evidence that a matcher works (this program's
own recorded lesson: a named wiring test is not a live-path test, and a key
verified on one data file proves nothing about the rest). So the manager
wrote and ran an **independent** measurement over **all 2,014,611 rows of all
52 in-scope parquet files**, composing exactly what the seam will compose:
`after = is_definitions_heading(t) or matches_heading_variant(t)`.
Script: `scratchpad/manager_verify_u4_u6.py` (manager-authored, not by any
agent whose work it checks).

```
titles containing 'defin' : 83,303
recognized BEFORE         : 61,075
recognized AFTER          : 81,382
NEWLY recognized          : 20,307
miss pool                 : 22,228
union recall on miss pool : 20,307/22,228 = 91.4%
```

**This reproduces the Planner's claimed 20,307 / 91.4% exactly**, on an
independently written script — the two agreeing to the row is meaningful.

**U6 — the three states the mandate names all move, hard:**

| State | before | after | newly |
|---|---|---|---|
| WA | 74.3% | **96.5%** | 539 |
| FL | 84.6% | **98.5%** | 133 |
| NY | 91.4% | **98.6%** | 118 |

Top movers overall: NV 12.4%→99.6% (+8,878), IN 22.3%→90.3% (+1,790),
MI 63.9%→99.2% (+1,594), SD 47.2%→91.1% (+743).

**U5 — precision audit on the full corpus, two independent tests:**
1. New rule fires on a title containing **no `defin` substring at all**:
   **0 rows.**
2. New rule fires on a title with a `defin` substring but no exact
   `definitions?`/`defined` token: **123 rows** — which the manager then
   classified rather than assuming:

   ```
   {'trunc': 117, 'misspell': 6, 'GENUINE_NOISE': 0, 'other': 0}   sum = 123
   ```

   All 117 are the Colorado source-truncation cluster (**R-TRUNC**, intended)
   and all 6 are the misspelling cluster (**R-MISSPELL**, intended).
   **Zero** genuine morphology-noise rows (`definite`/`undefined`/`redefine`/
   `defining`) were captured, and zero rows were unexplained. The imprecise
   thing was the manager's first audit regex, not the module.

**Verdict: on every test the manager could construct against the real corpus,
the new rule adds 20,307 recognitions and zero false positives.** Gates U1
(heading layer), U5 and U6 are satisfied at the Phase-A level; their formal
QA certification still has to run against the post-core wired state.

---

## 2026-08-04 — Manager quantification of the U2 gap (before escalating)

The Planner escalated U2 with one real example. A one-row anecdote is not a
basis for a program-level decision, so the manager measured the **size of the
affected class** across the full corpus before forwarding it.

Of the **20,308 newly-recognized headings**, the number that name a scope unit
at all is **10 — 0.05%**. Complete enumeration (this is the whole class, not a
sample):

| # | Juris | act_id | scope named |
|---|---|---|---|
| 1 | AK | `STATE_AK_T13_C13.06_S13.06.050` | multi-chapter RANGE (`AS 13.06 — AS 13.36`) |
| 2 | CT | `STATE_CT_T12_C202_S12-35b` | "for sections concerning state liens…" |
| 3 | KY | `STATE_KY_TIII_C17_S17.185` | "Definitions for section" |
| 4 | KY | `STATE_KY_TXIII_C156_S156.106` | "for section and KRS 161.605" |
| 5 | KY | `STATE_KY_TXXI_C246_S246.420` | "Definitions for section" |
| 6 | KY | `STATE_KY_TXI_C139_S139.486` | "Definitions for section" |
| 7 | NJ | `STATE_NJ_T17_C35_S35-23` | `"Agent" defined; penalty…` |
| 8 | TN | `STATE_TN_T6_C51_S6-51-101` | "Part definitions and definitions for Section 6-51-301" |
| 9 | UT | `STATE_UT_T78A_S78A_5_201` | "Definition of drug court program" |
| 10 | VA | `STATE_VA_T8.01_C1_S8.01-2` | "General definitions for this title" |

Two things this measurement changes about the escalation:

1. **The blast radius is 10 rows, not a family.** Whatever is decided, it does
   not gate the sprint's 20,307-row recall win.
2. **This is NOT new exposure created by this sprint.** The same
   inexpressible-scope shapes occur in headings baseline ALREADY recognizes
   (`Definitions for chapter.`, `Definitions for parts 2-5` — the Planner
   verified these are baseline-True today, independent of us). The seam's
   2-value scope model under-describes those rows right now, in production,
   with or without this sprint. Our 10 rows are a small increment on a
   pre-existing, larger, core-owned modelling gap — which is an argument for
   routing the scope-model question to the CORE panel as a program-level
   follow-up rather than treating it as a family-4 blocker.

Manager's lean recorded here and forwarded: ship Phase A, record these 10
`act_id`s as a named known limitation, and route the scope-model question to
core — do NOT hold a 20,307-row correctness win for a 10-row modelling gap,
and do NOT let a silently-wrong "law-wide" stamp pass unrecorded.

---

## 2026-08-04 — Program-manager ruling on U2 + scout Round 2 received

**Ruling: Option C accepted.** Ship the verified recall win; the 10 enumerated
`act_id`s are recorded in the contract as a named known limitation; the
scope-model gap is routed to the core panel. **Seam v2 will carry a generic
`(unit_kind, unit_value)` scope mechanism** — this panel must **recheck the 10
rows once core pushes v2**; if they become expressible, stamping their true
scope is a normal item, not a limitation. Routings accepted at program level
(verb-form bodies → markers; heading-absence populations → preamble; CO
truncated titles + repealed stubs → data-quality list).

**Scout Round 2 did return** (to the program manager, not to this panel).
Its results are an INDEPENDENT cross-check of the shipped rule set:

| Scout Round-2 result | Bearing on what we shipped |
|---|---|
| `True→False` flips = **0** across all rules | Confirms ruling H-R4's structural claim on real data |
| R-SEC 81 flips, R-COLON 31 — clean and **disjoint** | Matches the Planner's per-rule recall exactly |
| R-MID precision **16/20 YES** (1 NO = a repealed stub; 3 unverifiable at 400 chars) | R-MID is a good trade — shipped |
| R-VERB-EXT delta **16/20 YES** | R-VERB-extended is a good trade — shipped |
| **R-MID-NOPREP and the preposition cluster ≈10–15% precision**; the `of`-exclusion protects ~90% | **Independent confirmation that keeping the preposition exclusion was correct.** The shipped module keeps it. Had we "fixed" the preposition rule to chase 287 rows, we would have bought ~30 real captures for ~257 false ones |
| Conservative bundle union 19,452 / 22,228 | Our shipped 6-rule union is **20,307** — the difference is R-VERB-extended (765), R-TRUNC (117) and R-MISSPELL (6) minus overlap, all three of which the scout's conservative bundle excluded by construction. **QA must reconcile this arithmetic rather than assume it.** |

Scout artifacts handed to QA to RE-RUN (not re-derive): `round2_rules.py`,
`round2b_sample.py`, `round2_results.json`, `round2b_samples.json` in the
session scratchpad.

Main-checkout cleanliness independently confirmed by the program manager.
One-writer-per-worktree remains absolute.

---

## 2026-08-04 — QA report (items 7 + 8, gates U1/U3/U4/U5/U6)

Addressed to the manager. All work in `/Users/nerya/LexGraph-wt/defs-us-headings`,
branch `claude/defs-us-headings`. All scripts below are QA-authored, independent
of the Planner's/scout's/manager's own scripts (except where explicitly noted as
a re-run of the scout's own artifacts, per the brief). Scripts and intermediate
JSON live in the session scratchpad (`/private/tmp/claude-501/.../scratchpad/qa/`
and `.../scratchpad/round2*`); not committed (throwaway verification tooling,
same pattern the manager used for `manager_verify_u4_u6.py`).

### Headline verdict: gate U4 does NOT pass as claimed

The contract's claim ("the 1,921 residual rows are ... correctly-excluded ...
QA's job is to confirm that") **does not hold**. I independently recomputed the
residual set (exact reproduction: 1,921 rows) and found that **at least 556 of
those 1,921 rows (29%) match one of five concrete, mechanical tokenizer/regex
gaps in the shipped module** — not morphology noise, not preposition-guarded
true negatives. Hand-verdicting representative samples of each gap (well over
150 rows read with real body text, far past the ≥60 floor) shows a **very high
genuine-miss rate**, not the claimed 0%. I also found **one confirmed, real
false positive** via adversarial construction that slipped past both of the
manager's precision audits. Full detail below.

### Item 7 — U4 zero-miss sweep

**Independent residual computation.** Script:
`scratchpad/qa/qa_residual_sweep.py`, written from scratch (imports only
`is_definitions_heading` and `matches_heading_variant` live from the worktree
source; no reuse of the Planner/scout/manager's pre-computed pools as the
source of truth). Scans all 52 in-scope `us_*_statutes.parquet` files (PR
excluded, confirmed out of scope — separate Spanish-language sprint) directly
from the local HF cache (never downloaded by this or any committed test).

```
titles containing 'defin' : 83,303
recognized BEFORE         : 61,075
recognized AFTER          : 81,382
NEWLY recognized          : 20,307
miss pool (defin & !before): 22,228
union recall on miss pool  : 20307/22228 = 91.36%
RESIDUAL (defin & !before & !newrule): 1,921
```

**Exact reproduction** of the Planner's and manager's headline numbers, on
independently written code — third agreement on the same figures, which is
meaningful. Precision audit (independently reproduced, same methodology as the
manager's): 0 rows with no `defin` substring; 123 rows with `defin` but no
exact `definitions?`/`defined` token, decomposing (confirmed) as exactly 117
R-TRUNC + 6 R-MISSPELL, 0 unexplained. **These two precision checks hold** —
but see the Adversarial precision hunt section below for a check neither the
Planner nor the manager ran, which does not hold.

**Miss-pool well-definedness (requested sanity check).** The pool is defined
as `section_title` containing the substring `defin` — so a genuine definitions
section whose heading contains NEITHER `defin` NOR a `defined`-family word
(none exist in this corpus's drafting conventions, verified) would be
structurally invisible to this entire sweep, and so would any jurisdiction
whose `section_title` field never carries heading text at all. **Confirmed
boundary**: CA/GA/IL/MD/MS/NE have zero `defin`-containing titles (verified
directly: 0 rows across all 6 in my own scan) — this is the heading-ABSENCE
population the manager already routed to the preamble/body-derived-heading
panel. I did not re-litigate it; I confirm it is correctly out of this sweep's
reach, and that the boundary is real (not a gap silently swallowed into
either "recognized" or "residual" — those 6 jurisdictions' definitions
sections simply never enter this sweep in either direction).

#### Classification of the 1,921 residual rows

I classified the full residual set by concrete, testable shape (script:
inline, see the five `BUG*_RE` regexes run over `qa_residual_rows.json`).
Five patterns, each a genuine mechanism in the shipped module's tokenizer or
guard logic, **not mutually exclusive but union computed**:

| Pattern | Rows | Mechanism |
|---|---:|---|
| **BUG1** — mid-heading `Definitions.`/`Definition.` (interior, period-terminated) | 118 | `_tail_tokens`'s split regex `[\s\-–—:;,]+` does **not** include `.` — so an interior clause-ending period stays glued to the token (`"Definitions."` ≠ `"definitions"`), and R-MID's exact-match check silently fails. Realized almost entirely as Connecticut's own drafting convention (116 of 118): headings that enumerate every subsection topic separated by periods, e.g. `"Sec. 22a-905i. Tire stewardship program. Definitions. Tire stewardship organization. Plan. ..."` |
| **BUG2** — `defined` immediately followed by a dash (`-`/`–`/`—`/`--`), mid-heading | 421 | R-VERB-extended's punctuation set is `[;:]` only — the extremely common `"TERM defined - more clauses"` / `"TERM defined -- more clauses"` drafting convention (MO/CO/SD/KY/TN/ND/OK/UT/…) uses a dash instead, and is covered by **none** of the 6 rules |
| **BUG3** — dash acts as a clause boundary but the preposition-exclusion guard fires across it | 15 | The guard checks only the single token immediately before `definitions`/`definition`; when a dash separates `"[clause ending in a preposition] — definitions — [more clauses]"` (Missouri's own flagship convention — recall the mandate's own MO dossier example uses exactly this shape), the tokenizer collapses the dash the same as a space, so the guard misreads a NEW clause's subject as the OLD clause's object |
| **BUG4** — `/`-joined, e.g. `"Program/definitions"` | 1 | `/` is in neither the split-char class nor the trailing-bracket regex, so it never tokenizes apart |
| **BUG5** — parenthetical `(Definitions)` | 1 | The trailing-bracket regex only strips **square** brackets `[...]`; round parens survive as part of the token |
| **Union (1–5)** | **556** | 29% of the 1,921-row residual |

The remaining 1,365 rows are dominated by genuine morphology noise
(`definite`/`indefinite`/`undefined`/`redefine`), true preposition-guarded
cross-reference stubs (the majority of the `"... of/for/to Definitions"`
shape), pension-law jargon (`"defined benefit plan"` / `"defined contribution
plan"` as a compound noun, unrelated to a Definitions heading), "authority to
define" delegation clauses (a board/department empowered to define something
by future rule), and genuine cross-references to definitions declared
elsewhere. My stratified sample of this remainder (below) confirms these are
mostly, but not 100%, correctly excluded.

#### Hand-verdict sample and tally

I read real body text (fetched fresh from the parquet, not truncated to a
short excerpt where that mattered) for **well over 150 individual rows**
across two passes: (a) a stratified random sample of 102 rows drawn from 5
shape buckets covering the full residual (seed `20260804`, script:
`scratchpad/qa/qa_sample_for_verdict.json` / `qa_sample_fulltext.json`), drawn
**before** I had identified the 5 mechanical bugs; (b) targeted samples of
each bug pattern once found (BUG1: all 118, exhaustively, via a definitional-
marker regex over full text, not truncated; BUG2: a fresh 30-row random
sample, seed `20260804`, of the 421-row population; BUG3/4/5: all rows, small
enough to read exhaustively). Verdict is YES/NO/UNCLEAR per the brief's
instruction — "does this section genuinely define one or more terms, in ANY
prose or marker form, ignoring whether today's extractor can parse it."

**BUG1 (118 rows, exhaustive check, not sampled):**
- **82 YES** — confirmed by a `"Term" means` / `“Term” means` / `as used in
  this section` marker found directly in the row's full text.
- **36 UNCLEAR** — 33 of these 36 rows' `text` field starts literally with
  `"(b) ..."` (no `(a)` at all), and several explicitly cross-reference
  `"subsection (a) of this section"` that is simply absent from the `text`
  column. Given the identical drafting convention on the 82 confirmed rows
  (CT's own "as used in this section, (a) 'Term' means..." style), I judge
  these as **likely also genuine** but cannot prove it from the data
  available — flagging as UNCLEAR rather than guessing YES. This looks like
  a **separate, distinct corpus data-quality gap** (missing subsection-(a)
  text for a subset of CT rows), not a rule-precision issue — noting it here
  rather than silently treating it as this rule module's fault.
- **0 NO.**

**BUG2 (421-row population, 30-row random sample, seed 20260804):**
- **27 YES**, **3 UNCLEAR** (2 Louisiana twin-rows describing prohibited
  discharge acts without a visible `"pollution" means` clause in 1,400 chars
  read; 1 Missouri row on physical page-formatting requirements that reads as
  an operational/implicit definition of "page" but never uses "means"), **0
  NO.** 90% definitive-YES on a random sample is a strong population signal.

**BUG3 (15-row population, effectively all read via the containing 22-row
bucket): overwhelmingly YES** — the large majority contain an explicit `"the
following terms mean:"` block (this is literally Missouri's own standard
definitions-clause opener); a handful were UNCLEAR because the fetched excerpt
ended before reaching the definitions block. **0 NO.**

**BUG4 (NC) / BUG5 (WI): both YES**, confirmed (`"MH/DD/SA" means mental
health..."`; `"Appeal" means a review..."`).

**Original 102-row general stratified sample** (the 5 broad shape buckets,
covering the residual outside the crisp bug patterns; overlaps partially with
BUG2/BUG3 above where a row happened to land in both):
- `morphology_noise` (10/10 sampled): **10 NO** — UCC "payable ... at a
  definite time" (WV/CT/OR/ME/CO/FL, all the same national UCC Article 3
  provision), "indefinite delivery/quantity contract" (OH x2), etc. Correctly
  excluded: the heading itself never signals a Definitions section, even
  though the body's operative test happens to use quoted-term "if it is..."
  phrasing.
- `other_defin_substring_only` (15/15 sampled): **15 NO** — uniformly
  "authority/duty to define X" delegation clauses (a board defines something
  by future rule) or unrelated "defining boundaries" procedural provisions.
  Correctly excluded.
- `preposition_guarded_definitions` (20/20 sampled): **5 YES/borderline-YES,
  1 UNCLEAR, 14 NO.** This is the cluster the scout's Round 2 already
  quantified (`R-MID-NOPREP` ≈10–15% precision) and the manager/scout already
  decided to keep excluded as a deliberate, reasoned trade-off. My sample's
  25% true-positive rate is consistent with (a bit above) that estimate —
  **this confirms the already-known, already-accepted trade-off; it is not a
  new finding**, but see `IN 32-31-10-2` and `IN 21-44-7-1` below for two real
  examples of what is being traded away, for the manager's record.
- `has_defined_word_no_rule_match` (35/35 sampled): mixed — a real, distinct
  negative control worth recording: **pension/insurance-law jargon
  (`"defined benefit plan"` / `"defined contribution plan"` / `"defined cost
  sharing"`, ~6–8 of the 35) is correctly excluded** — the module does NOT
  chase the word "defined" as a bare adjective, which is exactly right (this
  jargon dominates the raw 1,089-row "has 'defined' somewhere" bucket and
  would have been a precision disaster to chase indiscriminately). The
  remainder of this bucket's genuine hits overlap with BUG2 above.
- `has_definitions_word_no_rule_match_other` (22/22 sampled): overlaps almost
  entirely with BUG3 above.

**Aggregate tally across every row I hand-verdicted with real body text**
(BUG1 118 exhaustive + BUG2 30 sample + BUG3/4/5 ~17 + general 102 sample,
duplicates not double-counted): **at least 139 confirmed YES**, **~43
UNCLEAR** (mostly the CT missing-subsection-(a) rows and a few excerpts I
didn't fetch far enough for), **39 confirmed NO** (all in the general
sample's morphology/authority-to-define/pension-jargon/preposition-guarded
buckets — proving the module's restraint is *mostly* correct there). **Zero
NO verdicts among the 556 bug-pattern rows.**

#### P-R2 escalation — genuine misses, real rows

Per the brief, every genuine miss found is reported here rather than noted
silently. Representative real rows (act_id, verbatim heading, why it's a
genuine miss):

1. **BUG1** — `STATE_CT_T17b_C319v_S17b-278j`, heading `"Sec. 17b-278j.
   Complex rehabilitation technology. Definitions. Report."`, body opens `(1)
   "Complex rehabilitation technology" means products classified as durable
   medical equipment...`. Missed because the tokenizer never strips the
   interior period off `"Definitions."`.
2. **BUG2** — `STATE_MO_C590_S590.650`, heading `"590.650 Racial profiling —
   minority group defined — reporting requirements — annual report — ..."`,
   body: `As used in this section "minority group" means individuals of
   African, Hispanic, Native American or Asian descent.` Missed because
   `defined` is followed by an em-dash, not `;`/`:`.
3. **BUG3** — `STATE_MO_C173_S173.685`, heading `"173.685 STEM grants,
   eligibility for — definitions — rules — sunset provision."`, body: `As
   used in this section, the following terms mean: (1) "Approved
   institution"...`. Missed because the token immediately before the dash
   (`"for"`) is a guarded preposition, even though it belongs to the
   PRECEDING clause, not to `"definitions"`.
4. **BUG4** — `STATE_NC_C122C_S122C-11`, heading `"§ 122C-11. MH/DD/SA
   Consumer Advocacy Program/definitions"`, body: `(1) "MH/DD/SA" means
   mental health, developmental disabilities, and substance abuse.` Missed
   because `/` never tokenizes.
5. **BUG5** — `STATE_WI_C809_S809.01`, heading `"Rule (Definitions)."`, body:
   `(1) "Appeal" means a review in an appellate court...`. Missed because the
   trailing-bracket regex only handles `[...]`, not `(...)`.
6. **Preposition-guard trade-off, for the record (not a new escalation, the
   trade-off is already accepted)** — `STATE_IN_T32_A31_C10_S32-31-10-2`,
   heading `"Applicability of definitions; \"eviction action\""`, body: `(2)
   "eviction action" means: (A) an action for possession of the rental
   premises...`; and `STATE_IN_T21_A44_C7_S21-44-7-1`, heading `"Application
   of definitions"`, body: `The following definitions apply throughout this
   chapter: (1) "Board" refers to... (2) "Fund" refers to...`. Both are real
   misses inside the deliberately-excluded preposition-guarded cluster.

Full row lists for BUG1 (118), BUG2 (421 population / 30 sample), BUG3 (15)
are in `scratchpad/qa/qa_mid_period_hits_fulltext.json`,
`scratchpad/qa/qa_dash_defined_hits.json` /
`qa_dash_defined_sample.json`, and the relevant slice of
`qa_sample_fulltext.json` respectively — available for the manager/Developer
to re-open directly.

**My assessment for the manager**: BUG1–BUG5 are not judgment calls the way
the preposition-guarded cluster is (that one is a real precision/recall
trade-off, already reasoned through and accepted). BUG1–BUG5 are places where
the module's OWN stated design intent ("match X" per ruling H-R4, extending
R-VERB's own already-accepted dash-adjacent-punctuation pattern, extending
R-MID's own already-accepted mid-token pattern) silently fails to fire on
real, common, high-volume drafting shapes already inside the six rules'
intended scope — not a new precision trade-off, but an implementation gap in
rules the sprint already committed to shipping. I am reporting this as a
**P-R2 escalation**: recall on the 20,307/22,228 = 91.4% headline is real and
correct as measured, but the residual is NOT the "confirmed correctly
excluded" set the contract claims — a substantial, well-evidenced fraction
(conservatively 556 rows, likely closer to 450–500 after excluding the
~36-row CT missing-data UNCLEAR set and the handful of BUG2/BUG3 UNCLEARs)
are real, capturable misses under the director's absolute zero-miss bar.

### Item 8 — U6 independent measurement

Own script (not a run of `manager_verify_u4_u6.py`): folded into
`scratchpad/qa/qa_residual_sweep.py`'s single pass (per-state counters
computed alongside the residual sweep, to avoid a second multi-minute corpus
scan — the before/after logic itself is independently written, not copied).
Output: `scratchpad/qa/qa_u6_per_state.json`.

| State | defin | before | after | newly | before% | after% |
|---|---:|---:|---:|---:|---:|---:|
| WA | 2,424 | 1,800 | 2,339 | 539 | 74.3% | **96.5%** |
| FL | 952 | 805 | 938 | 133 | 84.6% | **98.5%** |
| NY | 1,619 | 1,479 | 1,597 | 118 | 91.4% | **98.6%** |

**Confirms the mandate's three named states move, exactly matching the
manager's own figures** (independently reproduced, not copied). Top movers
also reproduced exactly: NV 12.4%→99.6% (+8,878), IN 22.3%→90.3% (+1,790), MI
63.9%→99.2% (+1,594), SD 47.2%→91.1% (+743). 52 jurisdictions covered (PR
excluded). **Gate U6: CONFIRMED.**

### Scout Round 2 cross-check

Re-ran the scout's own scripts (not re-derived): `round2_rules.py` and
`round2b_sample.py`, both from the session scratchpad, against the same
cached `miss_pool.jsonl`/`true_pool_titles_only.jsonl`/`cluster_results_v2.json`
inputs.

- **`round2_rules.py` reproduced exactly**: `True→False` flips = 0 for every
  rule (R-SEC, R-COLON, R-MID, R-MID-NOPREP, R-VERB-BARE, R-VERB-EXT,
  R-MISSPELL); R-SEC 81 flips, R-COLON 31 flips, intersection 0 (disjoint,
  confirmed); R-MID-NOPREP delta over R-MID = 362; R-VERB-EXT delta over
  R-VERB-BARE = 1,810; conservative bundle `{R-SEC, R-COLON, R-MID,
  R-VERB-BARE}` union = **19,452**, exactly matching the log's figure.
- **`round2b_sample.py` reproduced byte-for-byte** (`diff` against the
  original `round2b_output.txt` on the first 50 lines: identical) — confirms
  the fixed-seed samples are genuinely deterministic/reproducible, not a
  one-off artifact.

**Arithmetic reconciliation (explicitly required by the brief, verified, not
assumed).** Wrote a fresh script using the shipped module's own `_rule_sec`,
`_rule_mid`, `_rule_verb_bare`, `_rule_verb_extended`, `_rule_trunc`,
`_rule_misspell` directly against the full 22,228-row miss pool:

```
conservative bundle {R-SEC, R-MID, R-VERB-bare} union : 19,452
shipped matches_heading_variant union                 : 20,307
shipped MINUS conservative bundle                      :    855
  explained by R-VERB-extended                         :    732
  explained by R-TRUNC                                 :    117
  explained by R-MISSPELL                               :      6
  UNEXPLAINED                                           :      0
full-population sizes: R-VERB-extended=765, R-TRUNC=117, R-MISSPELL=6, sum=888
overlap with conservative bundle (already captured by R-SEC/R-MID/R-VERB-bare): 33
888 - 33 = 855  ✓ exact match
```

**The arithmetic reconciles exactly, with zero unexplained rows.** The
manager's expected formula (`R-VERB-extended + R-TRUNC + R-MISSPELL − overlap`)
is confirmed correct on real data, not merely assumed.

### Regression + U5 + U3

**Full suite**: `backend/.venv/bin/pytest backend/tests -v` →

```
FAILED backend/tests/integration/test_us_heading_variants_end_to_end.py::TestRealProductionPipeline::test_connecticut_ucc_row_produces_real_definitions_via_the_real_pipeline
FAILED backend/tests/unit/test_definition_links_rules_registry_integration.py::test_module_self_registers_exactly_one_heading_rule_for_us_star
================= 2 failed, 669 passed, 18 warnings in 14.19s ==================
```

Exactly the 2 core-blocked failures predicted by the contract, both via a
genuine assertion / genuine `ImportError` tied to the missing
`app.definition_links.rules.registry` (not yet merged from
`claude/defs-core-scope`) — **no third failure, baseline 641 fully preserved
inside the 669.** **Gate U5 (regression): CONFIRMED at the Phase-A level.**

**Gate U3**:
```
git diff --stat 83532fe...HEAD -- backend/app/
 .../definition_links/rules/us_heading_variants.py | 269 +++++++++++++++++++
 1 file changed, 269 insertions(+)
```
Exactly one new file, zero edits to any existing shared module. `--
backend/tests/` shows only the Planner's own RED-test deliverables (5 files,
1,277 insertions — tests, fixtures, README), no Developer edits mixed in.
**Gate U3: CONFIRMED.**

### Adversarial precision hunt (item under "Regression + U5")

Beyond the manager's two audit tests (no-`defin`-substring / morphology-token
probes), I constructed 18 of my own synthetic attack headings (repealed-stub
shapes, cross-reference-only phrasing, incidental "defined"/"definition"
mentions, ALL-CAPS, mojibake/BOM/nbsp leading noise) and ran them through
`matches_heading_variant`. 15/18 correctly stayed False. **3 fired True**;
I then checked each against the real corpus to see whether the vulnerability
is actually realized in production, not just hypothetical:

1. **`"Article 5 Definitions repealed"`** (synthetic: mid-token `Definitions`
   immediately followed by a stub-signal word) — fires True in isolation, but
   **0 real corpus rows** match this shape (`definitions [repealed/omitted/
   reserved/vacant/deleted]` mid-heading, checked exhaustively across all 52
   files). Theoretical, not realized. No action needed.
2. **`"Application of the definitions found in Article 3"`** (synthetic: an
   article — "the"/"a"/"an" — inserted between the governing preposition and
   `definitions`, defeating the guard, which only inspects the single
   immediately-preceding token) — **CONFIRMED, REAL, currently realized in
   production**: `STATE_ME_T15_P4_C305-A_S2123-A`, real heading `"15 §2123-A.
   Method of review for administrative actions not included in the
   definition of \"post-sentencing proceeding\""`. Full body (single
   sentence): `Remedial relief from administrative actions ... that are not
   included in the definition of "post-sentencing proceeding" in section
   2121, subsection 2 is exclusively provided by Title 5, chapter 375,
   subchapter 7.` **This defines zero terms** — it is a jurisdictional
   cross-reference to a definition declared elsewhere (section 2121), exactly
   analogous to the already-confirmed TX true-negative pattern. It is
   `is_definitions_heading()` = False, `matches_heading_variant()` = True: a
   **genuine, real false positive**, newly introduced by this sprint's rule
   module, that passed both of the manager's precision audits undetected
   (the manager's `REAL_TOKEN_RE` correctly finds a standalone `"definition"`
   token here — it was never designed to catch "real token, wrong grammar").
   **P-R2 escalation.**
3. **`"﻿\xa0Sec. 4. Miscellaneous provisions; definition of terms used
   elsewhere"`** — fires True via R-MID with a legitimate non-prepositional
   preceding token (`"provisions"`); on inspection this is not actually the
   preposition-guard bypass I was probing for (the real preposition-guard
   shape needs the excluded word BEFORE `definitions`, not after) — I do not
   believe this is a defect, just a benign match on a synthetic string with
   no real-corpus counterpart to check.

**Also flagging (not a new defect, matches an already-documented
phenomenon)**: 35 of the 20,307 newly-recognized rows have a body that is
exactly `"Repealed."` (e.g. `STATE_DC_T50_C13_S50-1301.57`, `"§ 50-1301.57.
'Motor vehicle liability policy' defined."` → `Repealed.`), plus 62 more with
bodies under 40 characters (mostly DC "Recodified at..."/"Omitted." stubs and
4 Maine "REALLOCATED TO..." stubs). This is the same textually-correct/
zero-extraction-value phenomenon the scout already documented for baseline
(341 such rows, "pre-existing behaviour, not caused by this sprint") — now
proportionally present in the new rule's larger catch too. Not a defect, just
recorded so it isn't later mistaken for one.

### Per-gate verdict summary

| Gate | Verdict | Proven by |
|---|---|---|
| U1 | Heading-layer recognition holds for the rule set as specified | Unit suite 19/19, composed e2e 8/8 (re-run, unchanged from manager's numbers) |
| U3 | **CONFIRMED** | `git diff --stat 83532fe...HEAD -- backend/app/` = exactly 1 new file |
| U4 | **DOES NOT PASS AS CLAIMED** | Independent residual recompute (1,921, exact match) + classification found 556 rows (29%) matching 5 concrete tokenizer/regex gaps, hand-verdict sample confirms high genuine-miss rate (≥139 YES, 0 NO among bug-pattern rows) — see P-R2 escalation above |
| U5 | **CONFIRMED at Phase-A level** | Full suite 669 passed / 2 failed, exactly the core-blocked pair, zero regressions; **but** see the confirmed false positive (ME row) under the adversarial hunt — a real, if narrow, precision defect |
| U6 | **CONFIRMED** | Independent per-state before/after script reproduces WA 74.3%→96.5%, FL 84.6%→98.5%, NY 91.4%→98.6% exactly |

### What I could NOT verify

- Did not hand-verdict all 1,921 residual rows individually — read well over
  150 with real body text (the 556 bug-pattern rows nearly exhaustively, plus
  a 102-row general stratified sample of the remainder), which is the
  brief's "substantial random sample... more if the shapes are
  heterogeneous" bar, but the exact true-miss count among the ~43 UNCLEAR and
  the un-sampled remainder of the 1,365 "no identified bug" rows is not
  individually confirmed.
- The 36 BUG1 UNCLEAR rows' true status hinges on whether CT's `text` column
  is really missing subsection (a) content (I'm confident of the *symptom* —
  33/36 start literally with `"(b) "` — but have not traced *why* the corpus
  extraction drops it, which is out of this sprint's scope).
  the 2 LA and 1 MO UNCLEAR rows in the BUG2 sample similarly need a fuller
  body read than I fetched (up to 1,400–3,000 chars) to resolve definitively.
- Have not verified whether fixing BUG1–BUG5 is feasible without new
  precision risk of its own (e.g. widening the tail-tokenizer to strip
  interior periods, or teaching the preposition guard about clause
  boundaries, could plausibly introduce new false positives elsewhere in the
  corpus) — that is implementation work, not QA's to prescribe; flagging the
  gap, not the fix.
- Did not run the frontend suite (not touched by this sprint, per the
  contract).
- Have not verified jurisdictions outside the 52 in-scope
  `us_*_statutes.parquet` files (constitutions, PR) — confirmed out of scope.

### Branch state

All commits on `claude/defs-us-headings`. This report is doc-only
(this log file). No `backend/app/**` or `backend/tests/**` files touched —
role separation held throughout (I read and analyzed, but wrote no
test/fixture files, since every finding above is reported for the Planner to
turn into RED tests, not something QA authors itself).

---

## 2026-08-04 — Manager verdict on QA cycle 1: BOUNCE. U4 fails.

QA (Sonnet/high — adversarial verification + per-row legal-text judgement;
Haiku considered, rejected) delivered at `6a50349`, doc-only. **Role
separation held**: `git diff --stat 1ce38e7...HEAD -- backend/app/` is empty;
QA touched no implementation.

**The manager re-ran QA's six load-bearing claims directly against the shipped
module. All six reproduced exactly** — "QA said so" is not evidence, so this
was checked, not accepted:

| Claim | baseline | new rule | expected | result |
|---|---|---|---|---|
| BUG1 CT interior period | False | False | False | CONFIRMED |
| BUG2 MO dash after `defined` | False | False | False | CONFIRMED |
| BUG3 MO preposition across dash | False | False | False | CONFIRMED |
| BUG4 NC `/`-joined | False | False | False | CONFIRMED |
| BUG5 WI `(Definitions)` | False | False | False | CONFIRMED |
| **FP** ME "definition of" + article | False | **True** | True | **CONFIRMED** |

### Manager ruling H-R7 — this is a defect bounce, not scope creep

BUG1–BUG5 are **not** new rules, new families, or new precision trade-offs.
Each is a place where a rule the sprint **already committed to shipping**
silently fails to fire on a real, common drafting shape squarely inside its
own stated intent — a tokenizer/guard implementation gap. With **0 NO verdicts
across all 556 bug-pattern rows** and 139+ confirmed YES read from real
bodies, these are genuine misses under the director's absolute zero-miss bar.
They go back to the Developer as a normal QA cycle. The ME false positive is
a precision defect in the same module and is fixed in the same cycle.

Gates U3, U5 (regression), U6 stand CONFIRMED by QA's independent
re-measurement. **U4 FAILS.** `qa_cycles: 1`; items 1–2 return to in-progress.

### What QA got right that matters beyond this sprint

- It **reproduced 22,228 / 20,307 / 91.4% and the WA/FL/NY figures on
  independently written code** — that is now three agents agreeing to the row.
- It **verified the scout arithmetic instead of assuming it**: shipped union
  20,307 − conservative bundle 19,452 = 855 = R-VERB-extended(732 of 765) +
  R-TRUNC(117) + R-MISSPELL(6), overlap 33, **zero unexplained**.
- It confirmed the module's *restraint* is correct where it matters: 10/10 NO
  on morphology noise, 15/15 NO on "authority to define" delegation clauses,
  and it correctly does NOT chase pension-law jargon (`"defined benefit
  plan"`), which dominates the raw `defined`-containing bucket and would have
  been a precision disaster.

### Routed onward (not this sprint's work)

- **~36 Connecticut rows whose `text` column appears to omit subsection (a)**
  entirely (bodies starting at `(b)`, cross-referencing an absent `(a)`) —
  a corpus data-quality gap, not a matcher gap. → program data-quality list.
- **35 newly-recognized rows whose body is exactly `"Repealed."`** plus ~62
  more sub-40-character stubs — the same textually-correct/zero-value
  phenomenon already documented for baseline (341 rows). Not a defect;
  recorded so it is not later mistaken for one.

---

## 2026-08-04 — Developer cycle 2 verified by the manager

Dev cycle 2 at `965880a`. Manager verification, all re-run independently:

- **All six defects fixed, all guards still hold** (manager probe): BUG1–BUG5
  now True; the ME false positive now False; and the four standing guards (TX
  `APPLICABILITY OF DEFINITIONS`, morphology `undefined`, `Repeal of
  definitions`, `Terms as defined in section 5`) all still False.
- **Full suite**: 669 passed, 2 failed — the same two core-blocked tests, no
  third failure, baseline 641 intact.
- **U3 still holds**: exactly one production file; 299 lines (under the
  300-line style gate); zero Developer edits to tests.

**Manager's independent full-corpus re-measurement:**

```
recall  20,307/22,228 (91.4%)  ->  20,864/22,228 (93.9%)
residual        1,921          ->           1,364
```

**A discrepancy the manager chased rather than accepted.** The manager's audit
reported **128** non-canonical-token matches where the Developer reported
**123**. Re-running the audit with a corrected word-boundary class (`/`, `.`,
`(`, `)` are boundaries too — exactly the punctuation the BUG4/BUG5 fixes
introduced) gives:

```
{'trunc': 117, 'misspell': 6, 'GENUINE_NOISE': 0, 'other': 0}   total = 123
```

**The Developer was right and the manager's first script was stale.** Recorded
because the sprint's standard is that a number is checked, not asserted — in
this instance the check exonerated the code and corrected the manager.

**Net result of cycle 2: +557 rows recognized, one real false positive
removed, zero new false positives, zero regressions.**

### H-R8 — one deliberate residual, recorded not hidden

The Developer declined to chase federal `"Property defined-(Rule)"` (single
hyphen, no whitespace). Its BUG2 regex requires whitespace before a lone
hyphen precisely so `"defined-benefit plan"` pension jargon stays excluded —
which QA cycle 1 identified as the dominant shape in the raw `defined`
bucket and a precision disaster to chase. **Manager accepts**: one row traded
to protect a large jargon class is the right side of that trade, and it is
recorded here rather than left silent.

---

## 2026-08-04 — QA cycle 2 report (gate U4 certification)

Addressed to the manager. All work in `/Users/nerya/LexGraph-wt/defs-us-headings`,
branch `claude/defs-us-headings`, HEAD `d37387f` at start of this cycle. All
scripts below are QA-authored from scratch this cycle (independent of the
Planner's/scout's/manager's/my-own-cycle-1 scripts), against the real live
`is_definitions_heading` / `matches_heading_variant` imported from the
worktree source. Scripts and intermediate JSON live in the session
scratchpad (`.../scratchpad/qa2/`); not committed (throwaway verification
tooling, same pattern as cycle 1 and the manager's own scripts). Every
number below was independently computed, not taken from the log.

### Headline verdict: gate U4 still does NOT pass — a SIXTH mechanical gap found

Cycle 2 fixed all six of cycle 1's findings cleanly (verified below) and the
1,921→1,364 residual shrink is real. But hunting the new residual the same
way I hunted the old one (classify, don't just spot-sample) turns up a
**sixth mechanical gap in the same module, same class of defect as
BUG1–BUG5**: `R-VERB-extended`'s punctuation/connector set after `defined`
(`;`, `:`, dash) is still too narrow. Real corpus drafting commonly follows
`defined` with the word **`for`**, a **comma**, a **period**, or the word
**`as`** — none of which fire the rule, even though R-MID (the noun-form
rule) already treats period/`/`/`(`/`)` as boundaries. Full detail in item 1.

### Item 1 — U4 residual recompute, classification, sixth-gap hunt

**Independent residual computation.** Script: `scratchpad/qa2/residual_sweep.py`,
written from scratch (imports only `is_definitions_heading` and
`matches_heading_variant` live). Scans all 52 in-scope `us_*_statutes.parquet`
files from the local HF cache (never downloaded by this or any committed test).

```
titles containing 'defin'  : 83,303
recognized BEFORE          : 61,075
recognized AFTER           : 81,939
newly recognized           : 20,864
miss pool (defin & !before): 22,228
union recall on miss pool  : 20864/22228 = 93.86%
RESIDUAL (defin & !before & !newrule): 1,364
```

**Confirms the manager's claimed 20,864/22,228 (93.9%) and residual 1,364
exactly**, on independently written code.

**Precision audit, corrected-boundary methodology (per the brief).** Script:
`scratchpad/qa2/precision_audit.py`, word-boundary regex treating `/`, `.`,
`(`, `)` as boundaries (the manager's corrected methodology, re-derived
independently, not copied):

```
fires with NO 'defin' substring at all              : 0
fires with 'defin' substring but no canonical token : 123
  trunc    : 117
  misspell : 6
  other (UNEXPLAINED) : 0
```

**Confirms the corrected 123 exactly** (not the stale 128). Both precision
checks hold.

**Classification of the 1,364 residual.** Script: `scratchpad/qa2/classify_residual.py`
(regex buckets in priority order — morphology noise, pension jargon,
preposition-guarded tail, authority-to-define delegation, everything else):

| Bucket | Rows | Disposition (hand-verdicted sample) |
|---|---:|---|
| morphology noise (`definite`/`indefinite`/`undefined`/`redefin*`/`defining`) | 252 | 15 sampled, **0 genuine misses** — 13/15 clear NO (UCC "payable at a definite time", park-boundary redefinition, authority-to-define-by-rule delegation phrased with "defining"), 2 borderline (a bare-quoted-term heading and the UCC clause) already reasoned through in cycle 1 as correctly outside these rules' design scope, not a new miss |
| pension jargon (`defined benefit/contribution/cost`) | 157 | 15 sampled, **0 genuine misses** — all are procedural sections *about* such plans, not sections defining the term itself; matches cycle-1's finding |
| preposition-guarded tail (`... of/for/to/... Definitions`) | 245 | 15 sampled, **0 genuine misses** — dominated by an Indiana "the definitions in this chapter apply throughout this article" cross-reference convention (definitions declared elsewhere); consistent with the already-accepted trade-off |
| authority-to-define delegation | 15 | 12 sampled (of 15), **0 genuine misses** — "board/AG/department may define X [by future rule]" |
| everything else | 695 | **see sixth-gap finding below — this is where it lives** |

**The sixth mechanical gap.** Reading the "everything else" bucket's random
sample (not spot-checking — classifying, per the brief's explicit
instruction to repeat the method that found BUG1–5) surfaced a repeating
shape: `"Term" defined for X`, `Term defined, X`, `"Term" defined. X`, and
`Term defined as X` — `defined` followed by a **word or comma or period**
instead of `;`/`:`/dash. None of these fire `_rule_verb_extended` (which
requires punctuation immediately after `defined`) or `_rule_verb_bare`
(which requires `defined` to be the very last tail token — it isn't, there's
more clause text after it in every one of these). Full-corpus census, script
`scratchpad/qa2/full_defined_census.py` + `hunt_gap_b_c.py` +
`hunt_sixth_gap.py` (baseline False, new-rule False only):

| Sub-shape | Rows | Sample read | Verdict |
|---|---:|---|---|
| `defined for <clause>` | 109 | 43 (stratified by state) | **37 YES, 3 NO, 2 UNCLEAR, 1 REPEALED-STUB** |
| `defined, <clause>` | 31 | all 31 | **~29 YES (23 fully confirmed + 6 pattern-consistent but not fully read), 0 NO, 2 UNCLEAR** (1 CT missing-(a), 1 federal needs deeper read) |
| `defined. <clause>` (interior period) | 23–26 | all 23 candidates + deep full-text search on the 26 | **4 confirmed YES** via an explicit `"Term" means` marker found deep in the full `text` field (not the truncated excerpt) — `STATE_CT_T15_C268_S15-140q`, `STATE_CT_T19a_C368a_S19a-77`, `STATE_CT_T20_C384_S20-197`, `STATE_CT_T31_C567_S31-232l`; remaining ~19 UNCLEAR (same pre-existing, already-routed CT "text column omits subsection (a)" data-quality issue cycle 1 already flagged — **not a new finding**), 0 confirmed NO (1 row, `STATE_CT_T38a_C704_S38a-818` "Hearing on unfair practice **not so defined**", is a plausible true-negative on grammar alone but body is an unreadable citation-annotation stub — flagged as a precision caveat for whoever fixes this, not counted either way) |
| `defined as <clause>` | 25 | 5 spot-checked | **5/5 YES** (`"Abandon" DEFINED AS LEAVING TO ATTRACT CHILDREN`, `Egg -- when defined as unfit for human food`, `Systems defined as utilities`, `Fiduciary defined as used in ss. 518.11-518.14`, `Ritual slaughter defined as humane`) — not exhaustively read, but the pattern is as consistent as the other three sub-shapes |
| leading-adjective `Defined <noun>` (e.g. `Defined term`) | 17 | all 17 | 16 are the already-known pension-jargon class (`Defined contribution fund`, etc. — correctly excluded), **1 genuine miss**: `USC_T15_C122_S9801`, `"Defined term"`, body `In this title, the term "COVID–19 public health emergency"— (1) means the public health emergency first declared...` |
| **Total candidate rows** | **~192** | | **overwhelming majority genuine YES where readable; the UNCLEAR rows are the same pre-existing CT data gap already routed, not new noise** |

I explicitly checked and ruled OUT three superficially similar shapes as
**not** part of this gap (already-correctly-excluded, consistent with
established precedent, sampled and read):
- `defined in <clause>` (25 rows) — dominated by cross-reference (`"X" as
  defined in [federal law / another section]` — the definition lives
  elsewhere), same class as the already-fixed ME false positive and the TX
  true negative. Sampled 2 in depth (`STATE_MI_..._S289.1113`,
  `STATE_MI_..._S324.63501`), both genuine cross-references, correctly
  excluded.
- `defined by <clause>` (23 rows) — dominated by delegation-to-rule/ordinance
  (`"Undue hardship"—Defined by rule.`) or general "crimes are creatures of
  statute" meta-statements (`All offenses defined by statute.`), not this
  section's own definition. Sampled 3 in depth, all correctly excluded.
- `defined AREA(S)` / `defined BENEFIT/CONTRIBUTION/COST` (~314 rows within
  the 674 total `defined`-containing residual rows) — the pension/municipal-
  taxing-district jargon class, confirmed correctly excluded (see item 2's
  pension-jargon guard check, which is the same mechanism).

**P-R2 escalation — representative real rows, one per confirmed sub-shape:**

1. **`defined for`** — `STATE_KY_TXVIII_C214_S214.280`, heading `"Mattress"
   defined for KRS 214.290 to 214.310`, body: `As used in KRS 214.290 to
   214.310, "mattress" means any mattress, mattress pad or cushion...`.
2. **`defined,`** — `STATE_NJ_T58_C16A_S16A-102`, heading `"Emergency
   supplies" defined, regional directory database.`, body: `As used in this
   section "emergency supplies" means, but is not limited to: equipment such
   as vehicles...`.
3. **`defined.`** — `STATE_CT_T31_C567_S31-232l`, heading `Sec. 31-232l.
   Ineligibility for extended benefits. Suitable work defined. Duties of
   State Employment Service.`, body (found via full-text search past the
   visible `(b)`-only excerpt): `(c)(1) For purposes of this section,
   "suitable work" means any work which is within an individual's...`.
4. **`defined as`** — `STATE_ID_T18_C58_S18-5817`, heading `"ABANDON"
   DEFINED AS LEAVING TO ATTRACT CHILDREN.`, body: `"Abandon" means leaving
   unattended and uninclosed such appliance, in such manner and for such
   time that playing children may be attracted thereto...`.
5. **Leading-adjective** — `USC_T15_C122_S9801`, heading `Defined term`,
   body: `In this title, the term "COVID–19 public health emergency"— (1)
   means the public health emergency first declared on January 31, 2020...`.

**My assessment for the manager**: same framework as cycle 1's H-R7 finding
— this is not a new precision trade-off (unlike the preposition-guarded
cluster or the pension-jargon class, which are reasoned, accepted, and
correctly still excluded). It is a place where a rule the sprint already
committed to shipping (`R-VERB-extended`'s own stated purpose: `defined` +
punctuation + more clause text) silently fails to fire on real, common,
high-volume drafting shapes squarely inside its own intent, for the same
underlying reason BUG1 existed (a separator class that's narrower than the
rule's own design). Roughly 192 residual rows carry this shape, with a
strong, sample-confirmed genuine-miss rate in three of five sub-shapes and
a smaller but real confirmed rate in the fourth (period, CT-blocked by a
pre-existing, already-routed data issue for most of its rows, but not all —
4 confirmed YES survive that noise). **P-R2 escalation.**

### Item 2 — verification of the 558 newly-captured rows

**Independent reproduction of "exactly 558".** Script: `scratchpad/qa2/flip_check.py`,
loads the cycle-1 module (`git show c986001:...`) via `importlib` alongside
the live cycle-2 module and diffs their verdicts across all 22,228 miss-pool
rows (not a sample): **exactly 558** False(cycle1)→True(cycle2) flips,
tagged by which rule newly fires (`scratchpad/qa2/classify_558.py`):
**419 via `_rule_verb_extended` (BUG2), 139 via `_rule_mid`** (covers
BUG1=118 + BUG3=15 + BUG4=1 + BUG5=1 + 4 duplicated-number SD rows = 139) —
**exact match to the Developer's own breakdown.**

**Own random sample, ≥40 as required, weighted toward BUG2 (the largest,
riskiest change).** Script: `scratchpad/qa2/sample_558.py`, seed `20260804`:
**32 rows from the 419-row `_rule_verb_extended` (BUG2) population + 18 rows
from the 139-row `_rule_mid` population = 50 total.** Read real body text
(`scratchpad/qa2/qc2_sample_558.json`).

**Tally:**
- BUG2 dash-widening (32 rows): **31 YES, 1 REPEALED-STUB, 0 NO, 0 UNCLEAR.**
  All 31 YES rows show explicit `"Term" means`/`is`/`includes`-style
  definitional content matching the heading's named term (e.g.
  `STATE_MO_C542_S542.266` "Search warrant defined": `A search warrant is a
  written order of a court...`). The 1 REPEALED-STUB
  (`STATE_ND_T40_C40-57.1_S40-57.1-04.2`, body `Repealed by S.L. 1991, ch.
  447, § 10.`) matches the already-documented, already-accepted
  textually-correct/zero-extraction-value phenomenon from cycle 1 (35+62
  such rows already recorded) — not a defect.
- `_rule_mid` (18 rows, mostly Connecticut BUG1 rows): **11 YES, 7 UNCLEAR,
  0 NO.** All 7 UNCLEAR are the same pre-existing, already-routed CT
  "`text` column starts at `(b)`, subsection (a) is missing" data-quality
  gap cycle 1 already flagged — not a new finding. One UNCLEAR row
  (`STATE_CT_T4a_C58a_S4a-101`) turned out, on reading the FULL text (not
  just the visible `(b)` excerpt), to have its definitions in subsection
  (c) — confirmed **YES** on closer read (moved from UNCLEAR to YES in the
  final tally above).

**Combined: 42 YES, 7 UNCLEAR, 1 REPEALED-STUB, 0 NO** across the 50-row
sample — **zero false positives found**, exceeding the ≥40 floor.

**Pension-jargon guard re-confirmed under the BUG2 dash-widening
specifically** (the brief's explicit ask). Script:
`scratchpad/qa2/pension_jargon_check.py`, full 52-file scan for headings
matching `defined[\s-]{1,3}(benefit|contribution|cost|value)`: **165 total
matching headings corpus-wide, exactly 1 newly fires True**
(`STATE_NJ_T43_C15C_S15C-1`, `"Defined Contribution Retirement Program;
rules, regulations; terms defined."`) — and that one fires via
`_rule_verb_bare` on the heading's OWN trailing `"...terms defined."`
clause (unrelated to the "Defined Contribution" program name at the
heading's start), on a row whose body genuinely defines `"Base salary"` and
other terms — a correct, legitimate match, not a defeat of the guard. Also
directly tested 4 synthetic `"defined-benefit plan"` / zero-whitespace
hyphen variants: all 4 stay `False`. **The pension-jargon exclusion holds
exactly as designed, including against the BUG2 dash-widening.**

### Item 3 — True→False flip verification

Same `flip_check.py` run (full 22,228-row scan, not a sample): **exactly 1**
True(cycle1)→False(cycle2) flip, and it is `STATE_ME_T15_P4_C305-A_S2123-A`
(the ME row) — **confirmed, no extras.**

### Item 4 — Adversarial precision hunt, round 2

Targeted the new attack surface cycle 2 opened: `.`/`/`/`(`/`)` as token
boundaries, the dash-boundary-aware preposition guard, and the
article-skipping guard (checking the True→False direction too, not just
False→True). Constructed 8 synthetic headings
(`scratchpad/qa2/adversarial_hunt2.py` + inline probes); 4 fired
unexpectedly `True` in isolation. Checked each against the real corpus
(same "theoretical vs. realized" methodology that found the ME false
positive in cycle 1):

1. **Parenthetical cross-reference exploit** — `"Program requirements (see
   also definitions in section 5)."` fires `True` (the word `also`, not a
   preposition, sits immediately before the paren-exposed `definitions`
   token, so the guard never engages). Full-corpus check: **0 real rows**
   match this shape (`(see also definitions`/`(also definitions` anywhere
   in a residual or captured heading). **Theoretical, not realized** — same
   disposition as cycle 1's `"Article 5 Definitions repealed"` finding. No
   escalation.
2. **Dash-defeats-guard exploit** — `"Repeal of — Definitions"` /
   `"Repeal of--Definitions"` fire `True` (BUG3's dash-boundary rule treats
   ANY dash right before the candidate as a fresh clause, even when the
   dash sits directly after the very preposition that should govern it).
   Full-corpus check for `<preposition> <dash> definitions?`: **realized 15
   times**, but on reading real body text, **all 15 are genuine correct
   matches** — every one is the Missouri "clause — clause — clause" list
   convention BUG3 was explicitly built to fix (`"STEM grants, eligibility
   for — definitions — rules — sunset provision."`, body: `the following
   terms mean: (1) "Approved institution"...`), not a case where the dash is
   spuriously interposed between a preposition and its real object. 13/15
   confirmed via explicit `"Term" means`/`"official" means` markers in
   body text; the remaining 2 (`STATE_MO_C393_S393.1655`,
   `STATE_WA_T31_C12_S267`) are consistent with the same pattern but not
   fully confirmed from the available excerpt. **Not a vulnerability — this
   is BUG3 generalizing correctly, not a new defect.** No escalation.

No False→True precision defect found this round (matching item 3's
exhaustive corpus-wide confirmation of exactly one flip, which was in the
True→False direction). **No new false positive found in round 2** — a
different, cleaner result than cycle 1's round 1, which did find one (the
ME row, now fixed).

### Item 5 — Regression + gates

**Full suite**, `backend/.venv/bin/pytest backend/tests -v`:

```
FAILED backend/tests/integration/test_us_heading_variants_end_to_end.py::TestRealProductionPipeline::test_connecticut_ucc_row_produces_real_definitions_via_the_real_pipeline
FAILED backend/tests/unit/test_definition_links_rules_registry_integration.py::test_module_self_registers_exactly_one_heading_rule_for_us_star
2 failed, 669 passed, 18 warnings in 13.24s
```

Exactly the 2 core-blocked failures, same pair as every prior run, baseline
641 fully preserved inside the 669. **No third failure.**

**Gate U3**:
```
git diff --stat 83532fe...HEAD -- backend/app/
 .../definition_links/rules/us_heading_variants.py | 299 +++++++++++++++++++++
 1 file changed, 299 insertions(+)
```
Exactly one file. `git show --stat 965880a -- backend/tests/` is **empty** —
the Developer's cycle-2 commit touched zero test files. **U3 CONFIRMED.**

**Gate U6, own script** (`scratchpad/qa2/residual_sweep.py`, per-state
counters computed in the same pass as the residual sweep):

| State | defin | before | after | newly | before% | after% |
|---|---:|---:|---:|---:|---:|---:|
| WA | 2,424 | 1,800 | 2,385 | 585 | 74.3% | **98.4%** |
| FL | 952 | 805 | 938 | 133 | 84.6% | **98.5%** |
| NY | 1,619 | 1,479 | 1,597 | 118 | 91.4% | **98.6%** |

All three named states move, hard, independently reproduced. **U6 CONFIRMED.**

### Per-gate verdict summary

| Gate | Verdict | Proven by |
|---|---|---|
| U1 | Heading-layer recognition holds for the rule set as specified | Unaffected by this cycle's findings; unit/e2e suite unchanged and still green (28/30, 2 core-blocked) |
| U3 | **CONFIRMED** | `git diff --stat 83532fe...HEAD -- backend/app/` = exactly 1 file; `git show --stat 965880a -- backend/tests/` = empty |
| U4 | **DOES NOT PASS** | Independent residual recompute (1,364, exact match) + classification found a SIXTH mechanical gap (~192 candidate rows: `defined for`/`,`/`.`/`as`/leading-adjective), hand-verdict samples show a strong genuine-miss rate in 4 of 5 sub-shapes (37/43, ~29/31, 4 confirmed + ~19 pre-existing-data-gap-blocked/23, 5/5) — see P-R2 escalation above |
| U5 | **CONFIRMED at Phase-A level, precision holds** | Full suite 669/2, exactly core-blocked pair; 558-row-population sample (50 rows) = 0 NO; True→False flips = exactly 1 (already known, ME row); adversarial round 2 found 0 new false positives (one theoretical construction not realized, one realized-but-correct) |
| U6 | **CONFIRMED** | Independent per-state script: WA 74.3%→98.4%, FL 84.6%→98.5%, NY 91.4%→98.6% |

### What I could NOT verify

- Did not exhaustively hand-verdict all 1,364 residual rows — read/verdicted
  well over 250 individual rows across every major shape (82-row stratified
  sample of the non-sixth-gap buckets, 43+31+23+5+17 = 119 rows across the
  five sixth-gap sub-shapes, plus targeted spot-checks), far past the ≥60
  floor, but the exact true-miss count among the un-sampled remainder of
  the ~695-row "everything else" bucket outside the shapes I identified is
  not individually confirmed.
- The `defined for` sample's 2 UNCLEAR and the `defined,` sample's 2 UNCLEAR
  rows need a fuller body read than I fetched (2,500–3,000 chars) to
  resolve definitively.
- The `defined.` (interior period) sub-shape's ~19 UNCLEAR rows hinge on the
  same pre-existing CT "`text` column omits subsection (a)" data-quality
  gap already routed to the program manager by cycle 1 — I did not trace
  *why* the corpus extraction drops it (out of this sprint's scope), only
  confirmed the symptom recurs identically here.
- Did not exhaustively read all 25 `defined as` rows (5 spot-checked, all
  YES) or fully resolve `STATE_MO_C393_S393.1655` / `STATE_WA_T31_C12_S267`
  from the adversarial-hunt dash-defeats-guard check (both consistent with
  the pattern but the visible excerpt didn't reach an explicit `"Term"
  means` clause).
- Have not verified whether fixing the sixth gap (widening
  `_rule_verb_extended`'s connector class to `for`/comma/period/`as`) is
  feasible without new precision risk of its own — that is implementation
  work, not QA's to prescribe; flagging the gap, not the fix. Worth noting
  for whoever picks this up: the `defined by` (23) and `defined in` (25)
  near-miss shapes must stay OUT of any such widening (both are dominated
  by correctly-excluded cross-reference/delegation patterns, confirmed
  above), so a naive "any word after defined" widening would be a real
  precision regression, not a clean win the way BUG1–5 were.
- Did not run the frontend suite (not touched by this sprint, per contract).
- Have not verified jurisdictions outside the 52 in-scope
  `us_*_statutes.parquet` files (constitutions, PR) — confirmed out of scope.

### Branch state

All work this cycle is doc-only (this log entry). No `backend/app/**` or
`backend/tests/**` files touched — role separation held. Pushed SHA and
`git log --oneline -1` recorded by the manager/committer at push time below
this entry.

---

## 2026-08-04 — Manager verdict on QA cycle 2: SECOND BOUNCE. U4 still fails.

QA cycle 2 at `7de5f7e`, doc-only (`git diff --stat d37387f...HEAD --
backend/app/` empty — role separation held again).

**Manager re-probed the sixth gap directly. Every claim reproduced:** the
`defined for` / `defined,` / `defined.` / `Defined <noun>` rows all return
False today, and the two shapes QA deliberately ruled OUT (`defined in`,
`defined by`) also return False — i.e. QA's proposed boundary is exactly where
the current code sits, so the fix is well-targeted rather than a blanket
widening.

QA independently reproduced recall **20,864/22,228 (93.9%)**, residual
**1,364**, the corrected precision figure **123** (not the stale 128), the
single ME True→False flip by exhaustive scan, and U6's WA/FL/NY movement.
**U3, U5, U6 stand CONFIRMED. U4 fails a second time.** `qa_cycles: 2`.

### H-R9 — the sixth gap is another H-R7-class defect; fix it, but bounded

`R-VERB-extended` fires only on `;`/`:`/dash after `defined`. Real drafting
also uses a **word, comma or period**: `"Mattress" defined for KRS 214.290 to
214.310` (`STATE_KY_TXVIII_C214_S214.280`, body `"mattress" means…`),
`"Emergency supplies" defined, regional directory database.`
(`STATE_NJ_T58_C16A_S16A-102`), `… Suitable work defined. Duties of …`
(`STATE_CT_T31_C567_S31-232l`), `"Defined term"` (`USC_T15_C122_S9801`, body
defines "COVID-19 public health emergency"). ~192 candidate rows.

**Ruling: same class as BUG1–BUG5 — a rule already committed to shipping
failing to fire inside its own intent. Fix in dev cycle 3.** Two bounds the
next Developer must respect, both established by QA's own reading:

1. **Do NOT chase `defined in` (25 rows) or `defined by` (23 rows).** Both are
   dominated by cross-reference and delegation-to-rule shapes — the same class
   as the already-fixed ME false positive and the accepted TX true negative.
   Widening into them would re-introduce the precision defect cycle 2 just
   removed.
2. **`defined for` carries a real precision cost: QA's 43-row sample was 37
   YES / 3 NO / 2 UNCLEAR / 1 stub (~86%)** — below the ~90%+ the other rules
   hold. This is a genuine **P-R2 recall-vs-precision trade**, not a clean
   defect. The Developer must measure it per-sub-shape and **escalate rather
   than ship** if the measured precision lands materially below ~90%.

### P-R2 class escalated to the program manager (data attached)

Distinct from the above, and NOT a defect: the **preposition-guarded cluster**
(245 residual rows) is a deliberate exclusion. Independent estimates of how
much real content it costs: scout ~10–15% true positives, QA cycle 1 ~25% on a
20-row read, QA cycle 2 0 genuine misses in 15 (dominated by an Indiana
"definitions in this chapter apply throughout this article" cross-reference
convention). Real examples of what is being traded away:
`STATE_IN_T32_A31_C10_S32-31-10-2` and `STATE_IN_T21_A44_C7_S21-44-7-1`.
Under an ABSOLUTE zero-miss bar this is a director-level call, not a panel one:
relaxing the guard costs ~75–90% precision on that cluster; keeping it
knowingly leaves a minority of real definitions sections uncaptured. **The
panel's standing recommendation is to KEEP the guard** (three independent
measurements agree the trade is bad), recorded here so the choice is explicit
rather than silent.

---

## 2026-08-04 — Director ruling D-HG + program ruling P-R7 received

**D-HG (director) — keep the guard.** Our P-R2 escalation is resolved: the
heading stays untrusted, and the genuine minority is rescued through the
preamble panel's BODY-content rules under ungated dispatch — zero-miss through
the right mechanism, junk stays out. **The panel's recommendation was upheld.**
Handoff artifact produced by the manager directly against the shipped module
and all 52 in-scope files: `2026-08-04-defs-us-headings-guarded-cluster.md`,
**245 rows**, exactly matching QA cycle 2's independent count.

Composition: governing word `of` 232, `from` 7, `to` 3, `in` 2, `with` 1.
By jurisdiction: **IN 184**, WV 11, TX 10, NV 4, AL/AZ/MI/SC/WA 3 each, NM 2,
remainder singletons. Indiana's 184 are dominated by *"the definitions in this
chapter apply throughout this article"* — a cross-reference heading whose BODY
frequently does carry a real definition list, which is precisely the shape
D-HG routes to the preamble panel. That is a strong sign the ruling's mechanism
fits the actual data.

**P-R7 (program law) — ground truth must be independent of the capture
mechanism's own signals.** Recorded in the contract as binding on QA cycle 3.
The honest statement of our limitation: **this sprint's entire 22,228-row miss
pool is derived from the `defin` substring**, which is the same signal our
rules key on. It measures heading-recognition recall correctly, but it is
structurally incapable of seeing a definitions section whose heading contains
no `defin` at all. QA cycle 1 already identified and stated this boundary
(CA/GA/IL/MD/MS/NE — `defin` in zero titles, ~486k rows) and confirmed it was
neither counted as recognized nor as residual. What P-R7 now requires beyond
that is the **explicit cross-reference** with the preamble panel's consolidated
body-driven inventory proving the two families' coverage meets with no gap —
coordinated through the program manager, not re-derived here.

---

## 2026-08-04 — Dev cycle 3 verified; D-Q1 escalated rather than shipped silently

Dev cycle 3 at `a0419a4`. **Manager verification, all independently re-run:**

- **All four named rows flip True** (KY `defined for`, NJ `defined,`, CT
  `defined.`, FED `Defined term`), and **all nine guards hold**: `Terms as
  defined in section 5`, `Repeal of definitions`, TX `APPLICABILITY OF
  DEFINITIONS`, the ME false positive, `"Undue hardship"—Defined by rule.`,
  morphology `undefined`, and all three pension-jargon shapes incl. the
  hyphenated `Defined-benefit` form (ruling H-R8 property preserved).
- **Suite 669 passed / 2 failed** — the core-blocked pair only. One production
  file, **299 lines**, still under the style gate. Zero test edits.
- **Manager's full-corpus re-measurement**: recall **20,864 → 21,054 /
  22,228 = 94.7%** (was 93.9%); residual **1,364 → 1,174**. Matches the
  Developer's figures exactly.
- **Precision audit (corrected boundaries)**: `{'trunc': 117, 'misspell': 6,
  'GENUINE_NOISE': 0, 'other': 0}` = **123, zero unexplained** — unchanged
  from cycle 2. No new false positives at the audit level.

**Credit where due:** the Developer found a defect *not in its brief* — three
real false positives from grammatical negation (`plans NOT defined as pyramid
promotional schemes`, `improvements NOT defined as contract rent`) — and added
a negation lookbehind, verifying it touched no pre-existing match. It also
chose a **closed word whitelist** (`for`/`as`/`term`) rather than "any word",
which makes the `defined in` / `defined by` exclusions structural rather than
guard-dependent: verified 0/25 and 0/23 fire.

### D-Q1 — escalated, not decided here

The program manager pre-designated `defined for` as a D-Q1 escalation if
precision landed materially below ~90%. **Two independent human reads:**
QA **37/43 ≈ 86%**, Developer **31/35 ≈ 88.6%** (its own decision: ship).
The manager declines to treat this as settled, for three reasons:

1. Both samples were drawn from the same 109/110-row population with the same
   seed — they are **not independent draws**, so pooling them into a single
   larger-n estimate would overstate confidence. Overlap is unknown.
2. Both land **below** the ~90%+ every other shipped rule holds.
3. The manager's own full-population mechanical scan (all 110 rows, not a
   sample) finds only **72 (65.5%)** with a detectable self-definition body
   marker, 7 cross-reference-only, 31 neither. This is a **lower bound, not a
   refutation** — the regex is conservative and cannot see definitions phrased
   outside its patterns — but it does not corroborate ~88% either, and the
   honest position is that no measurement has confirmed this rule clears the
   bar.

**Quantified trade for the director:** `defined for` is 110 rows = **0.49%**
of the miss pool. With it, recall is **94.7%**; without it, **94.2%**. The
cost at the measured 86–89% precision is roughly **12–15 wrong captures**.
The fix is one alternation in one regex — **cheap to revert either way**.
Shipped in the working tree pending the ruling; **not** presented as settled.
