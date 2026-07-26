"""Track B, item B2 — live enrichment pipeline (gate G6).

`app.enrich.pipeline` does not exist yet -- ModuleNotFoundError is the
expected RED signal. `run_enrichment` must write REAL `Assertion` /
`AssertionRevision` / `AssertionEvidence` rows against a real DB session
(no mocking of the write path -- only the pure `suggest_assertions_from_spans`
heuristic feeds it, per B2's own unit tests), visible through the existing,
unmodified `GET /api/v1/assertions` list endpoint (live call-site on the
production read path).
"""

from __future__ import annotations

from tests.conftest import seed_document, seed_source_span


def test_run_enrichment_writes_real_draft_assertions_with_real_evidence(
    client, db_session, matter_with_users
):
    from app.enrich.pipeline import run_enrichment

    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(
        db_session,
        document_id=doc_id,
        matter_id=m["matter_id"],
        quote_text="This obligation shall survive termination of this Agreement.",
    )

    created = run_enrichment(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert len(created) >= 1

    listing = client.get(
        "/api/v1/assertions",
        params={"matter_id": m["matter_id"], "origin": "model_suggested"},
        headers=m["contributor_headers"],
    )
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) >= 1
    for item in items:
        assert item["status"] in ("draft", "proposed")
        assert item["status"] != "accepted"
        assert item["origin"] == "model_suggested"

    evidence = client.get(
        f"/api/v1/assertions/{items[0]['id']}/evidence", headers=m["contributor_headers"]
    ).json()
    assert any(e["source_span_id"] == span_id for e in evidence)


def test_run_enrichment_with_no_matching_spans_creates_nothing(
    client, db_session, matter_with_users
):
    from app.enrich.pipeline import run_enrichment

    m = matter_with_users
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    seed_source_span(
        db_session, document_id=doc_id, matter_id=m["matter_id"], quote_text="The sky is blue."
    )

    created = run_enrichment(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert created == []
