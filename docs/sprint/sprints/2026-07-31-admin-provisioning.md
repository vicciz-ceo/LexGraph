---
id: "2026-07-31-admin-provisioning"
status: done
current_role: planner
branch: claude/stitch-consensus-platform-b5fa87
locked_by: null
locked_at: null
last_agent: "claude-code:qa"
last_updated: "2026-07-31T12:59:20Z"
lint: "PASS 137 2026-11-16T08:56:54Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 5
completed_items: 5
dev_complete_items: 0
qa_cycles: 1
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

## Dev Complete

## Completed

- **B1 — Bootstrap CLI.** `python -m app.bootstrap`: empty-DB guard, creates
  org+repo+matter+admin user, prints user id. Full entry: `-log.md` §
  "Archived from contract (2026-11-16)".
- **B2 — Users API.** `GET`/`POST /api/v1/users`, global admin-on-any-matter
  gate (R2), 401/403/409/422 pinned. Full entry: `-log.md` § "Archived from
  contract (2026-11-16)".
- **UI1 — Admin console "User accounts".** Full entry: `-log.md` § "Archived
  from contract (2026-11-16)".
- **UI2 — Sign-in de-mocking (G3).** Removed the hardcoded `DEMO_ACCOUNTS`
  quick-fill chips section; User ID field/submit unaffected. Full entry:
  `-log.md` § "Archived from contract (2026-11-16)".
- **D1 — Docs.** Full entry: `-log.md` § "Archived from contract
  (2026-11-16)".

## Stale-pin sweep

Command: `grep -riE "demo workspace|DEMO_ACCOUNTS|admin.*reviewer.*contributor.*viewer" frontend/src/pages/__tests__ backend/tests`,
plus a full pass over every test root: `backend/tests/{unit,integration,e2e}`,
`frontend/src/components/__tests__`, `frontend/src/pages/__tests__`.

- Only hit: `frontend/src/pages/__tests__/SignInPage.test.tsx` — two tests
  ("fills the input from a demo-account chip and clears any prior error",
  "offers one chip per demo role") asserted the demo chips EXIST.
  Re-pointed in the same commit as the UI2 RED test: both removed and
  replaced with one new test, "does not render the hardcoded demo-account
  quick-fill chips (G3)", asserting their ABSENCE while still asserting
  the User ID field + submit button render.
- `backend/tests/{unit,integration,e2e}`: no hits.
- `frontend/src/components/__tests__`: no hits.
- `backend/tests` grep for `seed_demo`: no hits — no test imports or
  exercises `app/seed_demo.py` directly, so D1's doc repositioning of the
  seed touches no test file.
- `backend/tests/unit/test_local_first_runbook_docs.py` checked
  separately (not a stale pin — no gate-changing content, just a
  marker-substring check against `docs/RUNBOOK.md`): still passes as long
  as D1's RUNBOOK edits keep the words migration/backfill/backend/
  grading/mcp somewhere in the doc. Left untouched; flagged in D1's
  acceptance criteria above so Developer doesn't drop those sections.

## Evaluation Notes

- Baseline at sprint start: backend 485/485, frontend 148/148, typecheck
  clean (sprint 2026-07-31-consensus-ui closing numbers).

## QA Notes

2026-07-31T12:34:24Z — Evaluator: 504/151/clean (501 baseline + 3 new
regression tests; no flakes). All 5 items PASS, moved to Completed. G1
verified by fresh-clone execution: bootstrap prints admin id, re-run
refuses (exit 1); uvicorn :8200 — `/me` 200 admin, `POST /users` 201,
member grant 201, new user `/me` 200 viewer, `POST /users` as viewer 403;
`npm run build` clean. G3: no product-code `DEMO_ACCOUNTS`/"demo
workspace" hits (test-only); `seed_demo.py` still runs. G4: README/RUNBOOK
match the executed flow. Added 3 regression tests: bootstrap refusal vs.
seed_demo-populated DB; whitespace-padded duplicate-email 409; GET /users
403 for a zero-role account. No implementation bugs found.

## Context Dump

Sprint complete: status review, all 5 items Completed, gates G1-G4 passed
(QA Notes above; live walkthrough notes in the -log.md). Nothing in
flight. Real provisioning path: `python -m app.bootstrap` → sign in with
printed id → Admin → User accounts / Members & roles. Demo seed remains a
local-testing tool only. Successor candidates (log): span-text resolution,
detail-page name resolution, rating-summary embedding, real IdP.
