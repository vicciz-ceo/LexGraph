---
id: "2026-07-30-ratings-grade"
status: planned
current_role: developer
branch: sprint/2026-07-30-ratings-grade
locked_by: "claude-code:planner"
locked_at: "2026-07-30T20:35:12Z"
last_agent: "claude-code:planner"
last_updated: "2026-07-30T21:10:00Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 2
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
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

- [ ] **B1 — Derived standing/grade, exposed via the assertions API.**
  New pure functions in `backend/app/services/ratings.py` (co-located per
  R3's own text): `band_for_median(median: float) -> str` (weak <3,
  probable ==3, strong >3 — R4's fractional edges 2.5/3.5 included) and
  `compute_standing(status: str, ratings: list[dict], author_user_id:
  str) -> str` (non-"proposed" statuses pass through unchanged — this
  covers both G4's reviewer override and G5's born-accepted deterministic
  assertions in one rule; "proposed" excludes the author's own rating
  (G3) and returns "proposed" with none left (G1), else bands the
  outside-only median (G2)). Wire into
  `backend/app/routers/assertions.py::_serialize_assertion` as a new
  `"standing"` key (needs a revision-scoped, user_id-carrying query —
  `_rating_strengths_for_revision` only returns bare strengths today, not
  who rated) — this key then appears on every response that already
  includes `"status"` (create/get/list/patch/submit/withdraw), satisfying
  "visible via the assertions API" for free. Do NOT touch `status` itself
  (stays exactly as today; `test_ratings_api.py::test_high_aggregate_rating_does_not_change_review_status`
  already pins that and is unchanged). Unauthorized-rater (403) and
  invalid-strength (422) paths are already pinned by
  `test_ratings_api.py` — no new tests needed there. RED tests: `backend/tests/unit/test_standing_grade.py`
  (22, ImportError — documented exception), `backend/tests/integration/test_assertion_standing_api.py`
  (11, live TestClient routes, KeyError on the missing `"standing"` key).

- [ ] **UI1 — Standing (grade band) display in `AssertionCard` /
  `AssertionDetailPanel`.** Add a `standing` field to
  `AssertionCardData`/`AssertionDetailSummary` (alongside the unchanged
  `status`) and render it: `AssertionCard` gets a new
  `data-testid="assertion-standing"` element; `AssertionDetailPanel`
  gets a new sibling `<li data-indicator="standing">` next to its
  existing `data-indicator="review-status"` line (same convention, same
  overview-tab indicator list — spec §5 never merges separate
  indicators). `AssertionReviewPanel` renders no status text today (only
  reads `evidenceStatus` internally) — out of scope, nothing to change.
  RED tests (real component renders, no mocks): `AssertionCard.test.tsx`
  (+4), `AssertionDetailPanel.test.tsx` (+3) — all fail today on a
  missing element/null querySelector, never an import error.

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

## Evaluation Notes

## QA Notes

## Context Dump

- Sprint opened 2026-07-30 after director confirmed grading semantics.
  Prior sprint (deterministic-assertions) closed done; ratings service
  already aggregates 1-5 strengths (average/median/distribution);
  assertion status transitions currently happen only in routers/review.py.
