"""GET /api/v1/assertions: every spec §17 sort key and §10/§17 filter (api:13).

The list used to honour four sort keys and silently fall back to created_at
for anything else, and FastAPI dropped unknown filters, so e.g.
``sort=-average_rating`` or ``assertion_type=WEAKENS`` returned 200 with an
unsorted, unfiltered list. Unknown keys and parameters are now a 422.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.integration._assertion_list_fixtures import build_varied_matter, entity_id


@pytest.fixture()
def varied(client, matter_with_users, db_session):
    return build_varied_matter(client, matter_with_users, db_session)


def _get(client, m, headers=None, **params):
    return client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], **params},
        headers=headers or m["rater_headers"],
    )


def _ids(client, m, headers=None, **params) -> list[str]:
    response = _get(client, m, headers, **params)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def _instant(value):
    return datetime.fromisoformat(value) if value is not None else None


def _sort_values(m) -> dict:
    names = {
        m["contributor_id"]: "Contributor A",
        m["rater_id"]: "Contributor B (rater)",
        m["reviewer_id"]: "Reviewer",
    }

    def entity(item, key):
        ref = item[key]
        return (ref["type"], ref["id"]) if ref is not None else None

    return {
        "created_at": lambda it: _instant(it["created_at"]),
        "updated_at": lambda it: _instant(it["updated_at"]),
        "last_activity": lambda it: _instant(it["last_activity_at"]),
        "proposition": lambda it: it["proposition"],
        "assertion_type": lambda it: it["assertion_type"],
        "subject": lambda it: entity(it, "subject_entity"),
        "object": lambda it: entity(it, "object_entity"),
        "origin": lambda it: it["origin"],
        "author": lambda it: (names[it["author_user_id"]], it["author_user_id"]),
        "status": lambda it: it["status"],
        "evidence_status": lambda it: it["evidence_status"],
        "average_rating": lambda it: (it["ratings_summary"] or {}).get("average"),
        "rating_count": lambda it: (it["ratings_summary"] or {}).get("count", 0),
        "my_rating": lambda it: (it["current_user_rating"] or {}).get("strength"),
        "jurisdiction": lambda it: it["jurisdiction"],
        "effective_from": lambda it: it["effective_from"],
        "effective_to": lambda it: it["effective_to"],
    }


def _expected(items, value, descending) -> list[str]:
    """Stable sort of the insertion-ordered items; missing values last both ways."""
    present = [it for it in items if value(it) is not None]
    missing = [it for it in items if value(it) is None]
    return [it["id"] for it in sorted(present, key=value, reverse=descending) + missing]


SORT_KEYS = [
    "created_at", "updated_at", "last_activity", "proposition", "assertion_type", "subject", "object",
    "origin", "author", "status", "evidence_status", "average_rating", "rating_count", "my_rating",
    "jurisdiction", "effective_from", "effective_to",
]


@pytest.mark.parametrize("descending", [False, True], ids=["asc", "desc"])
@pytest.mark.parametrize("key", SORT_KEYS)
def test_every_spec_sort_key_orders_the_list(client, matter_with_users, varied, key, descending):
    m = matter_with_users
    items = _get(client, m).json()["items"]
    value = _sort_values(m)[key]
    expected = _expected(items, value, descending)
    actual = _ids(client, m, sort=f"-{key}" if descending else key)
    assert actual == expected
    # Not vacuous: the key really distinguishes rows of this matter.
    assert len({repr(value(it)) for it in items}) > 1


def test_rating_sorts_put_unrated_assertions_last_in_both_directions(client, matter_with_users, varied):
    m = matter_with_users
    unrated = {varied["bravo"], varied["foxtrot"]}
    for sort in ("average_rating", "-average_rating"):
        assert set(_ids(client, m, sort=sort)[-2:]) == unrated
    assert _ids(client, m, sort="-average_rating")[:2] == [varied["alpha"], varied["echo"]]  # 4.0, 4.0
    assert _ids(client, m, sort="-rating_count")[0] == varied["alpha"]  # three ratings


def test_several_sort_keys_apply_in_order(client, matter_with_users, varied):
    m = matter_with_users
    items = _get(client, m).json()["items"]
    values = _sort_values(m)
    by_name = sorted(items, key=values["proposition"], reverse=True)
    expected = [it["id"] for it in sorted(by_name, key=values["status"])]
    assert _ids(client, m, sort="status,-proposition") == expected


@pytest.mark.parametrize("sort", ["bogus", "-bogus", "created_at,bogus", "average", "author_user_id", ","])
def test_an_unknown_sort_key_is_rejected_not_ignored(client, matter_with_users, sort):
    response = _get(client, matter_with_users, sort=sort)
    assert response.status_code == 422
    assert "unsupported sort key" in response.json()["detail"]
    assert "average_rating" in response.json()["detail"]  # lists what is supported


@pytest.mark.parametrize(
    "params",
    [{"potential_duplicates": "true"}, {"assertion_typ": "WEAKENS"}, {"page": 2}, {"sort_by": "created_at"}],
)
def test_an_unknown_query_parameter_is_rejected_not_ignored(client, matter_with_users, params):
    response = _get(client, matter_with_users, **params)
    assert response.status_code == 422
    assert f"unsupported query parameter(s): {next(iter(params))}" in response.json()["detail"]


def test_filters_by_type_author_subject_and_object(client, matter_with_users, varied):
    m, v = matter_with_users, varied
    assert _ids(client, m, assertion_type="WEAKENS") == [v["bravo"]]
    assert _ids(client, m, author_user_id=m["rater_id"]) == [v["bravo"]]
    assert _ids(client, m, author_user_id=m["contributor_id"]) == [v["alpha"], v["delta"], v["echo"], v["foxtrot"]]
    assert _ids(client, m, subject_entity_type="Document") == [v["echo"]]
    assert _ids(client, m, subject_entity_id=entity_id(50)) == [v["bravo"]]
    assert _ids(client, m, object_entity_type="Clause") == [v["delta"]]
    assert _ids(client, m, object_entity_type="Provision", object_entity_id=entity_id(100)) == [v["alpha"]]
    body = _get(client, m, author_user_id=m["contributor_id"], status="proposed", limit=1).json()
    assert body["total"] == 3 and len(body["items"]) == 1  # alpha, echo, foxtrot


def test_filters_by_creation_and_last_activity_ranges(client, matter_with_users, varied):
    m, v = matter_with_users, varied
    items = {it["id"]: it for it in _get(client, m).json()["items"]}
    pivot = items[v["charlie"]]["created_at"]
    # Half-open [created_from, created_to).
    assert _ids(client, m, created_from=pivot) == [v["charlie"], v["delta"], v["echo"], v["foxtrot"]]
    assert _ids(client, m, created_to=pivot) == [v["alpha"], v["bravo"]]
    # The same instant written with another offset selects the same rows.
    tokyo = _instant(pivot).astimezone(timezone(timedelta(hours=9))).isoformat()
    assert _ids(client, m, created_from=tokyo) == [v["charlie"], v["delta"], v["echo"], v["foxtrot"]]
    assert _ids(client, m, created_from="2000-01-01", created_to="2000-01-02") == []

    latest = items[v["bravo"]]["last_activity_at"]  # the comment is the newest event
    assert _ids(client, m, last_activity_from=latest) == [v["bravo"]]
    assert v["bravo"] not in _ids(client, m, last_activity_to=latest)


def test_filters_by_the_effective_date(client, matter_with_users, varied):
    """effective_on=D: in effect on that day; an open bound is unbounded."""
    m, v = matter_with_users, varied
    # charlie, echo and foxtrot have no temporal scope at all.
    assert _ids(client, m, effective_on="2025-01-01") == [v["charlie"], v["delta"], v["echo"], v["foxtrot"]]
    assert _ids(client, m, effective_on="2026-01-01") == list(v.values())  # inclusive start date
    assert v["alpha"] in _ids(client, m, effective_on="2026-12-31")  # inclusive end date
    assert _ids(client, m, effective_on="2027-06-01") == [v["bravo"], v["charlie"], v["echo"], v["foxtrot"]]
    assert _get(client, m, effective_on="next tuesday").status_code == 422


def test_filters_by_evidence_status(client, matter_with_users, varied):
    m, v = matter_with_users, varied
    assert _ids(client, m, evidence_status="evidenced") == [v["alpha"], v["delta"], v["echo"]]
    assert _ids(client, m, evidence_status="unsupported") == [v["charlie"]]
    assert _ids(client, m, evidence_status="awaiting_evidence") == [v["bravo"], v["foxtrot"]]
    assert _get(client, m, evidence_status="supported").status_code == 422


def test_filters_by_the_callers_rating(client, matter_with_users, varied):
    m, v = matter_with_users, varied
    assert _ids(client, m, my_rating=5) == [v["alpha"]]
    assert _ids(client, m, my_rating=3) == [v["delta"]]
    # The rater rated foxtrot's revision 1 only; revision 2 is current.
    assert _ids(client, m, unrated_by_me=True) == [v["bravo"], v["charlie"], v["foxtrot"]]
    assert _ids(client, m, min_rating_count=2) == [v["alpha"]]
    assert _ids(client, m, min_average_rating=3.5) == [v["alpha"], v["echo"]]
    for bad in (0, 6):
        assert _get(client, m, my_rating=bad).status_code == 422


def test_filters_and_rating_sorts_never_count_another_matters_ratings(client, matter_with_users, db_session, varied):
    from tests.conftest import assertion_payload, seed_matter, seed_matter_role

    m = matter_with_users
    other = seed_matter(db_session, repository_id=m["repository_id"], name="Other matter")
    seed_matter_role(db_session, user_id=m["rater_id"], matter_id=other, role="contributor")
    seed_matter_role(db_session, user_id=m["reviewer_id"], matter_id=other, role="reviewer")
    elsewhere = client.post(
        "/api/v1/assertions",
        json=assertion_payload(other, m["repository_id"], save_as="proposed", proposition="Alpha elsewhere."),
        headers=m["rater_headers"],
    ).json()["id"]
    client.put(f"/api/v1/assertions/{elsewhere}/revisions/1/rating", json={"strength": 5}, headers=m["reviewer_headers"])
    assert elsewhere not in _ids(client, m, sort="-average_rating")
    assert _ids(client, m, min_rating_count=2) == [varied["alpha"]]
    other_ids = _ids(client, {"matter_id": other}, headers=m["rater_headers"], min_rating_count=1)
    assert other_ids == [elsewhere]
