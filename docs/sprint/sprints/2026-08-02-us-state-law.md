---
id: "2026-08-02-us-state-law"
status: planning
current_role: planner
branch: claude/us-state-law-compat-6d3ae8
locked_by: "claude-code:planner"
locked_at: "2026-08-02T10:00:34Z"
last_agent: "claude-code:manager"
last_updated: "2026-08-02T10:00:34Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-07-31-admin-provisioning"
prd_sections: []
design_sections:
  - docs/sprint/sprints/2026-08-02-us-state-law-review.md
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

_TBD — Planner records the true pre-sprint pass/fail counts here._

## Stale-pin sweep

_TBD — Planner._

## Next Steps

_TBD — Planner defines items here._

## Dev Complete

_None yet._

## Completed

_None yet._

## Evaluation Notes

_None yet._

## QA Notes

_None yet._

## Context Dump

Sprint opened by the manager 2026-08-02. Recon complete (two rounds; first-round
deterministic + dataset scouts failed and were re-run). Dossier at
`docs/sprint/sprints/2026-08-02-us-state-law-review.md` is the authoritative
findings record — read it, do not re-recon.

Verified by the manager directly: the HF dataset is live, public, non-gated,
CC-BY-4.0, 109 files, per-state parquet naming (`us_tx_statutes.parquet`).

Next: Planner establishes the true test baseline (R4), defines items, authors RED
tests. Nothing is implemented yet.
