"""B5 — user-submission validation + duplicate/related-assertion detection.

Spec §7 (validation), §8 (duplicate detection — surfaced, never auto-
prevents submission except exact duplicates, never auto-merges).

Owning track: B5. Extends the assertions router (POST /api/v1/assertions
validation) plus a duplicate-check surface exposed via
GET /api/v1/assertions/{id}/related (spec §13) and/or a pre-submission
check the create endpoint returns inline.
"""

from __future__ import annotations

from tests.conftest import assertion_payload


def test_subject_entity_must_belong_to_authorized_matter(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"])
    payload["subject_entity"] = {"type": "Provision", "id": "entity-from-another-matter"}
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 422


def test_dates_must_be_logically_consistent(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(
        m["matter_id"],
        m["repository_id"],
        effective_from="2026-01-01",
        effective_to="2020-01-01",
    )
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 422


def test_unknown_assertion_type_must_be_explicitly_marked_proposed(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], assertion_type="TOTALLY_NEW_TYPE")
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 422


def test_unknown_assertion_type_accepted_when_marked_proposed(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(
        m["matter_id"],
        m["repository_id"],
        assertion_type="TOTALLY_NEW_TYPE",
        assertion_type_is_proposed_new=True,
    )
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 201


def test_exact_duplicate_proposition_blocks_submission(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed")
    client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    r = client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])
    assert r.status_code == 409
    assert "duplicate" in r.json().get("detail", "").lower()


def test_similar_proposition_warns_but_does_not_block(client, matter_with_users):
    m = matter_with_users
    payload = assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed")
    client.post("/api/v1/assertions", json=payload, headers=m["contributor_headers"])

    similar_payload = assertion_payload(
        m["matter_id"],
        m["repository_id"],
        proposition="Clause 8.4 creates a narrow exception to the Clause 8.2 notice obligation.",
    )
    r = client.post("/api/v1/assertions", json=similar_payload, headers=m["contributor_headers"])
    assert r.status_code == 201
    assert r.json().get("similar_assertions", []) != []


def test_related_assertions_endpoint_surfaces_candidates(client, matter_with_users):
    m = matter_with_users
    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.get(f"/api/v1/assertions/{assertion_id}/related", headers=m["contributor_headers"])
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_evidence_from_inaccessible_matter_cannot_be_attached(client, matter_with_users, db_session):
    from tests.conftest import seed_organization, seed_repository, seed_matter, seed_document, seed_source_span

    m = matter_with_users
    other_org = seed_organization(db_session, name="Other Org")
    other_repo = seed_repository(db_session, organization_id=other_org)
    other_matter = seed_matter(db_session, repository_id=other_repo)
    other_doc = seed_document(db_session, repository_id=other_repo, matter_id=other_matter)
    other_span = seed_source_span(db_session, document_id=other_doc, matter_id=other_matter)

    create = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    assertion_id = create.json()["id"]
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/evidence",
        json={"source_span_id": other_span, "evidence_role": "supports"},
        headers=m["contributor_headers"],
    )
    assert r.status_code in (403, 404, 422)
