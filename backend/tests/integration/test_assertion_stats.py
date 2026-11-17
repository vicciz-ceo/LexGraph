"""GET /api/v1/matters/{id}/assertion-stats (ui:1, backend part).

Analytics and Profile downloaded every assertion of the matter (plus capped
per-row rating summaries) to count statuses, types, contributors and ratings
in the browser; at pipeline scale that took 60-90 s and the "average
strength" KPI only covered the first 50 rows. This endpoint returns the same
aggregates computed in SQL, over the list endpoint's filters.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event

from tests.conftest import assertion_payload, seed_matter, seed_matter_role
from tests.integration._assertion_list_fixtures import build_varied_matter, run_definition_link_pipeline


def _stats(client, m, headers=None, matter_id=None, **params):
    return client.get(
        f"/api/v1/matters/{matter_id or m['matter_id']}/assertion-stats",
        params=params,
        headers=m["reviewer_headers"] if headers is None else headers,
    )


def _ok(client, m, **params) -> dict:
    response = _stats(client, m, **params)
    assert response.status_code == 200, response.text
    return response.json()


def test_counts_and_aggregates_for_a_matter(client, matter_with_users, db_session):
    m = matter_with_users
    build_varied_matter(client, m, db_session)
    stats = _ok(client, m)
    assert stats["matter_id"] == m["matter_id"]
    assert stats["total"] == 6
    assert stats["by_status"] == {"proposed": 3, "draft": 1, "accepted": 1, "disputed": 1}
    assert stats["by_origin"] == {"user_suggested": 5, "model_suggested": 1}
    assert stats["by_origin_status"] == {
        "user_suggested": {"proposed": 2, "draft": 1, "accepted": 1, "disputed": 1},
        "model_suggested": {"proposed": 1},
    }
    assert stats["by_type"] == {
        "INTERPRETS": 1, "WEAKENS": 1, "SUPPORTS": 1, "CONFLICTS_WITH": 1, "RELEVANT_TO": 1, "MODIFIES": 1,
    }
    assert stats["by_evidence_status"] == {"evidenced": 3, "unsupported": 1, "awaiting_evidence": 2}
    # Sorted by authored count, then user id.
    assert stats["authors"][0] == {
        "user_id": m["contributor_id"], "total": 4, "by_status": {"proposed": 3, "disputed": 1},
    }
    assert sorted(stats["authors"][1:], key=lambda a: a["user_id"]) == sorted([
        {"user_id": m["rater_id"], "total": 1, "by_status": {"draft": 1}},
        {"user_id": m["reviewer_id"], "total": 1, "by_status": {"accepted": 1}},
    ], key=lambda a: a["user_id"])
    assert stats["confidence_by_origin"] == {"model_suggested": {"count": 1, "average": 0.8}}
    # Current revisions only: foxtrot's ratings stayed on revision 1.
    # alpha 4.0 (3 ratings), charlie 2.0, delta 3.0, echo 4.0.
    assert stats["ratings"] == {"rated_assertions": 4, "ratings": 6, "average_of_averages": 3.25}
    assert stats["created_buckets"] == []


def test_filters_narrow_the_statistics_like_the_list(client, matter_with_users, db_session):
    """The Profile page's authored/accepted/rejected counts in one request."""
    m = matter_with_users
    build_varied_matter(client, m, db_session)
    mine = _ok(client, m, author_user_id=m["contributor_id"])
    assert mine["total"] == 4 and mine["by_status"] == {"proposed": 3, "disputed": 1}
    listed = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "author_user_id": m["contributor_id"], "limit": 1},
        headers=m["reviewer_headers"],
    ).json()
    assert listed["total"] == mine["total"]
    accepted = _ok(client, m, status="accepted", evidence_status="unsupported")
    assert accepted["total"] == 1 and accepted["by_type"] == {"SUPPORTS": 1}
    none = _ok(client, m, assertion_type="NOT_A_TYPE")
    assert none["total"] == 0 and none["by_status"] == {} and none["authors"] == []
    assert none["ratings"] == {"rated_assertions": 0, "ratings": 0, "average_of_averages": None}


def test_creation_counts_per_caller_supplied_bucket(client, matter_with_users, db_session):
    """The Analytics page buckets by local ISO week, so the browser sends the
    week boundaries as instants and the server counts in UTC."""
    m = matter_with_users
    ids = build_varied_matter(client, m, db_session)
    detail = client.get(f"/api/v1/assertions/{ids['charlie']}", headers=m["reviewer_headers"]).json()
    pivot = datetime.fromisoformat(detail["created_at"])
    edges = [pivot - timedelta(days=7), pivot, pivot + timedelta(days=7)]
    stats = _ok(client, m, created_bucket_edges=",".join(e.isoformat() for e in edges))
    assert [b["count"] for b in stats["created_buckets"]] == [2, 4]  # alpha, bravo | charlie..foxtrot
    assert [datetime.fromisoformat(b["start"]) for b in stats["created_buckets"]] == edges[:2]
    assert [datetime.fromisoformat(b["end"]) for b in stats["created_buckets"]] == edges[1:]
    # The same boundaries written as +09:00 wall clock (percent-encoded '+') count the same.
    tokyo = ",".join(e.astimezone(timezone(timedelta(hours=9))).isoformat() for e in edges)
    assert _ok(client, m, created_bucket_edges=tokyo)["created_buckets"] == stats["created_buckets"]


@pytest.mark.parametrize(
    "params",
    [
        {"created_bucket_edges": "2026-01-01T00:00:00Z"},
        {"created_bucket_edges": "2026-02-01T00:00:00Z,2026-01-01T00:00:00Z"},
        {"created_bucket_edges": "2026-01-01T00:00:00Z,not-a-date"},
        {"q": "clause"},
        {"sort": "created_at"},
        {"limit": 5},
        {"bogus": "1"},
        # The matter comes from the path; a query copy would be silently ignored.
        {"matter_id": "00000000-0000-4000-8000-000000000001"},
    ],
)
def test_invalid_parameters_are_rejected(client, matter_with_users, params):
    m = matter_with_users
    response = client.get(
        f"/api/v1/matters/{m['matter_id']}/assertion-stats", params=params, headers=m["reviewer_headers"]
    )
    assert response.status_code == 422, response.text


def test_access_is_checked_and_other_matters_never_count(client, matter_with_users, db_session):
    m = matter_with_users
    build_varied_matter(client, m, db_session)
    other = seed_matter(db_session, repository_id=m["repository_id"], name="Other matter")
    seed_matter_role(db_session, user_id=m["rater_id"], matter_id=other, role="contributor")
    seed_matter_role(db_session, user_id=m["reviewer_id"], matter_id=other, role="reviewer")
    elsewhere = client.post(
        "/api/v1/assertions",
        json=assertion_payload(other, m["repository_id"], save_as="proposed"),
        headers=m["rater_headers"],
    ).json()["id"]
    client.put(f"/api/v1/assertions/{elsewhere}/revisions/1/rating", json={"strength": 1}, headers=m["reviewer_headers"])
    assert _ok(client, m)["total"] == 6
    assert _ok(client, m)["ratings"]["ratings"] == 6
    assert _ok(client, m, matter_id=other)["total"] == 1
    assert _stats(client, m, headers=m["outsider_headers"]).status_code == 403
    assert _stats(client, m, headers={}).status_code == 401
    assert _stats(client, m, headers={}, bogus="1").status_code == 401


def test_a_fixed_number_of_statements_at_pipeline_scale(app, client, matter_with_users, db_session):
    m = matter_with_users
    build_varied_matter(client, m, db_session)
    edges = "2026-01-01T00:00:00Z,2030-01-01T00:00:00Z,2031-01-01T00:00:00Z"

    def count_statements() -> tuple[int, dict]:
        hits = []
        listener = lambda *args, **kwargs: hits.append(1)  # noqa: E731
        event.listen(app.state.engine, "before_cursor_execute", listener)
        try:
            body = _ok(client, m, created_bucket_edges=edges)
        finally:
            event.remove(app.state.engine, "before_cursor_execute", listener)
        return len(hits), body

    small, _ = count_statements()
    created = run_definition_link_pipeline(db_session, m)
    large, body = count_statements()
    assert large == small <= 6
    assert body["total"] == 6 + created
    assert body["by_origin"]["system_generated"] == created == body["by_origin_status"]["system_generated"]["accepted"]
    assert body["created_buckets"][0]["count"] == 6 + created
