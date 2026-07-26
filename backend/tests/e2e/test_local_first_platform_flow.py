"""Track D, item D2 — gate G8 end-to-end flow, fully local, single process,
no network: seed a document via existing fixtures -> enrich/suggest ->
review -> grade.

Director scope amendment (2026-07-26): document acquisition is out of
scope, so "seed" here means the existing conftest raw-SQL helpers (the same
"existing means" every other integration test already uses), not a new
ingest pipeline. This test fails today at the `app.enrich.pipeline` import
(ModuleNotFoundError) -- once Track A (raw-text columns) and Track B
(enrichment) land, it proves the whole local chain works together against
one real SQLite file with the real API and the real review workflow.
"""

from __future__ import annotations

from tests.conftest import seed_document, seed_source_span


def test_seed_enrich_review_grade_flow_is_fully_local(client, db_session, matter_with_users):
    from app.enrich.pipeline import run_enrichment

    m = matter_with_users

    # 1. Seed a document + source span via the EXISTING fixture helpers
    #    (document acquisition/ingest is out of scope this sprint).
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(
        db_session,
        document_id=doc_id,
        matter_id=m["matter_id"],
        quote_text="This obligation shall survive termination of this Agreement.",
    )

    # 2. Enrich/suggest: the offline heuristic pipeline proposes a draft
    #    assertion with evidence linked to the real span above.
    created = run_enrichment(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert len(created) >= 1
    assertion_id = created[0]["id"]

    detail = client.get(
        f"/api/v1/assertions/{assertion_id}", headers=m["contributor_headers"]
    ).json()
    assert detail["origin"] == "model_suggested"
    assert detail["status"] != "accepted"
    evidence = client.get(
        f"/api/v1/assertions/{assertion_id}/evidence", headers=m["contributor_headers"]
    ).json()
    assert any(e["source_span_id"] == span_id for e in evidence)

    # 3. Review: submit for review, then a reviewer accepts it -- the
    #    existing, unmodified review workflow.
    submit = client.post(
        f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"]
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "proposed"

    accept = client.post(
        f"/api/v1/assertions/{assertion_id}/accept", headers=m["reviewer_headers"]
    )
    assert accept.status_code == 200
    assert accept.json()["status"] == "accepted"

    # 4. Grade: the accepted assertion is now visible in the graph the
    #    grading app reads, entirely from the local DB.
    graph = client.get(
        f"/api/v1/matters/{m['matter_id']}/graph", headers=m["reviewer_headers"]
    )
    assert graph.status_code == 200
    edges = {edge["assertion_id"]: edge for edge in graph.json()["edges"]}
    assert assertion_id in edges
    assert edges[assertion_id]["review_state"] == "accepted"
    assert edges[assertion_id]["evidence_count"] >= 1
