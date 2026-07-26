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
- 2026-07-25T20:45Z — dev F1 → aa580bfb2bbdf1d96 (sonnet, medium)
- 2026-07-25T20:45Z — dev UI1 → a581808ae137c65ae (sonnet, medium)
- 2026-07-25T20:45Z — dev UI2 → a272f4e312246004a (sonnet, medium)
- 2026-07-25T20:45Z — dev UI3 → a9467396891ea1dea (sonnet, medium)
- 2026-07-25T21:12Z — Manager: UI1 verified (diff clean, own probe 19/19) + merged @ 4e750e6. Wave-0 stall event: F1/UI2/UI3 agents killed by stream watchdog (600s). Worktree autopsy: dev-f1 clean (no work), dev-ui2 clean, dev-ui3 has all 6 components uncommitted. Recovery: resume UI3 via message; fresh respawns for F1/UI2 reusing existing worktrees.
- 2026-07-26T00:20Z — UI3 resumed via SendMessage (same agent a9467396891ea1dea); dev F1 respawn → a317ed8fecf2fb649 (sonnet, medium); dev UI2 respawn → aab01d89dbf8800ae (sonnet, medium)
- 2026-07-26T00:30Z — Manager: UI3 verified+merged @ 4c543a3 (probe 46/46 frontend). F1 respawn stalled again (zero work, worktree synced to 9c121c1); UI2 respawn died on API 529 but wrote BOTH components (uncommitted). Resuming both via SendMessage.
- 2026-07-26T00:42Z — Manager: UI2 verified+merged @ 0c5c436; full frontend probe 59/59 (11 files). All UI tracks dev-complete. Waiting on F1 (resumed) to unblock backend Wave 1.
- 2026-07-26T01:05Z — Manager: F1 verified (full 610-line persistence diff read; probe 126F/0E matches census) + merged @ 68871a3. Rulings R8 (models frozen) + R9 (cross-track RED expected; self-owned audit/notification mechanisms preferred) added after seam analysis of B3/B4/B6 test files. Spawning Wave 1: B1, B3, B4, B6.
- 2026-07-26T01:10Z — dev B1 → a67a9b7b6d6afb635 (sonnet, medium); dev B3 → a2f869318ce182531 (sonnet, medium); dev B4 → aaa9ea7473468b978 (sonnet, medium); dev B6 → ad47e8613b2cb814e (sonnet, medium)
- 2026-07-26T02:00Z — Manager PROCESS FAULT (self-report): a lingering `cd` into dev-b1's worktree caused two merge commands to run inside B1's dev branch instead of the main checkout. Damage: local-only pollution of sprint/…-b1 (never pushed); fixed by reset --hard 4ffea3f; real merges redone from the main checkout. Rule reinforced: manager git ops always use `git -C /Users/nerya/LexGraph`.
- 2026-07-26T02:05Z — Manager: B1 merged @ 22b1ac8 (16/16 probe), B4 merged @ b05df53 (19/19 matrix), B6 merged @ 420a51a. Combined suite 61F/65P, fully reconciled to unstarted tracks. CONFIRMED Planner test bug: test_review_decision_records_reviewed_revision accepts an unsupported assertion without `acceptance_justification` yet expects 200 (contradicts the two explicit 422/justification tests). Fix = add the justification body; HELD until B3's /history route lands (test also needs it) so the micro-fix gate is simply "test green".
- 2026-07-26T02:05Z — Ruling R10: `GET /api/v1/assertions/{id}/history` (spec §13, unassigned in the item list) is B3's (audit-backed read combining status/review/revision events); `GET /api/v1/assertions/{id}/related` is B5's (duplicates surface).
- 2026-07-26T03:00Z — Manager: B3 verified (audit middleware + history route read; no double-write with B4) + merged @ cb561d5. Suite 52F/74P reconciled. Spawning Wave 2: B2 ∥ B5 + Planner-role Haiku micro-fix (justification line in test_review_workflow, unblocked by /history).
- 2026-07-26T03:05Z — dev B2 → a3efc81df06a8d5df (sonnet, medium); dev B5 → a5f196869043a49c3 (sonnet, medium); planner micro-fix → adb701c506fe5901e (haiku, low)
- 2026-07-26T04:00Z — Manager: B2 verified+merged; testfix WIP committed by agent, verified+merged by manager. Suite 31F/95P. Remaining: B5 (23), same accept-bug in 3 more tests (graph x2, notifications x1 — micro-fix 2), B1 serialization gap → B5 scope, hostile-input 3 (B5+B7), e2e 1.
- 2026-07-26T04:05Z — planner micro-fix 2 → ac6a422788c04e0f8 (haiku, low); B5 resumed via SendMessage with serialization-enrichment scope
- 2026-07-26T04:20Z — Manager: micro-fix 2 verified (3 exact line replacements) + merged @ c2cdc46. Suite 28F/98P: 23 B5-owned + 3 hostile (B5/B7) + 1 serialization (B5 scope) + 1 e2e. Awaiting B5.
- 2026-07-26T05:00Z — Manager: B5 verified+merged @ 76ecf3b. Suite 3F/123P. Final wave scoped exactly: sanitize wiring in comments (B3 file) + rating rationale (B2 file) + evidence_count on graph edge (B6 file) → e2e. Spawning B7+E1 bundle dev.
- 2026-07-26T05:05Z — dev B7+E1 → a0cfc43cbd352c2fe (sonnet, medium)
- 2026-07-26T05:40Z — Manager: B7+E1 verified+merged @ c2f2b02. FULL EVALUATOR GREEN: 185/185. All 12 items dev-complete. Lock → claude-code:qa; spawning QA (sonnet, high).
- 2026-07-26T05:50Z — QA → a522c7ad182cfddcf (sonnet, high)
- 2026-07-26T06:10Z — QA (Sonnet, high), cycle 1: independent evaluator confirmed 126 backend + 59 frontend green (no flakes). 10/12 items PASS (F1, B1, B2, B4, B6, B7, E1, UI1, UI2*, UI3 — *UI2 escalated, see contract QA Notes), 2 bounced: B5 (sanitizer misses unclosed HTML tags with event-handler attributes — regex tag-stripper needs a closing `>` in the same string to fire; also PATCH/create-revision never call `sanitize_for_storage` at all, unlike CREATE) and B3 (evidence add/remove write zero `audit_events` rows — spec §16/gate G8 gap; `app.audit_middleware` was never extended to the evidence routes the way it was for `assertion_created`). Both confirmed live via the real API + raw SQL, both have committed RED tests. Added 4 passing regression tests (supersede flow x3, notification cross-matter isolation x1) confirming previously-untested-but-correct behavior. Full attention-list (a-f) reconciled — (d) unresolvable evidence span and (e) withdraw-from-accepted both confirmed as documented limitations per brief guidance. Escalation filed on UI2's submit-disabled formula (Planner test contradicts spec §7's absolute empty-proposition rule; not edited per brief instruction). Status → qa-fail, current_role → developer, qa_cycles → 1.
- 2026-07-26T06:30Z — Manager: QA verdict accepted (commit clean: tests+contract only; RED provenance verified: 6F/130P). Escalation answered via R11. Lock → developer. Spawning qa-fail fix dev (3 backend items, sonnet med) + UI2 test micro-fix (haiku).
- 2026-07-26T06:35Z — qa-fail fix dev → a65e32a58a26642fb (sonnet, medium); UI2 test micro-fix → a7b59a00566ab0cd8 (haiku, low)
- 2026-07-26T06:50Z — micro-fix 3 merged @ d6eee83; UI2 formula fix dev → aec4afaa83cf8f619 (haiku, medium)
- 2026-07-26T07:00Z — Manager: UI2 formula fix verified (exact 1-line diff) + merged @ 2345b88; frontend probe 60/60. Awaiting backend fix1 dev.
- 2026-07-26T07:20Z — Manager: fix1 verified (full diff read) + merged @ fc76c96. Own evaluator: 136/136 backend + 60/60 frontend. Lock → qa; spawning QA cycle 2.
- 2026-07-26T07:30Z — QA cycle 2 → a3f44cb5af84a6c7e (sonnet, high)
- 2026-07-26T07:40Z — QA (Sonnet, high), cycle 2: independent evaluator confirmed 136 backend + 60 frontend green (no flakes). B3-fix PASS (raw-SQL count before/after 1→2→3, ids-only, actor/matter/assertion correct) → moved to Completed. UI2-fix PASS (8/8, formula matches R11 exactly `hasExactDuplicate || propositionMissing`) → moved to Completed, resolving cycle-1 ESCALATION. B5-fix FAIL: adversarial re-probe found two NEW bypass classes beyond cycle-1's fix — (1) no-space-before-attribute evasion (`<img/onerror=...`, a documented real-world sanitizer-bypass shape) survives verbatim across all 5 write paths (create/PATCH/revisions/comments/rating-rationale, shared function); (2) pre-existing `_TAG_RE` naive first-`>` matching corrupts benign prose containing an unrelated later `>` (e.g. "amount < $500 ... term > 10 years"), violating spec §2's authored-text-preservation guarantee. Confirmed live via real API for both. Added 7 RED tests (4 unit, 3 integration) pinning required behavior, plus 4 regression pins for already-correct adjacent paths lacking coverage (revision/comment-edit/rating-update unclosed-tag, one quoted-attribute unit case). Status → qa-fail, current_role → developer, qa_cycles → 2.
- 2026-07-26T07:55Z — Manager: QA cycle 2 accepted (commit clean: tests+contract only; RED provenance 7F/140P verified). 11/12 items Completed. Ruling R12: replace regex sanitizer with html.parser-based tokenizer — two regex rounds + a prose-corruption bug prove the approach is structurally wrong, not just under-patched. Lock → developer; spawning fix2.
- 2026-07-26T08:00Z — sanitizer rewrite dev (R12) → a6d1a1dd5b06fbdcd (sonnet, medium)
- 2026-07-26T08:20Z — Manager: fix2 verified (full impl read + own 14-case probe: 9 attacks neutralized, 5 prose byte-exact) + merged @ abc5806; 147/147. Valid-tag-shaped-prose limitation logged for QA cycle 3. Lock → qa.
- 2026-07-26T08:25Z — QA cycle 3 → a5ef14b43ef2df3d0 (sonnet, high)
- 2026-07-26T08:55Z — QA (Sonnet, high), cycle 3: baseline 147/147 backend + 60/60 frontend confirmed clean. Adversarial round 3 on R12's `html.parser` rebuild found 2 NEW live bypasses: CDATA/RCDATA-wrapper (iframe/textarea/title/noembed/noframes/xmp — stdlib parser's own raw-text-element lists are wider than `_CDATA_CONTENT_TAGS`), confirmed on all 5 write paths; chained-abandoned-tag (2nd unclosed tag's markup leaks past `_salvage_trailing_prose`), confirmed on 2 paths. All other probed shapes + all required prose-integrity cases confirmed correct/byte-exact — 12 regression pins added. KNOWN LIMITATION (`a<b and c>d` -> `"ad"`) ruled ACCEPT (rare trigger shape, browser-faithful, pre-existing, real fix out of scope under R8). 16 RED tests added (9 unit + 7 integration via real API). B5-fix2 bounced to Next Steps as B5-fix3. Status → qa-fail, current_role → developer, qa_cycles → 3.
- 2026-07-26T08:55Z — Manager: QA cycle 3 accepted (commit clean; 16 RED verified; limitation ruling accepted). Ruling R13: fixpoint sanitization — manager-probed as closing both findings with prose idempotent. Lock → developer; spawning fix3. qa_cycles 3/5 — if cycle 4 bounces again, manager reassesses the criterion rather than looping.
- 2026-07-26T09:00Z — fixpoint sanitizer dev (R13) → ad2185d8e5d6174f5 (sonnet, medium)
- 2026-07-26T09:20Z — Manager: fix3 verified (impl read + own 17-case probe: 0 leaks across 11 attacks incl. nested wrappers, 6 prose byte-exact) + merged @ 0e2877a; 171/171 + 60/60. Lock → qa; spawning QA cycle 4 (final).
- 2026-07-26T09:25Z — QA cycle 4 (final) → a217c7e512ac2578c (sonnet, high)
- 2026-07-26T09:55Z — QA (Sonnet, high), cycle 4 (final): baseline 171/171 backend + 60/60 frontend confirmed clean; 16 cycle-3 RED green, 12 cycle-3 pins unregressed. Adversarial round 4 found one live finding: a 9-element chain of abandoned tags with event-handler attributes needs 9 fixpoint passes to fully resolve but `_MAX_SANITIZE_PASSES` caps the loop at 8, so a value still containing a literal, unclosed, live `<iframe onload=alert(9)` tag is returned — confirmed live via real API on create + comment paths. Mechanism itself sound (no oscillation across 20k fuzzed inputs); the fixed pass ceiling is attacker-guessable. All other cycle-4 probes (wrapper families beyond the element list, comment/CDATA, PI/doctype, entity-reassembly, long multi-paragraph prose) confirmed CORRECT — 15 regression pins added. B5-fix3 bounced to Next Steps as B5-fix4 with 3 RED tests. Status → qa-fail, current_role → developer, qa_cycles → 4.
- 2026-07-26T09:50Z — Manager: QA cycle 4 accepted (commit clean; 3 RED verified live). Defect traced to MANAGER-chosen constant in R13, not developer error. Ruling R14: convergence bound = len(raw)+2, fail-closed to empty; manager-probed at n=9/20/60/400 (0 leaks, prose byte-exact, 0.05s). Lock → developer; spawning fix4. Valve note: qa_cycles will be 5 next — a cycle-5 PASS closes to review normally; a cycle-5 FAIL sets blocked and goes to the director.
- 2026-07-26T09:55Z — convergence-bound dev (R14) → abfa1846d41db91b4 (sonnet, medium)
- 2026-07-26T10:15Z — Manager: fix4 verified (diff read + own probe: chains 5-400 → 0 leaks, wrappers/evasions → 0 leaks, prose byte-exact) + merged @ 21de194; 189/189 + 60/60. Lock → qa; spawning QA cycle 5 (valve cycle).
- 2026-07-26T10:20Z — QA cycle 5 (closing/valve) → afb2938fd3be41368 (sonnet, high)
- 2026-07-26T10:45Z — Manager: QA cycle 5 accepted (commit clean: tests+contract only; perf RED verified; G10 content-safety PASS re-confirmed at all chain lengths). Quadratic blowup manager-reproduced (0.08/0.30/1.18s at n=500/1000/2000). Ruling R15: linearize salvage now; no auto QA cycle 6 (valve honored — manager verification + director sign-off); length cap deferred to director as product decision. Lock → developer; spawning fix5.
- 2026-07-26T10:50Z — linearize-salvage dev (R15) → a1b8baaabfb2fc76d (sonnet, medium)
- 2026-07-26T11:15Z — Manager: fix5 verified (diff read + differential probe vs merged: ZERO prose regressions; 2 differences are both leaks CLOSED — hyphenated/underscored tag names had been leaking in merged code; perf now linear, 5000-tag chain 0.008s) + merged @ e552e58. Evaluator 195/195 + 60/60. Sprint → review; lock released. Independent 4-lens adversarial audit workflow running as closing evidence.
