"""Rating API contract: strict strength, revision addressing, rationale
preservation and rationale visibility.

Fix package "detail" (spec §4, §5, §10, §12, §13, §18):

- api:22: `strength` must be a JSON integer from 1 to 5. Booleans, numeric
  strings and floats (even integral ones such as 4.0) are rejected with 422
  instead of being coerced.
- api:30: the rating routes address a revision by its per-assertion
  revision NUMBER (as `current_revision_number` and every existing client
  do); the spec now says so. Rating rows and summaries carry both the
  revision UUID (`assertion_revision_id`) and its number
  (`assertion_revision_number`), so a client holding a payload can build
  the route without a lookup. A revision UUID in the path stays a 422.
- review:7: omitting `rationale` on PUT keeps the stored rationale and its
  exact raw text (a strength-only update never rewrites `rationale_raw`);
  `null` or blank text removes it. The summary's `current_user_rating`
  exposes `rationale_raw`, so a client can prefill its editor with the
  author's exact text instead of the sanitized copy.
- ui:16 (backend part): GET .../ratings returns every rater's rationale to
  roles holding `assertion:view_rating_rationales` (reviewer, admin) and
  only the caller's own rationale to everyone else, in a stable
  (creation) order.
- new:blank-rationale-count: whitespace-only rationales are stored as "no
  rationale", and `rationale_count` only counts rationales with readable
  text.

Every test drives the real API through the `client` fixture.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from tests.conftest import assertion_payload, auth_header, seed_matter_role, seed_user

ANGLE_BRACKET_RATIONALE = "Compare <Annex 2> with clause 8.4"
SANITIZED_ANGLE_BRACKET_RATIONALE = "Compare  with clause 8.4"


def _create_proposed_assertion(client, m) -> str:
    r = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"),
        headers=m["contributor_headers"],
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _seed_member(db_session, m, role: str) -> str:
    user_id = seed_user(db_session, display_name=f"{role} member")
    seed_matter_role(db_session, user_id=user_id, matter_id=m["matter_id"], role=role)
    return user_id


def _rating_url(assertion_id: str, revision="1") -> str:
    return f"/api/v1/assertions/{assertion_id}/revisions/{revision}/rating"


def _summary(client, assertion_id, headers, revision="1") -> dict:
    r = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/{revision}/ratings/summary", headers=headers
    )
    assert r.status_code == 200, r.text
    return r.json()


def _list(client, assertion_id, headers, revision="1") -> list[dict]:
    r = client.get(f"/api/v1/assertions/{assertion_id}/revisions/{revision}/ratings", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# --- api:22: strict integer strength -------------------------------------------


@pytest.mark.parametrize("strength", [True, False, "4", "four", 4.0, 3.5, None, [4], {"value": 4}])
def test_non_integer_strength_is_rejected_without_storing_a_rating(
    client, matter_with_users, strength
):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)

    r = client.put(_rating_url(assertion_id), json={"strength": strength}, headers=m["rater_headers"])

    assert r.status_code == 422
    assert _summary(client, assertion_id, m["reviewer_headers"])["count"] == 0


def test_non_integer_strength_does_not_overwrite_an_existing_rating(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)
    client.put(_rating_url(assertion_id), json={"strength": 4}, headers=m["rater_headers"])

    r = client.put(_rating_url(assertion_id), json={"strength": True}, headers=m["rater_headers"])

    assert r.status_code == 422
    own = client.get(_rating_url(assertion_id), headers=m["rater_headers"]).json()
    assert own["strength"] == 4


@pytest.mark.parametrize("strength", [1, 2, 3, 4, 5])
def test_every_integer_strength_from_1_to_5_is_accepted(client, matter_with_users, strength):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)

    r = client.put(_rating_url(assertion_id), json={"strength": strength}, headers=m["rater_headers"])

    assert r.status_code == 201
    assert r.json()["strength"] == strength


# --- api:30: revision addressing -------------------------------------------------


def test_rating_payloads_identify_the_revision_by_id_and_number(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)
    revision = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions", headers=m["reviewer_headers"]
    ).json()[0]

    put = client.put(_rating_url(assertion_id), json={"strength": 3}, headers=m["rater_headers"])
    own = client.get(_rating_url(assertion_id), headers=m["rater_headers"]).json()
    summary = _summary(client, assertion_id, m["rater_headers"])
    rows = _list(client, assertion_id, m["reviewer_headers"])

    for payload in (put.json(), own, summary, rows[0]):
        assert payload["assertion_revision_id"] == revision["id"]
        assert payload["assertion_revision_number"] == revision["revision_number"] == 1


def test_rating_routes_take_the_revision_number_not_the_revision_id(client, matter_with_users):
    """Decision for api:30: the `{revision_number}` path segment is the
    deliberate design (it matches `current_revision_number`,
    `expected_revision_number`, the history feed's `assertion_revision_number`
    and every client), and spec §13 was corrected to say so. A revision UUID
    is not silently accepted under a second meaning."""
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)
    revision_id = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions", headers=m["reviewer_headers"]
    ).json()[0]["id"]

    by_id = client.put(
        _rating_url(assertion_id, revision_id), json={"strength": 3}, headers=m["rater_headers"]
    )
    unknown_number = client.put(
        _rating_url(assertion_id, "2"), json={"strength": 3}, headers=m["rater_headers"]
    )

    assert by_id.status_code == 422
    assert unknown_number.status_code == 404
    assert _summary(client, assertion_id, m["reviewer_headers"])["count"] == 0


# --- review:7: rationale preservation ------------------------------------------


def test_strength_only_update_keeps_the_rationale_and_its_raw_text(
    client, matter_with_users, db_session
):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)
    created = client.put(
        _rating_url(assertion_id),
        json={"strength": 3, "rationale": ANGLE_BRACKET_RATIONALE},
        headers=m["rater_headers"],
    ).json()
    assert created["rationale"] == SANITIZED_ANGLE_BRACKET_RATIONALE
    assert created["rationale_raw"] == ANGLE_BRACKET_RATIONALE

    updated = client.put(
        _rating_url(assertion_id), json={"strength": 5}, headers=m["rater_headers"]
    )

    assert updated.status_code == 200
    assert updated.json()["strength"] == 5
    assert updated.json()["rationale"] == SANITIZED_ANGLE_BRACKET_RATIONALE
    assert updated.json()["rationale_raw"] == ANGLE_BRACKET_RATIONALE
    stored = db_session.execute(
        text(
            "SELECT strength, rationale, rationale_raw FROM assertion_ratings "
            "WHERE assertion_id = :aid AND user_id = :uid"
        ),
        {"aid": assertion_id, "uid": m["rater_id"]},
    ).one()
    assert tuple(stored) == (5, SANITIZED_ANGLE_BRACKET_RATIONALE, ANGLE_BRACKET_RATIONALE)
    # The strength-only update is still an audited rating change.
    changed = db_session.execute(
        text(
            "SELECT COUNT(*) FROM audit_events WHERE assertion_id = :aid "
            "AND event_type = 'rating_changed'"
        ),
        {"aid": assertion_id},
    ).scalar_one()
    assert changed == 1


def test_summary_exposes_the_raw_rationale_and_resubmitting_it_is_lossless(
    client, matter_with_users
):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)
    client.put(
        _rating_url(assertion_id),
        json={"strength": 3, "rationale": ANGLE_BRACKET_RATIONALE},
        headers=m["rater_headers"],
    )

    mine = _summary(client, assertion_id, m["rater_headers"])["current_user_rating"]
    assert mine["rationale"] == SANITIZED_ANGLE_BRACKET_RATIONALE
    assert mine["rationale_raw"] == ANGLE_BRACKET_RATIONALE

    resubmitted = client.put(
        _rating_url(assertion_id),
        json={"strength": 4, "rationale": mine["rationale_raw"]},
        headers=m["rater_headers"],
    ).json()

    assert resubmitted["rationale_raw"] == ANGLE_BRACKET_RATIONALE
    assert resubmitted["rationale"] == SANITIZED_ANGLE_BRACKET_RATIONALE


def test_another_users_summary_never_exposes_my_raw_rationale(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)
    client.put(
        _rating_url(assertion_id),
        json={"strength": 3, "rationale": ANGLE_BRACKET_RATIONALE},
        headers=m["rater_headers"],
    )

    reviewer_summary = _summary(client, assertion_id, m["reviewer_headers"])

    assert reviewer_summary["current_user_rating"] is None


@pytest.mark.parametrize("cleared", [None, "", "   \n"])
def test_null_or_blank_rationale_removes_the_stored_rationale(client, matter_with_users, cleared):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)
    client.put(
        _rating_url(assertion_id),
        json={"strength": 3, "rationale": ANGLE_BRACKET_RATIONALE},
        headers=m["rater_headers"],
    )

    r = client.put(
        _rating_url(assertion_id),
        json={"strength": 2, "rationale": cleared},
        headers=m["rater_headers"],
    )

    assert r.status_code == 200
    assert (r.json()["rationale"], r.json()["rationale_raw"]) == (None, None)
    summary = _summary(client, assertion_id, m["rater_headers"])
    assert summary["rationale_count"] == 0
    assert summary["current_user_rating"]["rationale"] is None
    assert summary["current_user_rating"]["rationale_raw"] is None


def test_new_rating_without_a_rationale_has_none(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)

    r = client.put(_rating_url(assertion_id), json={"strength": 2}, headers=m["rater_headers"])

    assert r.status_code == 201
    assert (r.json()["rationale"], r.json()["rationale_raw"]) == (None, None)


def test_rating_with_a_new_rationale_replaces_the_old_one(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)
    client.put(
        _rating_url(assertion_id),
        json={"strength": 3, "rationale": ANGLE_BRACKET_RATIONALE},
        headers=m["rater_headers"],
    )

    r = client.put(
        _rating_url(assertion_id),
        json={"strength": 3, "rationale": "Clause 8.2 alone is decisive."},
        headers=m["rater_headers"],
    )

    assert r.json()["rationale"] == "Clause 8.2 alone is decisive."
    assert r.json()["rationale_raw"] == "Clause 8.2 alone is decisive."


# --- new:blank-rationale-count --------------------------------------------------


def test_rationale_count_only_counts_rationales_with_readable_text(
    client, matter_with_users, db_session
):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)
    client.put(
        _rating_url(assertion_id),
        json={"strength": 4, "rationale": "Clause 8.2 is express."},
        headers=m["rater_headers"],
    )
    client.put(
        _rating_url(assertion_id),
        json={"strength": 2, "rationale": "   "},
        headers=m["reviewer_headers"],
    )
    markup_only_rater = _seed_member(db_session, m, "contributor")
    client.put(
        _rating_url(assertion_id),
        json={"strength": 3, "rationale": "<b></b>"},
        headers=auth_header(markup_only_rater),
    )
    # A whitespace-only rationale written before this fix (no API path
    # stores one any more) must not be counted either.
    legacy_rater = _seed_member(db_session, m, "contributor")
    revision_id = db_session.execute(
        text("SELECT id FROM assertion_revisions WHERE assertion_id = :aid"), {"aid": assertion_id}
    ).scalar_one()
    # Same text format SQLAlchemy's DateTime type writes to SQLite.
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    db_session.execute(
        text(
            "INSERT INTO assertion_ratings (id, organization_id, repository_id, matter_id, "
            "assertion_id, assertion_revision_id, user_id, strength, rationale, rationale_raw, "
            "created_at, updated_at) VALUES (:id, :org, :repo, :matter, :aid, :rid, :uid, 5, "
            "' ', ' ', :now, :now)"
        ),
        {
            "id": str(uuid.uuid4()),
            "org": m["organization_id"],
            "repo": m["repository_id"],
            "matter": m["matter_id"],
            "aid": assertion_id,
            "rid": revision_id,
            "uid": legacy_rater,
            "now": now,
        },
    )
    db_session.commit()

    summary = _summary(client, assertion_id, m["reviewer_headers"])

    assert summary["count"] == 4
    assert summary["rationale_count"] == 1
    reviewer_row = next(
        r for r in _list(client, assertion_id, m["reviewer_headers"]) if r["user_id"] == m["reviewer_id"]
    )
    assert (reviewer_row["rationale"], reviewer_row["rationale_raw"]) == (None, None)


# --- ui:16 (backend part): who can read which rationale ----------------------------


def test_rationales_are_readable_by_reviewers_and_admins_and_own_rationale_by_everyone(
    client, matter_with_users, db_session
):
    m = matter_with_users
    viewer_id = _seed_member(db_session, m, "viewer")
    admin_id = _seed_member(db_session, m, "admin")
    assertion_id = _create_proposed_assertion(client, m)
    client.put(
        _rating_url(assertion_id),
        json={"strength": 4, "rationale": "Rater: verbatim in the survival clause."},
        headers=m["rater_headers"],
    )
    client.put(
        _rating_url(assertion_id),
        json={"strength": 2, "rationale": "Reviewer: <i>Annex</i> 3 cuts against it."},
        headers=m["reviewer_headers"],
    )

    def rationales(headers):
        return {
            row["user_id"]: (row["strength"], row["rationale"], row["rationale_raw"])
            for row in _list(client, assertion_id, headers)
        }

    everything = {
        m["rater_id"]: (4, "Rater: verbatim in the survival clause.", "Rater: verbatim in the survival clause."),
        m["reviewer_id"]: (2, "Reviewer: Annex 3 cuts against it.", "Reviewer: <i>Annex</i> 3 cuts against it."),
    }
    assert rationales(m["reviewer_headers"]) == everything
    assert rationales(auth_header(admin_id)) == everything
    # The rater sees their own rationale but not the reviewer's.
    assert rationales(m["rater_headers"]) == {
        m["rater_id"]: everything[m["rater_id"]],
        m["reviewer_id"]: (2, None, None),
    }
    # A contributor who did not rate and a viewer see strengths only.
    hidden = {m["rater_id"]: (4, None, None), m["reviewer_id"]: (2, None, None)}
    assert rationales(m["contributor_headers"]) == hidden
    assert rationales(auth_header(viewer_id)) == hidden
    # Every role sees how many ratings carry a rationale.
    assert _summary(client, assertion_id, auth_header(viewer_id))["rationale_count"] == 2


def test_rating_list_is_in_creation_order(client, matter_with_users, db_session):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)
    raters = [_seed_member(db_session, m, "contributor") for _ in range(4)]
    for strength, rater in enumerate(raters, start=1):
        client.put(_rating_url(assertion_id), json={"strength": strength}, headers=auth_header(rater))
    # Updating an earlier rating does not move it.
    client.put(_rating_url(assertion_id), json={"strength": 5}, headers=auth_header(raters[0]))

    rows = _list(client, assertion_id, m["reviewer_headers"])

    assert [r["user_id"] for r in rows] == raters
    assert [r["strength"] for r in rows] == [5, 2, 3, 4]


def test_viewer_can_read_rating_summaries_but_cannot_rate_or_remove(
    client, matter_with_users, db_session
):
    m = matter_with_users
    viewer_id = _seed_member(db_session, m, "viewer")
    assertion_id = _create_proposed_assertion(client, m)

    put = client.put(_rating_url(assertion_id), json={"strength": 4}, headers=auth_header(viewer_id))
    delete = client.delete(_rating_url(assertion_id), headers=auth_header(viewer_id))

    assert put.status_code == 403
    assert delete.status_code == 403
    assert _summary(client, assertion_id, auth_header(viewer_id))["count"] == 0


# --- new:rating-revision-number-overflow (also api:20 part c) ---------------------


@pytest.mark.parametrize("revision", ["99999999999999999999", str(2**63), str(2**31), "0", "-1"])
@pytest.mark.parametrize(
    "method,suffix",
    [("GET", "rating"), ("PUT", "rating"), ("DELETE", "rating"), ("GET", "ratings"), ("GET", "ratings/summary")],
)
def test_a_revision_number_that_cannot_exist_is_not_found_rather_than_a_500(
    client, matter_with_users, revision, method, suffix
):
    """Numbers beyond the database integer range used to crash the SQLite
    bind with OverflowError (HTTP 500); every integer that names no
    revision is a plain 404."""
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)

    r = client.request(
        method,
        f"/api/v1/assertions/{assertion_id}/revisions/{revision}/{suffix}",
        json={"strength": 3} if method == "PUT" else None,
        headers=m["rater_headers"],
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "revision not found"


# --- new:unpaired-surrogate-text (also api:20 part b, for this router) -------


def test_rationale_with_an_unpaired_surrogate_is_rejected_not_a_500(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_proposed_assertion(client, m)

    r = client.put(
        _rating_url(assertion_id),
        content=b'{"strength": 3, "rationale": "lone \\ud800 surrogate"}',
        headers={**m["rater_headers"], "Content-Type": "application/json"},
    )

    assert r.status_code == 422
    assert _summary(client, assertion_id, m["reviewer_headers"])["count"] == 0
