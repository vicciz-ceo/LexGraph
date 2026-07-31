---
id: "2026-07-31-admin-provisioning"
status: planned
current_role: developer
branch: claude/stitch-consensus-platform-b5fa87
locked_by: "claude-code:planner"
locked_at: "2026-07-31T11:50:25Z"
last_agent: "claude-code:planner"
last_updated: "2026-07-31T11:59:00Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 5
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

### B1 — Bootstrap CLI

`python -m app.bootstrap` (new `backend/app/bootstrap.py`). On an EMPTY
database (no `users` rows): creates one organization + repository +
matter + the first user, with an `admin` `matter_roles` row on that
matter; prints the sign-in user id clearly to stdout (R3 — the id IS the
credential). Flags: `--db <path>` (sets `LEXGRAPH_DATABASE_URL`, mirrors
`app/seed_demo.py`) or read `LEXGRAPH_DATABASE_URL` directly when `--db`
is omitted; `--org-name`, `--matter-name`, `--user-name`, `--user-email`
(sane defaults acceptable). Creates tables via `Base.metadata.create_all`
like `seed_demo.py`. On a NON-empty database (any `users` row exists):
refuses, non-zero exit, prints a message, mutates nothing.
Files: `backend/app/bootstrap.py` (new).
RED tests: `backend/tests/integration/test_bootstrap_cli.py` — run with
`backend/.venv/bin/pytest backend/tests/integration/test_bootstrap_cli.py -v`.

### B2 — Users API

`GET /api/v1/users` → bare JSON array `[{id, email, display_name}, ...]`.
`POST /api/v1/users` → body `{email, display_name, id?}`, 201 with
`{id, email, display_name}` (id prominent in the response, R3). Gate
(R2): caller holds `admin` role on ≥1 matter — NOT scoped to the current
matter. 401 unknown/missing token; 403 non-admins (incl. reviewers); 409
duplicate email (R4, API-layer check, no DB unique constraint); 422
invalid email / empty display_name / duplicate caller-chosen id.
Files: new router (workspace.py conventions — local `get_session`/
`get_current_user_id`, `APIRouter(prefix="/api/v1")`) + one registration
line in `app/main.py`'s append-only zone (that file's own R6 ruling from
an earlier sprint, not this sprint's R6).
RED tests: `backend/tests/integration/test_users_api.py` — run with
`backend/.venv/bin/pytest backend/tests/integration/test_users_api.py -v`.

### UI1 — Admin console "User accounts"

New "User accounts" tab on `AdminPage.tsx` (admin-only — same gate as the
existing mutating members controls, `session.role === "admin"`): lists
accounts via `api.listUsers()`; create-account form (email, display name)
via `api.createUser(email, displayName)`; renders the returned id on
success so the admin can copy it. Wiring: after a successful create, the
new account's email pre-fills the existing "Add member" email field on
the Members & roles tab (one assertion — that flow is already tested,
not re-tested deeply). The tab must not render, and accounts must not be
fetched, for non-admin roles.
Files (Developer): `frontend/src/pages/AdminPage.tsx`,
`frontend/src/api/client.ts` (adds `listUsers`/`createUser`, matching the
B2 response shapes exactly).
RED tests: `frontend/src/pages/__tests__/AdminPage.test.tsx` (api module
mocked per existing convention) — run with
`npm --prefix frontend run test -- --run AdminPage`.

### UI2 — Sign-in de-mocking (G3)

`SignInPage.tsx` no longer renders the hardcoded demo-account chips
section (`DEMO_ACCOUNTS`, the admin/reviewer/contributor/viewer
quick-fill buttons) — accounts are now provisioned by an admin, not
baked into the sign-in page. The User ID field and submit button are
unaffected and must still render.
Files (Developer): `frontend/src/pages/SignInPage.tsx`.
RED tests + stale-pin re-point (same commit — see sweep below):
`frontend/src/pages/__tests__/SignInPage.test.tsx` — run with
`npm --prefix frontend run test -- --run SignInPage`.

### D1 — Docs (doc-only, no RED test)

README + RUNBOOK document bootstrap → sign in → create users → grant
access as THE provisioning path (replacing the "run the seed, sign in as
`admin`" framing as the primary flow). `app/seed_demo.py` and
`scripts/demo.sh` are repositioned as an optional local-testing mockup,
clearly labeled as such, not "the" path. Must preserve every marker
`backend/tests/unit/test_local_first_runbook_docs.py` checks for in
`docs/RUNBOOK.md` (case-insensitive substrings: "migration", "backfill",
"backend", "grading", "mcp") — that test is untouched by this sprint and
must keep passing.
Files (Developer): `README.md`, `docs/RUNBOOK.md`.
Acceptance: reads correctly end-to-end from a fresh clone; no RED test —
verified by review, not pytest/vitest.

## Dev Complete

## Completed

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

## Context Dump

New sprint, planning phase. Prior sprint (Consensus UI) closed done; its
demo stack may still be running locally (uvicorn :8000 + vite :5173).
Everything about the app's architecture is in
docs/design/consensus-ui-review.md and the prior sprint contract.
