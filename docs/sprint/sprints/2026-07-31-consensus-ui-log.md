# Sprint log — 2026-07-31-consensus-ui (append-only; not auto-loaded)

## Agent roster

- Screen-analysis workflow: wf_f461bba1-69a (11 agents, complete)
- Developer pass workflow (UI1–UI9): wf_dfea95a4-a7c (9 agents, complete)
- Planner (qa-fail RED tests, walkthrough defects): ae0bfd6870363ab18

## Manager live walkthrough (G1) — 2026-07-31, seeded dev.db, vite :5173 + uvicorn :8000

Verified working end-to-end against the real backend:
- Sign-in card (bare chrome, demo chips, single User ID field); programmatic
  submit → /me → session. NOTE: the in-app browser pane's synthesized clicks
  did not reach React (pane quirk — form worked via real DOM events and via
  the agent's own live test); not an app defect.
- Reviewer (riva): queue shows 4 proposed w/ origin chips, standing badges
  (weak 1.5/5, strong 4.0/5), separate model-confidence chips; Accept on
  evidenced item → 201, count 4→3, list refreshed; detail page full render
  (proposition, entities, evidence w/ span ids, comments, revision activity,
  team rating distribution + median, own-rating preload); rating update 4→5
  → verified via ratings summary API (avg 4.0, distribution {3:1,5:1}).
- Knowledge Base: 5 accepted (incl. live-accepted item), server-side q=
  "liability" → 1 row, "Results for" banner, ratings/`independent of review
  status` legend, Export CSV present.
- Contested: 2 disputed, rating-strength bars, red Unsupported chip; drawer
  w/ summary tiles + contradicts evidence; Accept on unsupported → guided
  justification textarea (no premature API call) → Confirm accept →
  status=accepted, reviewed_by=reviewer (API-verified).
- Contributor (caleb): Suggest form (real AssertionSuggestionForm) → filled
  subject UUID/standalone/SUPPORTS/proposition → Submit for review →
  created proposed/user_suggested/author=contributor (API-verified),
  navigated to detail. Profile: stats independently recomputed and correct
  (12 authored, 3 accepted, 75% = 3/(3+1), 4 awaiting my rating), tabs +
  matters card + notifications count.
- Viewer (vera): NO Accept/Reject buttons, NO rating radios, NO Admin nav,
  per-card "Reviewer role required to decide." note. Role gating airtight.

Defects found (routed Planner→Developer per harness):
- D1 (high): AdminPage blank crash — client.ts mistypes GET /matters/{id}/members
  as {items:[...]}; backend returns a bare array. res.items → undefined →
  members.length TypeError at render. MANAGER-AUTHORED defect (client.ts is
  baseline code); page agents coded to the type as briefed.
- D2 (medium): same root cause — author display-name resolution dead on
  ReviewQueue/Analytics ("Suggested by admin" instead of "Ada Admin");
  detail page never resolves non-self names (uses session user only).
- D3 (medium): Accept on evidence_status="awaiting_evidence" fires the API
  and surfaces the server 4xx instead of opening the pre-flight justification
  form (AssertionReviewPanel only gates on "unsupported"; backend requires
  justification for BOTH no-evidence states). Error WAS surfaced honestly
  (role=alert with backend detail); data integrity unaffected.

Environment notes: browser-pane screenshots intermittently stale/mis-scaled;
verification cross-checked via DOM reads + direct API probes throughout.
Stale localStorage from the dev-agent's session (old matter id) produced a
one-time 403 banner before storage clear — fresh-boot behavior verified
clean; not reproducible for fork users.

## Roster update
- Developer (D1–D3 fix): a2368941f27a7c9c8 (spawned after Planner RED commit 9b99ce4)
- QA (V1, gates G2-G4): ac07912070ab91187 (spawned at 266ca3c)

## QA (V1) — 2026-07-31, independent verification

HEAD confirmed at 266ca3c before starting; no `git stash` used.

### Evaluator (own run, not reused)
- `backend/.venv/bin/pytest backend/tests -v` → 479 passed, 11 warnings, 19.6s.
- `npm --prefix frontend run test -- --run` → 148 passed (20 files), 6.83s.
- `npm --prefix frontend run typecheck` → clean, no output.
- Matches the sprint's stated baseline exactly. No flakes encountered (no
  re-runs needed).

### Item verification
- Commits `d11ff9e`, `9b99ce4`, `6c155f6` all present in `git log`.
- F1/W1 files all present on disk at the paths named in the contract.
- All 9 UI page/test/css files present; `App.tsx` routes every page
  (SignIn via `session === null`, ReviewQueue at `/` and `/review`,
  KnowledgeBase, SuggestAssertion, Contested, Analytics, Profile,
  Admin role-gated on `session.role === "admin"`, AssertionDetail via
  `/assertions/:id`).
- Live-path: `backend/tests/conftest.py::client` fixture builds
  `TestClient` from the real `app.main.create_app()` — confirmed by
  reading the fixture, not assumed.
- Frontend page tests use Testing Library `render()` against the actual
  page components (`AdminPage`, `ReviewQueuePage`, etc.), not stubs —
  confirmed by reading imports in AdminPage.test.tsx, ReviewQueuePage.test.tsx,
  AnalyticsPage.test.tsx.

### Bug-fix pin check (D1/D2/D3) — method: diff reading (no fresh worktree
build; a clean `9b99ce4` checkout would need its own `npm install` which
the brief allows skipping if diff-reading suffices — it did).
- `git show 9b99ce4 -- frontend/src/pages/__tests__/AdminPage.test.tsx`:
  RED test mocks `listMatterMembers` resolving a bare array (`roster`,
  matching the real backend shape) and asserts the roster renders. Before
  `6c155f6`, `AdminPage.tsx` read `res.items` off that bare array →
  `undefined` → `setMembers(undefined)` → crash reading `.length` (matches
  the RED test's own comment). After `6c155f6`, `client.ts`'s
  `listMatterMembers` return type and `AdminPage.tsx`'s two call sites both
  switched from `res.items` to `res`. Same defect class fixed identically
  in `AnalyticsPage.tsx` (D2, contributor name resolution) and
  `ReviewQueuePage.tsx` (D2, author name resolution).
- D3 (`ReviewQueuePage.test.tsx`): RED test clicks Accept on an
  `evidence_status="awaiting_evidence"` assertion, asserts
  `api.acceptAssertion` is NOT called immediately and a justification
  textarea appears first. Before the fix, `AssertionReviewPanel` only
  gated the pre-flight form on `evidenceStatus === "unsupported"`; the fix
  maps `awaiting_evidence` onto `unsupported` for the panel's prop in
  `ReviewQueuePage.tsx`, `ContestedPage.tsx`, and `AssertionDetailPage.tsx`.
- **Finding** (not a QA-FAIL, flagged for the record): the D3 comments
  ("the backend requires an acceptance justification whenever there is no
  supporting evidence, which covers both 'unsupported' and
  'awaiting_evidence'") and this log's earlier D3 entry ("backend requires
  justification for BOTH no-evidence states") overstate the backend's
  actual gate. Empirically probed against the live `client` fixture: an
  assertion created with evidence `[{"evidence_role": "contradicts"}]`
  (rows exist, none supporting → `evidence_status="unsupported"` per
  `assertions.py::_evidence_status`) submits and **accepts with 200 and no
  `acceptance_justification` in the body**. `review.py::_has_evidence`
  only checks "does any evidence row exist at all", which is true for
  `unsupported` — so the backend's justification requirement in practice
  only bites `awaiting_evidence` (zero rows). The frontend's pre-existing
  (pre-D3, unchanged by 6c155f6) behavior of also showing the justification
  form for `unsupported` is therefore stricter than the backend requires —
  harmless (extra confirmation step, not a broken flow) and out of D3's
  actual scope (D3 was specifically about the `awaiting_evidence` gap,
  which is correctly fixed and independently confirmed via
  `test_unsupported_assertion_cannot_be_accepted_without_justification` /
  `..._with_recorded_justification` in test_review_workflow.py, both of
  which use zero-evidence assertions).

### Extra-scrutiny sweep (director mandate)
Read `backend/app/routers/workspace.py` in full plus
`backend/tests/integration/test_workspace.py` (18 tests at baseline).
Untested error paths found and pinned (6 new tests, `test_workspace.py`
now 24/24 green, full suite 485/485):
- `test_me_empty_bearer_token_is_401` — `Authorization: Bearer ` (and
  `Bearer    `) is a malformed credential per `app/auth.py`, not a
  header that resolves to an empty user id.
- `test_add_member_unknown_matter_is_404_even_with_invalid_role` — proves
  the route's actual guard ordering (`_get_matter_or_404` before
  `_validate_role`): an unknown matter must 404, not 422, even with a
  bogus role in the body.
- `test_role_change_unknown_matter_is_404`, `test_remove_member_unknown_matter_is_404`
  — PUT/DELETE members shared the same `_get_matter_or_404` guard as GET
  (already tested) and POST (now tested) but had no direct coverage.
- `test_role_change_on_non_member_is_404`, `test_remove_non_member_is_404`
  — PUT/DELETE on a `member_user_id` with no `MatterRole` row in that
  matter correctly 404s (code already handled this; now pinned).
All 6 pass against the current code unmodified — real coverage gaps, not
RED traps.

Frontend mock-shape spot check (director's "members-shape bug class"):
read `frontend/src/api/client.ts` against
`AdminPage.test.tsx`/`AnalyticsPage.test.tsx`/`ReviewQueuePage.test.tsx`
(already fixed, bare-array mocks correct) plus
`KnowledgeBasePage.test.tsx`, `AssertionDetailPage.test.tsx`,
`ProfilePage.test.tsx`, `ContestedPage.test.tsx` — `listAssertions`
(`{items, total}`), `getAssertion` (embeds `evidence`/`comments`/
`ratings_summary`/`revision_history` exactly matching
`assertions.py::get_assertion`'s response assembly), `listEvidence`
(bare array), `notifications` (bare array, confirmed against
`notifications.py::get_notifications`'s `list[dict]` return type) — no
further wrong-shape mocks found.

### Gate G3 — fork quickstart (executed, not read)
1. `git clone … /tmp/lexgraph-fork-check --branch claude/stitch-consensus-platform-b5fa87 --single-branch` — OK (clones committed HEAD 266ca3c;
   QA's own test-file changes are uncommitted at clone time, irrelevant to
   this gate).
2. `cd backend && python3 -m venv .venv && .venv/bin/pip install -q -e '.[dev]'` — OK, silent success.
3. `.venv/bin/python -m app.seed_demo --db dev.db` — OK, printed
   "Seeded dev.db — 2 matters, 4 users, 8 source spans." + serve command +
   sign-in ids.
4. `LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/uvicorn app.main:app --port 8100 &`, then `curl http://127.0.0.1:8100/healthz` → 200 (well under the 2-minute bound).
5. `curl -H "Authorization: Bearer admin" http://127.0.0.1:8100/api/v1/me` → `user.display_name="Ada Admin"`, 2 matters, both role `admin`. Matches.
6. `npm --prefix frontend install --no-audit --no-fund` — OK, 178 packages.
7. `npm --prefix frontend run build` — OK, `tsc -b && vite build` succeeded, `dist/` produced.
8. Killed the uvicorn PID, confirmed the port stopped responding, `rm -rf /tmp/lexgraph-fork-check`.
All 8 steps PASS.

### Gate G4 — docs vs. reality
Read README.md "Running the app", RUNBOOK.md Quickstart + Web Application
sections, consensus-ui-review.md "Backend additions" + "Known limitations".
Checked every concrete claim against code/behavior verified above:
- `./scripts/demo.sh` contents match README's manual steps exactly (ports
  8000/5173, `LEXGRAPH_DATABASE_URL`, sign-in ids).
- `LEXGRAPH_API_PROXY` override confirmed present in `frontend/vite.config.ts`.
- Endpoint list in consensus-ui-review.md's "Backend additions" matches
  `workspace.py` exactly (GET /me, GET/POST/PUT/DELETE members, last-admin
  lockout).
- Seed re-run independently: 17 assertions across 8 distinct statuses
  (accepted 5, disputed 2, draft 1, proposed 5, rejected 1,
  revision_requested 1, superseded 1, withdrawn 1) — supports README's
  "assertions in every status" claim; the contract's own W1 bullet says
  "15 assertions" (stale by 2, not in a G4-scoped doc, noted above).
- "No span-resolution endpoint" and "Analytics computed client-side, no
  stats endpoint" both confirmed by reading the relevant serializers/pages.
- **Finding (not blocking):** RUNBOOK.md's opening summary says "3. A React
  grading application" and later "Start the grading app" (line ~6, ~288),
  while its own "Web Application" section correctly describes the
  Consensus UI (Review Queue/Knowledge Base/etc.). Stale label pre-dating
  this sprint's rename (likely carried from sprint
  2026-07-30-ratings-grade); harmless, cosmetic, reported for the docs
  owner to clean up — not a QA-FAIL since it doesn't misdescribe any
  behavior a user would rely on.

No other stale or false claims found.
