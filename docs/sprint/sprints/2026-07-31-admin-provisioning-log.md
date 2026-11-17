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
- QA (all gates): a265993b7fa2285f7 (spawned at 3fbf70b)

## Manager live verification (G1/G2/G3) — 2026-07-31
Scratch DB /tmp/lexgraph-g1.db: bootstrap printed credential; re-run refused
exit 1. Browser: signed in as Root Admin → Admin → User accounts → created
"Noa Attorney" (credential banner rendered) → granted reviewer via Members →
/me as Noa shows ('First Matter','reviewer') → signed in as Noa: reviewer
meta, NO Admin nav, queue accessible. Sign-in page: 0 demo chips, helper
copy "accounts are provisioned by your administrator."

## Archived from contract (2026-11-16)

Moved verbatim from the sprint contract (`2026-07-31-admin-provisioning.md`)
by a contract-hygiene pass, under the "move, never delete" rule. The
contract's `lint:` stamp `PASS 159 2026-07-31T12:37:20Z` had not been
earned: `scripts/contract_lint.sh`'s "Completed entry <= 3 lines" check
never ran under gawk, the awk CI uses: `awk -v` rewrote the entry regex's
`\*\*` to `**`, so no `- **A1** ...` bullet counted as an entry. With the
check fixed (LexGraph audit finding ops:0) the entries below exceeded the
3-line cap. Each is the exact prior contract text; nothing was summarized,
reworded or dropped. The contract keeps each entry's opening words,
verbatim, and a pointer to this section, where each entry has its own
subsection. Its `lint:` stamp is now `PASS 137 2026-11-16T08:56:54Z`.

### Completed, B1

- **B1 — Bootstrap CLI.** `python -m app.bootstrap`: empty-DB guard,
  creates org+repo+matter+admin user, prints user id. Files:
  `backend/app/bootstrap.py` (new). Commit `008cfc3`. Result: 4/4 green.
  QA: verified live in a fresh clone (G1) — bootstrap prints the admin id,
  a re-run refuses (exit 1); added a regression pin for refusal against a
  DB seeded by `app/seed_demo.py` (origin-agnostic guard), 5/5 green.

### Completed, B2

- **B2 — Users API.** `GET`/`POST /api/v1/users`, global admin-on-any-matter
  gate (R2), 401/403/409/422 pinned. Files: `backend/app/routers/users.py`
  (new), `backend/app/main.py` (registration). Commit `008cfc3`. Result: 12/12 green.
  QA: verified live via the `client` fixture (real app) and via curl
  against a fresh-clone uvicorn instance — 201 create, 201 member grant,
  200 `/me` with the new viewer role, 403 when that viewer tries to POST
  `/users`. Added 2 regression pins (whitespace-padded duplicate email 409;
  authenticated user with zero matter roles, not just non-admin, gets 403),
  14/14 green.

### Completed, UI1

- **UI1 — Admin console "User accounts".** New admin-only tab: lists
  accounts (`api.listUsers`), creates one (`api.createUser`), surfaces the
  returned sign-in id, pre-fills the Members & roles add-member email.
  Files: `frontend/src/pages/AdminPage.tsx`, `frontend/src/api/client.ts`,
  `frontend/src/styles/pages/admin.css`. Commit `98b1519`. Result: 4/4 new + 10/10 existing green.
  QA: confirmed the test file renders the real `AdminPage` component
  (no self-mock); no changes needed.

### Completed, UI2

- **UI2 — Sign-in de-mocking (G3).** Removed the hardcoded `DEMO_ACCOUNTS`
  quick-fill chips section; User ID field/submit unaffected. Files:
  `frontend/src/pages/SignInPage.tsx`, `frontend/src/styles/pages/sign-in.css`.
  Commit `98b1519`. Result: 8/8 green.
  QA: grepped built product for `DEMO_ACCOUNTS`/"demo workspace" — only
  hit is the test file's absence assertion; no product-code remnants.

### Completed, D1

- **D1 — Docs.** README + RUNBOOK now lead with bootstrap → sign in →
  create users → grant access; `scripts/demo.sh`/`seed_demo.py`
  repositioned as optional local-testing. Files: `README.md`,
  `docs/RUNBOOK.md`. Commit `98b1519`. Result: RUNBOOK marker test (migration/
  backfill/backend/grading/mcp) still passes; reviewed end-to-end.
  QA: README/RUNBOOK commands, flags, ports, and id-is-credential framing
  match the G1 execution exactly; `seed_demo.py` still runs standalone.
