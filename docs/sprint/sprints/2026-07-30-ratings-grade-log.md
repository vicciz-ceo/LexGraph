# Sprint log — 2026-07-30-ratings-grade (append-only)

## Agent roster

- 2026-07-30T20:36Z planner (general-purpose, sonnet high) → agentId a36f5fb67d4d386af

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
