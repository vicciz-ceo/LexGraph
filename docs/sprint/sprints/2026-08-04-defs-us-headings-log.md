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

