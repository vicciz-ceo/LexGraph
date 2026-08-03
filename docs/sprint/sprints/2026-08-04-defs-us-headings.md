---
id: "2026-08-04-defs-us-headings"
status: planning
current_role: planner
branch: claude/defs-us-headings
worktree: /Users/nerya/LexGraph-wt/defs-us-headings
locked_by: "claude-code:planner"
locked_at: "2026-08-04T00:00:00Z"
last_agent: "claude-code:sprint-manager"
last_updated: "2026-08-04"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 9
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
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
   fully green (19 tests: 10 positive-rule + 9 negative-guard). This item
   does NOT require core — only `app.definition_links.rules.registry`
   (imported at the bottom of the new module) is missing right now, and
   that import can be stubbed/deferred by writing `matches_heading_variant`
   first and the registration call last, then running the unit test file
   alone (it never imports `registry`) to confirm the pure function is
   correct before wiring the registration call.

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

### Not a dev/QA item — program-level escalation, tracked here so it isn't
lost

9. **U2 scope-seam gap for scope-unit-naming headings** (e.g. AK's real
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

_None._

## Completed

_None._

## Context Dump

New sprint. Planner: read program doc + dossier §2 family 4 + §6 addendum
(finding #2 verb-form table), re-confirm examples live, author RED tests.
