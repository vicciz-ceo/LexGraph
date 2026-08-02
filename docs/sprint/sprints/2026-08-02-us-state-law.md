---
id: "2026-08-02-us-state-law"
status: dev-complete
current_role: qa
branch: claude/us-state-law-compat-6d3ae8
locked_by: "claude-code:planner"
locked_at: "2026-08-02T10:00:34Z"
last_agent: "claude-code:qa"
last_updated: "2026-08-02T11:02:46Z"
lint: "PASS 238 2026-08-02T11:03:56Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 6
completed_items: 4
dev_complete_items: 0
qa_cycles: 1
previous_sprint: "2026-07-31-admin-provisioning"
prd_sections: []
design_sections:
  - docs/sprint/sprints/2026-08-02-us-state-law-review.md
  - docs/sprint/sprints/2026-08-02-us-state-law-log.md
---

# Sprint: U.S. state law compatibility — deterministic pipeline

## Mandate (director)

> "Let's also bring all U.S. state law compatibility on board. here is the link
> to the DB: https://huggingface.co/datasets/vaquill/open-us-law
> Let's do all the same for the deterministic part."

Recon dossier: `docs/sprint/sprints/2026-08-02-us-state-law-review.md` (read it;
do not re-derive its findings).

## Director decisions (2026-08-02, AskUserQuestion — binding)

1. **Architecture — jurisdiction seam.** Refactor the six
   `backend/app/definition_links/` modules so language/citation rules live behind
   a per-jurisdiction profile. Port Hebrew to the seam FIRST and keep the existing
   suite green (that is what proves the seam is faithful), then add US as the
   second profile. Explicitly NOT a fork.
2. **Corpus scope — bulk-ingest everything.** All 109 parquet files (50 states +
   DC + PR + federal, statutes + constitutions, ~2M sections). Director's stated
   reason: "we want to prove this works." Ingestion must actually be RUN and
   measured, not sampled and extrapolated.
3. **Jurisdiction — controlled vocabulary now.** Fixed set (IL + US-AL…US-WY +
   US-DC, US-PR, US-FED), validated at the API, and the deterministic pipeline
   must stamp it on every assertion it creates. Today the column is free-text,
   unvalidated, and never written by the pipeline.
4. **UI — full pass.** Jurisdiction picker, badges, review-queue filtering, and
   profile preferences across every affected page.

## Manager rulings

- **R1 — Branch.** Sprint runs on `claude/us-state-law-compat-6d3ae8` (already
  created for this task), not `sprint/{id}`. Carve-out from the harness default:
  this repo's established flow is `claude/*` → PR → main (cf. PR #17).
- **R2 — Hebrew is a regression surface, not a rewrite target.** Every existing
  Hebrew definition-linking test must pass unchanged after the seam refactor. A
  test edited to accommodate the refactor is a planning bug: escalate, do not edit.
- **R3 — Bulk ingest must be honest.** The full-corpus run is a measured
  deliverable: report rows ingested, wall time, peak memory, and per-file
  failures. If the full run is infeasible here, report the wall hit with numbers.
  Do NOT report success from a subset.
- **R4 — Test baseline first.** `docs/sprint/repo-profile.md` records a stale
  July snapshot (39 FAILED / 87 ERROR). The Planner establishes the TRUE current
  baseline before authoring RED tests, and records it below, so this sprint is
  never blamed for pre-existing failures.
- **R5 — Vocabulary is shared surface.** The jurisdiction enum is touched by
  backend models, API schemas, and frontend types. It is defined ONCE, upfront,
  in a single Planner-owned commit before any parallel track starts.
- **R6 — No test may download the corpus.** The routine suite must run offline
  and fast. RED/regression tests use SMALL fixtures containing REAL rows copied
  out of the vaquill parquet files (real column names, real statute text) and
  committed to the repo. The 1.1GB full-corpus run of G6 is a separate,
  explicitly-invoked, measured deliverable — never part of `pytest backend/tests`.
  Any network-dependent test is marked and skipped by default.

- **R7 — Manager live-path + real-data findings (2026-08-02, after wave 3).**
  (a) Live path VERIFIED by the manager directly: 3 real Delaware rows through
  the real `ingest_us_statute_rows` -> `run_definition_linking` produce 3
  definitions (`Affiliate`, `Branch office`, `Insured depository institution`)
  and 2 DERIVES_FROM_LAW assertions incl. real federal cite `12 U.S.C. § 1813(c)`,
  all stamped `US-DE`, zero nulls. Pre-fix the same probe produced 0 and 0.
  (b) **NEW DEFECT, item 5, found by manager probe of the REAL dataset:** the
  wave-3 idempotency fix skips any row with an empty `chapter`. On the real
  `us_de_statutes.parquet` (21,649 rows) **647 rows (3.0%) have an empty
  `chapter`** and would be dropped — real law lost, one state alone. `citation`
  is null/empty in **0%** of rows and is the canonical unique legal identifier
  (e.g. `5 Del. C. § 796`). QA must reproduce this and bounce item 5.

## Acceptance gates (manager-defined, plain language)

Each gate is a pass/fail condition about observable product behavior. The Planner
turns each into failing tests across the pyramid before any Developer is spawned.

- **G1 — Hebrew is unharmed.** After the refactor, every existing Hebrew
  definition-linking behaviour is identical: same definitions found, same links
  created, same cross-law references detected, on the same fixtures.
- **G2 — A real US statute parses.** Given a real file from the vaquill dataset,
  the pipeline finds an English "Definitions" section and extracts its terms,
  with no Hebrew-specific rule involved.
- **G3 — English term linking works.** A term defined in a US statute and used
  later in that statute produces a link, using English word-boundary rules (not
  Hebrew prefix-letter expansion), and does not false-match inside longer words.
- **G4 — US citations are recognised.** References such as "as defined in
  Section 5", "§ 101", and "15 U.S.C. § 1" are detected as law/section references
  rather than silently dropped.
- **G5 — Jurisdiction is always stamped and always valid.** Every assertion the
  pipeline creates carries the correct jurisdiction code; the API rejects a value
  outside the controlled vocabulary.
- **G6 — The whole corpus loads.** All 109 dataset files ingest through one
  documented command, with a real measured report (see R3).
- **G7 — A reviewer can work state-by-state.** In the UI, filtering to a single
  jurisdiction shows only that jurisdiction's content, and jurisdiction is
  visible on the items themselves.

## Test baseline (Planner fills in — R4)

`docs/repo-profile.md`'s snapshot (126 backend / 39 FAILED / 87 ERROR; 59
frontend RED) is **stale and wrong**. True baseline, verified 2026-08-02:
- Backend: `backend/.venv/bin/pytest backend/tests -q` → **504 passed**, 0
  failed, 0 error (14 warnings, pre-existing deprecation noise only).
- Frontend: `npm --prefix frontend run test -- --run` → **151 passed** (20
  files), 0 failed.
- Typecheck: `npm --prefix frontend run typecheck` → exit 0, no output.

No pre-existing failures to protect against — this sprint starts all-green.
Full commands + output: sprint log §"R4 — true test baseline".

## Stale-pin sweep

Swept all 4 test roots (case-insensitive `grep -riE` for jurisdiction
literals) + `*.snap` (none exist). **No re-pointing needed**: the only
hits are `"IL"`/`"US-DE"` fixture literals already valid under the chosen
vocabulary (`ContestedPage.test.tsx:74`, `KnowledgeBasePage.test.tsx:59`,
`ProfilePage.test.tsx:70`, `ReviewQueuePage.test.tsx:91`,
`AssertionDetailPage.test.tsx:80,132`) plus 2 unrelated prose matches
(the word "jurisdiction" inside proposition/comment text, not a value).
One REAL drift risk found outside the sweep's test-root scope:
`app/seed_demo.py` sets `jurisdiction="EU"` (4x, via the real API) — not
in the new vocabulary; flagged as a required same-commit fix for the
vocabulary item's Developer (change to `"IL"`). Full detail: sprint log.

## Next Steps

### Item 3 — US jurisdiction profile [G2, G3, G4]
[QA-FAIL: `USProfile`/`get_profile` have zero production call sites (grep-
verified: referenced only inside `profiles.py`/`us_profile.py` and test files) —
`pipeline.py` never dispatches to any profile, so a real US-DE document ingested
via `ingest_us_statute_rows` and run through the real `run_definition_linking`
recognizes ZERO Definitions sections and creates ZERO assertions/definitions.
Proven by `test_real_pipeline_never_recognizes_a_real_us_definitions_section_for_a_us_document`
(backend/tests/integration/test_qa_regression_us_state_law_FAIL.py). Expected:
G2/G3/G4 satisfied by the real pipeline, not only by unit tests that call
`get_profile(...)`'s methods directly, bypassing `pipeline.py` entirely.
ADDITIONALLY: `is_definitions_heading`'s unanchored `\bDefinitions?\b` substring
check false-positives on real non-definitions headings ("Application of
Definitions to Prior Acts", "Repeal of Definitions") — proven by
`test_us_profile_is_definitions_heading_false_positives_on_non_definitions_headings`.
Expected: only genuine Definitions sections match. Fix needs `pipeline.py` (item 4's
file) to call `get_profile(document.jurisdiction)` per document at Stages 1-4, plus
tightening the heading regex.]

### Item 5 — US dataset ingester [G6 — code only]
[QA-FAIL: `ingest_us_statute_rows`'s idempotency key is `(document_id,
section_number)` only, ignoring title/chapter — the module's own docstring warns
real statute files repeat a bare section number across titles/chapters, but the
implementation doesn't guard it. A second, genuinely different row sharing an
already-seen `section_number` is silently dropped: not persisted, not counted in
`skipped_rows` either. Proven by
`test_ingest_us_statute_rows_drops_a_row_when_its_section_number_collides_with_another_rows_across_titles`
(backend/tests/integration/test_qa_regression_us_state_law_FAIL.py). Expected: every
genuinely distinct row persists as its own Article, or is explicitly reported as
skipped — idempotency key must include title/chapter, not section_number alone.]

## Dev Complete

_None — all 6 items processed this QA cycle (4 to Completed, 2 bounced above)._

## Completed

- **Item 1 — Jurisdiction controlled vocabulary [G5].** Commit `be609a5`.
  QA: PASS — P5: 54-code vocabulary byte-identical across backend/frontend/live
  endpoint; regression `test_frontend_jurisdiction_list_source_matches_backend_source_exactly`.
- **Item 2 — Jurisdiction-profile seam, Hebrew ported [G1].** Commit `7daf286`.
  QA: PASS (narrow claim — Hebrew pass-through verified identical on untested inputs).
  QA FLAG: `pipeline.py` never calls `get_profile` — seam unwired; see Item 3 QA-FAIL.
- **Item 4 — Jurisdiction stamping [G5].** Commit `9662def`.
  QA: PASS — P1: null-jurisdiction miss proven unreachable via either production
  ingester; regression `test_document_jurisdiction_is_never_null_after_either_production_ingester_runs`.
- **Item 6 — UI jurisdiction pass [G7].** Commit `70db22e`.
  QA: PASS — frontend 165/165 green, typecheck clean; vocabulary drift-guard
  (Item 1) covers this item's picker source too.

**Merged-tree evaluator (manager-run, 2026-08-02, all 6 items):**
backend **621 passed / 0 failed / 0 errors**; frontend **165 passed / 0 failed**;
typecheck clean. Zero regressions against the 504/151 baseline.

**QA-run evaluator (2026-08-02, independent re-run):** backend **626 passed**
(621 + 5 new QA PASS-regression tests) **/ 0 failed** on the merged tree, **+ 3
intentional RED tests** in `test_qa_regression_us_state_law_FAIL.py` proving the
2 bounces above; frontend **165 passed / 0 failed**; typecheck clean.

## Evaluation Notes

_None yet._

## QA Notes

- **Mandatory live-path trace (central finding).** `get_profile`/`USProfile`
  have ZERO production call sites (grep-verified) — `pipeline.py` still
  calls the bare `sections`/`extract`/`matcher`/`derivation` functions
  directly for every document regardless of jurisdiction. A real US-DE
  document ingested via item 5's ingester and run through the real
  `run_definition_linking` produces zero definitions/assertions. Item 3's
  own "end-to-end" test bypasses `pipeline.py`; item 4's "US document"
  test uses HEBREW text merely labeled `US-DE`. Bounced item 3.
- **P1 (silent null jurisdiction) — not reachable, item 4 PASS.** Both real
  ingesters (`ingest_wiki_law`, `ingest_us_statute_rows`) always create a
  Document and its Articles with the SAME `matter_id` in one call, and
  `Document.jurisdiction` is NOT NULL (ORM default + DB `server_default`,
  both `"IL"`). A genuinely-ingested Article's document is always present
  in `document_jurisdictions` with a real value — the `.get()` miss branch
  is defensive-only, unreachable via any production path. Regression added.
- **P2 (`HebrewProfile.find_citations` stub) — moot, not a live risk.**
  Since `pipeline.py` never calls `get_profile` for ANY jurisdiction
  (Hebrew included — see live-path trace above), `find_citations` is
  unreachable for Hebrew too, same as for US. G1 holds only because the
  bare Hebrew functions were never touched, not because dispatch correctly
  routes to `HebrewProfile`.
- **P3 (US heading false-positive) — confirmed, item 3 bounced.**
  `is_definitions_heading`'s unanchored `\bDefinitions?\b` search matches
  "Application of Definitions to Prior Acts" and "Repeal of Definitions" —
  neither is a definitions section. RED test committed.
- **P4 (idempotency data loss) — confirmed, item 5 bounced.**
  `ingest_us_statute_rows` keys idempotency by `(document_id,
  section_number)` only; a second row sharing a section number across
  titles/chapters within one file is silently dropped, uncounted even in
  `skipped_rows`. RED test committed with real fixture text proving loss.

## Context Dump

Planner pass complete 2026-08-02: true baseline established (all-green,
see above), 6 items defined, RED tests authored + confirmed for all 6
(23 backend RED signals, 14 frontend RED tests across 5 files — full
per-file breakdown in the sprint log). Real DE fixture rows committed at
`backend/tests/fixtures/us_statutes/`. Zero implementation written.
Next: manager reviews item/track split, rules on parallelization, spawns
Developer(s) starting with Item 1 (no dependencies) and Item 2 (blocks
Items 3/4). Full rationale for every design call: sprint log.
