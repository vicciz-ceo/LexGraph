---
id: "2026-07-31-consensus-ui"
status: in-progress
current_role: developer
branch: claude/stitch-consensus-platform-b5fa87
locked_by: "claude-code:developer"
locked_at: "2026-07-31T10:55:00Z"
last_agent: "claude-code:manager"
last_updated: "2026-07-31T10:55:00Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 11
completed_items: 0
dev_complete_items: 2
qa_cycles: 0
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

- **V1 — Independent QA of the full sprint** (blocked until UI1–UI9 land):
  re-run the evaluator, verify each item against its acceptance criteria,
  scrutinize pre-harness code (backend/app/routers/workspace.py,
  backend/app/seed_demo.py, frontend/src/{api,app,styles}) and
  agent-authored page tests for gaps, add regression tests where coverage is
  thin, execute gate G3 (fork quickstart in a scratch clone). QA commits
  touch only test and contract files.

## Dev Complete

- **F1 — Frontend foundation** (pre-harness, manager-authored): app shell,
  hash router, session context, typed API client (field-verified against
  backend serializers), design tokens + shared CSS, inline icons, Inter
  bundling, vite proxy, page stubs. Files: frontend/index.html,
  frontend/src/{main.tsx,App.tsx}, frontend/src/api/*,
  frontend/src/app/*, frontend/src/styles/*. Verified: `tsc --noEmit`
  clean; 69 pre-existing component tests green; production build succeeds.
- **W1 — Backend workspace surface + demo seed** (pre-harness,
  manager-authored): GET /api/v1/me, matter member roster + admin role
  management with last-admin lockout guard; seed script driving the real
  API (15 assertions across all 8 statuses, 2 matters, 4 role-named users);
  scripts/demo.sh. Files: backend/app/routers/workspace.py,
  backend/app/seed_demo.py, backend/tests/integration/test_workspace.py,
  scripts/demo.sh. Verified: 479/479 backend tests pass (18 new); seed
  executed against a scratch DB and API-smoke-checked.

## In Flight (Developer pass — nine parallel screen agents, workflow wf_dfea95a4-a7c)

- **UI1 — SignInPage** · **UI2 — ReviewQueuePage** · **UI3 —
  KnowledgeBasePage** · **UI4 — AssertionDetailPage** · **UI5 —
  SuggestAssertionPage** · **UI6 — ContestedPage** · **UI7 — AdminPage** ·
  **UI8 — ProfilePage** · **UI9 — AnalyticsPage**. Each: implement the
  adapted design (briefs embedded in the workflow script; adaptation
  authority is docs/design/consensus-ui-review.md), own Vitest coverage,
  typecheck + own tests green before handoff. Acceptance criteria per item:
  renders real API data for the current matter; role gating per R2;
  design fidelity per R3/R4; tests cover load, key interactions, role
  gating, empty/error states.

## Completed

(none yet)

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

(pending)

## Context Dump

Sprint adopts a large pre-harness baseline (see Harness-compliance
disclosure). Nine screen agents are mid-flight in workflow wf_dfea95a4-a7c
writing frontend/src/pages/* + styles/pages/* + pages/__tests__/*. When they
land: manager risk-classed diff read → authoritative evaluator run → G1
browser walkthrough (manager) → spawn QA (Sonnet, high) for V1 → gates →
review. Demo stack: seed backend/dev.db via `python -m app.seed_demo`, serve
uvicorn :8000, vite :5173 (proxy configured), sign-in ids
admin/reviewer/contributor/viewer.
