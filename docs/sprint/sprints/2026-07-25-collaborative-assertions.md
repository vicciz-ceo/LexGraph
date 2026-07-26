---
id: "2026-07-25-collaborative-assertions"
status: qa-fail
current_role: developer
branch: sprint/2026-07-25-collaborative-assertions
locked_by: "claude-code:developer"
locked_at: "2026-07-26T07:55:00Z"
last_agent: "claude-code:qa"
last_updated: "2026-07-26T07:40:00Z"
lint: "PASS 185 2026-07-25T20:24:02Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 12
completed_items: 11
dev_complete_items: 0
qa_cycles: 2
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
- R11 UI2 escalation ruling (QA cycle 1): submit-for-review must be disabled whenever the proposition is empty, regardless of similar-assertion warnings; exact duplicate always disables. The Planner test that asserts enabled without typing a proposition is a test bug — Planner-role micro-fix types a proposition there and adds a RED test pinning disabled-when-empty-despite-similars; a Haiku Developer then simplifies the formula to `hasExactDuplicate || propositionMissing`.
- R12 Sanitizer architecture (manager ruling, QA cycle 2): STOP patching regexes. Two rounds of regex whack-a-mole (unclosed tags, then `/`-separated attributes) plus a benign-prose corruption bug show a regex tag-stripper is the wrong tool: it must decide what a browser would parse, which only a parser can do. Replace `sanitize_for_storage`'s regex internals with a real HTML tokenizer — Python stdlib `html.parser.HTMLParser` (no new dependency; `nh3`/`bleach` acceptable if the developer prefers and it installs cleanly). Required semantics: (a) text that a browser would parse as a tag is dropped (with `<script>`/`<style>` element CONTENT dropped too); (b) text a browser would render as literal text — `a<b`, `5 < 10`, `amount is < $500 ... term is > 10 years` — survives BYTE-EXACT (spec §2 "stored as authored"); (c) no HTML-escaping of quotes/ampersands/dashes. Public signature and call-sites unchanged.
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

- [QA-FAIL: B5, cycle 2] Cycle-1's fix closed the with-space unclosed-tag
  bypass but two new gaps remain in `sanitize_for_storage`
  (`backend/app/services/validation.py`): (1) no-space-before-attribute
  bypass — `<img/onerror=alert(1)` / `<svg/onload=...` survive verbatim
  because `_UNCLOSED_TAG_RE` requires `\s+` before every attribute, but
  a `/` right after the tag name puts real browsers into
  self-closing-start-tag state and the next text is reconsumed as a
  live attribute anyway (documented OWASP evasion shape); confirmed live
  across create/PATCH/revisions/comments/rating-rationale (shared
  function). (2) `_TAG_RE = r"<[^>]+>"` corrupts benign prose containing
  both a `<` and a later unrelated `>` (e.g. "amount is < $500 ... term
  is > 10 years" loses the text between them) — pre-existing, violates
  spec §2 "stored exactly as authored". RED tests (required behavior,
  not the bug): `backend/tests/unit/test_validation.py::{
  test_sanitize_neutralizes_unclosed_tag_with_no_space_before_attribute,
  test_sanitize_neutralizes_unclosed_svg_with_no_space_before_attribute,
  test_sanitize_preserves_prose_with_less_than_and_later_unrelated_greater_than,
  test_sanitize_preserves_prose_with_multiple_unrelated_comparisons}`,
  `backend/tests/integration/test_hostile_input.py::{
  test_proposition_no_space_slash_bypass_is_neutralized,
  test_patch_proposition_no_space_slash_bypass_is_neutralized,
  test_proposition_preserves_legit_text_with_lt_and_later_unrelated_gt}`.

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

(empty — B3-fix and UI2-fix verified PASS and moved to Completed; B5-fix bounced back to Next Steps, cycle 2)

## Completed

- F1 — 13 ORM models + constraints. Verdict: PASS. Probe: full suite (all integration tests persist/read through these tables). Regression: none needed (pre-existing coverage sufficient).
- B1 — assertion CRUD/evidence/revisions. Verdict: PASS (own scope). Probe: `test_assertions_crud.py` 24/24 green via real API; PATCH-sanitization gap in this file is attributed to B5 per spec-ownership (see Next Steps). Regression: none added here.
- B2 — ratings + aggregates. Verdict: PASS. Probe: `test_ratings_api.py` + `test_ratings_aggregate.py` all green; DELETE audit direct call and PUT audit via middleware both confirmed via live API + raw-SQL. Regression: none needed.
- B3-fix (cycle 2) — evidence add/remove audit rows via `audit_middleware.py` (commit `9d179f2`). Verdict: PASS. Probe: independent raw-SQL count before/after (1→2→3), rows carry ids only (no quote/document text; existing `test_audit_events_have_no_full_document_content` covers this), actor/matter/assertion/correlation_id all correct. Regression: none needed (existing RED-turned-green test + no-leak test sufficient).
- B4 — review workflow + permissions. Verdict: PASS. Probe: permission matrix 19/19 + accept/reject/dispute/request-revision live via API; supersede endpoint had zero prior coverage — now proven live (accept, permission-denied, cross-matter-successor-rejected). Regression: `test_review_workflow.py::test_reviewer_can_supersede_with_assertion_in_same_matter` (+`test_contributor_cannot_supersede`, `test_supersede_rejects_successor_from_another_matter`).
- B6 — graph projection + notifications. Verdict: PASS. Probe: G7 default/show-unreviewed views + matter isolation confirmed via `test_graph_projection*.py`; notification recipient-derivation confirmed matter-scoped via live cross-matter API probe (real reviewer-on-a-different-matter never sees another matter's notification). Regression: `test_notifications.py::test_reviewer_of_another_matter_does_not_see_this_matters_submission_notification`.
- B7 — matter isolation + hostile-input wiring + sanitization wiring (comments, rating rationales) + graph evidence_count. Verdict: PASS. Probe: `test_matter_isolation.py` + `test_hostile_input.py` (original) all green; comments.py/ratings.py both correctly call `sanitize_for_storage` at create AND edit — the unclosed-tag bypass that also reproduces through these call sites is B5's function bug, not a B7 wiring gap. Regression: none added here (see B5 Next-Steps RED tests).
- E1 — 10-step contributor→rater→reviewer→graph e2e. Verdict: PASS. Probe: `test_full_flow.py` full 10-step flow green against the real API (Playwright browser-E2E remains a documented Planner deferral for G12 — not added, per brief "optional, only if quick").
- UI1 — AssertionCard + AssertionRatingWidget + AssertionRatingDistribution. Verdict: PASS. Probe: `AssertionRatingWidget.tsx` uses a proper roving-tabindex `role="radiogroup"` with Arrow/Home/End nav + `aria-checked`/`aria-label` per option (gate G11); own suite 19/19. Regression: none needed.
- UI3 — 6 workspace/review/discussion/history components. Verdict: PASS. Probe: own suite 27/27; explanatory "individual opinions, not legal conclusions" text present (`AssertionDetailPanel.tsx`, `AssertionCard.tsx`). Regression: none needed.
- UI2 + UI2-fix (R11, cycle 2) — AssertionSuggestionForm + AssertionEvidenceSelector; `submitDisabled` formula fixed to `hasExactDuplicate || propositionMissing` (1 line, commit `9d5aa3e`, merged `2345b88`) resolving cycle-1's ESCALATION per ruling R11. Verdict: PASS. Probe: own suite 8/8 green incl. new pin `submit stays disabled when proposition is empty even with similar assertions present`; formula in `AssertionSuggestionForm.tsx` read and matches R11 exactly. Regression: none needed.

## Evaluation Notes

2026-07-26T05:40Z (manager, dev-phase close): full evaluator on merged tree `c2f2b02` — backend 126/126, frontend 59/59 (185/185). All 12 items in Dev Complete. Known QA-attention flags: UI2 submit-disabled semantics; regex-sanitizer edge cases; PATCH-path proposition sanitization; evidence attach accepts unresolvable span ids (pinned by B1 test); withdraw allowed from any status; notifications store is in-process per R4 (restart-volatile, documented MVP limit).

## QA Notes

2026-07-26T06:10Z (QA, Sonnet high, cycle 1): Independent evaluator: backend 126/126, frontend 59/59 baseline confirmed, no flakes. 10/12 items PASS → Completed; 2 bounced (B3, B5 — see Next Steps `[QA-FAIL: ...]`), both with committed RED tests reproducing the required behavior via the real API. Attention-list a-f: (a) UI2 formula — genuine test/spec tension, see ESCALATION below, not failed; (b)(c) sanitizer bugs confirmed live → B5 FAIL (2 findings); (d) unresolvable evidence span id → 201 confirmed as documented limitation (resolvable foreign-matter spans correctly 422, `test_evidence_from_inaccessible_matter_cannot_be_attached`); (e) withdraw from `accepted` → 200/allowed, confirmed live; spec §13 is silent on preconditions so recorded as a documented limitation per brief guidance (note: spec §1 bullet 5's "withdraw their own unreviewed assertions" phrasing is in mild tension with this — flagging for awareness, not blocking); (f) notification matter-scoping confirmed correct live (cross-matter reviewer never sees another matter's notification), restart-volatility remains a documented MVP limit. New finding beyond the attention list: evidence add/remove produce zero audit_events rows (spec §16 / gate G8) → B3 FAIL. Added 4 passing regression tests (supersede flow x3, notification cross-matter x1) and 6 RED tests (sanitizer x4, PATCH-sanitization x1, evidence-audit x1) — see Completed/Next-Steps entries for exact names.

ESCALATION: UI2's `submitDisabled = hasExactDuplicate || (propositionMissing && similarAssertions.length === 0)` lets an empty proposition through whenever `similarAssertions` is non-empty. The Planner's own test at `AssertionSuggestionForm.test.tsx:56-66` ("warns (without blocking)...") never types a proposition yet asserts submit is NOT disabled — so it directly pins this exact empty+similar-list combination as intended-enabled, contradicting `AssertionSuggestionForm.test.tsx:27-30` ("requires the user to enter a proposition...", empty+no-similars => disabled) and reading of spec §7 ("submitting an EMPTY proposition should never be possible"). Per brief instruction I did not edit either test or the component. Options: (1) fix the test to type a matching proposition before asserting enabled, and change the formula to `hasExactDuplicate || propositionMissing` (always required) — my lean, since it's the only version consistent with spec §7's absolute wording; (2) accept current behavior as intentional (a near-duplicate warning fully waives the empty-proposition guard) and update spec/QA-brief expectations instead. Not gate-breaking today because `validate_proposition_not_empty` still rejects blank propositions server-side (defense in depth) — no accepted-order bug reaches storage.

RESOLVED (R11, cycle 2): formula fixed to `hasExactDuplicate || propositionMissing`; confirmed matching in cycle-2 QA (see QA Notes below and Completed/UI2 entry).

2026-07-26T07:40Z (QA, Sonnet high, cycle 2): Independent evaluator: backend 136/136, frontend 60/60 baseline confirmed before any new tests. B3-fix PASS (raw-SQL count 1→2→3 add/remove, ids-only, actor/matter/assertion correct). UI2-fix PASS (8/8 own suite; formula in `AssertionSuggestionForm.tsx` reads `hasExactDuplicate || propositionMissing`, exact R11 match). B5-fix FAIL, new findings beyond the cycle-1 shapes: (1) no-space-before-attribute bypass `<img/onerror=...` / `<svg/onload=...` (real OWASP evasion shape — HTML5 tokenizer treats `/` after tag name as self-closing-start-tag then reconsumes following text as a live attribute) survives verbatim, confirmed live across create/PATCH/revisions/comments/rating-rationale (shared `sanitize_for_storage`); (2) `_TAG_RE`'s naive first-`>` matching corrupts benign prose with an unrelated later `>` (e.g. "amount < $500 ... term > 10 years" loses the middle) — pre-existing, violates spec §2. Benign single/double-quoted-attribute and bare-`<tag`-no-attrs cases confirmed still correct (not regressed). Added 7 RED tests (4 unit + 3 integration) pinning required behavior for both findings, plus 4 regression pins for already-correct adjacent paths (revisions/comment-edit/rating-update unclosed-tag, one quoted-attribute unit case) that lacked dedicated coverage. Full suite after additions: 140 backend passed + 7 RED (147 total) + 60 frontend green.

Greenfield repo, Planner pass complete. Scaffolding + 185 RED tests
committed (backend FastAPI/SQLAlchemy, frontend Vite/Vitest/RTL — see
"Scaffolding already committed" above). Developer: start with item F1
(sequential gate), then any of B1-B7/UI1-UI3 in parallel per the plan
above; E1 last. Deviation: python@3.12 unavailable locally — backend
venv built with python3.13 (R1 pin was 3.12; functionally compatible).
