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
dev_complete_items: 9
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
- R8 Models frozen post-F1: `backend/app/models/**` is read-only for all B-tracks; a needed schema change is a mandatory escalation, never an inline edit.
- R9 Cross-track RED is EXPECTED in Wave-1 worktrees: backend integration tests drive routes across tracks (B4 tests create via B1; B3/B6 tests drive B1/B4/B2 routes). Each track greens its unit tests + own-route behavior, implements its full surface to the test contract, and reports which tests remain RED-for-missing-other-routes. The combined suite after all Wave-1 merges is the real gate. For cross-cutting concerns (audit rows, notifications) prefer mechanisms fully owned by your track (middleware/dependency registered via your own append-only line) over call-sites in other tracks' routers.
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

### B5 — Validation + duplicate detection + search/sort
Fill `app/services/validation.py` and `app/services/duplicates.py`
bodies; extend B1's `assertions.py` router with query-param search/sort
and inline duplicate-check on create (call into `duplicates.py`, do not
rewrite B1's CRUD handlers). Depends on F1 + B1 (function-call dependency
only, not a file conflict). RED tests: `tests/integration/test_validation_duplicates_api.py` (8),
`tests/integration/test_search_sort.py` (8), `tests/unit/test_validation.py` (8).

### B7 — Cross-cutting: matter isolation & hostile input (test-only, no write-set)
No new source files — proves G9/G10 against whatever B1 (evidence
matter-check), B4 (permission checks), and B5 (sanitization) ship.
Sequence last among backend tracks; any Developer picking this up should
re-run and fix regressions in the owning track's files, not add new ones.
RED tests: `tests/integration/test_matter_isolation.py` (6),
`tests/integration/test_hostile_input.py` (6).

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

- B2 — ratings + aggregates (`app/routers/ratings.py`, `app/services/ratings.py`), dev commit `414c1ac`, merged; 18/18 scoped green, full diff read (upsert, permission-gated rationales, DELETE audit call-site). Suite now 31F/95P.
- TESTFIX — planner-role micro-fix `8c451ad` (acceptance justification), anti-gaming diff check passed, manager-verified 1 passed, merged.
- B3 — comments + audit service/middleware + /history (R10) (6 files), dev commit `132ea2c`, merged `cb561d5`; 9/10 scoped green (1 expected-RED pending B2); suite 52F/74P, fully reconciled. Note for B7: comment sanitization wiring pending B5's sanitize_for_storage.
- B1 — assertion CRUD/evidence/revisions (`app/routers/assertions.py` + include line), dev commit `4ffea3f`, merged `22b1ac8`; manager probe 16/16 in worktree + full 674-line diff read (no test edits, no boundary violations).
- B4 — review workflow + permissions (`app/routers/review.py`, `app/services/permissions.py`), dev commit `db1a22f`, merged `b05df53`; permissions matrix 19/19; flagged the test-contract bug now confirmed (see log + pending Planner micro-fix).
- B6 — graph projection + notifications (6 owned files incl. notification middleware), dev commit `b4b72ff`, merged `420a51a`; unit 5/5; combined-suite reconciliation clean (61F/65P, all remaining RED maps to unstarted tracks).
- F1 — 13 ORM models + constraints (`backend/app/models/**`, one import line in `main.py`), dev commit `251e19d`, merged `68871a3`; manager probe: 126 failed / 0 errors (all no-such-table gone, per-file counts match census), full persistence diff read and approved.
- UI1 — AssertionCard + AssertionRatingWidget + AssertionRatingDistribution (`frontend/src/components/`), dev commit `b33715d`, merged `4e750e6`; 19/19 scoped green, manager probe confirmed.
- UI3 — 6 workspace/review/discussion/history components (`frontend/src/components/`), dev commit `5b3aee5`, merged `4c543a3`; 27/27 scoped green, manager full-frontend probe 46/46 across UI1+UI3.
- UI2 — AssertionSuggestionForm + AssertionEvidenceSelector (`frontend/src/components/`), dev commit `8fffe53`, merged `0c5c436`; 13/13 scoped green; manager full-frontend probe 59/59 (all 11 files). QA flag: verify submit-disabled logic semantics vs spec §6/§7 (dev reconciled two tests with `hasExactDuplicate || (propositionMissing && no similars)` — check the Planner tests didn't encode a contradiction).

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
