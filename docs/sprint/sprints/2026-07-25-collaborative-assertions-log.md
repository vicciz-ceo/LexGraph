# Sprint log — 2026-07-25-collaborative-assertions

Append-only overflow sink. Never auto-loaded; the contract points here.

## Acceptance gates (manager-defined, director-correctable)

Plain-language pass/fail conditions. The Planner turns each into failing
tests across the pyramid; QA re-verifies each independently at the end.

- G1 Draft creation: a signed-in contributor can create a draft assertion scoped to a repository + matter, and attach one or more exact documentary source spans as evidence with explicit roles (supports/contradicts/qualifies/…).
- G2 Submission: the contributor can submit the draft for review; it is visibly marked user-suggested and draft/proposed — it never appears as accepted merely from submission or high ratings.
- G3 Ratings: a second authorized user can rate the assertion revision 1–5 with an optional written rationale, and later update or remove that rating; one current rating per user per revision; every rating mutation is audited.
- G4 Aggregates: the assertion shows count, arithmetic mean (unrounded in storage), median, and 1–5 distribution — displayed separately from model confidence, review status, and evidence status; no aggregate is computed or shown with zero ratings; aggregates never change review status, confidence, or evidence status.
- G5 Review: a reviewer sees proposition, evidence (supporting and contradicting), ratings + rationales, comments, and full history, and can accept / reject / dispute / request revision; unsupported assertions cannot be accepted without recorded justification; reviewer decisions never erase user ratings.
- G6 Revisions: a material edit creates a new revision; the original stays available; editing an accepted assertion yields a new proposed revision, not a silent change; review decisions record which revision was reviewed; ratings stay attached to the revision that was rated and never auto-copy forward.
- G7 Graph: only accepted assertions appear as accepted relationships in the default graph view; proposed/disputed/rejected/superseded appear only in an opt-in "show unreviewed" mode with distinct states; rating aggregates in the graph are rebuildable projections, never authoritative.
- G8 Permissions + audit: every assertion, rating, comment, evidence, and review mutation is permission-checked server-side (viewer/contributor/reviewer/admin) and produces an audit event with actor, timestamp, matter, assertion, revision, before/after where relevant, and a correlation id; no full-document content in routine audit logs.
- G9 Matter isolation: a user without matter access cannot view, rate, comment on, or attach evidence to an assertion; evidence from an inaccessible matter cannot be attached; aggregates never mix matters — proven by automated tests.
- G10 Hostile input: raw HTML/scripts in propositions, rationales, and comments are stored/rendered as inert data; prompt-injection text inside a suggested assertion is treated as data, never as instructions; propositions are stored exactly as authored.
- G11 UI: assertion cards and a detail workspace exist with an accessible 1–5 rating widget (keyboard + screen-reader), separate "your rating" vs "team rating" displays, evidence/ratings/discussion/revision-history views, a suggest-assertion form (from selected text and from graph entities), and a reviewer panel — with explanatory text that ratings are individual opinions, not legal conclusions.
- G12 End-to-end: the 10-step contributor→rater→reviewer flow (spec §18) passes against the real API: suggest from highlighted text → second user rates 4 → summary updates → reviewer inspects → accept/reject → history preserved → accepted assertion visible in graph with evidence.

## Phase log

- 2026-07-25T20:02Z — Manager (Fable 5): repo bootstrapped, private GitHub remote created (vicciz-ceo/LexGraph), sprint state initialized, gates defined. Director gave a broad implement-the-spec mandate; gates presented in the kickoff report rather than blocking on confirmation (autonomous session). Stack ruling R1 recorded — director may override; re-planning trigger.
- 2026-07-25T20:23Z — Planner (Sonnet, high): defined 12 sprint items (F1 + B1-B7 + UI1-UI3 + E1) covering G1-G12; scaffolded backend (FastAPI bare app factory, SQLAlchemy Base, test-token auth seam, GraphProjection interface + in-memory adapter shape, 4 service-stub modules) and frontend (Vite/Vitest/RTL toolchain) build/config only — no business logic; authored 185 RED tests (126 backend across 15 files, 59 frontend across 11 files); verified genuine RED (39 NotImplementedError, 87 no-such-table, 11 import-resolution — see census above). python@3.12 unavailable in this environment (only python@3.13 installed via Homebrew) — used python3.13 for the backend venv, a minor deviation from ruling R1's "Python 3.12" pin.

## Data model reference (Planner, for item F1)

Column names lifted verbatim from spec §2-4/§9/§16 wherever the spec
enumerates them; table/column names below are the Planner's concrete
schema proposal for anything the spec left implicit (org/repo/matter/
user/role/document/span/audit tables). `backend/tests/conftest.py` seed_*
helpers INSERT into these tables via raw SQL — no ORM models are defined
by the Planner. Item F1 registers matching SQLAlchemy models against
`app.db.Base`; column names/types below are non-binding except where they
are directly quoted from the spec (assertions, assertion_revisions,
assertion_evidence, assertion_ratings, assertion_comments, audit_events).

- `organizations(id, name)`
- `repositories(id, organization_id, name)`
- `matters(id, repository_id, name)`
- `users(id, email, display_name)`
- `matter_roles(id, user_id, matter_id, role)` — role ∈ viewer/contributor/reviewer/admin; unique(user_id, matter_id)
- `documents(id, repository_id, matter_id, title)`
- `source_spans(id, document_id, matter_id, quote_text)`
- `assertions` — exact spec §2 field list (id, organization_id, repository_id, matter_id, assertion_type, proposition, subject_entity_type, subject_entity_id, object_entity_type, object_entity_id, origin, status, author_user_id, confidence, jurisdiction, effective_from, effective_to, created_at, updated_at, submitted_at, reviewed_by, reviewed_at, superseded_by_assertion_id, current_revision_number)
- `assertion_revisions` — exact spec §3 field list
- `assertion_evidence` — exact spec §2 field list (id, assertion_id, source_span_id, evidence_role, added_by_user_id, created_at)
- `assertion_ratings` — spec §4/§10 field list, PLUS `assertion_revision_id` (ruling R5); unique(user_id, assertion_revision_id)
- `assertion_comments` — exact spec §9 field list
- `audit_events(id, actor_user_id, event_type, timestamp, repository_id, matter_id, assertion_id, assertion_revision_id, previous_value, new_value, correlation_id)`

### API surface assumptions beyond spec §13's literal list

Spec §13 does not enumerate a graph-read or notifications-read endpoint,
though §11/§14/§15 require them. Planner assumption (tests encode these
paths; Developer/QA may adjust — not a locked contract):
- `GET /api/v1/matters/{matter_id}/graph?show_unreviewed=bool` — B6
- `GET /api/v1/notifications` — B6

## Expected RED census (Planner pass, before any Developer work)

Two legitimate non-import RED shapes for backend (see conftest.py
docstring): FAILED (NotImplementedError from a scaffolded service stub —
unit tests) and ERROR (OperationalError: no such table — schema pending
item F1, integration/e2e tests). Frontend: import-resolution failure is
the documented, accepted exception (component files don't exist yet).

| Test file | Expected count | RED shape | Owning track |
|---|---|---|---|
| backend/tests/integration/test_assertions_crud.py | 16 | ERROR (no such table) | B1 |
| backend/tests/integration/test_ratings_api.py | 11 | ERROR (no such table) | B2 |
| backend/tests/unit/test_ratings_aggregate.py | 7 | FAILED (NotImplementedError) | B2 |
| backend/tests/integration/test_comments_audit.py | 10 | ERROR (no such table) | B3 |
| backend/tests/integration/test_review_workflow.py | 11 | ERROR (no such table) | B4 |
| backend/tests/unit/test_permissions_matrix.py | 19 | FAILED (NotImplementedError) | B4 |
| backend/tests/integration/test_validation_duplicates_api.py | 8 | ERROR (no such table) | B5 |
| backend/tests/integration/test_search_sort.py | 8 | ERROR (no such table) | B5 |
| backend/tests/unit/test_validation.py | 8 | FAILED (NotImplementedError) | B5 |
| backend/tests/integration/test_graph_projection_api.py | 6 | ERROR (no such table) | B6 |
| backend/tests/integration/test_notifications.py | 4 | ERROR (no such table) | B6 |
| backend/tests/unit/test_graph_projection.py | 5 | FAILED (NotImplementedError) | B6 |
| backend/tests/integration/test_matter_isolation.py | 6 | ERROR (no such table) | B7 |
| backend/tests/integration/test_hostile_input.py | 6 | ERROR (no such table) | B7 |
| backend/tests/e2e/test_full_flow.py | 1 | ERROR (no such table) | E1 |
| **Backend total** | **126** | 39 FAILED + 87 ERROR | — |
| frontend/src/components/__tests__/AssertionCard.test.tsx | 6 | import-resolution failure | UI1 |
| frontend/.../AssertionRatingWidget.test.tsx | 8 | import-resolution failure | UI1 |
| frontend/.../AssertionRatingDistribution.test.tsx | 5 | import-resolution failure | UI1 |
| frontend/.../AssertionSuggestionForm.test.tsx | 7 | import-resolution failure | UI2 |
| frontend/.../AssertionEvidenceSelector.test.tsx | 6 | import-resolution failure | UI2 |
| frontend/.../AssertionDetailPanel.test.tsx | 5 | import-resolution failure | UI3 |
| frontend/.../AssertionReviewPanel.test.tsx | 5 | import-resolution failure | UI3 |
| frontend/.../AssertionComments.test.tsx | 5 | import-resolution failure | UI3 |
| frontend/.../AssertionRevisionHistory.test.tsx | 4 | import-resolution failure | UI3 |
| frontend/.../RelatedAssertionsPanel.test.tsx | 5 | import-resolution failure | UI3 |
| frontend/.../AssertionComparisonView.test.tsx | 3 | import-resolution failure | UI3 |
| **Frontend total** | **59** | 11 files fail to resolve | — |
| **Grand total** | **185** | | |

Verified: `cd backend && .venv/bin/pytest tests -q` → `39 failed, 87 errors`
(no collection errors — all import statements resolve; `python -c "from
app.main import create_app; create_app()"` succeeds). `cd frontend && npx
vitest run` → `11 failed (import resolution)`, 0 collected (expected —
component modules genuinely do not exist).

## Agent roster

(role → agentId, appended at every spawn)
- 2026-07-25T20:05Z — planner → ab341a135505f0cb8 (sonnet, high)
- 2026-07-25T20:39Z — Manager (Fable 5): Planner handoff verified (RED census re-run matched: 39F+87E backend; roots exist; commits pushed). Rulings R6/R7 added (append-only router zone, wave sequencing). Lock → claude-code:developer. Spawning Wave 0: F1, UI1, UI2, UI3.
