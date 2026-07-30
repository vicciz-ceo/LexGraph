"""QA regression coverage — sprint 2026-07-30-ratings-grade, item B1
(`app.services.ratings.compute_standing`/`band_for_median`, wired into
`app.routers.assertions._serialize_assertion` as the new `"standing"` key).

Independent QA pass (separate agent from the Developer of commits
5aaca94/ea6bd43). The Developer's own `test_assertion_standing_api.py`
already exercises G1-G5 thoroughly via the live `TestClient`, but four
live-path scenarios implied by the gates are never actually hit by any
existing test, backend or frontend:

- Every existing "standing on the API" assertion reads a single
  `GET /assertions/{id}` response. `GET /assertions?matter_id=...`
  (`list_assertions`) shares the same `_serialize_assertion` function, but
  no test ever reads `"standing"` off a *list* response -- a regression
  that broke it only for the list branch (e.g. a future refactor that
  special-cased list serialization) would go unnoticed.
- `test_authors_own_rating_does_not_grade_standing` only has the author
  rate (alone) -- it never combines an author rating with an outside
  rating through the *live* PUT-rating route. The pure-function unit test
  `test_proposed_with_authors_rating_plus_one_outside_rating_grades_on_outside_only`
  covers the math in isolation, but nothing proves `_rating_pairs_for_revision`
  actually threads the right `user_id` through the real router/DB path --
  a wiring bug there (e.g. swapped columns) could pass every existing test
  while still leaking the author's rating into the live-computed grade.
- No test ever overwrites an existing rating (PUT again, same user) and
  re-checks `standing` -- `put_rating`'s upsert branch (`existing is not
  None`) is only proven to update the `AssertionRating` row itself
  elsewhere (`test_ratings_api.py`), never proven to flow through to a
  changed `standing` on a subsequent GET.
- No test ever withdraws an assertion that already carries ratings and
  checks `standing` afterwards -- G4's passthrough is proven for
  accept/reject only; `withdraw_assertion` sets `status = "withdrawn"`
  through a different code path (no `_apply_decision` call) and is never
  exercised against a *graded* assertion.

All four tests below hit real routes via `TestClient` (`client` fixture),
no mocks.
"""

from __future__ import annotations

from tests.conftest import assertion_payload, rating_payload


def _create_submitted_assertion(client, m, proposition=None):
    # Create-time duplicate detection (409) rejects a second identical
    # proposition in the same matter -- each assertion in a multi-assertion
    # test needs its own distinct text.
    overrides = {"save_as": "draft"}
    if proposition is not None:
        overrides["proposition"] = proposition
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], **overrides),
        headers=m["contributor_headers"],
    )
    body = create.json()
    assert "id" in body, f"create failed: {create.status_code} {body}"
    client.post(f"/api/v1/assertions/{body['id']}/submit", headers=m["contributor_headers"])
    return body["id"], body.get("current_revision_number", 1)


def _rate(client, assertion_id, rev, headers, strength):
    r = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        json=rating_payload(strength=strength),
        headers=headers,
    )
    assert r.status_code in (200, 201), r.text
    return r


def _get(client, assertion_id, headers):
    return client.get(f"/api/v1/assertions/{assertion_id}", headers=headers).json()


def test_list_assertions_route_carries_standing_for_every_row(client, matter_with_users):
    """G1+G2 via `GET /assertions?matter_id=...`, not just single-GET.

    Three assertions in one matter, at three different standings, all read
    back off ONE list response.
    """
    m = matter_with_users

    unrated_id, _ = _create_submitted_assertion(
        client, m, proposition="Clause 3.1 imposes a 30-day notice period before termination."
    )

    graded_id, graded_rev = _create_submitted_assertion(
        client, m, proposition="Clause 5.2 requires written consent before any assignment."
    )
    _rate(client, graded_id, graded_rev, m["rater_headers"], 5)

    accepted_id, _ = _create_submitted_assertion(
        client, m, proposition="Clause 9.7 caps liability at the fees paid in the prior 12 months."
    )
    accept = client.post(
        f"/api/v1/assertions/{accepted_id}/accept",
        json={"acceptance_justification": "Reviewed and confirmed despite no attached evidence."},
        headers=m["reviewer_headers"],
    )
    assert accept.status_code == 200

    listing = client.get(
        f"/api/v1/assertions?matter_id={m['matter_id']}", headers=m["reviewer_headers"]
    )
    assert listing.status_code == 200
    items_by_id = {item["id"]: item for item in listing.json()["items"]}
    assert len(items_by_id) == 3, "sanity: all three assertions must appear in the listing"

    assert items_by_id[unrated_id]["standing"] == "proposed"
    assert items_by_id[graded_id]["standing"] == "strong"
    assert items_by_id[accepted_id]["standing"] == "accepted"


def test_authors_rating_of_5_excluded_when_outsider_rates_1_grade_is_weak_not_probable(
    client, matter_with_users
):
    """G3, live path: author rates high, an outsider rates low afterwards.

    If the author's rating leaked into the median (a wiring bug, not a
    `compute_standing` bug -- the pure function already excludes it), the
    median of [5, 1] would be 3 -> "probable". The correct outside-only
    median of [1] is 1 -> "weak". This distinguishes the two outcomes
    through the real PUT-rating route and real GET, not the unit-tested
    pure function directly.
    """
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)

    _rate(client, assertion_id, rev, m["contributor_headers"], 5)  # contributor == author
    _rate(client, assertion_id, rev, m["rater_headers"], 1)  # outsider

    body = _get(client, assertion_id, m["reviewer_headers"])
    assert body["status"] == "proposed"
    assert body["standing"] == "weak"
    assert body["standing"] != "probable"


def test_rating_strength_overwrite_recomputes_standing_grade(client, matter_with_users):
    """PUT-overwrite (same rater, new strength) must flip the derived grade.

    `put_rating`'s upsert branch changes the existing `AssertionRating` row
    in place -- this proves that change is actually reflected in the
    read-time-derived `standing`, not just in the rating row itself.
    """
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)

    _rate(client, assertion_id, rev, m["rater_headers"], 5)
    graded = _get(client, assertion_id, m["reviewer_headers"])
    assert graded["standing"] == "strong", "sanity: must be graded strong before the overwrite"

    overwrite = _rate(client, assertion_id, rev, m["rater_headers"], 1)
    assert overwrite.status_code == 200, "same-user PUT again must upsert (200), not create (201)"

    after = _get(client, assertion_id, m["reviewer_headers"])
    assert after["standing"] == "weak"


def test_withdrawn_assertion_standing_is_withdrawn_even_with_an_existing_high_rating(
    client, matter_with_users
):
    """G4-adjacent passthrough via `withdraw_assertion`, a code path distinct
    from `_apply_decision` (accept/reject/dispute/...) -- proven separately
    since it sets `status` directly rather than going through the reviewer
    decision machinery G4's existing tests exercise.
    """
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)

    _rate(client, assertion_id, rev, m["rater_headers"], 5)
    graded = _get(client, assertion_id, m["reviewer_headers"])
    assert graded["standing"] == "strong", "sanity: must be graded strong before withdrawing"

    withdraw = client.post(
        f"/api/v1/assertions/{assertion_id}/withdraw", headers=m["contributor_headers"]
    )
    assert withdraw.status_code == 200

    after = _get(client, assertion_id, m["reviewer_headers"])
    assert after["status"] == "withdrawn"
    assert after["standing"] == "withdrawn"
    assert after["standing"] != "strong"
