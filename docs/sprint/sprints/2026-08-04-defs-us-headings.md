---
id: "2026-08-04-defs-us-headings"
status: blocked
current_role: manager
branch: claude/defs-us-headings
worktree: /Users/nerya/LexGraph-wt/defs-us-headings
locked_by: "claude-code:sprint-manager"
locked_at: "2026-08-04T00:00:00Z"
last_agent: "claude-code:sprint-manager-phase2"
last_updated: "2026-08-04"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 9
completed_items: 0
dev_complete_items: 3
qa_cycles: 2
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

## BLOCKED — two core-owned seam gaps (escalated to the program manager)

Phase B items 3, 5, 6, dev cycle 4 (D-DF), and gates U1/U2/U4 are blocked.
Full evidence in `-log.md` § "Manager phase 2 — takeover verification".

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

Phase-2 manager took over after dev cycle 3, merged core (`1d17d81`), landed
Phase B item 4 (`f461371`), and escalated both blockers above. **Resume point:**
await the program manager's ruling on who wires detection-kind consumption and
how D-DF gets heading+body access. Nothing further in this sprint is
implementable until then — every remaining item depends on one of the two.
Corrections to earlier context: the "defined for" rule is COMMITTED (`a0419a4`),
not uncommitted; and QA cycle 2's "sixth gap" was already closed in dev cycle 3.
