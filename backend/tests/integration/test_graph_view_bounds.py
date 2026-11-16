"""GET /api/v1/matters/{id}/graph: spec §11 states, matter scope, bounds (api:23, api:14).

* ``show_unreviewed`` returned every status, drafts and withdrawn suggestions
  included; spec §11 lists accepted, proposed, disputed, rejected and
  superseded for that view.
* Every request loaded every assertion of EVERY matter, cleared and refilled
  the one projection shared by the app (a data race between threadpool
  requests: an in-process run of the route's two statements returned 0 edges
  instead of 3), then issued three queries per edge, with no bound on the
  response.
"""

from __future__ import annotations

import pytest
from sqlalchemy import event

from tests.conftest import assertion_payload, seed_document, seed_source_span

SPEC_UNREVIEWED_STATES = {"accepted", "proposed", "disputed", "rejected", "superseded"}


def _create(client, m, save_as="proposed", **overrides) -> str:
    response = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as=save_as, **overrides),
        headers=m["contributor_headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _graph(client, m, headers=None, matter_id=None, **params):
    response = client.get(
        f"/api/v1/matters/{matter_id or m['matter_id']}/graph",
        params=params,
        headers=headers or m["reviewer_headers"],
    )
    assert response.status_code == 200, response.text
    return response.json()


def _one_per_status(client, m) -> dict[str, str]:
    reviewer = m["reviewer_headers"]
    ids = {status: _create(client, m, proposition=f"A {status} assertion.") for status in (
        "proposed", "accepted", "rejected", "disputed", "superseded", "revision_requested", "withdrawn")}
    ids["draft"] = _create(client, m, save_as="draft", proposition="A private draft.")
    justification = {"acceptance_justification": "Accepted for the test."}
    assert client.post(f"/api/v1/assertions/{ids['accepted']}/accept", json=justification, headers=reviewer).status_code == 200
    assert client.post(f"/api/v1/assertions/{ids['rejected']}/reject", headers=reviewer).status_code == 200
    assert client.post(f"/api/v1/assertions/{ids['disputed']}/dispute", headers=reviewer).status_code == 200
    assert client.post(
        f"/api/v1/assertions/{ids['superseded']}/supersede",
        json={"superseded_by_assertion_id": ids["accepted"]},
        headers=reviewer,
    ).status_code == 200
    assert client.post(
        f"/api/v1/assertions/{ids['revision_requested']}/request-revision", json={}, headers=reviewer
    ).status_code == 200
    assert client.post(f"/api/v1/assertions/{ids['withdrawn']}/withdraw", headers=m["contributor_headers"]).status_code == 200
    return ids


def test_show_unreviewed_shows_exactly_the_spec_states(client, matter_with_users):
    m = matter_with_users
    ids = _one_per_status(client, m)
    unreviewed = {e["assertion_id"]: e["review_state"] for e in _graph(client, m, show_unreviewed=True)["edges"]}
    assert set(unreviewed.values()) == SPEC_UNREVIEWED_STATES
    assert {ids[s]: s for s in SPEC_UNREVIEWED_STATES} == unreviewed
    # A draft is private, a withdrawn suggestion was retracted, and a revision
    # request returned the assertion to its author: none is a graph relationship.
    for hidden in ("draft", "withdrawn", "revision_requested"):
        assert ids[hidden] not in unreviewed
    default = _graph(client, m)
    assert [e["assertion_id"] for e in default["edges"]] == [ids["accepted"]]
    assert default["total"] == 1


def test_edges_carry_the_current_revision_aggregate_and_evidence_count(client, matter_with_users, db_session):
    m = matter_with_users
    document = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span = seed_source_span(db_session, document_id=document, matter_id=m["matter_id"])
    rated = _create(client, m, evidence=[{"source_span_id": span, "evidence_role": "supports"},
                                         {"source_span_id": span, "evidence_role": "contradicts"}])
    revised = _create(client, m, proposition="Rated, then revised.")
    for assertion_id in (rated, revised):
        for headers, strength in ((m["rater_headers"], 5), (m["reviewer_headers"], 2)):
            client.put(f"/api/v1/assertions/{assertion_id}/revisions/1/rating", json={"strength": strength}, headers=headers)
    client.patch(f"/api/v1/assertions/{revised}", json={"proposition": "Revised once."}, headers=m["reviewer_headers"])
    edges = {e["assertion_id"]: e for e in _graph(client, m, show_unreviewed=True)["edges"]}
    assert edges[rated]["rating_aggregate"] == {
        "count": 2, "mean": 3.5, "median": 3.5, "distribution": {"1": 0, "2": 1, "3": 0, "4": 0, "5": 1},
    }
    assert edges[rated]["evidence_count"] == 2
    # Ratings stay with revision 1; the current revision 2 is unrated.
    assert edges[revised]["rating_aggregate"] == {
        "count": 0, "mean": None, "median": None, "distribution": {str(i): 0 for i in range(1, 6)},
    }
    assert edges[revised]["evidence_count"] == 0


def test_the_response_is_bounded_and_pages(client, matter_with_users):
    m = matter_with_users
    ids = [_create(client, m, proposition=f"Proposed number {i}.") for i in range(5)]
    default = _graph(client, m, show_unreviewed=True)
    assert default["limit"] == 1000 and default["offset"] == 0 and default["total"] == 5
    assert [e["assertion_id"] for e in default["edges"]] == ids  # insertion order
    page = _graph(client, m, show_unreviewed=True, limit=2, offset=2)
    assert page["total"] == 5 and [e["assertion_id"] for e in page["edges"]] == ids[2:4]
    for bad in ({"limit": 0}, {"limit": 5001}, {"offset": -1}):
        response = client.get(f"/api/v1/matters/{m['matter_id']}/graph", params=bad, headers=m["reviewer_headers"])
        assert response.status_code == 422


class _Recorder:
    def __init__(self, engine):
        self.engine, self.statements = engine, []

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self._hit)
        return self

    def __exit__(self, *exc):
        event.remove(self.engine, "before_cursor_execute", self._hit)

    def _hit(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append((statement, parameters))


def test_only_the_requested_matter_is_read_in_a_fixed_number_of_statements(
    app, client, matter_with_users, db_session
):
    from tests.conftest import seed_matter, seed_matter_role

    m = matter_with_users
    other = seed_matter(db_session, repository_id=m["repository_id"], name="Busy matter")
    seed_matter_role(db_session, user_id=m["contributor_id"], matter_id=other, role="contributor")
    for i in range(12):
        client.post(
            "/api/v1/assertions",
            json=assertion_payload(other, m["repository_id"], save_as="proposed", proposition=f"Elsewhere {i}."),
            headers=m["contributor_headers"],
        )

    def measure() -> list:
        with _Recorder(app.state.engine) as recorder:
            _graph(client, m, show_unreviewed=True)
        return recorder.statements

    for i in range(3):
        rated = _create(client, m, proposition=f"Here {i}.")
        client.put(f"/api/v1/assertions/{rated}/revisions/1/rating", json={"strength": 4}, headers=m["rater_headers"])
    few = measure()
    for i in range(30):
        rated = _create(client, m, proposition=f"More here {i}.")
        client.put(f"/api/v1/assertions/{rated}/revisions/1/rating", json={"strength": 3}, headers=m["rater_headers"])
    many = measure()
    assert len(many) == len(few) <= 6
    for statement, parameters in many:
        if "FROM assertions" in statement:
            values = parameters.values() if isinstance(parameters, dict) else parameters
            assert m["matter_id"] in values, f"not scoped to the requested matter: {statement}"


def test_requests_never_rebuild_state_shared_by_the_app(app, client, matter_with_users):
    """The projection is request-local: concurrent requests cannot clear each
    other's edges, and nothing is refilled from every matter per request."""
    from app.graph_projection import InMemoryGraphProjection

    class _Untouchable(InMemoryGraphProjection):
        def _fail(self, *args, **kwargs):
            raise AssertionError("the graph route touched the app-wide projection")

        project_assertion = remove_assertion = rebuild = get_visible_assertions = _fail

    m = matter_with_users
    accepted = _create(client, m)
    client.post(f"/api/v1/assertions/{accepted}/accept", json={"acceptance_justification": "x"}, headers=m["reviewer_headers"])
    app.state.graph_projection = _Untouchable()
    assert [e["assertion_id"] for e in _graph(client, m)["edges"]] == [accepted]


@pytest.mark.parametrize("show_unreviewed", [False, True])
def test_outsiders_still_get_403(client, matter_with_users, show_unreviewed):
    m = matter_with_users
    response = client.get(
        f"/api/v1/matters/{m['matter_id']}/graph",
        params={"show_unreviewed": show_unreviewed, "limit": 10},
        headers=m["outsider_headers"],
    )
    assert response.status_code == 403
