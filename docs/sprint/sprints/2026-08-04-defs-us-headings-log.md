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
