---
id: "2026-07-25-collaborative-assertions"
status: in-progress
current_role: developer
branch: sprint/2026-07-25-collaborative-assertions
locked_by: "claude-code:developer"
locked_at: "2026-07-25T20:39:00Z"
last_agent: "claude-code:manager"
last_updated: "2026-07-25T20:39:00Z"
lint: "PASS 185 2026-07-25T20:24:02Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 12
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
prd_sections:
  - docs/specs/collaborative-assertions.md
design_sections: []
---

# Sprint: Collaborative assertion assessment & user-suggested assertions

Authoritative spec: `docs/specs/collaborative-assertions.md` (20 sections + 16-point definition of done).
Acceptance gates: `docs/sprint/sprints/2026-07-25-collaborative-assertions-log.md` § Acceptance gates.
Data model reference, API-path assumptions, and the full Expected RED census: same log file.

## Manager rulings

- R1 Stack: backend Python 3.12 + FastAPI + SQLAlchemy 2 + Pydantic v2 + pytest; SQLite for test runs on a Postgres-compatible schema (PostgreSQL is the declared production authority per spec §11); frontend React 18 + TypeScript + Vite + Vitest + Testing Library. No live Neo4j here: graph projection goes behind a `GraphProjection` interface with an in-memory adapter; a Neo4j adapter may be stubbed but is not required to run.
- R2 Greenfield scaffold: the Planner MAY commit build/config scaffolding and empty package skeletons (pyproject, package.json, configs, bare app factory with no routes/handlers) so RED tests fail on assertions (404/missing behavior), never collection errors. All business logic and route handlers remain Developer work.
- R3 Auth: in-DB users + per-matter roles (viewer/contributor/reviewer/admin) with a test-friendly token scheme; no external IdP this sprint. All permission checks server-side (spec §12).
- R4 Notifications: in-app only (spec §15 MVP). No email/push.
- R5 Ratings are revision-scoped (spec §10 MVP): AssertionRating carries assertion_id + assertion_revision_id; one current rating per user per revision; prior-revision ratings preserved, never auto-copied.
- R6 Append-only zones: the `include_router` block in `app/main.py::create_app()` and the docstring in `app/routers/__init__.py` — each track appends only its own registration line(s); merge conflicts there are resolved by concatenating both sides, then a full evaluator run.
- R7 Wave sequencing (manager, from write-set + seam analysis): Wave 0 = F1 ∥ UI1 ∥ UI2 ∥ UI3; Wave 1 (after F1 merges) = B1 ∥ B3 ∥ B4 ∥ B6; Wave 2 (after Wave 1 merges) = B2 ∥ B5 (B2 needs B3's audit service — its tests assert audit rows; B5 edits B1's router file); Wave 3 = B7+E1 bundled, one Developer, sequential last. Audit call-sites in each router belong to that router's owning track, calling B3's `app/services/audit.py`. Shared frontend types stay local to each component file this sprint — no shared types module (add/add risk).

## Scaffolding already committed (Planner)

`backend/{pyproject.toml,app/**,tests/**}` — bare FastAPI app factory with
NO routes (`app/main.py`), SQLAlchemy `Base` with zero models
(`app/db.py`), a real (non-mocked) test-token auth-header seam
(`app/auth.py`), a `GraphProjection` interface + `InMemoryGraphProjection`
shape (`app/graph_projection.py`), 4 service-stub modules that raise
`NotImplementedError` (`app/services/{ratings,validation,permissions,duplicates}.py`),
`app/notifications.py` shape, and `tests/conftest.py` (client/db fixtures,
`auth_header`, raw-SQL `seed_*` helpers, `matter_with_users` fixture,
`assertion_payload`/`rating_payload` builders). `frontend/{package.json,
vite.config.ts,tsconfig.json,src/test/setup.ts}` — Vite/Vitest/React
Testing Library toolchain, no components. 185 RED tests already authored
across 26 files (15 backend, 11 frontend) — see Expected RED census in
the log. Every item below is a Developer track filling in real behavior
behind this scaffolding; no item creates its own toolchain.

## Next Steps

### F1 — Data model & schema (sequential, FIRST — blocks all other backend items)
Register SQLAlchemy ORM models against `app.db.Base` (see log § Data
model reference for the 13 tables) matching spec §2-4/§9/§16 field lists
exactly, plus `organizations/repositories/matters/users/matter_roles/
documents/source_spans`. Add proper constraints (unique(user_id,
assertion_revision_id) on ratings, FKs, NOT NULL where the spec implies
it). No routes, no service logic. Acceptance: `matter_with_users` fixture
in `backend/tests/conftest.py` succeeds (no more `OperationalError: no
such table`); `backend/.venv/bin/pytest backend/tests -q` shows 87 ERRORs
convert to FAILED/PASSED (still red on missing routes/services — that's
expected, B-tracks land those).

### B1 — Assertion CRUD, evidence, revisions
Implement `app/routers/assertions.py` (create/get/patch/submit/withdraw/
evidence add-remove/revisions) + `app/models/` files for assertion/
evidence/revision, wired via `app.state`-based DB access into
`create_app()`. Depends on F1. Owns: `app/routers/assertions.py`,
`app/models/assertion*.py`. RED tests: `tests/integration/test_assertions_crud.py` (16).

### B2 — Ratings + aggregates
Fill `app/services/ratings.py::compute_rating_summary` body; implement
`app/routers/ratings.py` (PUT/GET/DELETE rating, summary, list) +
`app/models/assertion_rating.py`. Depends on F1; reads assertion/revision
rows B1 creates (no B1 file writes). RED tests:
`tests/integration/test_ratings_api.py` (11), `tests/unit/test_ratings_aggregate.py` (7).

### B3 — Comments + audit
Implement `app/routers/comments.py` + `app/models/assertion_comment.py`,
`app/models/audit_event.py`, `app/services/audit.py` (new — emits
`audit_events` rows for every mutation across B1/B2/B4). Depends on F1.
RED tests: `tests/integration/test_comments_audit.py` (10).

### B4 — Review workflow + permissions
Fill `app/services/permissions.py::has_permission` body; implement
`app/routers/review.py` (accept/reject/dispute/request-revision/supersede)
+ `app/models/matter_role.py`, `app/models/user.py`. Depends on F1. RED
tests: `tests/integration/test_review_workflow.py` (11),
`tests/unit/test_permissions_matrix.py` (19).

### B5 — Validation + duplicate detection + search/sort
Fill `app/services/validation.py` and `app/services/duplicates.py`
bodies; extend B1's `assertions.py` router with query-param search/sort
and inline duplicate-check on create (call into `duplicates.py`, do not
rewrite B1's CRUD handlers). Depends on F1 + B1 (function-call dependency
only, not a file conflict). RED tests: `tests/integration/test_validation_duplicates_api.py` (8),
`tests/integration/test_search_sort.py` (8), `tests/unit/test_validation.py` (8).

### B6 — Graph projection + notifications
Fill `app/graph_projection.py::InMemoryGraphProjection` method bodies;
fill `app/notifications.py` bodies; implement `app/routers/graph.py`
(`GET /api/v1/matters/{id}/graph`) and notifications read route (`GET
/api/v1/notifications`) — see log § API surface assumptions. Depends on
F1 + B1 (assertion status) + B4 (accept/reject events). RED tests:
`tests/integration/test_graph_projection_api.py` (6),
`tests/integration/test_notifications.py` (4), `tests/unit/test_graph_projection.py` (5).

### B7 — Cross-cutting: matter isolation & hostile input (test-only, no write-set)
No new source files — proves G9/G10 against whatever B1 (evidence
matter-check), B4 (permission checks), and B5 (sanitization) ship.
Sequence last among backend tracks; any Developer picking this up should
re-run and fix regressions in the owning track's files, not add new ones.
RED tests: `tests/integration/test_matter_isolation.py` (6),
`tests/integration/test_hostile_input.py` (6).

### UI1 — AssertionCard + rating widget + rating distribution
Create `frontend/src/components/{AssertionCard,AssertionRatingWidget,
AssertionRatingDistribution}.tsx` per spec §5 (accessible 1-5 widget:
keyboard nav, ARIA labels, your-vs-team rating separation, no ratings ==
no aggregate shown). Independent of backend tracks. RED tests (currently
import-resolution failures — documented exception): `AssertionCard.test.tsx` (6),
`AssertionRatingWidget.test.tsx` (8), `AssertionRatingDistribution.test.tsx` (5).

### UI2 — Suggestion form + evidence selector
Create `frontend/src/components/{AssertionSuggestionForm,
AssertionEvidenceSelector}.tsx` per spec §6 (Method A/B creation, add/
remove supporting/contradicting evidence, save-draft/submit/cancel/
preview). Independent of backend tracks. RED tests: `AssertionSuggestionForm.test.tsx` (7),
`AssertionEvidenceSelector.test.tsx` (6).

### UI3 — Detail workspace + review panel + discussion + history
Create `frontend/src/components/{AssertionDetailPanel,
AssertionReviewPanel,AssertionComments,AssertionRevisionHistory,
RelatedAssertionsPanel,AssertionComparisonView}.tsx` per spec §5/§9/§14
(tabbed workspace, reviewer actions incl. justify-unsupported-accept,
comment thread w/ reviewer distinction, revision compare). Independent of
backend tracks. RED tests (5 files, 22 tests total — see census).

### E1 — Thin end-to-end flow (sequential, LAST)
No new source files. API-driven E2E (Playwright deferred to QA's
regression pass — decision recorded, not a scope cut) proving the full
spec §18 10-step flow against the real API. Depends on F1, B1, B2, B4,
B6 all complete. RED test: `tests/e2e/test_full_flow.py` (1).

## Parallelization plan

F1 is a hard sequential gate (all backend tracks read/write the same
`Base.metadata`). After F1 lands: B1-B7 run in parallel with
non-overlapping write-sets (B5 calls into B1's router but never edits
B1's file bodies directly — coordinate via a PR review, not a merge
conflict; B7 and E1 write no source at all). UI1-UI3 have zero backend
dependency and can start immediately, in parallel with F1/B-tracks. E1 is
a hard sequential gate at the end, after F1+B1+B2+B4+B6.

## Expected RED census

See `docs/sprint/sprints/2026-07-25-collaborative-assertions-log.md` §
"Expected RED census" — full per-file table (126 backend tests: 39
FAILED/NotImplementedError + 87 ERROR/no-such-table; 59 frontend tests
across 11 files, all import-resolution RED per the documented frontend
exception; 185 total). Verified by direct run, not inferred.

## Stale-pin sweep

none — greenfield, no renames.

## Dev Complete

## Completed

## Evaluation Notes

## QA Notes

## Context Dump

Greenfield repo, Planner pass complete. Scaffolding + 185 RED tests
committed (backend FastAPI/SQLAlchemy, frontend Vite/Vitest/RTL — see
"Scaffolding already committed" above). Developer: start with item F1
(sequential gate), then any of B1-B7/UI1-UI3 in parallel per the plan
above; E1 last. Deviation: python@3.12 unavailable locally — backend
venv built with python3.13 (R1 pin was 3.12; functionally compatible).
