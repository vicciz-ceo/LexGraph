---
id: "2026-08-02-us-state-law"
status: review
current_role: planner
branch: claude/us-state-law-compat-6d3ae8
locked_by: "claude-code:planner"
locked_at: "2026-08-02T10:00:34Z"
last_agent: "claude-code:qa"
last_updated: "2026-08-03T21:18:00Z"
lint: "PASS 320 2026-08-03T21:18:13Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 6
completed_items: 6
dev_complete_items: 0
qa_cycles: 5
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

- **R7-R13 — historical verification rulings** (wave 3/4/5/5b findings, live-path
  proofs, per-state coverage tables, invalid-test ruling): moved to
  `2026-08-02-us-state-law-log.md#manager-rulings-r7-r13` to hold the contract
  budget. Key standing outcomes: heading matcher verified 0 false positives across
  10 states; ingest key is the dataset's own `act_id` (0 collisions / 570,397 real
  rows); QA's IL unit test was ruled invalid and inverted.
- **R14 — Wave 6 verified by the manager (2026-08-03).** Real rows through the
  REAL pipeline: **IL 40 rows -> 240 definitions / 102 assertions** (terms
  `Bias-free`, `BIPOC`, `Child welfare court personnel`); **CA 40 rows -> 73
  definitions / 25 assertions** (`Electronic poll book`, `Vote by mail ballot drop
  box`); **DE unchanged at 217/125** (no regression). Both IL and CA produced ZERO
  before this wave. Suite 639 passed / 0 failed — first full green since QA
  cycle 1. Test-owner correctly INVERTED the invalid assertion (now asserts a bare
  `"Section N"` placeholder is REJECTED), turning R12's hazard into a guard.
- **R15 — Two open risks carried into QA cycle 4 (manager-flagged).**
  (a) **Precision is unmeasured.** Wave 6 added an inline-quote extraction
  FALLBACK inside `pipeline.py` (not the profile) because IL/CA bodies carry no
  `(N)` markers. Every prior cycle measured RECALL (how much we miss). Nobody has
  measured PRECISION — whether the ~9,661 IL / ~6,961 CA candidate terms are
  genuine defined terms or noise. A fallback extractor firing on body-derived text
  is exactly where junk terms would enter. QA must sample and judge quality.
  (b) **Architectural smell:** definition-extraction logic now lives in
  `pipeline.py` rather than behind the jurisdiction profile. Developer flagged it
  honestly as a deviation forced by file ownership. Not a defect; a follow-up.
  (c) **Georgia still effectively blind:** 5 detected / 28,154 rows. GA's
  convention (`"As used in this chapter, the term:"`) carries no "definitions"
  word. Deliberately not forced under the zero-false-positive priority.

- **R16 — Wave 7 merged; manager-verified WITH a stated residual (2026-08-03).**
  Root cause was broader than QA's report: the entry splitter only accepted a bare
  `(N)` digit marker, so LETTER-led entries (`(d) (1) "Dispose" means`, `(e)
  "Open-space purposes" means`, TX's `(6)(A) "Gross revenues"`) were never treated
  as boundaries. Not a CA-only bug — DE (+756 terms) and TX (+75) were silently
  losing terms too. Evaluator: **641 backend / 165 frontend / typecheck clean**.
  **Manager probe of the exact defective row (`STATE_CA_..._S54221`): 10
  definitions now extracted (was 2); `Open-space purposes` recovered; `Dispose`
  26,715 -> 286 chars.**
  **RESIDUAL, not fixed — carried as a known limitation:** the bloat MOVED rather
  than cleared. `Open-space purposes` is now itself **21,174 chars**, and two
  extracted "terms" on that row are sentence fragments (`A contract or contracts
  serving as an enforceable restrict...`), not defined terms. Corpus-wide impact
  looks small (QA cycle 4 sampled 120 terms across IL/CA/DE/TX: 120/120 genuine;
  Developer measured >5,000-char records CA 13 -> 5), but this one real section is
  still not cleanly parsed. Manager decision: DO NOT spend the last QA cycle
  bouncing this; document it and let QA cycle 5 sign off gates with the limitation
  recorded. Follow-up sprint candidate.

- **R17 — GATE G6 PROVEN. Full-corpus run executed and measured by the manager
  (2026-08-03/04), per ruling R3.** Not sampled, not extrapolated:
  | metric | measured |
  |--------|----------|
  | parquet files found / processed / failed | **105 / 105 / 0** |
  | rows newly ingested | **2,045,897** |
  | rows skipped (counted, with reason) | **112** — all "missing required 'text' column" |
  | rows accounted for | **2,046,009** = 2,045,897 + 112 (invariant holds) |
  | DB documents / articles / source_spans | **105 / 2,045,897 / 2,045,897** |
  | distinct jurisdictions stamped | **53** (50 states + DC + PR + FED) |
  | download wall time | 0.4 min (1.19 GB) |
  | ingest wall time | **18.9 min** |
  | peak RSS | **606 MB** (QA feared multi-GB; it did not materialise) |
  | CLI exit code | 0 |
  **The CLI's self-reported count matches the DB ground truth EXACTLY** — the
  manager queried the database directly rather than trusting the tool's summary,
  which is precisely the conflation QA cycle 3 caught and wave 5b fixed. Zero
  silent loss: every one of the 112 skipped rows is reported with a reason.
  Corrects an earlier manager error: the corpus is **105** parquet files, not 109
  (109 = total repo files including non-data files).

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

_None — sprint complete. All 6 items PASS, all 7 gates signed off (see
`## Completed` and `## Known limitations at sprint close`). Next action is
the director's merge decision._

## Dev Complete

_None._

## Completed

- **Item 1 — Jurisdiction controlled vocabulary [G5].** Commit `be609a5`.
  QA: PASS — P5: 54-code vocabulary byte-identical across backend/frontend/live
  endpoint; regression `test_frontend_jurisdiction_list_source_matches_backend_source_exactly`.
- **Item 2 — Jurisdiction-profile seam, Hebrew ported [G1].** Commit `7daf286`.
  QA cycle 5: PASS, re-confirmed final time — 167 Hebrew/definition-link
  tests green, unchanged after wave 7 (`HebrewProfile.code=="IL"` guard).
- **Item 3 — US jurisdiction profile [G2/G3].** Wave 7 (entry-splitter fix
  for letter-led entries). QA cycle 5: PASS-with-limitation — live-path
  verified the cycle-4 bounce is fixed (`Open-space purposes` recovered,
  `Dispose` 26,715→286 chars); residual bloat/truncation quantified and
  recorded as a known limitation, not re-bounced (see below).
- **Item 4 — Jurisdiction stamping [G5].** Commit `9662def`.
  QA: PASS — P1: null-jurisdiction miss proven unreachable via either production
  ingester; regression `test_document_jurisdiction_is_never_null_after_either_production_ingester_runs`.
- **Item 5 — US dataset ingester [G6].** Wave 5b fix. QA cycle 5: PASS —
  R17's full 105-file/2,045,897-row corpus run independently spot-checked
  (4 real files, DB counts match CLI exactly, 112 corpus-wide skips
  reproduced exactly); no longer code-only, gate is RUN-verified.
- **Item 6 — UI jurisdiction pass [G7].** Commit `70db22e`.
  QA: PASS — frontend 165/165 green, typecheck clean; vocabulary drift-guard
  (Item 1) covers this item's picker source too.

## Known limitations at sprint close

- **Georgia's definitions convention is undetected.** Only 5 of 28,154 GA
  rows are recognized; 438 rows (1.56%) open with `"As used in this
  chapter, the term:"`, a convention with no "definitions" word at all. A
  follow-up needs a GA-specific body-preamble rule, added carefully to
  avoid false positives elsewhere.
- **A small number of extracted definitions are still garbled.** The
  shared extractor's entry-boundary detection is imprecise around nested
  lettered/numbered sub-clauses, in BOTH directions: it can swallow too
  much (the CA "Dispose" row: fixed from 26,715→286 chars, but
  `Open-space purposes` on the same row is itself ~21,174 chars with 2
  sentence-fragment "terms"), or cut too early (a `"Term" means:` stub
  right before an unquoted sub-list, or — TX only — a list of terms that
  share one definition stated in a parent clause). Corpus-wide: 424 of
  258,472 extracted definitions (0.16%) exceed 5,000 characters; among
  wave 7's newly-recovered terms specifically, degenerate (near-empty)
  definitions run CA 0.22%, DE 1.72%, TX 17.33% of that small subset
  (TX: 13 of only 75 recovered). A follow-up needs the extractor to
  distinguish "new entry" from "sub-clause enumeration inside the current
  entry" more precisely.
- **Extraction logic lives in `pipeline.py`, not behind the profile seam.**
  The inline-quote fallback and body-heading derivation were added to
  `pipeline.py` rather than `USProfile`, a deviation from the intended
  architecture forced by file-ownership constraints. Not a functional bug;
  a structural cleanup for later.
- **Heading-matcher recall gaps in 3 of 7 working states.** WA 10.3%, FL
  5.5%, NY 4.4% of real Definitions sections are not recognized (real
  headings with extra words, e.g. multi-topic titles) — a recall gap, not
  a false-positive risk; zero false positives held throughout.
- **Bulk-ingest memory is unbounded within one run.** Bulk directory mode
  holds one DB session across all 105 files without expunging, so the
  identity map grows with total rows processed; the manager's real run
  measured 606 MB peak RSS for the full corpus, well under the several-GB
  worst case once feared, but a very large future corpus could still grow
  this unboundedly without a periodic expunge/flush.

## Evaluation Notes

Cycle 5 (final) reproduces the contract's stated baseline exactly: backend
641 passed / 0 failed, frontend 165 passed / 0 failed, typecheck clean,
167/167 Hebrew+definition-link tests green. No implementation code touched
this cycle (QA scope only); 2 tests renamed out of
`test_qa_regression_us_state_law_cycle4_FAIL.py` into the standing
`test_qa_regression_us_state_law.py` file per close-out (both already
passed; net test count unchanged), and the FAIL-named file deleted.

## QA Notes

- **Q1 (cycle 5, FINAL) — wave-7 precision re-audit.** General 30-term
  samples CA/DE/TX all 30/30 genuine (matches cycle 4). Targeted the
  ~2,400 letter-led recovered terms specifically: degenerate-definition
  rate CA 0.22%, DE 1.72%, TX 17.33% (13/75) — materially above the
  pre-existing shape's own ~0.1% rate, but not a regression (these terms
  were extracted 0% of the time before wave 7). Same root cause as R16's
  residual, inverse symptom (truncation, not swallow). Log §"QA cycle 5" Q1.
- **Q2 (cycle 5, FINAL) — R16 residual verified TRUE, bloat quantified.**
  Reproduced the exact row: 10 unique terms (was 2), `Dispose` 286 chars,
  `Open-space purposes` 21,174 chars, exactly 2 sentence-fragment terms —
  all match R16 verbatim; no correction needed. Corpus-wide (full 105-file
  live-dispatch replay): 424 of 258,472 extracted definitions (0.164%)
  exceed 5,000 chars. Log §"QA cycle 5" Q2.
- **Q3 (cycle 5, FINAL) — R17's G6 numbers independently re-verified,
  all correct.** Corpus is exactly 105 parquet files (confirmed via the
  real snapshot directory). 112 skipped-with-reason reproduced exactly via
  an independent pyarrow scan (110 GA + 2 NC, all genuinely empty `text`).
  Spot-ingested 4 real files through the live CLI against a fresh DB: DB
  Article counts match CLI-reported counts exactly every time; idempotent
  re-run confirmed. Log §"QA cycle 5" Q3.
- **Q4 — Hebrew final, unchanged.** 167/167 Hebrew+definition-link tests
  green after wave 7; `HebrewProfile.code=="IL"` guard unchanged.
- **Q5/Q6 — Georgia + heading-miss numbers re-verified unchanged; FINAL
  gate sign-off.** GA 5/28,154 (438 rows, 1.56%, undetected convention),
  WA/FL/NY 10.3%/5.5%/4.4% heading-miss — all reproduced exactly,
  unaffected by wave 7. G1/G3/G4/G5/G7 PASS, G2 PASS-with-limitation, G6
  now RUN-verified PASS (was code-only). Full table: log §"QA cycle 5".

## Context Dump

Sprint COMPLETE as of QA cycle 5 (final): all 6 items PASS, all 7 gates
signed off (G2 and G6 formerly open, now closed — see Completed), 641
backend / 165 frontend / typecheck clean, 167/167 Hebrew tests unchanged.
Known limitations documented above (Georgia, residual bloat/truncation,
architecture wrinkle, heading-miss rates, bulk-memory growth) — all
accepted scope, none gate-blocking. Next: director reviews for merge to
`main`; no further QA/dev cycles needed. Full evidentiary detail for every
claim in this contract: sprint log (`-log.md`).
