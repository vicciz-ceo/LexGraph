---
id: "2026-08-02-us-state-law"
status: dev-complete
current_role: qa
branch: claude/us-state-law-compat-6d3ae8
locked_by: "claude-code:planner"
locked_at: "2026-08-02T10:00:34Z"
last_agent: "claude-code:manager"
last_updated: "2026-08-02T10:28:30Z"
lint: "PASS 267 2026-08-02T10:28:55Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 6
completed_items: 0
dev_complete_items: 6
qa_cycles: 0
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

_All items moved to Dev Complete._

## Dev Complete

### Item 1 — Jurisdiction controlled vocabulary [G5]
Files: `app/services/jurisdiction.py` (new), `app/routers/assertions.py`,
`app/main.py`, `app/seed_demo.py`, `frontend/src/constants/jurisdictions.ts` (new).
Branch `claude/us-state-law-vocabulary` @ `be609a5`, merged to sprint branch.
Result: 54-code vocabulary enforced on POST/PATCH/revisions + list filter (422 on
invalid, null still allowed); `GET /api/v1/jurisdictions` serves the canonical list;
seed_demo's invalid `"EU"` fixed. 70 backend + 4 frontend target tests green.
Manager verification: diff read, zero test files touched; `main.py` 3-line addition
is inside the documented append-only registration zone — accepted.

### Item 2 — Jurisdiction-profile seam, Hebrew ported [G1]
Files: `app/definition_links/profiles.py` (new), `.../ingest.py`, `.../matcher.py`,
`app/models/document.py`.
Branch `claude/us-state-law-seam` @ `7daf286`, merged to sprint branch.
Result: `get_profile(code)` registry + `HebrewProfile` pass-through; additive only —
existing bare functions untouched; `profile=None` and `jurisdiction="IL"` defaults
keep every Hebrew call site working. 16 target tests green, all 504 pre-existing
tests still green (G1 satisfied).
Manager verification: full diff read (persistence surface). `server_default="IL"`
deviation accepted — `conftest.py` seeds documents via raw SQL that bypasses the
ORM default, and that fixture is Planner-owned, so a DB-level default was the
correct fix rather than editing the test.

### Item 3 — US jurisdiction profile [G2, G3, G4]
Files: `app/definition_links/us_profile.py` (new), `.../profiles.py`.
Branch `claude/us-state-law-us-profile` @ `b7d2678`, merged.
Result: `USProfile` registered for all 53 non-IL codes; English Definitions
headings (substring-based, tolerant of real DE scrape-noise), curly-quote-aware
numbered-entry term extraction, `\b` word-boundary matching, citation grammar
(`Section N`/`§ N`/`N U.S.C. § N`) with most-specific-first overlap claiming and
same-chapter exclusion. 19 target tests green.
Manager verification: diff read. Design decision (one US-family profile, not
per-state) is documented with evidence and is additively splittable later.

### Item 4 — Jurisdiction stamping [G5]
Files: `app/definition_links/pipeline.py`.
Branch `claude/us-state-law-stamping` @ `9662def`, merged.
Result: per-document jurisdiction map replaces hardcoded `jurisdiction=None` at
both creation sites (Stage 3 USES_DEFINITION, Stage 4 DERIVES_FROM_LAW). 2 target
tests green; mixed-jurisdiction matter case covered.
Manager verification: full diff read (persistence). **QA FOCUS:**
`document_jurisdictions.get(...)` returns `None` on a miss — a silent null
jurisdiction would violate G5. Probe this.

### Item 5 — US dataset ingester [G6 — code only]
Files: `app/definition_links/ingest_us_statutes.py` (new), `..._cli.py` (new),
`backend/pyproject.toml` (+pyarrow>=17.0), `docs/RUNBOOK.md`.
Branch `claude/us-state-law-ingester` @ `6a8d737`, merged.
Result: one Document per file / one Article+SourceSpan per row; jurisdiction
validated; text-less rows skipped with reasons; empty batch rejected; idempotent
re-ingest; CLI streams via `iter_batches` (bounded memory), non-zero exit on
missing input. 10 target tests green.
Manager verification: diff read. **G6 IS NOT YET PROVEN** — the measured 109-file
run has not been executed. Code-complete only.

### Item 6 — UI jurisdiction pass [G7]
Files: `AssertionSuggestionForm.tsx`, `KnowledgeBasePage.tsx`,
`ReviewQueuePage.tsx`, `ProfilePage.tsx`.
Branch `claude/us-state-law-ui` @ `70db22e`, merged.
Result: free-text jurisdiction input → `<select>`; jurisdiction filter on KB and
Review Queue; default-jurisdiction preference on Profile persisted to
localStorage. 10 target tests green, full frontend suite 165 green, typecheck clean.
Manager verification: containment checked (frontend-only, no test files).

**Merged-tree evaluator (manager-run, 2026-08-02, all 6 items):**
backend **621 passed / 0 failed / 0 errors**; frontend **165 passed / 0 failed**;
typecheck clean. Zero regressions against the 504/151 baseline.

## Completed

_None yet._

## Evaluation Notes

_None yet._

## QA Notes

_None yet._

## Context Dump

Planner pass complete 2026-08-02: true baseline established (all-green,
see above), 6 items defined, RED tests authored + confirmed for all 6
(23 backend RED signals, 14 frontend RED tests across 5 files — full
per-file breakdown in the sprint log). Real DE fixture rows committed at
`backend/tests/fixtures/us_statutes/`. Zero implementation written.
Next: manager reviews item/track split, rules on parallelization, spawns
Developer(s) starting with Item 1 (no dependencies) and Item 2 (blocks
Items 3/4). Full rationale for every design call: sprint log.
