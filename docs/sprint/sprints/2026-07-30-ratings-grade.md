---
id: "2026-07-30-ratings-grade"
status: review
current_role: planner
branch: sprint/2026-07-30-ratings-grade
locked_by: null
locked_at: null
last_agent: "claude-code:qa"
last_updated: "2026-07-30T21:05:19Z"
lint: "PASS 170 2026-07-30T21:05:20Z"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 2
completed_items: 2
dev_complete_items: 0
qa_cycles: 1
previous_sprint: "2026-07-30-deterministic-assertions"
prd_sections: []
design_sections: []
---

# Sprint: Ratings-driven grade — proposed until rated, then weak/probable/strong

## Mandate (director, 2026-07-30)

"Proposed" covers user-submitted AND AI-deduced assertions until they are
rated by other users; a rated assertion carries a 1-5 grade
(weak-probable-strong) instead. Director confirmed via batched gate
questions: (a) first rating by a non-author user ends "proposed"; (b) grade
= median of ratings, banded weak (1-2) / probable (3) / strong (4-5);
(c) the reviewer accept/reject workflow stays and overrides the grade.

## Acceptance gates (manager-defined, director-confirmed)

- **G1 — Proposed until rated:** a proposed assertion (user-submitted or
  AI-deduced) with zero ratings from non-author users still presents as
  "proposed" everywhere it is shown.
- **G2 — Grade after first outside rating:** once ≥1 non-author user has
  rated it, the assertion's standing is its grade — median strength banded
  weak (1-2) / probable (3) / strong (4-5) — visible via the assertions
  API and in the frontend wherever status is shown today.
- **G3 — Author ratings don't count:** the author's own rating never moves
  an assertion out of "proposed" (whether authors can rate at all follows
  current API rules — Planner characterizes; if currently allowed, it
  simply doesn't count toward G2).
- **G4 — Reviewer override intact:** explicit reviewer decisions
  (accept/reject/dispute/…) keep working unchanged and take precedence
  over the grade presentation.
- **G5 — Deterministic assertions untouched:** origin=system_generated
  assertions stay born-accepted (previous sprint) and never enter the
  proposed→grade flow.
- **G6 — Suites green:** full backend + frontend suites pass.

## Manager rulings

- R1: Sprint branch based on `main` @ 13c3484 (includes PR #13).
- R2: Scope is the LexGraph app only — the POC builder emits deterministic
  (accepted) assertions and has no ratings surface.
- R3: Manager lean, Planner may confirm or escalate with evidence: the
  grade/standing is DERIVED at read time from existing AssertionRating
  rows (services/ratings.py already computes median + distribution) and
  exposed as a field alongside `status` — no schema migration, no
  persisted status mutation on rating. Any schema/migration alternative is
  an ESCALATION, not a Planner decision.
- R4: "weak"/"probable"/"strong" are the only band names; band edges are
  weak ≤2, probable =3, strong ≥4 (median may be fractional, e.g. 2.5 —
  Planner pins the edge rule in tests: weak <3, probable =3, strong >3;
  fractional medians between 3 and 4 exclusive of 3 count per that rule —
  i.e. 3.5 → strong; 2.5 → weak).

## Next Steps

## Stale-pin sweep

Roots checked: `backend/tests/unit/`, `backend/tests/integration/`,
`backend/tests/e2e/`, `frontend/src/components/__tests__/*.test.tsx`.
Greps run: `grep -rn "toMatchSnapshot"` (none); `grep -rn "json() ==\|body ==\|result =="`
over backend tests (only unrelated string-equality assertions in
`test_validation.py`/`test_ratings_aggregate.py`, and
`test_notifications.py:78`'s unrelated `r.json() == []` for the
notifications endpoint); `grep -rn "Object.keys\|\.keys()"` over frontend
tests (no hits); `grep -rniE "\bstanding\b|\bgrade\b|\bweak\b|\bprobable\b|\bstrong\b"`
across all four roots (only unrelated prose/rationale-text hits — e.g.
`test_validation.py:474`'s "standing alone" case-law quote,
`rationale: "Strong support."` fixtures in several ratings/hostile-input
tests, `AssertionRatingWidget.test.tsx`'s per-star "very weak"/"very
strong" radio labels).

**none** — no test in this repo asserts an exhaustive/exact key set on
the assertion serialization (`_serialize_assertion`'s output is always
checked by individual `in`/`==` membership on named fields, e.g.
`test_assertions_crud.py::test_get_assertion_returns_full_shape`), and no
existing test's wording collides with the new `standing`/`weak`/
`probable`/`strong` vocabulary in a status-display sense. Adding the
`standing` field is purely additive; nothing needs re-pointing.

## Dev Complete

## Completed

- [x] **B1 — Derived standing/grade, exposed via the assertions API.**
  QA-verified (independent pass, commits 5aaca94/ea6bd43): `backend/app/services/ratings.py`
  (`band_for_median`, `compute_standing`), `backend/app/routers/assertions.py`
  (`_rating_pairs_for_revision`, `_serialize_assertion` now emits
  `"standing"` on every response — create/get/list/patch/submit/withdraw,
  confirmed by reading every `_serialize_assertion(...)` call site). R3
  confirmed: `git diff 7dd3a27..5aaca94 -- backend/app/models` is empty
  (no schema/model change); `status` column never mutated by rating flows;
  `standing` is derived at read time only, never persisted. Live-path
  G1-G5 confirmed via `test_assertion_standing_api.py` (real `TestClient`
  routes, no mocks) plus this cycle's own regression suite,
  `backend/tests/integration/test_qa_regression_ratings_grade.py` (4
  tests, all live-path): list route (`GET /assertions?matter_id=...`)
  carries `standing` per-row (not just single-GET); author-rating
  exclusion (G3) proven through the real PUT-rating route, not just the
  unit-tested pure function (author rates 5, outsider rates 1 → "weak",
  never the leaked-median "probable"); a PUT-overwrite (same rater, new
  strength) recomputes the derived grade; `withdraw_assertion` (a code
  path distinct from `_apply_decision`) overrides an existing "strong"
  grade to `"withdrawn"`. Full evaluator: backend 461 passed (457 + 4
  new), frontend 69 passed, 0 failures, 0 flakes.
- [x] **UI1 — Standing (grade band) display in `AssertionCard` /
  `AssertionDetailPanel`.** QA-verified: `frontend/src/components/AssertionCard.tsx`
  (`data-testid="assertion-standing"`, guarded on `standing != null`),
  `frontend/src/components/AssertionDetailPanel.tsx`
  (`data-indicator="standing"`, unconditional `?? status` fallback,
  never guarded). Render-guard scrutiny: `AssertionCard`'s guard exists
  only to avoid a `getByText(/proposed/i)` collision with a pre-existing
  synthetic fixture (`baseAssertion` in `AssertionCard.test.tsx`) that
  predates this sprint and has no `standing` field; the live backend API
  always emits `standing` (see B1 above), and this frontend codebase has
  no page/container/data-fetch layer wiring the real API response into
  `AssertionCardData` yet (`frontend/src/` is component-library-only —
  `AssertionCard`/`AssertionDetailPanel` are referenced nowhere outside
  their own files and tests) — so the guard cannot hide a grade on any
  real app data path today. No test was weakened between the RED commit
  (e702460) and the GREEN commit (5aaca94): `git diff e702460..5aaca94 --
  <test files>` is empty. `AssertionCard.test.tsx` (+4) and
  `AssertionDetailPanel.test.tsx` (+3) green.

## Evaluation Notes

- Scoped: `backend/tests/unit/test_standing_grade.py` +
  `backend/tests/integration/test_assertion_standing_api.py` → 33
  passed. Frontend `AssertionCard.test.tsx` +
  `AssertionDetailPanel.test.tsx` → 18 passed.
- Full authoritative pass (Developer): backend `pytest backend/tests -v`
  → 457 passed, 0 failed. Frontend `npm run test -- --run` → 69 passed
  (11 files), 0 failed.
- Full authoritative pass (QA, includes 4 new regression tests): backend
  `pytest backend/tests -v` → 461 passed, 0 failed. Frontend unchanged →
  69 passed (11 files), 0 failed. Raw logs → `-log.md`.

## QA Notes

- 2026-07-30T21:02:28Z — QA cycle 1, independent pass. Verdict: **PASS**
  (B1, UI1). Evaluator: backend 461 (457+4 new), frontend 69, 0 fail, 0
  flake. Live-path G1-G5 via real `TestClient`. R3 confirmed: model diff
  empty, `status` untouched, `standing` never persisted. Render-guard
  safe (no real data-fetch path in this frontend yet; API always emits
  `standing`). 4 regression tests added, RED-verified
  (`test_qa_regression_ratings_grade.py`). No deviations/escalations.
  Full transcript → `-log.md`.

## Context Dump

- Sprint opened 2026-07-30 after director confirmed grading semantics.
  Prior sprint (deterministic-assertions) closed done; ratings service
  already aggregates 1-5 strengths (average/median/distribution);
  assertion status transitions currently happen only in routers/review.py.
