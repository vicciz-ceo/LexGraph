"""List and statistics filter values are validated: 422, never 500 (review
listing:2).

The filters of GET /api/v1/assertions and GET /api/v1/matters/{id}/assertion-stats
reach SQLite as bound values. A count beyond SQLite's 64-bit integers, an
instant whose offset moves it outside the years 1-9999 once in UTC, the last
representable effective date, a bucket edge with such an offset and a sort
naming one key a thousand times all answered 500 (OverflowError, "too many
terms in ORDER BY clause"). A non-finite min_average_rating was silently
accepted, although spec section 7 makes a non-finite number a 422 wherever a
number is expected.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.services.assertion_listing import SORT_KEYS
from app.services.paging import MAX_OFFSET
from tests.integration._assertion_list_fixtures import build_varied_matter

HUGE = "99999999999999999999"

INVALID = [
    ("min_rating_count", HUGE),
    ("min_rating_count", str(2**63)),
    ("min_rating_count", str(MAX_OFFSET + 1)),
    ("min_rating_count", "-1"),
    ("min_rating_count", "-" + HUGE),
    ("min_rating_count", "1.5"),
    ("min_average_rating", "nan"),
    ("min_average_rating", "inf"),
    ("min_average_rating", "-Infinity"),
    ("min_average_rating", "1e999"),
    ("min_average_rating", "0.99"),
    ("min_average_rating", "5.01"),
    ("created_from", "0001-01-01T00:00:00+01:00"),
    ("created_to", "0001-01-01T00:00:00+01:00"),
    ("last_activity_from", "9999-12-31T23:00:00-05:00"),
    ("last_activity_to", "9999-12-31T23:00:00-05:00"),
    ("created_from", "10000-01-01T00:00:00Z"),
    ("effective_on", "10000-01-01"),
    ("my_rating", HUGE),
    ("unrated_by_me", "perhaps"),
]


def _routes(m) -> list[tuple[str, dict]]:
    return [
        ("/api/v1/assertions", {"matter_id": m["matter_id"]}),
        (f"/api/v1/matters/{m['matter_id']}/assertion-stats", {}),
    ]


@pytest.fixture()
def raw(app):
    """A client on which a server error is a 500 response, not an exception."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def varied(client, matter_with_users, db_session):
    return build_varied_matter(client, matter_with_users, db_session)


@pytest.mark.parametrize("name,value", INVALID)
def test_an_invalid_filter_value_is_a_422_on_the_list_and_the_stats(raw, matter_with_users, name, value):
    """No data needed: each value failed while being bound or converted."""
    m = matter_with_users
    for path, params in _routes(m):
        response = raw.get(path, params={**params, name: value}, headers=m["rater_headers"])
        assert response.status_code == 422, (path, name, value, response.status_code, response.text)
        assert name in response.text, (path, name, response.text)  # the 422 names the parameter


def test_the_extreme_valid_filter_values_answer_200(raw, matter_with_users, varied):
    m, v = matter_with_users, varied
    for path, params in _routes(m):
        for name, value in [
            ("min_rating_count", "0"),
            ("min_rating_count", str(MAX_OFFSET)),
            ("min_average_rating", "1"),
            ("min_average_rating", "5"),
            ("created_from", "0001-01-01T00:00:00Z"),
            ("created_to", "9999-12-31T23:59:59.999999Z"),
            ("created_from", "0001-01-01T01:00:00+01:00"),  # year 1 in UTC, at the boundary
            ("last_activity_to", "9999-12-31T18:59:59-05:00"),
            ("last_activity_from", "0001-01-01T00:00:00"),  # naive: UTC
            ("effective_on", "9999-12-31"),
            ("effective_on", "0001-01-01"),
        ]:
            response = raw.get(path, params={**params, name: value}, headers=m["rater_headers"])
            assert response.status_code == 200, (path, name, value, response.text)

    def ids(**params):
        response = raw.get("/api/v1/assertions", params={"matter_id": m["matter_id"], **params},
                           headers=m["rater_headers"])
        assert response.status_code == 200, response.text
        return [item["id"] for item in response.json()["items"]]

    everything = ids()
    assert ids(min_rating_count=MAX_OFFSET) == []
    assert ids(min_rating_count=0) == everything
    assert ids(created_from="0001-01-01T00:00:00Z") == everything
    assert ids(created_from="9999-12-31T23:59:59Z") == []
    # Open-ended or no temporal scope: bravo (from 2025-06-01), charlie,
    # echo and foxtrot are in effect on the last representable day.
    assert ids(effective_on="9999-12-31") == [v["bravo"], v["charlie"], v["echo"], v["foxtrot"]]
    assert ids(effective_on="0001-01-01") == [v["charlie"], v["delta"], v["echo"], v["foxtrot"]]


def test_an_instant_with_an_offset_is_compared_in_utc(raw, matter_with_users, varied):
    m = matter_with_users
    items = raw.get("/api/v1/assertions", params={"matter_id": m["matter_id"]}, headers=m["rater_headers"]).json()
    first = min(item["created_at"] for item in items["items"])
    # The same instant written with a +05:00 offset selects the same rows.
    instant = datetime.fromisoformat(first).astimezone(timezone(timedelta(hours=5)))
    utc = raw.get("/api/v1/assertions", params={"matter_id": m["matter_id"], "created_from": first},
                  headers=m["rater_headers"]).json()["total"]
    shifted = raw.get("/api/v1/assertions", params={"matter_id": m["matter_id"], "created_from": instant.isoformat()},
                      headers=m["rater_headers"]).json()["total"]
    assert utc == shifted == items["total"]


@pytest.mark.parametrize("edges", [
    "0001-01-01T00:00:00+01:00,2020-01-01T00:00:00Z",
    "2020-01-01T00:00:00Z,9999-12-31T23:00:00-05:00",
])
def test_a_bucket_edge_outside_the_supported_range_is_a_422(raw, matter_with_users, edges):
    m = matter_with_users
    response = raw.get(f"/api/v1/matters/{m['matter_id']}/assertion-stats",
                       params={"created_bucket_edges": edges}, headers=m["rater_headers"])
    assert response.status_code == 422, response.text
    assert "created_bucket_edges" in response.json()["detail"]


def test_the_widest_bucket_edges_answer_200(raw, matter_with_users, varied):
    m = matter_with_users
    response = raw.get(f"/api/v1/matters/{m['matter_id']}/assertion-stats",
                       params={"created_bucket_edges": "0001-01-01T00:00:00Z,9999-12-31T23:59:59Z"},
                       headers=m["rater_headers"])
    assert response.status_code == 200, response.text
    assert response.json()["created_buckets"][0]["count"] == response.json()["total"]


@pytest.mark.parametrize("sort", [
    ",".join(["-my_rating"] * 1001),
    "my_rating,-my_rating",
    "created_at,status,created_at",
])
def test_a_sort_key_given_twice_is_a_422(raw, matter_with_users, sort):
    m = matter_with_users
    response = raw.get("/api/v1/assertions", params={"matter_id": m["matter_id"], "limit": 5, "sort": sort},
                       headers=m["rater_headers"])
    assert response.status_code == 422, response.text[:300]
    assert "more than once" in response.json()["detail"]


def test_every_sort_key_at_once_answers_200(raw, matter_with_users, varied):
    m = matter_with_users
    sort = ",".join(f"-{key}" if n % 2 else key for n, key in enumerate(SORT_KEYS))
    response = raw.get("/api/v1/assertions", params={"matter_id": m["matter_id"], "limit": 5, "sort": sort},
                       headers=m["rater_headers"])
    assert response.status_code == 200, response.text
    assert response.json()["total"] == len(varied)
