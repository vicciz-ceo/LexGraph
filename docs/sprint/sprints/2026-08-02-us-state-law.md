---
id: "2026-08-02-us-state-law"
status: qa-fail
current_role: developer
branch: claude/us-state-law-compat-6d3ae8
locked_by: "claude-code:planner"
locked_at: "2026-08-02T10:00:34Z"
last_agent: "claude-code:qa"
last_updated: "2026-08-02T12:45:00Z"
lint: "PASS 348 2026-08-02T12:45:22Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 6
completed_items: 4
dev_complete_items: 0
qa_cycles: 3
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

- **R8 — Wave 4 verified by the manager directly (2026-08-02).** Heading matcher:
  linear time confirmed (0.0009 ms flat; 0.018 ms at 4,000-char noise — was
  15,800 ms at 29 chars). Accuracy on REAL data: **0 missed / 0 false positives**
  across `us_de_statutes` (21,649 headings, 973 candidates) AND `us_ny_statutes`
  (40,102 headings, 1,416 candidates); both over-match cases still rejected.
  Ingester: Developer found a THIRD defect the manager had missed — chapter codes
  collide ACROSS titles (179 collisions merging 293 real sections) — and correctly
  refuted the manager's `citation`-as-key suggestion (1 duplicate pair in 21,649).
  Final key `(section_number, section_title, text)` verified collision-free on all
  21,649 real DE rows; full real-file ingest 21,649 -> 21,649 Articles, 0 skipped,
  idempotent on re-run. Suite: **632 passed / 0 failed**.

- **R9 — Wave 5 heading matcher: manager-verified per-state coverage (2026-08-02).**
  Independently reproduced the Developer's table on 10 real state files. Zero
  false positives in every state; timing 0.002 ms/call (linear held).
  | st | rows | cands | missed | miss% |
  |----|------|-------|--------|-------|
  | tx | 122,535 | 5,033 | 24 | **0.5%** (was 100%) |
  | oh | 33,161 | 970 | 20 | **2.1%** (was 84.1%) |
  | fl | 24,866 | 852 | 47 | **5.5%** (was 27.1%) |
  | de | 21,649 | 1,036 | 16 | 1.5% |
  | ny | 40,102 | 1,547 | 68 | 4.4% |
  | pa | 14,547 | 547 | 4 | 0.7% |
  | wa | 51,498 | 2,007 | 207 | 10.3% |
  | ca / il / ga | 262,039 | **0** | — | structural, see R10 |
  Residual misses are multi-topic headings ("APPLICABILITY OF DEFINITIONS",
  "...; definitions; penalties.") where definitions is not the section's own
  subject — deliberately not chased, to hold false positives at zero.
- **R10 — CA/IL/GA root cause FOUND (Developer escalation, accepted).** Not
  unknowable after all: `section_title` for these states is a bare placeholder
  (`"Section 103-9"`, `"Section 22970.21"`, or a bare citation for GA). The real
  heading text lives inside the `text` body (`"Sec. 15. Definitions. As used in
  this Act..."`), which Stage 2 never receives. No change to `us_profile.py` can
  recover it — the fix is a `pipeline.py` Stage-2 input change. 262,039 rows
  across 3 states affected. Escalated to the director; NOT fixed in wave 5 per
  the director's binding "characterise, do not guess" ruling.
- **R11 — Wave 5 ingester agent did not complete.** It blocked on a background
  notification and pushed nothing; its work is lost. Cause: the manager omitted
  the standing "never block on Monitor" rule from the wave-5 brief preamble.
  Manager fault, not agent fault. Re-spawned fresh in wave 5b.

- **R12 — Director approved wave 6 (CA/IL/GA), and QA's IL unit test is INVALID.**
  Director ruling (AskUserQuestion, 2026-08-03): fix CA/IL/GA rather than defer.
  Manager ruling on the test estate: `test_is_definitions_heading_cannot_recognize_
  a_state_whose_section_title_carries_no_heading_text` asserts
  `is_definitions_heading("Section 15") is True`. That is a planning bug — making
  it pass would return True for ANY `"Section N"` heading, destroying the
  zero-false-positive result of R9 across all 10 states. The Developer's
  escalation was correct. The VALID spec is the sibling live-path test
  `test_real_pipeline_misses_a_real_illinois_definitions_section_end_to_end`.
  Wave 6 splits accordingly: a test-owning agent rewrites the invalid unit test;
  a Developer changes `pipeline.py` Stage 2 to derive the heading from the body
  when `section_title` is a bare placeholder. Developers may not touch tests.

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

_QA cycle 2's bounces for items 3 and 5 (ReDoS on a long non-letter run, the
letter-in-section-number under-match, and the empty-`chapter` row drop) were
fixed by Developers and independently re-verified as genuinely fixed by QA
cycle 3 (see `## QA Notes` — Q1/Q2). Both items bounce again below, for SIX
NEW defects QA cycle 3 found — this time by deliberately testing 6 real
state files NEITHER the Developer NOR QA cycle 2 had ever used (IL, TX, FL,
OH, PA, CA), per the cycle-3 brief's explicit instruction to do so. All 6 are
proven against REAL rows from those 6 files, committed at
`backend/tests/fixtures/us_statutes/qa_cycle3_rows.json` (full derivation in
that directory's README.md), not synthetic constructions._

### Item 3 — US jurisdiction profile [G2], the wave-4 heading fix is still badly broken on real data outside DE/NY

[QA-FAIL (defect 1, structural — no regex fix can address this alone): for
real Illinois rows, `section_title` is ALWAYS a generic `"Section N"`
placeholder — the genuine heading text ("Sec. 15. Definitions.") lives only
in the row's `text` body, which `is_definitions_heading` never sees (it is
only ever called on `Article.heading`, sourced from `section_title` in
`pipeline.py` Stage 2). Verified: **99.6% of all 72,456 real IL rows**, and
separately **100% of all 161,429 real CA rows**, and **100% of all 28,154
real GA rows**, share this exact shape — `section_title` never carries
descriptive heading text for these 3 states at all (~262,000+ real rows,
before counting the rest of the ~2M-row corpus not yet checked). Proven at
both the unit level
(`test_is_definitions_heading_cannot_recognize_a_state_whose_section_title_carries_no_heading_text`)
and the live production-pipeline level
(`test_real_pipeline_misses_a_real_illinois_definitions_section_end_to_end`
— the real `ingest_us_statute_rows` → `run_definition_linking` path creates
ZERO definitions from a real, genuine 5-term Illinois Definitions section),
both in `backend/tests/integration/test_qa_regression_us_state_law_cycle3_FAIL.py`.

ADDITIONALLY [QA-FAIL (defect 2, case-sensitivity — Texas)]:
`is_definitions_heading`'s regexes require exact-case `Definitions?`
(capital D, lowercase rest). Texas's real, standard heading convention is
ALL CAPS (e.g. `"§ 452.351. DEFINITION."`). Verified: **0 of 5,033** real
Texas headings containing the word "definition" match — a complete,
state-wide G2 miss for the entire state. Proven by
`test_is_definitions_heading_misses_all_caps_texas_definitions_headings`.

ADDITIONALLY [QA-FAIL (defect 3, same case-sensitivity bug, different real
shape — Ohio)]: Ohio's real headings routinely end in lowercase
`"...definitions"` in normal sentence case (e.g. `"§ 4513.01. Traffic laws -
equipment - load definitions"`), not the DE/PA capital-D convention the
wave-4 fix was validated against. Verified: **747 of 970 (77%)** of real OH
"definition"-containing headings use this lowercase shape and can never
match. Proven by
`test_is_definitions_heading_misses_lowercase_definitions_in_normal_sentence_case_headings`.

ADDITIONALLY [QA-FAIL (defect 4, number-stripping — Florida/Ohio's dotted
section-number convention)]: `_SECTION_NUMBER_TOKEN_RE` does not consume a
dot-separated section number (`"941.34"`) past the first period, leaving a
numeric fragment (`"34"`) stuck in front of "Definition" and breaking both
the first-word and last-word match rules. Verified: **127 of 748 (17%)** of
real Florida capital-D "Definition(s)" headings are under-matched this exact
way. Proven by
`test_is_definitions_heading_misses_dotted_section_numbers_like_florida_and_ohio`.

Expected: `is_definitions_heading` must (a) be case-insensitive for the
"Definitions" token match itself (both first-word and last-word rules), (b)
fully consume dot-separated section numbers, not just up to the first
period, and (c) the ingester/pipeline needs a documented fallback for states
whose `section_title` carries no descriptive text at all (at minimum IL, CA,
GA) — likely extracting the heading from the leading `"Sec. N. <Heading>."`
clause of `text` itself when `section_title` is a bare `"Section N"`
placeholder, since no per-field fix inside `is_definitions_heading` can see
information that was never passed to it.

### Item 5 — US dataset ingester [G6], the wave-4 idempotency key is not collision-free beyond the one file it was checked against

[QA-FAIL (defect 5): the `(section_number, section_title, text)` key
silently merges two REAL, DIFFERENT Pennsylvania sections (`74 Pa.C.S. § 7`
vs `51 Pa.C.S. § 7`) that happen to share byte-identical cross-title
boilerplate text — directly disproving the wave-4 fix's own docstring claim
that "two distinct real sections essentially never share byte-identical
body text". Verified: **9 collision groups / 11 rows silently merged, out
of only 14,547 real rows**, in `us_pa_statutes.parquet` alone — a file the
Developer never checked. Proven by
`test_ingest_us_statute_rows_silently_merges_two_different_real_pennsylvania_sections`.

ADDITIONALLY [QA-FAIL (defect 6, same key defect, larger + compounded by
defect 1 above)]: California — whose `section_title` is *also* always the
generic `"Section N"` (defect 1) — shows the identical collision shape at
much larger scale: **83 collision groups / 176 rows silently merged, out of
161,429 real rows** (the single largest file in the ~2M-row corpus). This
was found by re-running the bulk-ingest CLI end-to-end on the real,
un-truncated `us_pa_statutes.parquet` file and cross-checking its reported
"rows ingested" summary count (14,547) against the database's actual
`Article` row count afterward (14,536) — the two numbers silently
disagreed by 11, which is what led to finding this collision class; the
same cross-check technique then found CA's much larger instance of it.
Proven by
`test_ingest_us_statute_rows_silently_merges_two_different_real_california_sections`.

Expected: neither `chapter`, `citation` alone, nor `(section_number,
section_title, text)` is a safe sole key on the full real corpus (each has
a real, verified collision or drop somewhere in it) — the bulk-mode CLI's
own "rows ingested" summary number must also be corrected to distinguish
"newly created Article" from "matched an existing Article" (today both are
folded into the same `article_ids` count), since a `.parquet` file's own
internal duplicate-text collisions are otherwise invisible in that summary,
undermining ruling R3's "real measured report" requirement.

## Dev Complete

_None — items 3 and 5 processed this QA cycle (both bounced again above, for
NEW defects distinct from cycle 2's, which are confirmed fixed)._

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

**QA cycle 3 independent re-run:** backend **632 passed / 0 failed** on the
routine suite (cycle 2's 3 RED bounce-proofs re-verified genuinely fixed and
folded into `test_qa_regression_us_state_law.py`; `..._FAIL.py` cycle-2 file
deleted; net test count unchanged) **+ 7 intentional NEW RED tests** in
`test_qa_regression_us_state_law_cycle3_FAIL.py` proving 6 fresh real-data
defects (items 3 and 5, both bounced again — see `## Next Steps`), found by
independently testing 6 real state files (IL, TX, FL, OH, PA, CA) neither
the Developer nor QA cycle 2 had used; frontend **165 passed / 0 failed**;
typecheck clean.

## Evaluation Notes

_None yet._

## QA Notes

- **Q1 (cycle 3) — item 3 bounced again for 4 NEW defects, 6 states never
  tested before (IL/TX/FL/OH/PA/CA).** Cycle-2 fixes hold. NEW: (1)
  `section_title` carries NO heading text for IL/CA/GA (structural, proven
  live-path too). (2) case-sensitive match misses ALL-CAPS Texas (0/5,033).
  (3) misses lowercase Ohio headings (747/970). (4) dotted numbers
  (`941.34`) under-match FL (127/748). Stoplist probe found a real gerund
  gap (`excluding`/`governing`) but 0 real occurrences — reported, not a
  bounce reason. Full breakdown: log §"QA cycle 3".
- **Q2 (cycle 3) — item 5 bounced again: the wave-4 key collides beyond
  DE.** `(section_number, section_title, text)` merges 2 real PA sections
  (11 rows/14,547 lost) and 2 real CA sections (176/161,429 lost) sharing
  boilerplate text — disproves the fix's "essentially never" claim.
  `chapter`/idempotency probes from R7(b) still hold; `section_title`
  never empty in ~550k rows sampled. Full detail: log §"QA cycle 3".
- **Q3 (cycle 3) — bulk mode correct but its OWN summary is provably
  inaccurate; 2M rows feasible but slow.** `--input-dir` correctly
  continues past a bad filename + corrupt file, non-zero exit — but its
  "rows ingested" count hid the Q2 PA collision (14,547 reported vs 14,536
  real DB rows). Timing: real FL file, 24,866 rows = 34.7s (SQLite) →
  ~46min extrapolated for 2M (best case). N+1 SELECT + one session
  spanning the whole run confirmed unaddressed. Log §"QA cycle 3".
- **Q4 — Hebrew fidelity PASS, unchanged.** All Hebrew pipeline tests
  green; `find_citations` still has zero call sites in `pipeline.py`.
- **Q5 — gate sign-off, this cycle only.** G1/G4/G5/G7 PASS. G2/G3 FAIL
  (item 3's defects zero out whole real jurisdictions). G6 CODE-ONLY: bulk
  logic correct, but summary unverified-accurate and item 3/5 defects will
  cause more loss at scale; full 109/105-file run NOT run by QA — manager's
  job post-signoff. Full table: log §"QA cycle 3".

## Context Dump

Planner pass complete 2026-08-02: true baseline established (all-green,
see above), 6 items defined, RED tests authored + confirmed for all 6
(23 backend RED signals, 14 frontend RED tests across 5 files — full
per-file breakdown in the sprint log). Real DE fixture rows committed at
`backend/tests/fixtures/us_statutes/`. Zero implementation written.
Next: manager reviews item/track split, rules on parallelization, spawns
Developer(s) starting with Item 1 (no dependencies) and Item 2 (blocks
Items 3/4). Full rationale for every design call: sprint log.
