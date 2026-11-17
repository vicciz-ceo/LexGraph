---
id: "2026-07-31-consensus-ui"
status: done
current_role: planner
branch: claude/stitch-consensus-platform-b5fa87
locked_by: null
locked_at: null
last_agent: "claude-code:qa"
last_updated: "2026-07-31T11:50:25Z"
lint: "PASS 132 2026-11-16T08:56:54Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 11
completed_items: 11
dev_complete_items: 0
qa_cycles: 1
previous_sprint: "2026-07-30-ratings-grade"
prd_sections: []
design_sections: ["docs/design/consensus-ui-review.md", "docs/design/consensus-ui/DESIGN.md"]
---

# Sprint: Consensus UI — implement the Stitch design as the LexGraph web app

## Mandate (director, 2026-07-31)

Director supplied a Stitch design zip ("Consensus — knowledge verification
platform", 10 screens) with: "review it, fix what doesn't work and implement
it in the repo, so everyone that forks it can use it like this." Mid-sprint
the director invoked the sprint harness and ruled: adopt all pre-harness and
in-flight work as the sprint baseline; all four acceptance gates below
confirmed.

## Harness-compliance disclosure

Work up to the baseline commit predates harness governance: the manager
personally wrote the frontend foundation, the backend workspace router (+ its
tests), and the demo seed; the nine in-flight screen agents author both their
page code AND their page tests (no independent Planner-owned RED set).
Director accepted this with the condition that independent QA scrutinizes the
pre-harness code and agent-authored tests extra hard. From the baseline
commit onward, standard role separation applies.

## Acceptance gates (manager-defined, director-confirmed)

- **G1 — Live browser walkthrough:** every screen exercised in a real
  browser against the seeded backend, per role — reviewer accepts/rejects,
  contributor suggests + rates, viewer sees no privileged actions, admin
  manages roles. (Manager-run live smoke verification.)
- **G2 — All suites green:** backend pytest (479+), frontend typecheck +
  full Vitest including new page tests — one authoritative run, results
  quoted.
- **G3 — Fork quickstart works:** a clean environment runs
  `./scripts/demo.sh` (or the documented manual steps) to a working,
  signed-in UI — verified by execution, not by reading the script.
- **G4 — Docs match reality:** README, RUNBOOK, and
  docs/design/consensus-ui-review.md describe what actually shipped.

## Manager rulings

- R1: Sprint branch is `claude/stitch-consensus-platform-b5fa87` (the
  session worktree branch), not `sprint/{id}` — the branch pre-existed the
  harness with in-flight agent work targeting it; renaming mid-flight risks
  orphaning that work. Deviation recorded.
- R2: Domain-truth rules bind all UI work: strength ratings (1–5/revision),
  model confidence (0–1), and review status are three separate concepts,
  never merged; ratings never change status; review actions are
  reviewer/admin-gated. No vote/quorum language anywhere.
- R3: No CDN/runtime remote dependencies in the frontend (Tailwind CDN,
  Google Fonts, Material Symbols, remote images all banned); tokens are CSS
  custom properties, Inter is bundled, icons are inline SVG.
- R4: The design's fictions (SSO, passwords, departments, headshots, model
  version strings, vote tallies) are removed or replaced with real data, per
  docs/design/consensus-ui-review.md.
- R5: Screen agents own only their page file, page CSS, and page test file;
  shared foundation files are read-only to them.

## Next Steps

## Dev Complete

## Completed

- **F1 — Frontend foundation** (pre-harness, manager-authored). Full entry:
  `-log.md` § "Archived from contract (2026-11-16)".
- **W1 — Backend workspace surface + demo seed** (pre-harness,
  manager-authored). Full entry: `-log.md` § "Archived from contract
  (2026-11-16)".
- **D1+D2 — members-shape fix** and **D3 — awaiting-evidence justification
  gating** (walkthrough defects). Full entry: `-log.md` § "Archived from
  contract (2026-11-16)".

- **UI1–UI9 — nine screens** (workflow wf_dfea95a4-a7c, commit d11ff9e). Full
  entry: `-log.md` § "Archived from contract (2026-11-16)".

## Stale-pin sweep

Not run as a distinct pass (pre-harness deviation): no renames of existing
symbols were in scope — all sprint work is additive (new files) except
main.py's append-only router registration, tsconfig types, vite proxy, and
package.json deps. The 69 pre-existing frontend tests and 461 pre-existing
backend tests ran green post-change, which is the empirical equivalent for
the touched surfaces.

## Evaluation Notes

- Baseline: backend 479 passed (10.6s); frontend 69 passed + tsc clean +
  vite build clean, before screen agents' output landed.

## QA Notes

2026-07-31 — Independent QA (V1), all gates PASS. Evaluator (own run):
backend 479/479, frontend 148/148 (20 files), typecheck 0 errors — matches
baseline. All items F1/W1/D1-D3/UI1-9 verified against acceptance criteria;
commits d11ff9e/9b99ce4/6c155f6 confirmed in history. Live-path confirmed
(real create_app() via TestClient; real page components via RTL). Bug-fix
pins verified by diff reading. Extra-scrutiny sweep added 6 backend
regression tests for untested error paths (test_workspace.py, 24/24 green,
485/485 total). G3 fork quickstart: PASS, all steps executed in a scratch
clone + scratch venv. G4 docs: no false claims found; one stale label
("grading app" in RUNBOOK.md, pre-dates Consensus UI branding, harmless)
and one comment-accuracy nit on D3 flagged above — neither blocks. Full
detail: 2026-07-31-consensus-ui-log.md.

## Context Dump

Sprint complete: status review, all 11 items Completed, all four gates
passed (QA Notes above). Nothing in flight. Successor work would start a
NEW sprint — candidates recorded in the log: span-text resolution for
evidence lists, detail-page name resolution, backend rating-summary
embedding in list responses, real IdP story. Demo stack recipe: seed
backend/dev.db via `python -m app.seed_demo`, uvicorn :8000, vite :5173,
sign-in ids admin/reviewer/contributor/viewer.
