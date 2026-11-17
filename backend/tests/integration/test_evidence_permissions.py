"""Who may attach and remove evidence (audit finding api:11, spec section 12).

Attaching or removing evidence modifies the assertion, so it follows the
edit rule: a contributor may change the evidence of their own unreviewed
(draft, proposed, revision-requested) assertion; a reviewer or admin may
change any assertion's evidence. An accepted assertion keeps at least one
supporting span, and one span is attached at most once per role.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models.assertion_evidence import AssertionEvidence
from tests.conftest import (
    assertion_payload,
    auth_header,
    seed_document,
    seed_matter_role,
    seed_source_span,
    seed_user,
)


def _span(db_session, m) -> str:
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    return seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"])


def _create(client, m, headers, **overrides) -> str:
    response = client.post("/api/v1/assertions",
                           json=assertion_payload(m["matter_id"], m["repository_id"], **overrides),
                           headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _evidence(client, m, assertion_id) -> list[dict]:
    return client.get(f"/api/v1/assertions/{assertion_id}/evidence", headers=m["reviewer_headers"]).json()


def _attach(client, assertion_id, span, headers, role="supports"):
    return client.post(f"/api/v1/assertions/{assertion_id}/evidence",
                       json={"source_span_id": span, "evidence_role": role}, headers=headers)


def _accepted(client, db_session, m, author_headers) -> tuple[str, str]:
    span = _span(db_session, m)
    assertion_id = _create(client, m, author_headers, save_as="proposed",
                           evidence=[{"source_span_id": span, "evidence_role": "supports"}])
    accepted = client.post(f"/api/v1/assertions/{assertion_id}/accept", headers=m["reviewer_headers"])
    assert accepted.json()["status"] == "accepted", accepted.text
    return assertion_id, _evidence(client, m, assertion_id)[0]["id"]


def test_a_contributor_cannot_strip_another_users_accepted_assertion(client, db_session, matter_with_users):
    m = matter_with_users
    assertion_id, evidence_id = _accepted(client, db_session, m, m["reviewer_headers"])

    response = client.delete(f"/api/v1/assertions/{assertion_id}/evidence/{evidence_id}",
                             headers=m["contributor_headers"])

    assert response.status_code == 403, response.text
    detail = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["reviewer_headers"]).json()
    assert (detail["status"], detail["evidence_status"]) == ("accepted", "evidenced")


@pytest.mark.parametrize("status", ["proposed", "draft"])
def test_a_contributor_cannot_change_the_evidence_of_someone_elses_assertion(client, db_session,
                                                                            matter_with_users, status):
    m = matter_with_users
    span = _span(db_session, m)
    assertion_id = _create(client, m, m["contributor_headers"], save_as=status,
                           evidence=[{"source_span_id": span, "evidence_role": "supports"}])
    evidence_id = _evidence(client, m, assertion_id)[0]["id"]

    assert _attach(client, assertion_id, _span(db_session, m), m["rater_headers"]).status_code == 403
    assert client.delete(f"/api/v1/assertions/{assertion_id}/evidence/{evidence_id}",
                         headers=m["rater_headers"]).status_code == 403
    assert [e["id"] for e in _evidence(client, m, assertion_id)] == [evidence_id]


@pytest.mark.parametrize("decision", ["accept", "withdraw"])
def test_an_author_cannot_change_the_evidence_once_the_assertion_left_review(client, db_session,
                                                                            matter_with_users, decision):
    m = matter_with_users
    span = _span(db_session, m)
    assertion_id = _create(client, m, m["contributor_headers"], save_as="proposed",
                           evidence=[{"source_span_id": span, "evidence_role": "supports"}])
    headers = m["reviewer_headers"] if decision == "accept" else m["contributor_headers"]
    assert client.post(f"/api/v1/assertions/{assertion_id}/{decision}", headers=headers).status_code == 200
    evidence_id = _evidence(client, m, assertion_id)[0]["id"]

    assert _attach(client, assertion_id, _span(db_session, m), m["contributor_headers"]).status_code == 403
    assert client.delete(f"/api/v1/assertions/{assertion_id}/evidence/{evidence_id}",
                         headers=m["contributor_headers"]).status_code == 403


@pytest.mark.parametrize("status", ["draft", "proposed", "revision_requested"])
def test_an_author_manages_the_evidence_of_their_unreviewed_assertion(client, db_session,
                                                                     matter_with_users, status):
    m = matter_with_users
    assertion_id = _create(client, m, m["contributor_headers"], save_as="draft" if status == "draft" else "proposed")
    if status == "revision_requested":
        client.post(f"/api/v1/assertions/{assertion_id}/request-revision", headers=m["reviewer_headers"])
    # Evidence a reviewer attached is the author's to curate too.
    by_reviewer = _attach(client, assertion_id, _span(db_session, m), m["reviewer_headers"])
    assert by_reviewer.status_code == 201, by_reviewer.text

    mine = _attach(client, assertion_id, _span(db_session, m), m["contributor_headers"], role="contradicts")
    assert mine.status_code == 201, mine.text
    for evidence_id in (by_reviewer.json()["id"], mine.json()["id"]):
        assert client.delete(f"/api/v1/assertions/{assertion_id}/evidence/{evidence_id}",
                             headers=m["contributor_headers"]).status_code == 204
    assert _evidence(client, m, assertion_id) == []


def test_viewers_and_outsiders_cannot_change_evidence(client, db_session, matter_with_users):
    m = matter_with_users
    viewer = seed_user(db_session)
    seed_matter_role(db_session, user_id=viewer, matter_id=m["matter_id"], role="viewer")
    span = _span(db_session, m)
    assertion_id = _create(client, m, m["contributor_headers"], evidence=[{"source_span_id": span,
                                                                           "evidence_role": "supports"}])
    evidence_id = _evidence(client, m, assertion_id)[0]["id"]
    for headers in (auth_header(viewer), m["outsider_headers"]):
        assert _attach(client, assertion_id, _span(db_session, m), headers).status_code == 403
        assert client.delete(f"/api/v1/assertions/{assertion_id}/evidence/{evidence_id}",
                             headers=headers).status_code == 403


def test_a_reviewer_keeps_an_accepted_assertion_supported(client, db_session, matter_with_users):
    m = matter_with_users
    assertion_id, only_support = _accepted(client, db_session, m, m["contributor_headers"])
    path = f"/api/v1/assertions/{assertion_id}/evidence"

    refused = client.delete(f"{path}/{only_support}", headers=m["reviewer_headers"])
    assert refused.status_code == 409, refused.text
    assert "supporting" in refused.json()["detail"]

    context = _attach(client, assertion_id, _span(db_session, m), m["reviewer_headers"], role="contextualizes")
    assert client.delete(f"{path}/{context.json()['id']}", headers=m["reviewer_headers"]).status_code == 204
    replacement = _attach(client, assertion_id, _span(db_session, m), m["reviewer_headers"], role="primary_basis")
    assert replacement.status_code == 201, replacement.text
    assert client.delete(f"{path}/{only_support}", headers=m["reviewer_headers"]).status_code == 204
    detail = client.get(f"/api/v1/assertions/{assertion_id}", headers=m["reviewer_headers"]).json()
    assert (detail["status"], detail["evidence_status"]) == ("accepted", "evidenced")


def test_a_span_is_attached_at_most_once_per_role(client, db_session, matter_with_users):
    m = matter_with_users
    span = _span(db_session, m)
    assertion_id = _create(client, m, m["contributor_headers"])

    assert _attach(client, assertion_id, span, m["contributor_headers"]).status_code == 201
    again = _attach(client, assertion_id, span, m["contributor_headers"])
    assert again.status_code == 409, again.text
    assert _attach(client, assertion_id, span, m["contributor_headers"], role="qualifies").status_code == 201
    assert db_session.scalar(select(func.count()).select_from(AssertionEvidence)) == 2

    twice = client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], proposition="Another proposition entirely.",
        evidence=[{"source_span_id": span, "evidence_role": "supports"}] * 2), headers=m["contributor_headers"])
    assert twice.status_code == 422, twice.text
    assert db_session.scalar(select(func.count()).select_from(AssertionEvidence)) == 2
