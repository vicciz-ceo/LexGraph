# Sprint log — 2026-07-30-ratings-grade (append-only)

## Agent roster

- 2026-07-30T20:36Z planner (general-purpose, sonnet high) → agentId a36f5fb67d4d386af
- 2026-07-30T20:50Z dev B1+UI1 (general-purpose, sonnet medium — aggregation/banding + API/UI) → agentId a146f68f7fdfca1eb
- 2026-07-30T20:56Z qa (general-purpose, sonnet high) → agentId abc9df0249c92c859

## Characterization (Planner)

- **Can an author rate their own assertion today?** Yes. `routers/ratings.py::put_rating`
  gates on `_require_permission(..., "assertion:rate")` only — a
  matter-role check, with no author-vs-rater comparison anywhere in
  `ratings.py`. The `contributor` role (which the author of a
  user-submitted assertion always holds, per `services/permissions.py`)
  grants `assertion:rate`. So G3's "whether authors can rate at all
  follows current API rules" resolves to: yes, allowed today, and per the
  gate it must simply not count toward the derived grade.
- **Aggregate shapes today:** `services/ratings.py::compute_rating_summary`
  (pure, ALL ratings incl. author) returns `{count, average, median,
  distribution}` or `None` when empty — already fully implemented despite
  its module docstring's stale "shape only" framing (not this sprint's
  concern). `routers/assertions.py::_ratings_summary` duplicates similar
  math directly (own median/mean, doesn't call the services function) for
  the `ratings_summary` key on `GET /assertions/{id}` — this is the
  existing "team rating" aggregate (shown via
  `AssertionRatingDistribution.tsx`) and is explicitly UNCHANGED by this
  sprint: G3 only says the author's rating must not count toward the new
  derived *standing*, not toward the pre-existing team-rating display.
  Strength bounds: `RatingIn.strength: int = Field(ge=1, le=5)` at
  `ratings.py:96`, already enforced (422) — confirmed still green via
  `test_ratings_api.py::test_rating_below_1_rejected/_above_5_rejected/_non_integer_rating_rejected`.
- **`assertions.py` list/get shapes:** `_serialize_assertion` (line 192)
  is the single serialization function behind create/get/list/patch/
  submit/withdraw — adding a `"standing"` key here surfaces it "wherever
  status is shown" in the API for free. No existing test asserts an
  exhaustive key set on this output (see Stale-pin sweep in the
  contract) — only membership/equality checks on named fields, so this is
  purely additive.
- **`review.py::_apply_decision`:** sets `assertion.status = new_status`
  for accept/reject/dispute/request-revision/supersede and never touches
  `assertion_ratings` (explicit in the module docstring, R9-owned
  boundary). This is exactly the passthrough `compute_standing` needs:
  since none of these statuses is ever "proposed" again, gating
  `compute_standing` on `status == "proposed"` gives G4 (override) for
  free — no changes needed in `review.py` itself, and no new tests
  needed there; the override is proven by hitting the live
  `GET /assertions/{id}` route after a real `/accept`/`/reject` call.
- **`origin` values that actually exist:** `"user_suggested"`
  (`routers/assertions.py:525`, user-authored), `"model_suggested"`
  (`app/enrich/pipeline.py::_MODEL_ORIGIN`, the AI-deduced path — created
  `status="draft"`, reaches "proposed" via the same `/submit` route as
  user-suggested), `"system_generated"` (`app/definition_links/pipeline.py`,
  always created `status="accepted"`, ruling from the prior sprint
  2026-07-30-deterministic-assertions — and it creates NO
  `AssertionRevision` row at all, so these assertions cannot even be
  rated via the API today: `ratings.py::_get_revision_or_404` 404s).
  Net effect: gating `compute_standing` on `status == "proposed"` alone
  (not on `origin`) already satisfies G5 — deterministic assertions are
  never "proposed" and structurally can't collect ratings either way.
- **Frontend status display:** `AssertionCard.tsx` renders
  `humanize(status)` under a "Status" `<dt>/<dd>` row (no existing
  test pins that exact text, only a loose `/proposed/i` match — adding a
  new adjacent field carries no stale-pin risk). `AssertionDetailPanel.tsx`
  renders `Review status: {assertion.status}` inside a
  `<li data-indicator="review-status">` in its existing
  `.assertion-detail-status-indicators` list (same "never merge
  indicators" convention `AssertionRatingDistribution.tsx` already
  follows for team-rating vs. model-confidence). `AssertionReviewPanel.tsx`
  never renders `status` as visible text at all (only reads
  `evidenceStatus` internally) — out of scope for the frontend item.

## Design decision (Planner, not a director/manager ruling — a test-authoring choice)

Field name: **`standing`** (not `grade`), since the mandate's own phrase
is "the assertion's standing is its grade" — `standing` is the
overarching concept (covers both the unrated "proposed" state and the
rated/banded state), so it is the one API/prop field name across both
the "still proposed" and "now graded" cases, and it also cleanly covers
G4/G5 (an accepted/rejected/etc. assertion's `standing` is just its
`status`). Backend home: `app.services.ratings` (co-located with
`compute_rating_summary` per ruling R3's own text). New pure functions:
`band_for_median(median: float) -> str` and `compute_standing(status: str,
ratings: list[dict], author_user_id: str) -> str` where each `ratings`
item is `{"user_id": ..., "strength": ...}`. Frontend: `standing: string`
field on `AssertionCardData`/`AssertionDetailSummary`, rendered via
`data-testid="assertion-standing"` (AssertionCard, no existing indicator
convention there) and a `data-indicator="standing"` sibling `<li>`
(AssertionDetailPanel, matching its existing `data-indicator="..."`
convention). None of this is an ESCALATION-level ambiguity — R3 already
settled the mechanism (derived, read-time, alongside `status`); only the
concrete names needed picking, and the Developer is free to rename with
a same-commit test update if a better name surfaces during implementation.

## Baseline (before any new tests)

`backend/.venv/bin/pytest backend/tests -q` → 424 passed.
`npm --prefix frontend run test -- --run` → 62 passed (11 files).

## RED confirmation (after new tests, before commit)

`backend/.venv/bin/pytest backend/tests -q --continue-on-collection-errors`
→ 424 passed (unchanged), 11 failed (all `KeyError: 'standing'` in
`test_assertion_standing_api.py`), 1 error (`test_standing_grade.py`,
`ImportError: cannot import name 'band_for_median'` — documented
exception, pinning not-yet-written functions).

`npm --prefix frontend run test -- --run` → 62 passed (unchanged), 7
failed (4 in `AssertionCard.test.tsx` — `TestingLibraryElementError:
Unable to find an element by: [data-testid="assertion-standing"]`; 3 in
`AssertionDetailPanel.test.tsx` — null/non-Node `querySelector` result).
All RED for the right reason; no import/collection errors on the
frontend side (both components already exist).

## GREEN confirmation (Developer)

Implementation: `app.services.ratings.band_for_median`/`compute_standing`
(pure, co-located with `compute_rating_summary`); a new
`_rating_pairs_for_revision` helper in `routers/assertions.py` (user_id +
strength, since the pre-existing `_rating_strengths_for_revision` only
returns bare strengths and `compute_standing` needs to exclude the
author's own rating); `_serialize_assertion` now emits `"standing"`
alongside the untouched `"status"`. Frontend: `standing?: string` added
to `AssertionCardData`/`AssertionDetailSummary` (optional, falling back
to `status`, so pre-sprint fixtures without the field keep working);
`AssertionCard` renders it in a new meta row only when `standing` is
provided (`data-testid="assertion-standing"`) — guarding on presence
avoids a duplicate-text collision with the pre-existing
`getByText(/proposed/i)` assertion in `AssertionCard.test.tsx`'s first
test, whose `baseAssertion` fixture has no `standing` field;
`AssertionDetailPanel` always renders a `data-indicator="standing"`
sibling `<li>` (no such collision risk there — its tests use
`querySelector`/`toHaveTextContent`, not `getByText`).

Scoped: `backend/.venv/bin/pytest backend/tests/unit/test_standing_grade.py
backend/tests/integration/test_assertion_standing_api.py -q` → 33 passed
(22 + 11). `npm --prefix frontend run test -- --run
src/components/__tests__/AssertionCard.test.tsx
src/components/__tests__/AssertionDetailPanel.test.tsx` → 18 passed (10 +
8).

Full authoritative pass: `backend/.venv/bin/pytest backend/tests -v` →
457 passed, 0 failed. `npm --prefix frontend run test -- --run` → 69
passed (11 files), 0 failed (only pre-existing, unrelated `act(...)`
console warnings from `AssertionRatingWidget`, not a failure).

No test files touched; no pinned name deviated from (`standing`,
`band_for_median`, `compute_standing` implemented exactly as specified).
No escalations. Commit `5aaca94` (feat, B1+UI1), pushed.

## QA (independent verification, cycle 1)

Repo confirmed at expected HEAD `42dd903`, branch
`sprint/2026-07-30-ratings-grade`, clean tree except the roster-append
line above (bootstrap bookkeeping, not mine).

**R3 check:** `git diff 7dd3a27..5aaca94 -- backend/app/models` → empty.
`git diff --stat 7dd3a27..5aaca94` → only `assertions.py`, `ratings.py`,
`AssertionCard.tsx`, `AssertionDetailPanel.tsx` touched (93 insertions,
0 deletions) — no schema migration, no `status` mutation, no persisted
`standing` column.

**Code read:** `compute_standing`/`band_for_median`
(`backend/app/services/ratings.py:63-99`) match the contract's pinned
design exactly. `_serialize_assertion` (`backend/app/routers/assertions.py:193-231`)
emits `"standing"` via `compute_standing(a.status, ratings, a.author_user_id)`,
`ratings` from the new `_rating_pairs_for_revision` (carries `user_id`,
unlike the pre-existing bare-strength `_rating_strengths_for_revision`).
Confirmed `_serialize_assertion` backs every one of create (605), submit
(759), get (790), patch (859), revisions (882), withdraw (898), and list
(700, one call per row) — "standing" is on every response for free, list
included.

**Live-path probe (Developer's `test_assertion_standing_api.py`,
233 lines, 12 tests, real `TestClient`):** G1 (proposed/zero outside
ratings), G2 (single outside ratings of 2/3/4 → weak/probable/strong,
PLUS the two-rating fractional-median cases 2+3→2.5→weak and 3+4→3.5→
strong — R4's exact edges both covered), G3 (author's own 5/5 alone
stays "proposed"), G4 (accept AND reject both override an already-"strong"
grade to the decision's status), G5 (real `run_definition_linking`
pipeline, `system_generated` assertions read back `standing == status ==
"accepted"` via the live GET route), plus an edge case (deleting the only
outside rating reverts `standing` to "proposed"). All hit real routes, no
mocks of the acceptance target. Confirmed via `git diff e702460..5aaca94`
(RED commit to GREEN commit) that none of these test files were touched
after being written RED — no weakening.

**Render-guard scrutiny (UI1):** `AssertionCard.tsx:104`
(`{standing != null && (...)}`) only omits the standing row when
`standing` is absent. Searched `frontend/src` for any file other than
`AssertionCard.tsx`/`AssertionDetailPanel.tsx` and their own test files
referencing either component — none found. This frontend has no
App/page/container/data-fetch layer at all (pure component library,
11 components + 11 test files, nothing else) — there is no code path
today that maps a real API response into `AssertionCardData` and could
be affected by the guard. The guard exists solely to avoid a
`getByText(/proposed/i)` collision with the pre-existing `baseAssertion`
fixture (no `standing` field) in `AssertionCard.test.tsx`'s first,
pre-sprint test. `AssertionDetailPanel.tsx:189` never guards
(`assertion.standing ?? assertion.status`, always renders). Since the
live backend always emits `standing` (see above), a future real
consumer would always receive it — not a live-path FAIL today.

**Evaluator (full, from repo root):**
```
backend/.venv/bin/pytest backend/tests -v
======================= 457 passed, 10 warnings in 7.15s =======================
EXIT:0

npm --prefix frontend run test -- --run
 Test Files  11 passed (11)
      Tests  69 passed (69)
EXIT:0
```
Matches expected ~457/69 exactly. No untouched-file timeouts observed;
flake protocol not invoked.

**Regression gaps identified and closed** — none of the four scenarios
below were covered by any existing test (backend or frontend), all now
in `backend/tests/integration/test_qa_regression_ratings_grade.py`
(new file, 4 tests, all live `TestClient` routes):

1. `test_list_assertions_route_carries_standing_for_every_row` — every
   existing standing assertion reads a single `GET /assertions/{id}`;
   nothing ever read `"standing"` off `GET /assertions?matter_id=...`
   (list route), which serializes each row through the same
   `_serialize_assertion` but via a different call site (line 700).
2. `test_authors_rating_of_5_excluded_when_outsider_rates_1_grade_is_weak_not_probable`
   — the existing G3 test only has the author rate (alone); the
   author-excluded-from-median math is proven at the unit level
   (`compute_standing` called directly) but never through the live
   PUT-rating router + real DB round trip with BOTH an author and an
   outside rating present together. If the author's rating leaked in
   via a router-wiring bug (not a `compute_standing` bug), median([5,1])
   = 3 → "probable"; correctly excluding it, median([1]) = 1 → "weak".
   This test distinguishes the two outcomes on the live path.
3. `test_rating_strength_overwrite_recomputes_standing_grade` — no test
   ever PUT the same user's rating twice (upsert branch in
   `routers/ratings.py::put_rating`, `existing is not None`) and
   re-checked `standing` afterward; only the `AssertionRating` row
   change itself is proven elsewhere.
4. `test_withdrawn_assertion_standing_is_withdrawn_even_with_an_existing_high_rating`
   — `withdraw_assertion` sets `status = "withdrawn"` directly (no
   `_apply_decision` call, a code path distinct from accept/reject),
   never exercised against an already-graded ("strong") assertion.

Verified each test is not vacuous: temporarily reverted
`compute_standing`'s author-exclusion filter (`ratings if r["user_id"]
!= author_user_id` → `ratings`, i.e. author no longer excluded) and
re-ran the new suite — test 2 failed exactly as predicted
(`AssertionError: assert 'probable' == 'weak'`), the other 3 stayed
green (they don't exercise that exact combination). Reverted via the
saved original file content; `git diff backend/app/services/ratings.py`
confirmed empty afterward (no residual sabotage).

Full suite with regression tests added: `backend/.venv/bin/pytest
backend/tests -v` → **461 passed**, 0 failed (457 + 4 new). Frontend
unchanged, 69 passed.

No deviations from the brief. No escalations. Verdict: PASS, both B1
and UI1 move to Completed. `qa_cycles: 1`. Commit
`test: QA regression … (sprint/2026-07-30-ratings-grade)`, pushed.
