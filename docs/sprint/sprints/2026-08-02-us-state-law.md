---
id: "2026-08-02-us-state-law"
status: qa-fail
current_role: developer
branch: claude/us-state-law-compat-6d3ae8
locked_by: "claude-code:planner"
locked_at: "2026-08-02T10:00:34Z"
last_agent: "claude-code:qa"
last_updated: "2026-08-03T20:38:00Z"
lint: "PASS 290 2026-08-03T20:38:15Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 6
completed_items: 5
dev_complete_items: 0
qa_cycles: 4
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

_Cycle 3's 6 defects (items 3 and 5, heading-matcher + ingest-key collisions)
were fixed and independently re-verified as genuinely fixed this cycle
(folded into `test_qa_regression_us_state_law.py`; full cycle-3 defect
detail preserved at log §"QA cycle 3"). Item 5 now PASSES outright (see
`## Completed`). Item 3 bounces again below for ONE new, narrower defect
found by this cycle's headline precision audit (ruling R15a) — full detail
at log §"QA cycle 4"._

### Item 3 — US jurisdiction profile [G2/G3], one live-path-confirmed boundary-swallow defect in a real California section

[QA-FAIL (defect 8): a real California row
(`STATE_CA_Cgov_T5_D2_P1_C5_A8_S54221`, committed at
`backend/tests/fixtures/us_statutes/qa_cycle4_rows.json`) produces one
`Definition` for the term "Dispose" whose `definition_text` is **26,715
characters** and contains the complete, separately-defined text of 3 OTHER
real terms ("Open-space purposes", "Sectional planning area", "Sectional
planning area document") concatenated inside it — none of the 3 is ever
recovered as its own `Definition`. Root cause: `USProfile.extract_
definitions_from_section` (the shared DE/TX/IL/CA numbered-entry extractor,
NOT new wave-6 code) fails to recognize a new `"Term" means` entry start
after a run of lettered sub-clauses inside the PRECEDING entry, and keeps
consuming text until the NEXT entry it does recognize (3 entries later) —
newly EXPOSED to CA bodies for the first time by wave 6's heading-derivation
dispatch (CA never reached this function before this sprint). Proven
live-path by `test_real_pipeline_swallows_three_other_terms_into_one_
bloated_california_definition` in `backend/tests/integration/
test_qa_regression_us_state_law_cycle4_FAIL.py`. A companion suspected
defect in the SAME row (a curly-quote-style mismatch in entry (a)) was
investigated and found NOT to survive the live path —
`normalize_for_parsing` already collapses curly-quote variants before
extraction runs — kept as a green regression guard in the same file, not a
second bounce.

Expected: the shared extractor's entry-boundary detection must recognize a
new `"Term" means`/`has the meaning` entry start even immediately after a
run of lettered/numbered sub-clauses (`(A)`/`(B)`) belonging to the
PRECEDING entry's own body, rather than only re-synchronizing several
entries later.

## Dev Complete

_None — item 3 processed this QA cycle (bounced again above, for ONE new
defect distinct from cycle 3's six, all of which are now confirmed fixed)._

## Completed

- **Item 1 — Jurisdiction controlled vocabulary [G5].** Commit `be609a5`.
  QA: PASS — P5: 54-code vocabulary byte-identical across backend/frontend/live
  endpoint; regression `test_frontend_jurisdiction_list_source_matches_backend_source_exactly`.
- **Item 2 — Jurisdiction-profile seam, Hebrew ported [G1].** Commit `7daf286`.
  QA cycle 4: PASS, re-confirmed — 167 Hebrew/definition-link tests green;
  `HebrewProfile.code == "IL"` structurally blocks the wave-6 body-derivation
  fallback from ever reaching Hebrew documents (`pipeline.py`'s own guard).
- **Item 4 — Jurisdiction stamping [G5].** Commit `9662def`.
  QA: PASS — P1: null-jurisdiction miss proven unreachable via either production
  ingester; regression `test_document_jurisdiction_is_never_null_after_either_production_ingester_runs`.
- **Item 5 — US dataset ingester [G6].** Wave 5b fix. QA cycle 4: PASS —
  re-verified on `us_wa_statutes.parquet` (51,498 real rows, never checked
  before): CLI summary exactly matches DB Article count both fresh and
  re-ingested; 1,026 shared `section_number`s correctly produce distinct
  Articles (log §"QA cycle 4" Q2).
- **Item 6 — UI jurisdiction pass [G7].** Commit `70db22e`.
  QA: PASS — frontend 165/165 green, typecheck clean; vocabulary drift-guard
  (Item 1) covers this item's picker source too.

**Manager-measured state entering cycle 2:** backend **629 passed / 0 failed**;
frontend **165 passed**; typecheck clean.

**QA cycle 2:** backend **629 passed** + 3 new RED (Q2/Q3a/Q3b); frontend
**165/0**. **QA cycle 3:** backend **632 passed** (cycle 2's 3 folded green)
+ 7 new RED (6 fresh real-data defects, items 3/5 bounced); frontend
**165/0**. Full detail for both: log §"QA cycle 2"/§"QA cycle 3".

**QA cycle 4 independent re-run:** backend **640 passed / 1 failed** on the
routine suite (cycle 3's 7 RED bounce-proofs re-verified genuinely fixed and
folded into `test_qa_regression_us_state_law.py`;
`..._cycle3_FAIL.py` deleted, net test count unchanged) **+ 1 intentional
NEW RED test** (plus 1 new green regression guard disproving a second
suspected defect) in `test_qa_regression_us_state_law_cycle4_FAIL.py`,
proving one fresh real-data defect (item 3 bounced again — see
`## Next Steps`), found by a full-corpus precision audit (ruling R15a) of
`us_ca_statutes.parquet`; frontend **165 passed / 0 failed**; typecheck
clean.

## Evaluation Notes

_None yet._

## QA Notes

- **Q1 (cycle 4) — PRECISION audit (R15a), the headline probe.** Full-corpus
  scan (every real row, exact live dispatch replayed) + 30-term random
  samples for IL/CA/DE/TX: all 4 states' random samples 30/30 genuine, no
  fragments/citations/empty terms. Fallback (IL/CA) precision is NOT
  materially worse than the original extractor (DE/TX) — but ONE confirmed,
  live-path-proven junk record found (CA "Dispose", 26,715-char definition
  swallowing 3 other terms) → item 3 bounced. Full breakdown incl. all junk
  examples: log §"QA cycle 4" Q1.
- **Q2 (cycle 4) — ingest integrity PASS on a never-tested file (WA).**
  51,498 real rows: CLI summary exactly matches DB both fresh (51,498
  new/0/0) and re-ingested (0/51,498/0); 1,026 shared section_numbers all
  correctly produce distinct Articles. Item 5 now PASSES. Log §"QA cycle 4".
- **Q3/Q4 — Hebrew PASS, placeholder-misfire PASS.** 167 Hebrew tests green,
  `HebrewProfile.code=="IL"` structurally blocks the fallback. Placeholder
  pattern matched 7 ordinary rows across all 7 working states (1 NY + 6 NEW
  in PA) but 0 caused a real behavioural flip (body-derivation returns None
  for all 7, confirmed live). Log §"QA cycle 4".
- **Q5 — Georgia quantified.** 5/28,154 detected (confirms R15c); 438 rows
  (1.56%) share the exact undetected `"As used in this chapter, the term"`
  convention — real scope for the follow-up. Not fixed this sprint (by
  design). Log §"QA cycle 4".
- **Q6 + gate sign-off — GO, with a flagged memory caveat.** WA/CA/3-file
  bulk timing all measured (~3,700-4,000 rows/sec); extrapolated ~8-9 min
  for 2M rows. Memory bounded per-file (~280-380MB) but bulk mode's single
  un-expunged session means the identity map grows with TOTAL rows across
  all 105 files — extrapolated several-GB peak RSS, worth the manager
  monitoring. G1/G3/G4/G5/G7 PASS, G2 PASS-with-one-scoped-defect, G6
  CODE-ONLY. Full gate table: log §"QA cycle 4".

## Context Dump

Planner pass complete 2026-08-02: true baseline established (all-green,
see above), 6 items defined, RED tests authored + confirmed for all 6
(23 backend RED signals, 14 frontend RED tests across 5 files — full
per-file breakdown in the sprint log). Real DE fixture rows committed at
`backend/tests/fixtures/us_statutes/`. Zero implementation written.
Next: manager reviews item/track split, rules on parallelization, spawns
Developer(s) starting with Item 1 (no dependencies) and Item 2 (blocks
Items 3/4). Full rationale for every design call: sprint log.
