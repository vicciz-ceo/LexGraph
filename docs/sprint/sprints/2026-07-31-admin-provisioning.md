---
id: "2026-07-31-admin-provisioning"
status: planning
current_role: planner
branch: claude/stitch-consensus-platform-b5fa87
locked_by: "claude-code:planner"
locked_at: "2026-07-31T11:50:25Z"
last_agent: "claude-code:manager"
last_updated: "2026-07-31T11:50:25Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-07-31-consensus-ui"
prd_sections: []
design_sections: ["docs/design/consensus-ui-review.md"]
---

# Sprint: Admin provisioning — real access management, no seed dependence

## Mandate (director, 2026-07-31)

"Make sure the implementer can obtain admin access, then manage users and
grant them access within the organisation. No need for mockup data in the
app unless it is a local mockup you use for testing." Director rulings via
batched gate questions: work lands on the SAME branch/PR (#17, prior sprint
closed done); access model is per-matter admins (no org-admin schema
change); all four gates below confirmed.

## Acceptance gates (manager-defined, director-confirmed)

- **G1 — Fresh-instance bootstrap:** on an EMPTY database (no demo seed),
  one documented command creates the workspace and the first admin, who can
  then sign in. Verified by execution.
- **G2 — In-app user management:** as admin: create a user account in the
  app, grant it a role on a matter; the new user signs in and sees
  role-appropriate UI. Verified live in the browser.
- **G3 — No mockup data in the app:** the sign-in page stops hardcoding
  demo accounts; the seed becomes an optional local-testing tool, clearly
  framed that way in docs. The seed itself still works.
- **G4 — Suites green + docs:** full backend/frontend suites pass including
  new tests; README/RUNBOOK document the real provisioning path
  (bootstrap → sign in → create users → grant access).

## Manager rulings

- R1: Same branch (`claude/stitch-consensus-platform-b5fa87`); the work
  extends PR #17.
- R2: Access model — any holder of the admin role on ≥1 matter may create
  user accounts and list users; role grants stay per-matter via the
  existing members endpoints, admin-of-that-matter gated. NO changes under
  `backend/app/models/**` (users/matters/roles tables suffice).
- R3: The user id IS the sign-in credential (test-token seam,
  backend/app/auth.py). Creating an account mints the id; the API/UI must
  surface it clearly so the admin can hand it to the person. No passwords.
- R4: Email uniqueness is enforced at the API layer (schema has no unique
  constraint; adding one is a migration, out of scope — Planner pins the
  409 behavior).
- R5: Product code carries no demo/mockup fixtures. `app/seed_demo.py` and
  `scripts/demo.sh` remain as local-testing tools, repositioned in docs.
- R6: Roles stay viewer/contributor/reviewer/admin per
  services/permissions.py — no new permission names.

## Next Steps

(Planner defines items B1 bootstrap CLI, B2 users API, UI1 admin-console
user accounts, UI2 sign-in de-mocking, D1 docs — with acceptance criteria
and RED tests per item.)

## Dev Complete

## Completed

## Stale-pin sweep

(pending Planner — NOTE: removing the sign-in demo chips WILL break
existing SignInPage tests that assert them; the sweep must re-point those
pins in the same commit.)

## Evaluation Notes

- Baseline at sprint start: backend 485/485, frontend 148/148, typecheck
  clean (sprint 2026-07-31-consensus-ui closing numbers).

## QA Notes

## Context Dump

New sprint, planning phase. Prior sprint (Consensus UI) closed done; its
demo stack may still be running locally (uvicorn :8000 + vite :5173).
Everything about the app's architecture is in
docs/design/consensus-ui-review.md and the prior sprint contract.
