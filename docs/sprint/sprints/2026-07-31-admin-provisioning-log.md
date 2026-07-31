# Sprint log — 2026-07-31-admin-provisioning (append-only; not auto-loaded)

## Agent roster
- Planner: aafd3e0e02be87fe9 (spawned after pointer commit)

## Planner pass (2026-07-31)

Read `app/seed_demo.py` (the `--db`/`LEXGRAPH_DATABASE_URL` + `Base.metadata.create_all`
convention B1 must follow), `app/routers/workspace.py` (the local-deps,
bare-array-response router convention B2 must follow — `list_members`
already shows the "bare JSON array" precedent), `tests/conftest.py` +
`tests/integration/test_workspace.py` (fixture/seed-helper and
self-mock-ban conventions for the RED tests), `frontend/src/pages/AdminPage.tsx`
+ its test file (existing tab/mock structure for UI1), `frontend/src/pages/SignInPage.tsx`
+ its test file (the `DEMO_ACCOUNTS` chips UI2 removes), and
`frontend/src/api/client.ts` (confirmed no `listUsers`/`createUser` yet —
left untouched per the brief).

Five items defined (B1, B2, UI1, UI2, D1) with acceptance criteria and
RED tests, ≤10 lines each, in the contract's Next Steps.

Design decisions worth recording (Developer should treat these as the
contract, not just as Planner's test opinions):
- B2's access gate is "admin on ANY matter" (R2), a global check — NOT
  the current-matter-only gate `workspace.py`'s `_require_admin` uses.
  RED tests seed an admin role via a throwaway matter (from
  `matter_with_users`) and assert the caller can list/create regardless
  of which matter that role is on.
- B2 response shape is a bare array on GET (matching `list_members`'s
  existing convention) and a bare `{id, email, display_name}` object on
  POST 201 — no `{"items": [...]}` or `{"user": {...}}` envelope anywhere.
- 409 is reserved for duplicate EMAIL (R4); duplicate caller-chosen ID is
  422 (grouped with the other input-validation failures per the brief's
  explicit "422 invalid email/empty display_name/duplicate id" list).
- UI1's "wiring" requirement (create-account flow feeds the existing
  add-member flow) was under-specified in the brief beyond "one wiring
  assertion is enough" — Planner's concrete design: after a successful
  `api.createUser`, the returned account's email pre-fills the "Add
  member" email input on the Members & roles tab. Chose pre-fill over
  auto-submit because the brief says the existing add-member flow
  "already works" and shouldn't be re-driven with a different call
  signature under test; a pre-filled input is the minimal glue that
  proves the two features are connected without duplicating
  `test_workspace.py`-equivalent coverage.
- UI1's `api.listUsers`/`api.createUser` mocks reference methods not yet
  on `client.ts`'s declared `Api` type. Verified empirically that
  `vi.mock`'s factory isn't type-checked against the real module (so the
  mock object literal is fine), but the imported `api`/`vi.mocked(api)`
  bindings elsewhere in the test file ARE typed from the real module —
  so a narrow `as unknown as {...}` cast (`mockedUsersApi`) isolates just
  the two new symbols. Ran `npm run typecheck` after adding the tests to
  confirm zero errors (this matters because typecheck is part of this
  sprint's evaluator command).

## RED confirmation

- `backend/.venv/bin/pytest backend/tests/integration/test_bootstrap_cli.py backend/tests/integration/test_users_api.py -v`
  → 16 failed (4 bootstrap CLI, 12 users API), all on `ModuleNotFoundError`
  (subprocess) or `404` (route not registered) — right reason, no
  import/collection errors. Full suite: 485 passed (baseline, untouched)
  + 16 new RED = 501 total, 16 failed.
- `npm --prefix frontend run test -- --run` → 147 passed, 4 failed
  (3 new AdminPage "User accounts" tests + 1 re-pointed SignInPage test),
  all on `TestingLibraryElementError`/`toBeInTheDocument` — right reason.
  A 4th new AdminPage test ("does not render the tab ... for non-admin
  roles") passes today — vacuously true since the tab doesn't exist for
  anyone yet; kept as a regression guard, not a defect in the RED pass.
- `npm --prefix frontend run typecheck` → clean, 0 errors.

## Stale-pin sweep

See the contract's `## Stale-pin sweep` section — one file touched
(`SignInPage.test.tsx`), two stale-existence tests replaced by one
absence test, in the same commit as the UI2 RED test.
- Developer B1+B2 (backend): ab4ae45e4ff4cae99 (spawned at c9233a3)
- Developer UI1+UI2+D1 (frontend+docs): a39ae1152f592476e (spawned at 86ae9de)
- Manager: full diff read of 008cfc3 (auth-adjacent users router) — approved; no privilege escalation (account creation grants no roles), gate order 401→403→422/409 as pinned.
