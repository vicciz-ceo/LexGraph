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

---

## 2026-08-04 — Manager phase 2 (fresh context) — takeover verification

Predecessor clean-exited after dev cycle 3. Inherited state **verified, not
trusted**:

- Branch `claude/defs-us-headings` @ `639268f`, worktree clean, git
  `user.email` = `256402398+vicciz-ceo@users.noreply.github.com`. ✅
- **Correction to the resume brief:** the "defined for" rule is **not**
  uncommitted. It shipped in dev cycle 3 (`a0419a4`) as one alternation of the
  closed connector whitelist `for|as|term` in `_VERB_EXTENDED_RE`
  (`us_heading_variants.py:166`). D-DF therefore *changes shipped behavior*
  rather than deciding whether to add it.
- **Correction to the resume brief:** the "sixth gap" (post-`defined`
  word/comma/period continuations) was **already closed in dev cycle 3** and
  manager-verified there (all four named rows flip True: KY `defined for`, NJ
  `defined,`, CT `defined.`, FED `Defined term`). It is not outstanding work.
  Dev cycle 4's only content is D-DF.

### Merge onto merged core (not a rebase — recorded deviation)

`git merge origin/main` (main `0d57228`, which is core `06d67d8` + one docs
commit) instead of the briefed rebase. Reason: rebase replays 18 commits and
requires a force-push of a branch the program manager may already have
fetched; merge resolves the one conflict once and preserves every dev/QA cycle
commit for the audit trail. Merge commit `1d17d81`.

**Sole conflict:** `backend/tests/fixtures/us_statutes/README.md` — both sides
appended documentation for *different* fixture files (ours
`us_heading_variants_rows.json`; main's `ny_m14_newline_defect_row.json` and
`d_cf_structural_reference_rows.json`). Resolved as a **strict union**, nothing
dropped or reworded. Manager-performed mechanical merge; flagged for Planner
(fixture owner) verification, since the manager must not author test content.

Venv refreshed (`backend/.venv/bin/pip install -e '.[dev]'`, exit 0).
**Suite post-merge: 728 passed / 2 failed** (was 669/2 — main contributed ~59
tests). Zero regressions from the merge.

### BLOCKER — the merged core registers `HeadingRule` but never consumes it

The brief's expectation that the 2 core-blocked REDs "become unblockable" is
**half true**. One is a normal Developer item; the other is blocked by a
core-owned gap.

**Finding A — 5 of the 7 rule kinds are registered-but-dead on main.**
Only `ScopeTriggerRule` and `CitationRule` have consumption call sites.
`heading_rules_for` / `body_preamble_rules_for` / `entry_splitter_rules_for` /
`term_clause_rules_for` / `structural_unit_rules_for` are referenced **only**
by `backend/tests/unit/test_definition_links_rules_registry.py` — zero
production callers (`grep -rn '_rules_for(' backend/app/` → 4 hits, all
citation/scope_trigger).

Proven on the **live path**, not by reading code (manager probe, throwaway,
uncommitted): register a `HeadingRule(jurisdiction_codes=("US-*",),
matches=lambda h: True)`; `heading_rules_for("US-CT")` returns it; yet
`get_profile("US-CT").is_definitions_heading("Bananas and other fruit")`
still returns **False**. `USProfile.is_definitions_heading` (us_profile.py:1106)
is `return is_definitions_heading(heading)` — the module-level baseline, no
registry consultation. `pipeline.py:198/216` calls that profile method, so the
gap is on the only path that matters.

This contradicts the authoritative seam v2.5's published consumption contract
("Detection kinds … the profile's EXISTING baseline logic runs first …; only if
baseline returns false/empty does the profile try registered rules for its
code, IN FILENAME-SORT ORDER"). Core's I4 shipped the 7 **kinds** plus
auto-discovery and proved C4 with a throwaway `ScopeTriggerRule` — the one kind
that *is* wired — so the detection-kind consumption gap went unnoticed.

**Consequence for this sprint:** gates **U1** (heading RECOGNIZED on the live
path, ruling H-R1) and **U3** (rules ship as registry modules, zero shared-module
edits) are currently unsatisfiable together. Wiring `heading_rules_for` into
`us_profile.is_definitions_heading` is an edit to a shared, core-owned module —
exactly what U3 forbids and what H-R5 already ruled the Developer must not do
(concurrent panels editing the same shared dispatch collide).

**Blast radius beyond this panel** (reported, not owned): markers needs
`EntrySplitterRule`+`TermClauseRule`; multiterm needs `TermClauseRule`;
preamble needs `BodyPreambleRule`. Additionally `derive_heading_from_body`
(us_profile.py) still early-`return None`s on `not _is_placeholder_heading(heading)`
with no registered-rule step after it — i.e. seam v2 §4 / manager ruling M6 /
director **D-PREAMBLE-ALL** ("gating is off the table") is **not** implemented
in the merged code. Four panels are affected by the same root cause.

### BLOCKER — D-DF is not expressible in ANY current rule kind

`HeadingRule.matches: Callable[[str], bool]` receives the **heading only**.
D-DF requires capture only when **the body** also carries a defining marker —
a conjunction of heading and body. Checked every kind in `rules/registry.py`:

| Kind | Receives | Sees heading? | Sees body? |
|---|---|---|---|
| `HeadingRule.matches` | `(heading)` | yes | **no** |
| `BodyPreambleRule.derive_heading` | `(body)` | **no** | yes |
| `ScopeTriggerRule.extract` | `(article_body, RuleContext)` | **no** (`RuleContext` = article_number/chapter/unit_path) | yes |
| `EntrySplitterRule.split` / `TermClauseRule.parse` | `(text)` / `(block)` | **no** | yes |
| `StructuralUnitRule.derive` | `(StructuralContext)` | breadcrumbs only | no |

**No rule kind in the seam receives both the heading and the body.** D-DF
cannot be implemented as written without a core-owned seam change. Routing the
`defined for` shape to a body-side kind does not rescue it: those kinds cannot
see the heading, so they cannot tell `defined for` apart from any other row.

Scope of the change if authorized: `defined for` is **one alternation** in
`_VERB_EXTENDED_RE`'s closed whitelist `for|as|term` (`us_heading_variants.py:166`).
D-DF touches `for` only — `as`, `term`, and the punctuation forms are unaffected
and stay bare. 110 rows / 0.49% of the miss pool; recall 94.7% with, 94.2%
without.

**Both blockers escalated to the program manager.** Work that is NOT blocked
proceeds meanwhile (the `register_heading_rule` self-registration call, Phase B
item 4's unit RED).

### Work landed despite the blockers — Phase B item 4

Dev cycle (Sonnet medium; Haiku considered and rejected — the change bumps the
300-line convention and had to preserve ruling-bearing comments while avoiding
three tempting-but-forbidden shared-module edits). RED already existed
(Planner-authored, cycle 1), so no Planner spawn was needed: this was a pure
Developer task against a standing RED.

`f461371` adds the `register_heading_rule(HeadingRule(("US-*",),
matches_heading_variant))` call that H-R5 deferred.

**Manager verification (independent, materialized — not the agent's report):**
- Full diff read. Docstring prose rewrapped + one import + one registration
  line. **Proved all executable code byte-identical** to the prior commit apart
  from those two lines (docstring-stripped source comparison), so zero
  behavior change to R-SEC/R-MID/R-VERB-bare/R-VERB-extended/R-TRUNC/R-MISSPELL
  and the D-DF-pending `for|as|term` whitelist is untouched.
- Live auto-discovery check: `heading_rules_for("US-CT")` → exactly **1** rule,
  `heading_rules_for("IL")` → **0** (Hebrew regression surface protected).
- Manager-run full suite: **729 passed / 1 failed** (was 728/2).
- `git diff --stat -- backend/tests/` **empty** — role separation held.
- File now **304 lines**. The 4-line overage is entirely preserved rationale;
  recorded rather than cut, per the manager's explicit instruction that the
  line convention is soft and recorded rationale is not.

The one remaining failure is the Blocker-A wiring gap, by construction.

### Escalation raised to the program manager

Both blockers sent up with options and a lean. The panel cannot settle either:
both require edits to core-owned shared modules, which gate U3 forbids this
panel from making and which P-R1 assigned to core precisely so that four
concurrently-landing panels do not collide in the same dispatch code.

Sprint `status: blocked` pending the ruling. Nothing else in the item list is
implementable in the meantime — every remaining item depends on Blocker A
(live-path recognition) or Blocker B (D-DF).

---

## 2026-08-04 — Program ruling P-R8 received: escalation resolved

**Option 1 confirmed as program ruling P-R8** (main `0f4e8fc`). Core reopens
for a focused dispatch-completion sprint:

- all five dead rule kinds get consumption wiring;
- the ungated `derive_heading_from_body` (this panel's D-PREAMBLE-ALL
  non-implementation finding) is item 2 of core's scope;
- **this panel's `body_confirms` design is accepted as-is** — additive optional
  field on `HeadingRule`, consumed as
  `matches(heading) and (body_confirms is None or body_confirms(body))` — core
  scope item 4, credited to this panel.

The PR panel independently converged on the same dead-dispatch finding within
the hour; the two evidence sets together made the ruling immediate.

Both of this panel's corrections are recorded at program level: `defined for`
is committed (so D-DF *changes shipped behavior*, and the `body_confirms`
conjunction becomes the fix, landing as a rule-field update once core ships),
and the sixth gap was already closed in dev cycle 3. The merge-not-rebase
deviation is **accepted**, including the union-resolved README with Planner
verification to follow.

**HOLD (program manager):** U1's live-path leg, U4/P-R7 cross-reference, U6
re-measurement, and QA cycle 3 all wait for core's dispatch merge. The program
manager wakes this panel.

**Authorized meanwhile:** Planner pre-authors the D-DF `body_confirms` RED
against the agreed consumption semantics (genuine RED — stays red until core
lands AND this module adds the field; correct red-before-green order), and
verifies the README union.

---

## 2026-08-04 — Planner pre-authored the D-DF RED; manager verification

Planner (Sonnet high, P-R6) delivered both authorized items across `bc554e5`
(fixture) and `7f6964d` (tests + README + amendment). **Manager verification —
every claim re-run independently, none taken from the agent's report:**

| Check | Result |
|---|---|
| `git diff f4be09e..HEAD -- backend/app/` | **empty** — role separation held |
| Files touched | exactly 4, all tests/fixtures/docs |
| RED count + reasons | **12 RED: 11 `ImportError`** on genuinely-absent symbols (`matches_defined_for_heading` ×6, `defines_in_body` ×5) **+ 1 `assert 1 == 2`** call-count. All feature-absent, none broken-test |
| Fixture fidelity | **all 7 rows byte-identical to the real parquet, 24/24 columns** (manager script, written from scratch; exceeded the program manager's CT+KY spot-check ask — verified all 7) |
| Negatives isolated to `for` | **independently confirmed by simulating the split**: removing `for` from `_VERB_EXTENDED_RE`'s whitelist flips KY/CT/AL to False while ID(`as`)/FED(`term`)/NJ(comma)/CT(period) stay True |
| `defined for` population | **exactly 110 rows across 53 files**, reproducing the contract's figure on independently written code |
| Suite | **728 passed / 13 failed**, accounting exact: 729−1 passed (the amended test flipped RED by design), 1+11+1 failed |
| README union | still intact — **0 non-blank lines missing from either merge parent** after the Planner's append |

**On Task 1 (README union):** the Planner byte-verified it against both merge
parents and cleared it. Combined with the manager's independent mechanical
check (zero lines lost, zero duplication), the manager's merge resolution is
now cleared both mechanically and semantically, by a party that did not
perform it.

**Design accepted.** The Planner improved on the manager's sketch in two ways
worth recording: (1) `matches_heading_variant` **keeps its exact current
meaning** (verified zero existing tests exercise the `for` shape), so the
94.7% heading-only recall metric stays comparable across the change and 27
dependent tests are untouched — the two registered predicates are a
decomposition, pinned by an equivalence test; (2) the ordering and rule-2
narrowness are justified as safe under **both** plausible readings of
"first-positive-wins" dispatch, rather than assuming the one core happens to
implement.

**Minor nit, not a bounce:** `test_module_self_registers_exactly_one_heading_rule_for_us_star`
now asserts TWO registrations, so its name is stale. The Planner kept it
deliberately for git-blame traceability across the amendment and documented
that choice. Worth renaming at QA cycle 3 if the panel prefers.

**Carried-forward gap (Planner's own, honest):** the actual dispatch semantics
are unobservable until core ships. The design is proven safe under both, but
**QA cycle 3 must re-confirm against core's ACTUAL implementation** — added to
the resume checklist.

Pushed at `7f6964d`. Sprint remains `blocked` awaiting core's dispatch sprint.

---

## 2026-08-04 — Core dispatch merged; the Context Dump's prediction verified

Merged `origin/main` (`fbb6c9e`, past the `8524067` cited in the wake) — **no
conflicts**. Venv refreshed. Merge again rather than rebase: this branch
already carries a merge commit, so rebasing would rewrite it and force-push;
the deviation was accepted previously and is unchanged here.

**`HeadingRule` fields are now `('jurisdiction_codes', 'matches',
'body_confirms')`** — this panel's design shipped as specced.

### The prediction from the Context Dump — CONFIRMED

The parked Context Dump committed to a falsifiable claim: *the CT pipeline test
goes green with **no change from this panel**.* Verified exactly:

- `git diff dbd55d7..HEAD -- backend/app/definition_links/rules/us_heading_variants.py`
  → **empty**. This panel's production file is provably untouched.
- `TestRealProductionPipeline::test_connecticut_ucc_row_produces_real_definitions_via_the_real_pipeline`
  → **1 passed**.

**Gate U1's live-path leg is now real**: this panel's heading rule is consulted
by the actual production pipeline, and the recall win it measured is no longer
inert. Suite **799 passed / 12 failed** (core contributed +71 tests; the CT
failure cleared; the 12 remaining are exactly the Planner's D-DF REDs).

### Which dispatch semantics shipped — (A) OR-across-all

The Planner engineered for both readings without knowing which would land.
**Answer: (A).** Live source (`us_profile.py:1275-1289`, `profiles.py:149-152`):

```python
if is_definitions_heading(heading):
    return True                      # baseline positive is NEVER overridden
for rule in registry.heading_rules_for(self.code):
    if rule.matches(heading) and (rule.body_confirms is None or rule.body_confirms(body)):
        return True
return False
```

Proven empirically, not just read — manager probe registering rules in the
**adversarial** order (gated first, unconditional second):

| Probe | Result |
|---|---|
| gated-rule-first (matches, `body_confirms`→False) + unconditional second | **True** — (A) confirmed; (B) would have returned False |
| lone gated rule, body WITHOUT marker | **False** |
| lone gated rule, body WITH marker | **True** |

**Consequence for the design:** under (A), a gated rule that fails
`body_confirms` never suppresses another rule, so registration order and
rule-2 narrowness are **not load-bearing** — they are belt-and-braces. They
cost nothing, correctly guard against a future switch to (B), and are kept.
Recorded so QA cycle 3 does not mistake them for semantics the shipped code
actually depends on. Also confirmed: **a baseline positive is never
overridden**, so no registered rule can flip a currently-True heading False —
ruling H-R3's zero-false-positive baseline is structurally protected.

---

## 2026-08-04 — Dev cycle 4 (D-DF) implemented, bounced once, verified

Developer (Sonnet medium) shipped the two-rule decomposition; manager bounced
it on a measured under-capture; both verified independently.

### Manager verification of the implementation

| Check | Result |
|---|---|
| `git diff -- backend/tests/` | **empty** both rounds — role separation held |
| Suite | **811 passed / 0 failed** |
| Registration shape (live) | `US-CT` → 2 rules, `[0] matches_heading_variant_unconditional / body_confirms=None`, `[1] matches_defined_for_heading / body_confirms=defines_in_body`; `IL` → 0 |
| Decomposition equivalence | **0 violations across all 83,956 corpus headings** — the Planner pinned it on 25; it holds corpus-wide |
| Isolation | exactly **109** headings move to body-gated, and **all 109** are matched by the narrow predicate — zero collateral |
| Denominator reconfirmed | exact reproduction of the inherited **83,303 / 22,228 / 94.7%** on independently written code |

**Denominator convention pinned for QA cycle 3 (P-R7 relevant):** in-scope =
**52** `us_*_statutes.parquet` files, **Puerto Rico excluded** (own sprint,
Spanish-language), `defin` matched **case-insensitively**. Excluding PR's 653
titles is exactly what reconciles 83,956 → 83,303. QA must use this or its
numbers will not be comparable across cycles.

**Correction to a Planner claim:** the Planner reasoned that no `defined for`
row also matches unconditionally, calling the edge case theoretical. The
manager's full-population check found **1 real instance** —
`STATE_MI_C450_AAct-284-of-1972_S450.1569`, `"Corporation" defined for
purposes of MCL 450.1561 to 450.1567; "business organization" defined.` — which
carries a SECOND, independent definitional clause and so fires
`_rule_verb_bare`. It captures unconditionally, which is correct, and its body
confirms anyway. Benign, but the claim was empirically wrong and is corrected
here.

### The bounce — measured under-capture (H-R7/H-R9 class)

First implementation confirmed only **55/110 (50%)** while D-DF's stated intent
was "**72+ genuine kept**" and the predecessor's own conservative scan (an
explicit LOWER bound) found 72. Two mechanical gaps, both fixed:

1. **`shall mean` missing** (4 rows) — inconsistent with this codebase's own
   idiom set (`us_profile._MEANS_IDIOM_GAP_RE` = `means|shall mean|has the
   meaning`). Added. `has the meaning` deliberately still EXCLUDED: that is the
   cross-reference shape D-DF exists to suppress.
2. **Intervening-qualifier gap** (2 rows) — real drafting puts short qualifiers
   between term and verb (`"affiliated interest" with a public utility means`,
   `the term "capital," when referring to an Oregon commercial bank, means`).
   Whitelist replaced with a bounded, quote-forbidding non-greedy gap mirroring
   `us_profile._MEANS_IDIOM_GAP_RE`.

**Then a false positive removed.** The Developer honestly FLAGGED, rather than
counted, `STATE_WA_T41_C04_S005`: at a 200-char bound the regex bridged
`"period of war"` across 103 chars to a `means` defining a *different*,
unquoted sub-term. Manager measured bound sensitivity over the full 110 rows:

| bound | confirmed | OR_757 | OR_708A | WA_T41 (FP) |
|---|---|---|---|---|
| 60 / 80 | 60 | True | True | **False** |
| 100 / 200 | 61 | True | True | True |

Bound set to **80** — deliberately diverging from `us_profile`'s 200, which
operates on already-segmented entries rather than whole section bodies. Keeps
both genuine qualifier gaps (28 and 51 chars), drops the bridge. **60/110
clean beats 61-with-a-known-FP** (ruling H-R3).

**Final measured position:** recall on the 22,228 miss pool **94.5%**
(20,945 unconditional + 59 body-confirmed), versus 94.7% pre-D-DF and a 94.2%
unconditional-only floor. D-DF cost 0.2pp of heading recall to remove ~50
unconfirmed captures.

### OPEN — escalated to the program manager, not decided here

D-DF's stated intent was ~72+ kept; **we keep 60**. The residual is dominated
by **15 rows whose bodies define via `includes`** rather than `means`
(`A "period of war" includes: (a) World War I; ...`). Whether `includes` is a
defining verb is a genuine **D-Q1** precision/recall question with real
examples, not a mechanical defect — the Planner explicitly left it unpinned in
either direction. Also flagged by the Developer, and NOT counted:
`STATE_WA_T50_C29_S030` (`"wages" shall mean "wages" as defined for purpose of
payment of benefits in RCW 50.04.320`) — a cross-reference phrased with `shall
mean`, arguably the shape D-DF suppresses; it is currently CONFIRMED, so it is
a possible residual false positive worth QA's attention.

Module is **479 lines** vs the soft 300 convention — recorded, not cut.

---

## 2026-08-04 — Program ruling: the `shall mean` pointer row is D-MT-E1, not an FP

**Ruling received:** `STATE_WA_T50_C29_S030` (`"wages" shall mean "wages" as
defined for purpose of payment of benefits in RCW 50.04.320`) — **TRUE is
CORRECT**. It is a **POINTER definition under D-MT-E1**: the statute genuinely
defines the term by incorporation, so capture is REQUIRED, and the reference
edge to RCW 50.04.320 is what core's live citation plumbing emits.
`defines_in_body` accepting it is **not** a false positive.

Recorded here so QA cycle 3 does not re-litigate it. **The manager's earlier
framing of this row as a "possible residual false positive" is withdrawn.**

**New QA cycle 3 obligation from this ruling:** verify the reference edge
actually EMITS for that row. D-MT-E1 is a **two-capture** shape — a pointer
definition without its reference edge is a D-MT-E1 violation, not a partial
success. This is now on the QA checklist below.

Note this also slightly re-frames the residual: of the 50 suppressed rows, any
that are pointer-shaped (`shall mean`/`means` + incorporation by reference)
should be captured under D-MT-E1 rather than suppressed. QA should count that
class explicitly instead of folding it into the `includes` question.

## Phase B — COMPLETE

All four items now verified on the live path against merged core:

- **Item 3 — merge onto merged core.** Done (`fbb6c9e` merged, no conflicts).
  `import app.definition_links.rules.registry` succeeds; suite re-run.
- **Item 4 — registry-integration tests green.** 2/2, amended to the D-DF
  two-registration contract.
- **Item 5 — real production pipeline end-to-end green.** The CT UCC row test
  passes through the actual unmodified `pipeline.run_definition_linking`, with
  this panel's production file **provably untouched** at the moment it flipped.
  This is gate **U1's live-path leg**.
- **Item 6 — full regression, zero failures.** **811 passed / 0 failed.**

Gates **U1, U3, U5** stand met on the live path; **U6** re-measured (94.5%);
**U2** remains the accepted 10-row Option-C limitation (recheck against the
now-merged seam is a QA item); **U4** is QA cycle 3's certification.

---

## 2026-08-04 — QA cycle 3 report: BOUNCE — U4 and D-MT-E1 both fail

Independent recompute, all scripts written from scratch (`scratchpad/qac3_*`,
never read another agent's script). Every headline number below was produced
by code I wrote, not copied from the contract or the log.

### Denominator + U4 reproduction

Own extraction (`qac3_extract_defin_rows.py`, evidence venv, pyarrow) over
all 52 in-scope `us_*_statutes.parquet` files (PR excluded): **2,014,611**
total rows, **83,303** defin-titled — exact match to the pinned convention.
Analysis (`qac3_analyze.py`, backend venv, real unmodified production
functions): miss pool **22,228**; unconditional **20,945** (94.23%);
`matches_defined_for_heading` population **110**, confirmed **60** /
suppressed **50**; union **21,004/22,228 = 94.49%** — every one of these
reproduces the manager's/Planner's cited figures exactly. Decomposition
equivalence (`matches_heading_variant` == `unconditional or defined_for`):
**0 violations** across all 83,303 headings. Precision: **123 = 117 R-TRUNC +
6 R-MISSPELL**, **0** captures without a `defin` substring — exact match.

**U4 does NOT certify.** Classified the full 1,224-row residual (not a
sample): the 245-row D-HG cluster is still 100% intact and guarded (cross-
checked act_id-for-act_id against `-guarded-cluster.md`); found and
mechanically verified (via `_preposition_governs` called directly) a **29-row
sibling cluster** — `"Applicability/Application of definitions in/and X"`
headings guarded by the identical interior-token preposition mechanism, just
never enumerated by name in the 245-row report (same D-HG ruling applies,
recommend appending to that doc). Confirmed pension jargon (155), TX's
`DEFINED AREA`/`DESIGNATED PROPERTY` municipal-district jargon (169),
`definite`/`indefinite` morphology (161), authority-to-define delegation (91,
regex-verified against a tight grammatical pattern, not each hand-read),
active-voice `define`/`defines`/`defining` verb forms outside R-VERB's
passive-participle design (38) — all correctly excluded, as prior cycles
found. Manually read all remaining ~500 rows one by one. Found **four new,
real, evidenced mechanical gaps**, none previously reported:

1. **`"[TERM] defined and [continuation]"`** — `and` is not in R-VERB-
   extended's connector whitelist. **45 rows, 19 states, 0 currently
   captured.** Hand-verified 7/8 sampled bodies as genuine definitions
   (`STATE_MI_C440_AAct-174-of-1962_S440.4952`: body literally `As used in
   this section, "creditor process" means...`; also IA, KS, ND, NV, OK, WA
   confirmed). 14/45 are Louisiana's templated `"pollution defined and
   prohibited"` heading whose body never mentions "pollution" at all
   (verified — 0 occurrences in a 3,598-char body) — heading-correct,
   body-empty, same accepted H-R1 category as CO/NV/AK. Recommend the same
   D-DF-style body-gate treatment question this sprint already applied to
   `for` — escalate, don't decide.
2. **RI mojibake em-dash** (`\x80\x94`/`\x80\x9c`/`\x80\x9d` byte sequences
   in place of a real Unicode dash) defeats the dash-connector check. **10
   rows, all Rhode Island, 0 captured.** Hand-verified 2/2 sampled bodies
   clean (e.g. `STATE_RI_T44_C44-18_S44-18-15.2`: body `"Remote seller"
   means any seller...`). Narrow, high-confidence, low-risk — same class as
   R-TRUNC's existing corpus-defect handling.
3. **`"Other defined terms"` / `"Other definitions [appearing in ...]"` /
   `"Index of definitions in [code/act/chapter/title]"`** — a real,
   repeated drafting convention (a cross-reference TABLE mapping each term
   to the section that actually defines it), found in **CT, IA, ME, CO, OK,
   SC (7 rows), 0 captured.** Hand-verified 6/6 sampled bodies — every one
   is a genuine pointer table (e.g. `STATE_CO_T5_A1_P3_S5-1-303`: `"Actuarial
   method" section 5-1-301 (1)`, dozens of entries). This entire class is
   **D-MT-E1 pointer-definition territory** — high-value finding.
4. **`"[TERM] defined ([qualifier])."` / `"[TERM] defined to [verb]..."`**
   — a parenthetical or the word `to` immediately after `defined` isn't in
   the whitelist. **7 rows: KY(1), MO(4), PA(1, repealed, harmless),
   VA(1, uncertain).** Hand-verified KY and all 4 MO bodies genuine (e.g.
   `STATE_MO_C50_S50.770`: body `"supplies"... means materials,
   equipment...`).

Total newly-evidenced capturable-miss rows: **69** (conservatively; the 14 LA
rows are heading-correct/body-empty, still a legitimate U1 capture). Every
row is a real act_id, hand-verified against real corpus text — reported per
P-R2, not decided here.

### P-R7 boundary cross-reference

No live channel to page the manager existed in this session (single-agent
QA run, no multi-agent orchestrator to address). Rather than guess or
re-scan the corpus (forbidden), read the preamble panel's own **committed**
sprint log directly (`LexGraph-wt/defs-us-preamble/docs/sprint/sprints/
2026-08-04-defs-us-preamble-log.md`) — a legitimate, named, citable artifact,
not a generic scratchpad file (P-R9 respected). Their QA's `qa_d1_corpus_
scan.py` is a corpus-wide (2,038,247 rows, all 53 files), **signal-
independent** (body-prose-driven, not heading-derived) candidate scan: 7,383
rows, 1,468 gated + 5,915 ungated-only, touching 50/53 jurisdictions. The
six named zero-`defin`-title states (CA/GA/IL/MD/MS/NE) are confirmed
covered (CA/GA via the gated bucket, MD/MS/NE via ungated-only) — the
contract's "known starting point" holds. Caveat, stated plainly: the
preamble panel is itself pre-QA (`qa_cycles: 0`, `status: parked-blocked`)
and its own P-D1 section admits its count methodologies do not fully
reconcile (MD gap, floor/ceiling ranges) — this is the best obtainable
cross-reference in this session, not a mutually-certified closed boundary.
One specific residual: Alaska shows **zero** ungated-only exposure under
their 3-regex candidate rule — not necessarily a gap (AK's definitions
sections may simply carry `defin`-signal headings, this family's own
territory), but not independently confirmed clean either.

### Gate U6 — measured before/after, per jurisdiction

Own per-state computation, all 52 states (`qac3_per_state.json`). Baseline
reproduced **exactly**: WA 74.26%, FL 84.56%, NY 91.35%. After (current
shipped code, D-DF included): **WA 98.60%, FL 98.63%, NY 98.70%** — all
three **exceed** the contract's own earlier-cited 96.5%/98.5%/98.6% figures,
because those were measured before the H-R7/H-R9 bug-fix cycles landed; not
a regression, an improvement over a stale snapshot. Zero H-R3 violations
(`after < baseline`) across all 52 states — the biggest movers were IN
(22.3%→90.4%) and NV (12.4%→99.6%), consistent with the dossier's own
targets. IN's after-rate is the lowest of all states because 184 of the
245-row D-HG cluster is Indiana's own `"Application of definitions"`
convention (correctly guarded, not a defect).

### D-DF verification (60/50 reproduced) — read all 50 suppressed, not 25

`includes`-verb defining class: **~15-16 rows** (AK, MI, MO, OK, 10×OR,
2×WA) — closely corroborates the sprint's own cited 15; D-Q1 open question,
reported not decided. **D-MT-E1 pointer-shaped rows wrongly SUPPRESSED,
should be CAPTURED per the director's own WA_T50 ruling — a real defect**:
`STATE_NV_T38_C432A_S432A.1774` (`"child care facility"... Has the meaning
ascribed to it in NRS 432A.024`) and `STATE_OR_T28_C293_S293.235`
(`"state agency" has the meaning given that term in ORS 293.226`) are
direct structural analogs to the ruled WA_T50 shape; `STATE_AZ_T43_C3_A1_
S308` (external IRC reference) is a third, weaker candidate. SD's 11 rows
use its own unquoted comma-delimited `"the term, X, means"` convention,
which structurally cannot match D-DF's quoted-term-only regex by design —
consistent with SD's already-known/routed markers-family gap, not new.
One narrow near-miss: `STATE_WA_T48_C21_S015`, `"is FURTHER defined as
follows"` — the `is\s+defined\s+as` regex doesn't tolerate an inserted
adverb. Remainder (AL, ID, ND-repealed, CT-citation-only, NC×2, SC, WY,
TN, NM×2/WA-49 unquoted-term) genuinely non-defining or an already-
documented limitation — correctly suppressed.

### D-MT-E1 two-capture check — `STATE_WA_T50_C29_S030` — FAILS, verified live

Direct calls to the real, unmodified production functions on this row's
real corpus text:

- `detect_cross_law_derivations(text, source_term="wages")` → **`[]`**.
  None of the 5 trigger phrases match: the real text is `...shall mean
  "wages" as defined for purpose of payment of benefits in RCW 50.04.320`
  — `"for purpose of payment of benefits"` sits between `defined` and
  `in RCW`, breaking the `"as defined in"` trigger's contiguous-phrase
  requirement. **No reference edge would ever emit for this row today.**
- Worse: `extract_definitions_from_section(body, scope=..., heading_
  was_derived=False)` — the ACTUAL argument value on the live path, since
  this heading was recognized via the `HeadingRule` registry, never via
  `derive_heading_from_body` — also returns **`[]`**. The body is a single
  unnumbered sentence; the inline-quote fallback extractor that WOULD parse
  it is gated behind `heading_was_derived`, which is only ever True for the
  CA/IL/GA-style body-derived-heading path. Confirmed
  `heading_was_derived=True` (not what actually runs) WOULD extract it
  correctly.

**Net: on the live path today this row produces zero Definition rows and
zero DERIVES_FROM_LAW edges.** Not "captured without its reference edge" —
not captured at all. This is the director's own named precedent case for
D-MT-E1; it fails outright.

### Dispatch-semantics confirmation

Confirmed both claims independently: read the merged source
(`us_profile.py:1276-1291`) AND ran my own adversarial live probe (registered
a gated-first rule that always fails `body_confirms`, then an unconditional
second rule, against a throwaway jurisdiction code) — result **True**,
confirming (A) OR-across-all, not first-wins. Also confirmed a lone gated
rule alone returns False/True correctly by body content, and that a
baseline-True heading is never touched by the registry loop even with
adversarial rules registered (H-R3's zero-false-positive baseline
structurally protected).

### Regression + precision (task 7)

`backend/.venv/bin/pytest backend/tests -q` → **811 passed, 0 failed** —
exact match. Adversarial precision hunt on the 60 D-DF-confirmed rows (does
`_SELF_DEFINITION_RE`'s matched quoted term actually correspond to the
row's own heading term?): 3 apparent mismatches, all explained as artifacts
(a line-wrap newline inside a quoted term; the already-unconditionally-
captured MI row matching its own SECOND term; the OR row matching its own
second alternation term) — **0 genuine new false positives** introduced by
`defines_in_body`.

### U2 recheck

The seam's generic scope mechanism is confirmed **live and merged**:
`matcher._in_scope` supports M9 tuple-valued `source_chapter`/`source_
article_number`/`scope_value` (`_value_matches` does `actual in expected`
for a tuple) on the EXISTING `"chapter"`/`"local"` kinds, plus a fully
generic non-standard-kind path matched against `article.structural_units`
for any registered `StructuralUnitRule` kind. This converts U2 from a hard
technical blocker into an implementation question, per the ruling's own
framing. Concretely: AK's multi-chapter range and at least 2 of the 4 KY
`"for section and KRS X"` rows are directly expressible TODAY via a
tuple-valued `source_chapter`/`source_article_number` on the existing
`"chapter"`/`"local"` kinds — no new scope-kind registration needed. The
other rows (CT's prose scope description, NJ, TN's dual-scope, UT, VA's
title-level scope) are plausibly expressible via the generic kind +
`StructuralUnitRule` path but unverified/unimplemented — this is now a
normal Developer item, not a permanent limitation, but I did not implement
or fully re-verify each of the 10 individually (outside QA's role).

### U3 (registry-only)

Verified via `git show --stat` on every one of this panel's own commits:
100% touch only `backend/app/definition_links/rules/us_heading_variants.py`
under `backend/app/`. PASS.

### Per-gate verdicts

| Gate | Verdict | Check |
|---|---|---|
| U1 | PASS | source read + own dispatch probe + full-suite CT pipeline test green |
| U2 | Limitation status changed, not a fail | seam mechanism confirmed live; ≥3/10 rows concretely expressible now without new registration; recommend as normal Developer item |
| U3 | PASS | `git show --stat` on every panel commit, 100% single-file |
| U4 | **FAIL** | 69 newly-evidenced, hand-verified capturable-miss rows across 4 new mechanical-gap classes, on top of the 245+29-row guarded cluster correctly holding |
| U5 | PASS | 811/0 suite; 0 H-R3 violations across 52 states; 0 equivalence violations; 0 genuine new FPs on adversarial hunt |
| U6 | PASS | baseline exact-match; after exceeds the contract's own cited figures for all 3 named states; full 52-state table computed |
| D-DF | Defect found | 60/50 reproduced exactly, but 2+ D-MT-E1-pointer-shaped rows wrongly suppressed instead of captured |
| D-MT-E1 (two-capture) | **FAIL** | verified live: `STATE_WA_T50_C29_S030` produces zero Definition rows and zero reference edges today |

### Recommendation: BOUNCE

Two independent, concretely-verified gate failures (U4's 69 new real
misses; D-MT-E1's own named precedent row producing nothing on the live
path) plus a real D-DF defect (pointer rows wrongly suppressed). Under the
director's absolute zero-miss bar this cannot certify. Full row lists,
scripts, and intermediate JSON are in the shared scratchpad, all prefixed
`qac3_` per P-R9.

---

## 2026-08-04 — Manager verification of QA cycle 3: BOUNCE ACCEPTED

QA commit `a2faa30` is **doc-only** (1 file, the log, +228) — role separation
held. `qa_cycles: 3`.

**Both load-bearing findings independently reproduced by the manager:**

1. **U4 FAIL — the `defined and` gap is real. Exactly 45 rows**, reproducing
   QA's count precisely: `defined and` in `section_title`, baseline False, and
   neither registered rule fires. Manager-read samples are plainly genuine
   definitions: `Felony defined and classified.`, `Misdemeanor defined and
   classified.`, `Ice Cream Defined and Standardized`, `Common-law and
   statutory easements defined and determined.` **This is another
   H-R7/H-R9-class defect** — `and` is missing from R-VERB-extended's connector
   whitelist, exactly as `for`/comma/period were in cycle 2. Bounce accepted.

2. **D-MT-E1 two-capture — reproduced, but ROUTING differs from QA's framing.**
   On `STATE_WA_T50_C29_S030` the manager called the real production functions:
   - `profile.is_definitions_heading(heading, body)` → **True** (U1 works; the
     heading IS recognized and body-confirmed)
   - `find_citations(body)` → **`['RCW 50.04.320']`** (the citation IS found)
   - `extract_definitions_from_section(body, heading_was_derived=False)` →
     **0 candidates**
   - `detect_cross_law_derivations(...)` → **0 edges**

   So the row is correctly IDENTIFIED as a definitions section and its citation
   is extractable, but the body yields **zero definition candidates**, leaving
   nothing for a reference edge to attach to. **Per ruling H-R1 this is
   markers-family work, not this panel's**: "U1 'captured' = heading RECOGNIZED
   on the live path. Bodies that then yield zero are markers-family work: log
   the `act_id`, route via the program manager, touch no extraction code here."
   The fix lives in `us_profile.extract_definitions_from_section`, a shared
   core-owned module this panel is forbidden to edit (U3).

   **QA is factually right that D-MT-E1's two-capture does not happen on the
   director's own named row. It is a genuine program-level gap — but it is not
   fixable inside this sprint's write-set.** Escalated, with the act_id, rather
   than silently reclassified as someone else's problem.

**Other QA findings accepted as recorded** (not independently re-verified by
the manager; QA hand-verified against corpus text): RI mojibake em-dash 10
rows; `Other defined terms`/`Index of definitions in X` pointer-table
convention 7 rows (D-MT-E1 territory); `defined (qualifier)`/`defined to
[verb]` 7 rows. Total newly-evidenced capturable misses: **69**.

**Gates standing after cycle 3:** U1 PASS, U3 PASS, U5 PASS (811/0, zero H-R3
violations), U6 PASS (baseline reproduced exactly; after-rates 98.6/98.6/98.7%
for WA/FL/NY, exceeding the contract's cited figures). **U4 FAILS a third
time.** U2's limitation is now **expressible** against the merged seam — it
converts from a permanent limitation to a normal Developer item.

**P-R7 remains UNCERTIFIED and is the manager's failure, not QA's.** QA was
instructed to request the preamble panel's consolidated matrix through the
manager, but the manager was mid-run and unreachable, so QA fell back to
reading that panel's committed log directly — whose own inventory is pre-QA
and admits non-reconciled counts. **U4 cannot certify on this.** The manager
must obtain the matrix pointer from the program manager before QA cycle 4.
