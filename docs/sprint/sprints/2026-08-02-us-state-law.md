---
id: "2026-08-02-us-state-law"
status: qa-fail
current_role: developer
branch: claude/us-state-law-compat-6d3ae8
locked_by: "claude-code:planner"
locked_at: "2026-08-02T10:00:34Z"
last_agent: "claude-code:qa"
last_updated: "2026-08-02T11:34:57Z"
lint: "PASS 293 2026-08-02T11:35:03Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 6
completed_items: 4
dev_complete_items: 0
qa_cycles: 2
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

_QA cycle 1's bounces for items 3 and 5 (heading substring false-positive, the
missing pipeline.py dispatch wiring, and the section_number-only idempotency
key) were fixed by Developers and independently re-verified as genuinely
fixed by QA cycle 2 (see `## QA Notes` — Q1). Both items bounce again below,
this time for NEW defects QA cycle 2 found in the wave-3 fixes themselves,
proven against REAL Delaware rows, not the cycle-1 defects reopening._

### Item 3 — US jurisdiction profile [G2], NEW defects in the wave-3 heading fix
[QA-FAIL (Q3a, catastrophic backtracking / ReDoS): `us_profile
._DEFINITIONS_HEADING_RE`'s `(?:[^A-Za-z]+|Section\s+\d+\.?)*Definitions?\b`
construct is the classic `(X+)*` catastrophic-backtracking shape. On a real
US-DE heading with a long leading run of non-letter characters that does NOT
end up matching "Definitions" (`STATE_DE_T10_C54_S5402`'s real
`section_title`, a 43-char non-letter prefix — the dataset-wide maximum
across all 21,649 real DE rows), `is_definitions_heading` does not return
within 8 real wall-clock seconds (the PRE-fix unanchored substring check
returned instantly on the same input — this is a regression the wave-3 fix
itself introduced). Proven by
`test_is_definitions_heading_hangs_catastrophically_on_a_real_de_heading`
(backend/tests/integration/test_qa_regression_us_state_law_FAIL.py, bounded
by a 3s SIGALRM deadline so the suite fails fast instead of hanging). This
call sits directly on `pipeline.py` Stage 2's real per-article path
(`profile.is_definitions_heading(art.heading)`) — a single pathological
heading during the G6 bulk ingest (109 files, ~2M articles) would hang the
deterministic pipeline indefinitely on that one article.

ADDITIONALLY [QA-FAIL (Q3b, under-match regression)]: the same regex requires
"Definitions" to be the heading's first word after stripping a leading
non-letter run, but real DE section identifiers routinely embed a letter
INSIDE the section number itself (`4A-103`, `12D-102`, `9002A` — the standard
modern DE supplemental-section numbering convention), which breaks that
leading-non-letter-run assumption. `STATE_DE_T6_A4A_P1_S4A-103`'s real
heading ("Payment order — Definitions.") is a genuine 5-term Definitions
section (standard UCC "Topic — Definitions." convention, Title 6 Articles
2/2A/3/4/4A/8/9) that is silently NOT recognized. Verified not a one-off: of
973 real DE headings containing the word "Definition(s)", 152 (15.6%) are
under-matched by this exact failure mode. Proven by
`test_is_definitions_heading_undermatches_a_real_multiterm_definitions_section`
(same file). Expected: `is_definitions_heading` must both (a) terminate in
bounded time on any input, including long non-matching non-letter runs, and
(b) recognize "Topic — Definitions."-shaped real headings, not only
"Definitions."-first headings — likely needs a different anchoring strategy
than a nested-quantifier regex (e.g. a bounded/possessive skip of the leading
noise, or splitting on a fixed noise-prefix pattern instead of `[^A-Za-z]+`
repeated inside a `*` group), plus a check against "Topic — Definitions"
without reopening the P3 false-positive (`"Application of Definitions to
Prior Acts"` must still not match).]

### Item 5 — US dataset ingester [G6], real-data row loss (ruling R7(b))
[QA-FAIL (Q2): the wave-3 idempotency fix SKIPS any row with a missing/empty
`chapter`, even when `citation` — the dataset's actual canonical unique
identifier, non-empty in 0% of real rows — is present and unique. On the REAL
`us_de_statutes.parquet` (21,649 rows), 647 rows (3.0%) have an empty
`chapter` and are silently dropped this way — real law lost, one state alone,
with the full 109-file corpus this scales to the same ~3% cut across the
board. QA independently reproduced this percentage against the live
HuggingFace file during investigation (not part of the committed test, per
ruling R6). Proven by
`test_ingest_us_statute_rows_drops_a_real_row_with_empty_chapter_but_unique_citation`
(backend/tests/integration/test_qa_regression_us_state_law_FAIL.py), using a
REAL row (`STATE_DE_T5_C7_SVIII_S796`, citation `5 Del. C. § 796`) with only
`chapter` blanked to the real-world empty-string shape. Expected: a row with
an empty `chapter` but a valid, unique `citation` must be ingested (e.g. by
falling back to `citation` as the disambiguating key when `chapter` is
absent), not unconditionally skipped — `citation` is empty in 0% of real
rows and is the dataset's own canonical unique identifier.]

## Dev Complete

_None — items 3 and 5 processed this QA cycle (both bounced again above, for
NEW defects distinct from cycle 1's, which are confirmed fixed)._

## Completed

- **Item 1 — Jurisdiction controlled vocabulary [G5].** Commit `be609a5`.
  QA: PASS — P5: 54-code vocabulary byte-identical across backend/frontend/live
  endpoint; regression `test_frontend_jurisdiction_list_source_matches_backend_source_exactly`.
- **Item 2 — Jurisdiction-profile seam, Hebrew ported [G1].** Commit `7daf286`.
  QA cycle 2: PASS, upgraded from cycle 1's narrow claim — dispatch is now
  wired into the live pipeline and Hebrew is confirmed UNCHANGED end-to-end
  (18/18 Hebrew pipeline integration tests green; `HebrewProfile.find_citations`
  confirmed to have zero call sites anywhere in `app/`, including `pipeline.py`
  — dead code, but not a live risk for either jurisdiction family).
- **Item 4 — Jurisdiction stamping [G5].** Commit `9662def`.
  QA: PASS — P1: null-jurisdiction miss proven unreachable via either production
  ingester; regression `test_document_jurisdiction_is_never_null_after_either_production_ingester_runs`.
- **Item 6 — UI jurisdiction pass [G7].** Commit `70db22e`.
  QA: PASS — frontend 165/165 green, typecheck clean; vocabulary drift-guard
  (Item 1) covers this item's picker source too.

**Manager-measured state entering cycle 2:** backend **629 passed / 0 failed**;
frontend **165 passed**; typecheck clean; all 3 cycle-1 bounce-proofs green.

**QA cycle 2 independent re-run:** backend **629 passed / 0 failed** (unchanged
— QA's own cycle-1 bounce-proofs were folded into
`test_qa_regression_us_state_law.py` in place of 3 that used to be RED, net
test count unchanged), **+ 3 intentional NEW RED tests** in
`test_qa_regression_us_state_law_FAIL.py` proving cycle 2's fresh findings
(Q2, Q3a, Q3b); frontend **165 passed / 0 failed**; typecheck clean.

## Evaluation Notes

_None yet._

## QA Notes

- **Q1 — cycle-1 fixes genuinely verified, not merely test-satisfied.** All 3
  cycle-1 bounce-proofs re-run green. Independently reproduced the live path
  from scratch (own script, not the committed test): real DE rows through
  the real `ingest_us_statute_rows` → `run_definition_linking` produced
  exactly 3 definitions (Affiliate, Branch office, Insured depository
  institution) + 2 DERIVES_FROM_LAW assertions incl. `12 U.S.C. § 1813(c)`,
  all stamped `US-DE` — matches the manager's R7(a) probe exactly. Folded
  into `test_qa_regression_us_state_law.py`.
- **Q2 — CONFIRMED, item 5 bounced (ruling R7(b)).** Reproduced the
  manager's 647/21,649 (3.0%) empty-`chapter` figure independently against
  the live `us_de_statutes.parquet` (citation empty in 0%, confirmed).
  Committed RED test uses a real row with only `chapter` blanked. See
  `## Next Steps`.
- **Q3 — NEW, severe: item 3's wave-3 heading fix broken two ways, bounced.**
  (a) ReDoS: `_DEFINITIONS_HEADING_RE` catastrophically backtracks; a real
  DE heading (43-char non-letter prefix, dataset-wide max) doesn't return
  within 8s — on `pipeline.py` Stage 2's live path, hangs the G6 bulk run.
  (b) Under-match: real section numbers with an embedded letter (`4A-103`)
  break the "Definitions first word" assumption — 152/973 (15.6%) of real
  DE headings silently missed. Full detail + real fixture: sprint log
  §"QA cycle 2".
- **Q4 — Hebrew fidelity PASS.** All 18 Hebrew pipeline integration tests
  green with dispatch now live; `HebrewProfile.find_citations` confirmed
  unreachable from any production call site (grep: only test files call
  `.find_citations`).
- **Q5 — bulk-run readiness: NOT ready, blocked by Q3a.** The Q3a ReDoS
  alone would hang the definition-linking pass on the real corpus. 4 more
  lower-severity concerns (N+1 queries, session memory growth across a
  file, mid-file-corruption reporting, no filename→jurisdiction mapping)
  logged in full in the sprint log, same section as Q3.

## Context Dump

Planner pass complete 2026-08-02: true baseline established (all-green,
see above), 6 items defined, RED tests authored + confirmed for all 6
(23 backend RED signals, 14 frontend RED tests across 5 files — full
per-file breakdown in the sprint log). Real DE fixture rows committed at
`backend/tests/fixtures/us_statutes/`. Zero implementation written.
Next: manager reviews item/track split, rules on parallelization, spawns
Developer(s) starting with Item 1 (no dependencies) and Item 2 (blocks
Items 3/4). Full rationale for every design call: sprint log.
