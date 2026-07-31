---
id: "2026-07-31-consensus-ui"
status: done
current_role: planner
branch: claude/stitch-consensus-platform-b5fa87
locked_by: null
locked_at: null
last_agent: "claude-code:qa"
last_updated: "2026-07-31T11:50:25Z"
lint: "PASS 179 2026-07-31T11:08:11Z"
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

- **F1 — Frontend foundation** (pre-harness, manager-authored): app shell,
  hash router, session context, typed API client (field-verified against
  backend serializers), design tokens + shared CSS, inline icons, Inter
  bundling, vite proxy, page stubs. Files: frontend/index.html,
  frontend/src/{main.tsx,App.tsx}, frontend/src/api/*,
  frontend/src/app/*, frontend/src/styles/*. Verified: `tsc --noEmit`
  clean; 69 pre-existing component tests green; production build succeeds.
  QA: confirmed all files present, App.tsx wires every page route, page
  mocks match backend serializer shapes exactly (spot-checked 5 page test
  files against client.ts/types.ts).
- **W1 — Backend workspace surface + demo seed** (pre-harness,
  manager-authored): GET /api/v1/me, matter member roster + admin role
  management with last-admin lockout guard; seed script driving the real
  API (17 assertions across all 8 statuses, 2 matters, 4 role-named users);
  scripts/demo.sh. Files: backend/app/routers/workspace.py,
  backend/app/seed_demo.py, backend/tests/integration/test_workspace.py,
  scripts/demo.sh. Verified: 479/479 backend tests pass (18 new); seed
  executed against a scratch DB and API-smoke-checked.
  QA: extra-scrutiny sweep of workspace.py found 6 untested error paths
  (empty bearer token; unknown-matter ordering ahead of role validation on
  POST members; unknown-matter on PUT/DELETE members; role-change/removal
  of a non-member) — all confirmed correct on read, now pinned with 6 new
  tests in test_workspace.py (24/24 green). Seed re-verified independently:
  actual assertion count is 17 (not 15) across 8 distinct statuses — minor
  stale figure in this bullet's own text, not in any user-facing doc, so
  not a G4 finding; noted for the next edit of this line.
- **D1+D2 — members-shape fix** and **D3 — awaiting-evidence justification
  gating** (walkthrough defects): RED tests committed by Planner (9b99ce4,
  tests-only, 15 RED), fixed by Developer (6c155f6, 6 files, minimal diff,
  manager-read in full). Suite 148/148 + typecheck + backend 479/479
  re-verified by manager independently. Live re-verification: AdminPage
  renders + add-member + last-admin 409 banner; Analytics KPIs
  arithmetically verified against seed+live actions; queue/analytics show
  display names; Accept on awaiting_evidence opens the justification form
  pre-flight. G1 walkthrough COMPLETE across all screens and roles.
  QA: bug-fix pin verified by reading the 9b99ce4→6c155f6 diff pair (no
  fresh worktree/npm-install needed — the RED tests mock the real bare-array
  shape and assert `res.items`-style code throws before the fix, `res`-style
  code passes after; confirmed by inspection, method=diff-reading). One
  finding: the D3 code comments/log describe the backend as requiring
  justification for both "unsupported" and "awaiting_evidence" — empirically
  (live client fixture probe) the backend's `_has_evidence` gate only fires
  on zero evidence rows (true `awaiting_evidence`); an assertion with only
  non-supporting evidence (`evidence_status="unsupported"`) accepts fine
  with no justification. This is pre-existing UI behavior unchanged by
  6c155f6 (harmless over-conservatism, not a regression) — not a QA-FAIL,
  flagged for the director/manager as a comment-accuracy nit.

- **UI1–UI9 — nine screens** (workflow wf_dfea95a4-a7c, commit d11ff9e):
  SignIn, ReviewQueue, KnowledgeBase, AssertionDetail, SuggestAssertion,
  Contested, Admin, Profile, Analytics — each page + namespaced CSS + Vitest
  coverage (75 new tests; suite 144/144, typecheck clean). Manager G1 live
  walkthrough verified sign-in, queue+review actions, detail+rating,
  knowledge search, contested adjudication incl. justification flow, suggest
  submission, profile stats, viewer role gating. See
  2026-07-31-consensus-ui-log.md for the full walkthrough record.
  QA: files/commit verified on disk and in history; App.tsx routes all 9
  pages; page tests render real components via RTL (not stubs).

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
