"""E1 — thin end-to-end flow (spec §18, gate G12).

API-driven E2E (Manager-acceptable per Planner brief §4): real backend +
real HTTP via FastAPI TestClient, no browser/Playwright. Browser-level E2E
is deferred to QA's regression pass — recorded decision, not a scope cut;
this test still proves the full 10-step contributor -> rater -> reviewer
-> graph flow against the real API end to end.

Depends on ALL backend tracks (B1, B2, B4, B6) being complete — sequenced
last. No dedicated write-set.
"""

from __future__ import annotations

from tests.conftest import assertion_payload


def test_contributor_to_rater_to_reviewer_to_graph_flow(client, matter_with_users, db_session):
    from tests.conftest import seed_document, seed_source_span

    m = matter_with_users

    # 1-2. Contributor opens a provision and highlights supporting text
    #      (modeled as a pre-existing document + source span).
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(
        db_session,
        document_id=doc_id,
        matter_id=m["matter_id"],
        quote_text="except where prohibited by law",
    )

    # 3. The contributor suggests an assertion from the highlighted text.
    payload = assertion_payload(
        m["matter_id"],
        m["repository_id"],
        evidence=[{"source_span_id": span_id, "evidence_role": "primary_basis"}],
        save_as="proposed",
    )
    create = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert create.status_code == 201
    assertion = create.json()
    assertion_id = assertion["id"]
    assert assertion["status"] == "proposed"
    assert assertion["origin"] == "user_suggested"

    # 4. A second contributor opens the assertion.
    fetched = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["rater_headers"])
    assert fetched.status_code == 200

    # 5. The second contributor assigns a strength rating of 4.
    rate = client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 4, "rationale": "Strong textual support, subject to a limited exception."},
        headers=m["rater_headers"],
    )
    assert rate.status_code in (200, 201)
    assert rate.json()["strength"] == 4

    # 6. The rating summary updates.
    summary = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/1/ratings/summary",
        headers=m["reviewer_headers"],
    )
    assert summary.status_code == 200
    assert summary.json()["count"] == 1
    assert summary.json()["average"] == 4.0

    # 7. A reviewer inspects the evidence and ratings.
    review_view = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["reviewer_headers"])
    assert review_view.status_code == 200
    review_body = review_view.json()
    assert review_body["evidence"]
    assert review_body["ratings_summary"]["count"] == 1

    # 8. The reviewer accepts the assertion.
    accept = client.post(f"/api/v1/assertions/{assertion_id}/accept", headers=m["reviewer_headers"])
    assert accept.status_code == 200
    assert accept.json()["status"] == "accepted"

    # 9. The assertion history remains available.
    history = client.get(f"/api/v1/assertions/{assertion_id}/history", headers=m["reviewer_headers"])
    assert history.status_code == 200
    assert len(history.json()) >= 1

    revisions = client.get(f"/api/v1/assertions/{assertion_id}/revisions", headers=m["reviewer_headers"])
    assert revisions.status_code == 200
    assert revisions.json()[0]["revision_number"] == 1

    # 10. The accepted assertion appears in the graph with its source evidence.
    graph = client.get(f"/api/v1/matters/{m['matter_id']}/graph", headers=m["contributor_headers"])
    assert graph.status_code == 200
    edge = next(e for e in graph.json()["edges"] if e["assertion_id"] == assertion_id)
    assert edge["review_state"] == "accepted"
    assert edge.get("evidence_count", 0) >= 1

    # Rating remained attached to the reviewed revision throughout.
    post_accept_rating = client.get(
        f"/api/v1/assertions/{assertion_id}/revisions/1/ratings", headers=m["reviewer_headers"]
    )
    assert len(post_accept_rating.json()) == 1
