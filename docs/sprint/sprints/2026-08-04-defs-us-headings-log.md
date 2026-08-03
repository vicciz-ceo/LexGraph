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
