---
id: "2026-08-04-defs-us-headings"
status: in-progress
current_role: planner
branch: claude/defs-us-headings
worktree: /Users/nerya/LexGraph-wt/defs-us-headings
locked_by: "claude-code:sprint-manager"
locked_at: "2026-08-04T00:00:00Z"
last_agent: "claude-code:sprint-manager-phase3"
last_updated: "2026-08-04"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 14
completed_items: 0
dev_complete_items: 6
qa_cycles: 3
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
---

# Sprint: US family 4 — heading variants the matcher never sees

## Mandate

Definitions sections whose HEADINGS defeat the first/last-word "Definitions"
rule (dossier §2 family 4 + §6 addendum):
- **Compound/mid-token headings**: `"Reciprocity — definitions — procedure —
  fees."` (MO, 20/300), `"Definition of Terms."` (NH), dash/semicolon-joined
  compounds (TN/SC/SD/PA/UT), `"APPLICABILITY OF DEFINITIONS."` (TX), NV/NY/
  MI variants. Includes the prior sprint's recorded WA 10.3% / FL 5.5% /
  NY 4.4% heading-miss rates.
- **NEW verb-form family**: `"X" defined` / `Employee defined` / `Words and
  phrases defined` — no "Definitions" token at all. VA 57, WA 279, WV 204,
  WI 16, WY 45, DC 38, FED 163 sampled instances — 0% captured everywhere.
The false-positive hazard is real (a heading MENTIONING definitions is not
always a definitions section — TX's "APPLICABILITY OF DEFINITIONS" needs
judgment): P-R2 escalation with examples when recall and precision collide.

## Acceptance gates (program manager-defined)

- **U1 — Every heading variant above is captured**, RED tests from real rows
  of the named states before implementation.
- **U2 — Scope stamped/enforced** where the heading or body names a scope
  unit, via the core seam, live-path both directions.
- **U3 — Rules ship as registry modules**; zero shared-module edits.
- **U4 — Zero-miss sweep (director bar)**: QA sweeps ALL 53 jurisdictions
  for def-signal headings (incl. `defin*` substrings and verb-form shapes);
  every hit captured or proven not-a-definitions-section.
- **U5 — Nothing regresses**: zero false positives held by the current
  matcher across 10 states must not break; baseline states hold; P-R2
  escalation on conflicts.
- **U6 — Measured before/after**: heading-recognition rates per
  jurisdiction (WA/FL/NY prior-known misses must move) on the full corpus.

## Coordination

Core sprint owns scope plumbing + registry; read its `## Seam spec` from
branch `claude/defs-core-scope`; merge after core. Note the interaction with the markers sprint: a newly
RECOGNIZED heading only helps if the extractor can parse the body — bodies
that then yield zero belong to the markers family; route them via the
program manager, do not fix extraction here. Registry registrations
append-only. Out-of-family misses route via program manager.

## Standing constraints

All program standing constraints apply (program doc): CodeGraph first;
red-before-green live-path tests; Planner owns tests; QA independent; no
test downloads the corpus; absolute zero-miss bar; P-R2.

## Manager rulings (details + panel dialogue in `-log.md`)

- **H-R1** — U1 "captured" = heading RECOGNIZED on the live path. Bodies that
  then yield zero are markers-family work: log the `act_id`, route via the
  program manager, touch no extraction code here.
- **H-R2** — the dossier's family-4 example list is partly wrong (manager
  probe, live): 5 of 19 cited headings are ALREADY captured, and NH's miss is
  a section-NUMBER-format bug (colon numbering `21:2` defeats
  `_SECTION_NUMBER_TOKEN_RE`, whose separators are `[.-]` only), not a
  heading-word bug. Re-confirm every example against real parquet rows.
- **H-R3** — zero-false-positive baseline (`test_qa_regression_us_state_law.py`
  R9/R12 guards, `_PRECEDING_EXCLUSION_WORDS`) is a hard gate; any widening
  that flips a currently-False heading to True needs a real row whose body
  genuinely defines terms, else P-R2 escalation.

Baseline (manager-run): `backend/.venv/bin/pytest backend/tests -q` →
**641 passed** at `83532fe`.

## Next Steps

Full evidence (re-confirmed counterfactuals, per-rule recall/precision
numbers, the R-COLON drop, the verb-form yield refinement, U2 escalation)
is in the panel log's `## 2026-08-04 — Planner report`. This section is
the executable item list only. RED proof for every item below: `cd
/Users/nerya/LexGraph-wt/defs-us-headings && backend/.venv/bin/pytest
backend/tests/unit/test_definition_links_us_heading_variants.py
backend/tests/unit/test_definition_links_rules_registry_integration.py
backend/tests/integration/test_us_heading_variants_end_to_end.py -v` — 30
failed (29 `ModuleNotFoundError`, 1 real assertion failure proving the
pipeline is genuinely unwired), 0 passed, full baseline suite still 641
green alongside them.

### Phase A — buildable now (no core dependency; ONE new file)

1. **Create `backend/app/definition_links/rules/us_heading_variants.py`**
   exposing `matches_heading_variant(heading: str) -> bool` implementing
   R-SEC + R-MID + R-VERB-bare + R-VERB-extended + R-TRUNC + R-MISSPELL
   (exact per-rule spec in the module docstring of the test file below;
   do NOT build R-COLON — measured redundant with R-MID, see log). Module
   is self-contained (own normalization; does not import/touch
   `us_profile.py`'s private regexes, ruling H-R4). Registers itself via
   `register_heading_rule(HeadingRule(jurisdiction_codes=("US-*",),
   matches=matches_heading_variant))` at import time — this call will
   itself fail (`ModuleNotFoundError`) until Phase B's dependency lands;
   write the module anyway, it is correct code waiting on an import.
   Serves **U1, U3**. CHECK:
   `backend/tests/unit/test_definition_links_us_heading_variants.py`
   fully green (19 tests: 10 positive-rule + 9 negative-guard).

   **Manager correction (ruling H-R5) — item 1 as originally written was
   internally inconsistent** ("write the registration call, accept
   `ModuleNotFoundError`" cannot coexist with "unit tests fully green": a
   module-level import error fails all 19). Corrected shape, verified live
   by the manager:
   - The `rules/` package does **not exist on this branch or on
     `origin/claude/defs-core-scope`** — core has not written it yet.
     `rules/__init__.py` and `rules/registry.py` are **core-authored and
     stable forever** per the seam; **the Developer must NOT create
     either** (doing so guarantees a rebase collision and forks the
     auto-discovery implementation).
   - Manager verified empirically that **PEP 420 namespace packages work
     here**: a `rules/` directory containing only our module, with NO
     `__init__.py`, imports fine as
     `app.definition_links.rules.us_heading_variants`.
   - **Phase A therefore ships the PURE FUNCTION ONLY**: create
     `rules/us_heading_variants.py` containing `matches_heading_variant`
     and its own normalization helpers, with **no `__init__.py` and no
     `register_heading_rule` import/call**. All 19 unit tests go green
     now, with zero core dependency.
   - The `register_heading_rule(...)` call is added in **Phase B, item 3**
     (post-rebase), when `rules/registry.py` actually exists.

2. **Composed deterministic-engine end-to-end tests green** — no code
   change beyond item 1; these exercise `matches_heading_variant` chained
   with the REAL, already-existing `us_profile.extract_definitions_from_
   section` / `matcher.link_articles_to_definitions` (hand-composed
   baseline-first/registry-second, not through `profiles.py`). Serves
   **U1** (both layers: heading recognition AND body-yield-where-parseable,
   ruling H-R1). CHECK:
   `backend/tests/integration/test_us_heading_variants_end_to_end.py::TestComposedDeterministicEngine`
   fully green (8 tests) — includes 4 positive end-to-end yields (CT 82
   candidates, MO 6, WI 27, CT-misspelled 3), the MO term-use-links-back
   proof, and 3 documented zero-yield hand-offs (CO/NV/AK) that must stay
   `candidates == []` (pin, not a bug to fix here).

### Phase B — blocked on core (`claude/defs-core-scope` merging + this
branch rebasing onto it)

3. **Rebase this branch onto merged core** once
   `origin/claude/defs-core-scope` lands on `main` (or is merged directly
   if the program manager sequences it that way) — brings in
   `app.definition_links.rules.registry` (the `register_heading_rule`
   function and the `HeadingRule` dataclass item 1 depends on) and the
   registry consultation wiring in `profiles.py`/`pipeline.py`. Not a
   code-writing item — a merge/rebase + re-run-tests item. CHECK: `import
   app.definition_links.rules.registry` succeeds; full suite re-run.

4. **Registry-integration tests green.** Serves **U3, U5**. CHECK:
   `backend/tests/unit/test_definition_links_rules_registry_integration.py`
   fully green (2 tests: self-registration via a patched
   `register_heading_rule`, and the hand-composed baseline-first/registry-
   second contract proof across positive + negative fixture rows).

5. **Real production pipeline end-to-end test green.** Serves **U1**
   (live-path proof through the actual, unmodified `pipeline.run_
   definition_linking`, DB-backed). CHECK:
   `backend/tests/integration/test_us_heading_variants_end_to_end.py::TestRealProductionPipeline::test_connecticut_ucc_row_produces_real_definitions_via_the_real_pipeline`
   green — today it fails with a REAL assertion (`0 > 0`), not an import
   error, proving the pipeline runs but the registry is genuinely not
   consulted yet; do not treat this as a Developer defect before item 3 is
   done.

6. **Full regression suite, zero new failures.** Serves **U5**. CHECK:
   `backend/.venv/bin/pytest backend/tests -v` — all of items 1/2/4/5's
   tests green, the pre-sprint 641 still green, total count exactly
   641 + 30 = 671 passed (this sprint added no other tests).

### Binding rulings received from above (apply in QA cycle 3)

- **D-HG (director)** — the preposition guard **STAYS**. The genuine minority
  in that cluster is rescued by the preamble panel's body-content rules under
  ungated dispatch, not by relaxing our heading guard. The complete 245-row
  list is handed off in
  `docs/sprint/sprints/2026-08-04-defs-us-headings-guarded-cluster.md`; any row
  NEITHER path reaches goes back to the director **by name**. **Do not relax
  the guard.** This closes the panel's P-R2 escalation.
- **P-R7 (program law)** — a zero-miss sweep must build ground truth
  INDEPENDENT of the capture mechanism's own signals. **Our 22,228-row miss
  pool is `defin`-substring-derived**, so it is valid for measuring
  heading-recognition recall but is structurally blind to definitions sections
  carrying NO `defin` substring anywhere (GA-style body-preamble-only signals).
  **U4 cannot be certified on the `defin` pool alone.** QA cycle 3 must add an
  explicit boundary cross-reference against the preamble panel's consolidated
  body-driven inventory — obtained by coordinating with that panel via the
  program manager, **not** by re-scanning the corpus — demonstrating that this
  family's misses end exactly where that family's coverage begins, **with no
  gap between**. Any population reached by neither is a director-level miss and
  is reported by name. Known starting point: CA/GA/IL/MD/MS/NE have `defin` in
  ZERO section titles (~486k rows) and are already routed to that panel.

### QA (after Phase A+B dev-complete)

7. **Zero-miss full-corpus sweep, gate U4.** Independently re-run the
   census this sprint's evidence rests on (`is_definitions_heading(h) or
   matches_heading_variant(h)` over all `section_title` values containing
   `defin`, all 52 in-scope `us_*_statutes.parquet` files — corpus is
   HF-cached locally, `~/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/`,
   never downloaded by a committed test, ruling R6). Planner's own
   measurement (reproduce, don't trust): miss pool 22,228 rows; union
   recall with the recommended rule set 20,307/22,228 (91.4%); the 1,921
   residual rows are, on inspection, either the 339-ish correctly-excluded
   morphology shapes or preposition-guarded true negatives — QA's job is
   to confirm that residual is genuinely all correctly-excluded, not
   silently-missed capturable rows (spot-check at minimum 60 of the 1,921,
   report any genuine miss found as a P-R2 escalation with the real row).

8. **Measured before/after heading-recognition rates, gate U6.**
   Per-jurisdiction, full corpus, before (baseline `is_definitions_
   heading` alone) vs. after (with the registry rule). WA/FL/NY's prior-
   known heading-miss rates (recorded in the mandate) must move; report
   the new rate per state, not just the aggregate.

### RESOLVED by program-manager ruling — U2 known limitation (Option C)

**Program manager ruling, 2026-08-04: Option C accepted.** Ship the verified
recall win; record the 10 enumerated rows as a NAMED KNOWN LIMITATION; the
scope-model gap is routed to the core panel. **Seam v2 will carry a generic
`(unit_kind, unit_value)` scope mechanism**, which may make these 10
expressible — **recheck once core pushes seam v2; if expressible, capturing
their true scope becomes a normal sprint item, not a limitation.**

**U2 KNOWN LIMITATION — the complete affected set (10 rows, 0.05% of the
20,308 newly recognized; not a sample):**

`STATE_AK_T13_C13.06_S13.06.050` (multi-chapter range `AS 13.06 — AS 13.36`),
`STATE_CT_T12_C202_S12-35b`, `STATE_KY_TIII_C17_S17.185`,
`STATE_KY_TXIII_C156_S156.106`, `STATE_KY_TXXI_C246_S246.420`,
`STATE_KY_TXI_C139_S139.486`, `STATE_NJ_T17_C35_S35-23`,
`STATE_TN_T6_C51_S6-51-101`, `STATE_UT_T78A_S78A_5_201`,
`STATE_VA_T8.01_C1_S8.01-2`.

These headings are correctly RECOGNIZED (U1); their declared scope is not
expressible in the seam's current 2-value model (`chapter`/`law-wide`), so
they take whatever `determine_scope` computes — recorded here rather than
passed off as correct. Not new exposure: the same shapes occur in headings
the baseline already recognized before this sprint.

### Not a dev/QA item — program-level escalation, tracked here so it isn't
lost

9. **[RESOLVED — see the ruling above] U2 scope-seam gap for scope-unit-naming headings** (e.g. AK's real
   `"General definitions for AS 13.06 — AS 13.36."`, `STATE_AK_T13_C13.06_S13.06.050`
   — a genuine family-4 R-MID capture). The published core seam's
   `determine_scope` returns only `"chapter" | "law-wide"` for the
   Definitions-SECTION path; it has no slot for a named multi-chapter
   range, and no registered-rule kind exists to teach it one (`ScopeTriggerRule`
   is the ORDINARY-ARTICLE path, a different code path). Recognizing this
   heading (item 1) is correct and safe on its own; claiming its scope is
   CORRECTLY enforced is not yet true. Full analysis, options, and the
   Planner's lean are in the panel log — routed to the manager for
   forwarding to the program manager per the brief's instruction (report,
   do not unilaterally decide). Not gated on Phase A/B; can resolve on its
   own timeline. If unresolved by ship time, ship item 1 anyway (heading
   recognition, U1) with this gap explicitly flagged as a known limitation
   in the Completed entry, not silently papered over with a guessed scope
   value.

## Residual ledger

Program-wide pattern (established by the PR panel). Every row this panel does
NOT capture, by name and with its disposition. A residual is honest only if it
is either (a) ruled correctly-excluded, (b) owned by a named other panel with a
closing condition, or (c) open at director level. Nothing sits here unlabelled.

| # | Class | Rows | Disposition | Closes when |
|---|---|---|---|---|
| L1 | D-MT-E1 zero-yield reference edge — `STATE_WA_T50_C29_S030` | 1 | **Cross-panel dependency → MARKERS** (program ruling, H-R1). Heading IS recognized (live-verified True) and `find_citations` returns `['RCW 50.04.320']`, but `extract_definitions_from_section` yields 0 candidates, so no Definition row exists for the reference edge to attach to. Fix lives in core-owned `us_profile.extract_definitions_from_section` — forbidden to this panel by U3. | markers' entry-boundary / zero-yield work lands and the row emits a Definition row + its DERIVES_FROM_LAW edge |
| L2 | `includes`-verb defining bodies in the D-DF suppressed set | 15 | **OPEN at DIRECTOR level (D-Q1).** Director did NOT rule capture: ruling is **"measure FP exposure first."** Panel commissions a read-only FP-exposure scout; class is **not built and not closed** until the director rules on the measurement. | director rules capture (→ becomes a capture item) or residual (→ stays here, ruled) |
| L3 | D-HG guarded cluster — `Application/Applicability of definitions …` | 245 + 29 sibling | **Ruled correctly-excluded** (D-HG, director). Guard STAYS. Genuine minority rescues via the preamble panel's body-content rules under ungated dispatch. The 29-row sibling cluster QA cycle 3 found is the same mechanism, never enumerated by name — recommend appending to `-guarded-cluster.md`. | preamble panel's coverage confirmed; any row NEITHER path reaches goes back to the director BY NAME |
| L4 | Louisiana templated `"pollution defined and prohibited"` bodies | 14 | **Heading-correct / body-empty → MARKERS family (H-R1).** Cycle 5 captures the HEADING (correct, U1); the body genuinely never mentions the term, so zero yield is expected, same accepted category as the pinned CO/NV/AK hand-offs. | markers' zero-yield work lands, or ruled permanently body-empty |
| L5 | U2 scope rows not expressible even against merged seam v2.7 | ≤7 of 10 | Cycle 5 item 14 takes the **expressible** subset (AK multi-chapter range + ≥2 KY rows) as a normal Developer item. Whatever remains unexpressible after that measurement stays here, enumerated by act_id. | cycle 5 item 14 measures each of the 10 individually; remainder re-escalates |
| L6 | Morphology / jargon / active-voice exclusions | 155+169+161+91+38 | **Ruled correctly-excluded**, re-confirmed by QA cycle 3 against the full 1,224-row residual (not a sample). Includes `definite`/`indefinite` morphology — note `STATE_RI_T34_C34-11_S34-11-37` (`Indefinite references to "trustee"`) must STAY excluded after cycle 5's mojibake normalization; it is a negative-guard test, not a capture. | n/a — closed, held by negative-guard tests |

## Next Steps — cycle 5 (manager-defined, phase 3)

Manager re-verification of the inherited state is complete and recorded in
`-log.md` § "Phase-3 manager takeover". All numbers below were reproduced by
the manager on independently written code
(`scratchpad/headings_mgr3_census.py`, `headings_mgr3_reconcile.py`) and pass
P-R10 probe sanity against the pinned figures before any new number is used.

**Evidence file for the Planner (manager-authored, exact path):**
`…/scratchpad/headings_mgr3_gap_rows.json` — every gap row with `act_id`,
`state`, `section_title`, `body_head`, `body_len`.

10. **R-VERB-extended `and` connector gap.** `and` is missing from the
    connector whitelist — the same H-R7/H-R9 defect class as `for`/comma/
    period in cycle 2. **45 rows, 19 states** (manager count, exactly
    reproducing QA's). Serves **U4**. NOTE: 14 of the 45 are the Louisiana
    body-empty rows (ledger L4) — capturing the HEADING is still correct and
    required under H-R1; do not gate them on body yield.
11. **RI mojibake em-dash normalization.** `\x80\x94` / `\x80\x9c` / `\x80\x9d`
    byte sequences stand in for a real dash/curly quotes and defeat the
    dash-connector check. **10 genuine rows, all Rhode Island.** Same class as
    R-TRUNC's existing corpus-defect handling. Serves **U4**. **Negative guard
    required:** `STATE_RI_T34_C34-11_S34-11-37` (`Indefinite references to
    "trustee"`) carries the same mojibake but is a `defin`-morphology row —
    it must remain **False** after normalization (ledger L6).
12. **D-MT-E1 pointer-table headings.** `Other defined terms` / `Other
    definitions [appearing in …]` / `Index of definitions in [code/act/
    chapter/title]` — a real repeated drafting convention whose body is a
    cross-reference TABLE mapping each term to its defining section.
    **Manager count: 9 rows / 7 states (CO, CT, IA, ME, OK, SC×3, WY)** —
    QA reported 7 rows / 6 states; the manager's independently authored
    pattern additionally finds `STATE_OK_T14A_S14A-1-303` and
    `STATE_WY_T40_C14_S40-14-142`, both hand-read and both genuine pointer
    tables. Use the manager's 9. Serves **U4**; D-MT-E1 territory.
13. **`defined (qualifier)` / `defined to [verb]`.** A parenthetical or `to`
    immediately after `defined` is not in the whitelist. **7 rows: KY(1),
    MO(4), PA(1 repealed, harmless), VA(1).** Serves **U4**. **Planner
    judgment call, escalate rather than guess:** the VA row
    (`STATE_VA_T8.01_C14_A4_S8.01-397.1`, `Evidence of habit or routine
    practice; defined (Supreme Court Rule 2:406 derived from this section)`)
    has an evidence-rule body, not a definitions body — it is a precision
    risk, and a negative guard may be the right answer.
14. **U2 — the 10-row scope item, now expressible.** QA cycle 3 confirmed the
    merged seam's generic `(unit_kind, unit_value)` model is **live**:
    `matcher._in_scope` supports M9 tuple-valued `source_chapter` /
    `source_article_number` / `scope_value` on the existing `chapter`/`local`
    kinds, plus a generic non-standard-kind path against
    `article.structural_units`. AK's multi-chapter range and ≥2 KY rows are
    expressible TODAY with no new scope-kind registration. Normal Developer
    item. Serves **U2**, live-path BOTH directions (in-scope mention links;
    out-of-scope mention does NOT — program standing constraint). Measure each
    of the 10 individually; whatever stays unexpressible goes to ledger L5 by
    act_id.

**Style gate:** `us_heading_variants.py` is **479 lines** vs the repo's
300-line convention — carried as a preserved-rationale exception. If cycle 5
grows it materially, **split it** and update the PRD agent inventory per repo
style gates. This is a Planner design input, not an afterthought.

## Dev Complete

- **Item 1 — `rules/us_heading_variants.py`** (dev `c986001`). Six rules
  (R-SEC, R-MID, R-VERB-bare, R-VERB-extended, R-TRUNC, R-MISSPELL), 269
  lines, pure function, no `__init__.py`, no registration call (ruling
  H-R5). CHECK PASSED: unit suite **19 passed**; `git diff --stat -- backend/app/`
  = exactly one new file (U3); `-- backend/tests/` = empty (role separation).
- **Item 2 — composed deterministic-engine end-to-end** (no extra code).
  CHECK PASSED: `TestComposedDeterministicEngine` **8 passed**, incl. the 4
  positive yields (CT 82, MO 6, WI 27, CT-misspelled 3), the term-use
  link-back proof, and the 3 zero-yield hand-offs pinned as documented
  markers-family routing (H-R1).

Full suite: **669 passed, 2 failed** (baseline 641 → +28 green, zero
regressions). The 2 failures are the core-blocked pair, item 3's dependency.

**Manager's independent full-corpus verification** (not the fixture suite —
`scratchpad/manager_verify_u4_u6.py`, all 2,014,611 rows, 52 files):
newly recognized **20,307 / 22,228 miss pool = 91.4%**, reproducing the
Planner's figure exactly on independently written code. WA 74.3%→96.5%,
FL 84.6%→98.5%, NY 91.4%→98.6% (U6's named states). Precision: **zero**
false positives — 0 rows matched without a `defin` substring, and the 123
non-canonical-token matches are exactly 117 R-TRUNC + 6 R-MISSPELL intended
captures with 0 morphology noise and 0 unexplained. Details in `-log.md`.

- **Item 4 — `HeadingRule` self-registration** (dev `f461371`, phase-2 manager).
  The `register_heading_rule(HeadingRule(("US-*",), matches_heading_variant))`
  call H-R5 deferred out of Phase A, added now that core is merged. CHECKS
  PASSED: registry-integration unit suite **2/2**; auto-discovery live check
  registers exactly **1** rule for `US-CT` and **0** for `IL`; full suite
  **729 passed / 1 failed**; `git diff --stat -- backend/tests/` empty.
  Manager proved all executable code byte-identical to the prior commit apart
  from the import + registration line. File 304 lines (soft-300 convention
  overage, entirely preserved rationale — recorded, not cut).

## Completed

_None._

## BLOCKED — two core-owned seam gaps (RESOLVED by ruling P-R8; awaiting core)

**Both blockers are ruled, not open questions.** Program ruling **P-R8**
(main `0f4e8fc`): core reopens for a dispatch-completion sprint covering all
five dead rule kinds, the ungated `derive_heading_from_body` (this panel's
D-PREAMBLE-ALL non-implementation finding = core's scope item 2), and **this
panel's `body_confirms` design accepted as-is** (core's scope item 4, credited
to this panel). The PR panel independently found the same dead dispatch.

**This sprint stays `blocked` until core's dispatch merges — the program
manager wakes this panel.** Phase B items 3, 5, 6, dev cycle 4 (D-DF), and
gates U1 (live-path leg) / U2 / U4 / U6 remain gated on that merge. Full
evidence in `-log.md` § "Manager phase 2 — takeover verification".

- **Blocker A — `HeadingRule` is registered but never consumed.** 5 of the 7
  rule kinds (heading, body_preamble, entry_splitter, term_clause,
  structural_unit) have **zero production callers** on merged main; only
  `ScopeTriggerRule` and `CitationRule` are wired. Proven live-path: an
  everything-matching `HeadingRule` is returned by `heading_rules_for("US-CT")`
  yet `profile.is_definitions_heading` still returns False. This sprint's
  entire measured recall win (20,307 headings, 91.4%→94.7%) therefore has
  **zero production effect** today. Gates **U1** (live-path recognition) and
  **U3** (zero shared-module edits) cannot both be met by this panel: the fix
  is an edit to core-owned `us_profile.py`. Also blocks the markers, multiterm,
  and preamble panels.
- **Blocker B — D-DF is not expressible in any rule kind.** `HeadingRule.matches`
  receives the heading only; no kind in the seam receives **both** heading and
  body, which is exactly what D-DF's body-confirmed capture requires. Note the
  body (`matcher_article.body`) is already in scope at the detection call site
  (`pipeline.py:198`), so this needs no new plumbing — only a seam decision.

## Context Dump

**Parked cleanly, waiting on core's dispatch sprint (ruling P-R8).**

What the phase-2 manager did: verified the inherited state, merged core into
this branch (`1d17d81`, merge not rebase — accepted deviation, see log), landed
Phase B item 4 (`f461371`), escalated both seam gaps, and got them ruled.

**Suite state: 728 passed / 13 failed — all 13 red by design.** 12 are the
Planner's pre-authored D-DF REDs (11 `ImportError` on symbols the Developer
has not written yet, 1 registration-count assertion); the 13th is
`test_us_heading_variants_end_to_end.py::TestRealProductionPipeline::test_connecticut_ucc_row_produces_real_definitions_via_the_real_pipeline`,
the core dispatch gap. **Zero unexplained failures.** Accounting from the
pre-Planner 729/1: 729−1 passed (the amended registration test flipped RED
deliberately), 1+11+1 = 13 failed.

**Resume point (when the program manager wakes this panel):**

1. Re-run the suite. The CT pipeline test should go green with **no change from
   this panel** once core wires heading-rule consumption — if it does not, that
   is the first thing to diagnose.
2. **Developer implements D-DF against the Planner's already-committed RED**
   (`7f6964d`), which locks the design precisely: register **TWO**
   `HeadingRule`s — unconditional FIRST
   (`matches_heading_variant_unconditional` = today's union minus the `for`
   alternation, `body_confirms=None`), then the narrow gated one
   (`matches_defined_for_heading`, `body_confirms=defines_in_body`). Three new
   symbols required. `matches_heading_variant` **keeps its exact current
   meaning** (27 tests depend on it; an equivalence test pins the
   decomposition). **The trap:** attaching `body_confirms` to the existing
   single union rule would body-gate all ~20,307 recognized headings instead
   of the 110 `defined for` rows. Order and rule-2 narrowness are load-bearing,
   not stylistic — see the D-DF test module docstring.
3. QA cycle 3 (`qa_cycles` is 2 of 5): U1 live-path leg, U6 re-measurement,
   U4 + the P-R7 cross-reference against the preamble panel's consolidated
   body-driven inventory (request the pointer through the program manager —
   do NOT re-scan the corpus). Our 22,228-row miss pool is `defin`-substring-
   derived and so cannot certify U4 alone. **Additionally:** re-confirm the
   `body_confirms` dispatch semantics against core's ACTUAL implementation —
   the design is proven safe under both plausible readings of
   "first-positive-wins", but which one core shipped is unobservable until
   then. Consider renaming
   `test_module_self_registers_exactly_one_heading_rule_for_us_star`, whose
   name is now stale (it asserts two registrations; kept deliberately for
   git-blame traceability).

**Corrections to earlier context, both recorded at program level:** the
"defined for" rule is COMMITTED (`a0419a4`), so D-DF *changes shipped
behavior*; and QA cycle 2's "sixth gap" was already closed in dev cycle 3.

**Standing items, unchanged:** the U2 10-row known limitation (recheck against
seam v2 now that core is reopening); the 245-row D-HG guarded cluster handed
off in `-guarded-cluster.md`; the ~19 UNCLEAR Connecticut rows and
`STATE_CT_T38a_C704_S38a-818` ("not so defined" defeats the negation guard via
an intervening "so") on the program data-quality list.
