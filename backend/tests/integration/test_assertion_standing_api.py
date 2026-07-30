"""Sprint 2026-07-30-ratings-grade, item B1 — standing/grade on the LIVE
assertions API.

Gates exercised end-to-end through the real app (`TestClient` over
`app.main.create_app()`, real routes, real DB — no mocks of any
acceptance-target function):

- G1: a "proposed" assertion with zero non-author ratings still presents
  a `standing` of "proposed".
- G2: the first rating from a NON-author user flips `standing` to the
  median-banded grade ("weak"/"probable"/"strong", ruling R4 — including
  the fractional-median edges 2.5 and 3.5).
- G3: the author's own rating never counts toward the grade — a
  proposed assertion the author rates 5/5 themselves still presents
  "proposed" until someone else rates it too.
- G4: an explicit reviewer decision (accept/reject) overrides the grade
  presentation — `standing` becomes the decision's status, never a band,
  even for an assertion that was already graded before the decision.
- G5: origin=system_generated assertions (sprint 2026-07-30-deterministic-
  assertions: born "accepted", never "proposed") never enter this flow —
  `standing` mirrors `status` for them, via the real definition-links
  pipeline + the real GET route (same live-pattern as
  `test_definition_links_pipeline_live.py`).
- Edge case (contract): deleting the one outside rating that had graded
  an assertion returns its `standing` to "proposed".

New field `standing` is asserted alongside the existing, unchanged
`status` field (ruling R3: derived at read time, never persisted/
mutated — `status` itself keeps meaning exactly what it means today,
per the pre-existing, untouched
`test_ratings_api.py::test_high_aggregate_rating_does_not_change_review_status`).
"""

from __future__ import annotations

import pathlib

from tests.conftest import assertion_payload, auth_header, rating_payload, seed_matter_role, seed_user

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _create_submitted_assertion(client, m):
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    body = create.json()
    client.post(f"/api/v1/assertions/{body['id']}/submit", headers=m["contributor_headers"])
    return body["id"], body.get("current_revision_number", 1)


def _rate(client, assertion_id, rev, headers, strength):
    return client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        json=rating_payload(strength=strength),
        headers=headers,
    )


def _get(client, assertion_id, headers):
    return client.get(f"/api/v1/assertions/{assertion_id}", headers=headers).json()


# --- G1 — proposed, zero outside ratings -----------------------------------


def test_proposed_with_zero_outside_ratings_has_standing_proposed(client, matter_with_users):
    m = matter_with_users
    assertion_id, _rev = _create_submitted_assertion(client, m)
    body = _get(client, assertion_id, m["reviewer_headers"])
    assert body["status"] == "proposed"
    assert body["standing"] == "proposed"


# --- G3 — author ratings don't count ---------------------------------------


def test_authors_own_rating_does_not_grade_standing(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    r = _rate(client, assertion_id, rev, m["contributor_headers"], 5)  # contributor == author
    assert r.status_code in (200, 201)
    body = _get(client, assertion_id, m["reviewer_headers"])
    assert body["status"] == "proposed"
    assert body["standing"] == "proposed"


# --- G2 — first outside rating grades it, banded per R4 --------------------


def test_single_outside_rating_of_2_bands_weak(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    _rate(client, assertion_id, rev, m["rater_headers"], 2)
    body = _get(client, assertion_id, m["reviewer_headers"])
    assert body["status"] == "proposed"
    assert body["standing"] == "weak"


def test_single_outside_rating_of_3_bands_probable(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    _rate(client, assertion_id, rev, m["rater_headers"], 3)
    body = _get(client, assertion_id, m["reviewer_headers"])
    assert body["standing"] == "probable"


def test_single_outside_rating_of_4_bands_strong(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    _rate(client, assertion_id, rev, m["rater_headers"], 4)
    body = _get(client, assertion_id, m["reviewer_headers"])
    assert body["standing"] == "strong"


def test_two_outside_ratings_fractional_median_2_5_bands_weak(client, matter_with_users, db_session):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    for strength in (2, 3):
        rater = seed_user(db_session, display_name=f"Outside rater ({strength})")
        seed_matter_role(db_session, user_id=rater, matter_id=m["matter_id"], role="contributor")
        _rate(client, assertion_id, rev, auth_header(rater), strength)
    body = _get(client, assertion_id, m["reviewer_headers"])
    assert body["standing"] == "weak"


def test_two_outside_ratings_fractional_median_3_5_bands_strong(client, matter_with_users, db_session):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    for strength in (3, 4):
        rater = seed_user(db_session, display_name=f"Outside rater ({strength})")
        seed_matter_role(db_session, user_id=rater, matter_id=m["matter_id"], role="contributor")
        _rate(client, assertion_id, rev, auth_header(rater), strength)
    body = _get(client, assertion_id, m["reviewer_headers"])
    assert body["standing"] == "strong"


# --- G4 — reviewer decision overrides the grade presentation ---------------


def test_reviewer_accept_overrides_an_existing_grade(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    _rate(client, assertion_id, rev, m["rater_headers"], 5)
    graded = _get(client, assertion_id, m["reviewer_headers"])
    assert graded["standing"] == "strong", "sanity: must really be graded before the override"

    accept = client.post(
        f"/api/v1/assertions/{assertion_id}/accept",
        json={"acceptance_justification": "Reviewed and confirmed despite no attached evidence."},
        headers=m["reviewer_headers"],
    )
    assert accept.status_code == 200

    after = _get(client, assertion_id, m["reviewer_headers"])
    assert after["status"] == "accepted"
    assert after["standing"] == "accepted"


def test_reviewer_reject_overrides_an_existing_grade(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    _rate(client, assertion_id, rev, m["rater_headers"], 1)
    graded = _get(client, assertion_id, m["reviewer_headers"])
    assert graded["standing"] == "weak", "sanity: must really be graded before the override"

    reject = client.post(
        f"/api/v1/assertions/{assertion_id}/reject",
        headers=m["reviewer_headers"],
    )
    assert reject.status_code == 200

    after = _get(client, assertion_id, m["reviewer_headers"])
    assert after["status"] == "rejected"
    assert after["standing"] == "rejected"


# --- Edge case: deleting the only outside rating reverts to "proposed" ----


def test_deleting_the_only_outside_rating_returns_standing_to_proposed(client, matter_with_users):
    m = matter_with_users
    assertion_id, rev = _create_submitted_assertion(client, m)
    _rate(client, assertion_id, rev, m["rater_headers"], 5)
    graded = _get(client, assertion_id, m["reviewer_headers"])
    assert graded["standing"] == "strong", "sanity: must really be graded before the delete"

    delete = client.delete(
        f"/api/v1/assertions/{assertion_id}/revisions/{rev}/rating",
        headers=m["rater_headers"],
    )
    assert delete.status_code == 204

    after = _get(client, assertion_id, m["reviewer_headers"])
    assert after["status"] == "proposed"
    assert after["standing"] == "proposed"


# --- G5 — deterministic (system_generated) assertions never enter the flow -


def test_deterministic_assertion_standing_mirrors_status_never_a_grade_band(
    client, matter_with_users, db_session
):
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=_read("חוק להגנת רכוש מופקד.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    created = result["created_assertions"]
    assert created, "expected at least one system_generated assertion from the live pipeline"

    for item in created:
        body = _get(client, item["id"], m["reviewer_headers"])
        assert body["origin"] == "system_generated"
        assert body["status"] == "accepted"
        assert body["standing"] == "accepted"
