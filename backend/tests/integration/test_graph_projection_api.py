"""B6 — graph projection surfaced through the API.

Gate G7: only accepted assertions appear as accepted relationships in the
default graph view; proposed/disputed/rejected/superseded appear only in
an opt-in "show unreviewed" mode with distinct states; graph rating
aggregates are rebuildable projections, never authoritative.

Owning track: B6. A graph read surface is exposed at
GET /api/v1/matters/{matter_id}/graph (not enumerated verbatim in spec
§13's REST list, but required by spec §11/§14's graph explorer — Developer
may adjust the exact path, documented here as the Planner's assumption for
this pass; QA re-verifies against whatever path B6 actually ships).
"""

from __future__ import annotations

from tests.conftest import assertion_payload


def _create_and_submit(client, m):
    r = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="draft"),
        headers=m["contributor_headers"],
    )
    assertion_id = r.json()["id"]
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])
    return assertion_id


def test_default_graph_view_excludes_proposed_assertions(client, matter_with_users):
    m = matter_with_users
    _create_and_submit(client, m)
    r = client.get(f"/api/v1/matters/{m['matter_id']}/graph", headers=m["contributor_headers"])
    assert r.status_code == 200
    assert r.json()["edges"] == []


def test_default_graph_view_includes_accepted_assertions(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_and_submit(client, m)
    client.post(f"/api/v1/assertions/{assertion_id}/accept", headers=m["reviewer_headers"])
    r = client.get(f"/api/v1/matters/{m['matter_id']}/graph", headers=m["contributor_headers"])
    assert r.status_code == 200
    edge_ids = [e["assertion_id"] for e in r.json()["edges"]]
    assert assertion_id in edge_ids


def test_show_unreviewed_mode_includes_proposed_with_distinct_state(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_and_submit(client, m)
    r = client.get(
        f"/api/v1/matters/{m['matter_id']}/graph",
        params={"show_unreviewed": True},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    matches = [e for e in r.json()["edges"] if e["assertion_id"] == assertion_id]
    assert len(matches) == 1
    assert matches[0]["review_state"] == "proposed"


def test_graph_rejected_assertion_hidden_by_default(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_and_submit(client, m)
    client.post(f"/api/v1/assertions/{assertion_id}/reject", headers=m["reviewer_headers"])
    r = client.get(f"/api/v1/matters/{m['matter_id']}/graph", headers=m["contributor_headers"])
    assert all(e["assertion_id"] != assertion_id for e in r.json()["edges"])


def test_graph_edge_exposes_rating_aggregate_as_distinct_field(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_and_submit(client, m)
    client.post(f"/api/v1/assertions/{assertion_id}/accept", headers=m["reviewer_headers"])
    client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 5, "rationale": None},
        headers=m["rater_headers"],
    )
    r = client.get(f"/api/v1/matters/{m['matter_id']}/graph", headers=m["contributor_headers"])
    edge = next(e for e in r.json()["edges"] if e["assertion_id"] == assertion_id)
    assert "rating_aggregate" in edge
    assert "review_state" in edge
    assert edge["rating_aggregate"] != edge["review_state"]


def test_outsider_cannot_read_matter_graph(client, matter_with_users):
    m = matter_with_users
    r = client.get(f"/api/v1/matters/{m['matter_id']}/graph", headers=m["outsider_headers"])
    assert r.status_code == 403
