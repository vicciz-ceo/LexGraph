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


# --- Which existing assertions an exact duplicate collides with (api:16,
# api:17). Only LIVE assertions -- proposed, revision_requested, accepted,
# disputed -- and the author's own drafts block; withdrawn, rejected and
# superseded ones and other users' drafts are returned as non-blocking
# `similar_assertions`. The same rule guards create, edit (PATCH and
# POST /revisions) and submitting a draft.

import pytest  # noqa: E402

from tests.conftest import new_id  # noqa: E402

_TEXT = "The notice period is thirty days."


def _create(client, m, proposition=_TEXT, *, save_as="proposed", headers=None):
    return client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], proposition=proposition, save_as=save_as),
        headers=headers or m["contributor_headers"],
    )


def _accept(client, m, assertion_id):
    r = client.post(f"/api/v1/assertions/{assertion_id}/accept",
                    json={"acceptance_justification": "Checked against the clause text."},
                    headers=m["reviewer_headers"])
    assert r.status_code == 200, r.text


def _move_to(client, m, assertion_id, status):
    path = f"/api/v1/assertions/{assertion_id}"
    if status == "withdrawn":
        r = client.post(path + "/withdraw", headers=m["contributor_headers"])
    elif status == "rejected":
        r = client.post(path + "/reject", headers=m["reviewer_headers"])
    elif status == "disputed":
        r = client.post(path + "/dispute", headers=m["reviewer_headers"])
    elif status == "revision_requested":
        r = client.post(path + "/request-revision", json={"comment": "Cite the clause."},
                        headers=m["reviewer_headers"])
    elif status == "accepted":
        return _accept(client, m, assertion_id)
    elif status == "superseded":
        _accept(client, m, assertion_id)
        successor = _create(client, m, "A narrower successor proposition.").json()["id"]
        _accept(client, m, successor)
        r = client.post(path + "/supersede", json={"superseded_by_assertion_id": successor},
                        headers=m["reviewer_headers"])
    else:
        return None
    assert r.status_code == 200, r.text
    assert client.get(path, headers=m["reviewer_headers"]).json()["status"] == status


@pytest.mark.parametrize("ended", ["withdrawn", "rejected", "superseded"])
def test_an_ended_assertion_does_not_block_proposing_the_same_text_again(client, matter_with_users, ended):
    m = matter_with_users
    old = _create(client, m).json()["id"]
    _move_to(client, m, old, ended)

    again = _create(client, m, "  the notice period is THIRTY days.  ")

    assert again.status_code == 201, again.text
    assert {"assertion_id": old, "match_kind": "exact_proposition", "score": 1.0} in again.json()["similar_assertions"]


@pytest.mark.parametrize("live", ["proposed", "revision_requested", "accepted", "disputed"])
def test_a_live_assertion_blocks_an_exact_duplicate_from_any_user(client, matter_with_users, live):
    m = matter_with_users
    old = _create(client, m).json()["id"]
    _move_to(client, m, old, live)

    duplicate = _create(client, m, _TEXT.upper(), save_as="draft", headers=m["rater_headers"])

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == (
        f"duplicate: an identical proposition already exists in this matter (assertion {old})")


def test_another_users_draft_does_not_block_but_cannot_be_submitted_over_a_live_twin(client, matter_with_users):
    m = matter_with_users
    draft = _create(client, m, save_as="draft", headers=m["rater_headers"]).json()["id"]

    mine = _create(client, m)
    assert mine.status_code == 201, mine.text
    assert draft in {s["assertion_id"] for s in mine.json()["similar_assertions"]}

    submit = client.post(f"/api/v1/assertions/{draft}/submit", headers=m["rater_headers"])
    assert submit.status_code == 409
    assert mine.json()["id"] in submit.json()["detail"]
    assert client.get(f"/api/v1/assertions/{draft}", headers=m["rater_headers"]).json()["status"] == "draft"


def test_an_authors_own_draft_blocks_an_identical_new_assertion_until_it_is_withdrawn(client, matter_with_users):
    m = matter_with_users
    draft = _create(client, m, save_as="draft").json()["id"]
    for save_as in ("draft", "proposed"):
        r = _create(client, m, save_as=save_as)
        assert r.status_code == 409 and draft in r.json()["detail"], r.text

    assert client.post(f"/api/v1/assertions/{draft}/submit", headers=m["contributor_headers"]).status_code == 200
    assert client.post(f"/api/v1/assertions/{draft}/withdraw", headers=m["contributor_headers"]).status_code == 200
    assert _create(client, m).status_code == 201


@pytest.mark.parametrize("route", ["patch", "revisions"])
def test_an_edit_cannot_copy_a_live_assertions_proposition(client, matter_with_users, route):
    m = matter_with_users
    target = _create(client, m, "Clause 4 limits liability to fees paid.").json()["id"]
    edited = _create(client, m, "Clause 4 limits liability.").json()["id"]
    body = {"proposition": "  clause 4 LIMITS liability to fees paid. ", "expected_revision_number": 1}

    if route == "patch":
        r = client.patch(f"/api/v1/assertions/{edited}", json=body, headers=m["contributor_headers"])
    else:
        r = client.post(f"/api/v1/assertions/{edited}/revisions", json=body, headers=m["contributor_headers"])

    assert r.status_code == 409
    assert r.json()["detail"] == (
        f"duplicate: an identical proposition already exists in this matter (assertion {target})")
    after = client.get(f"/api/v1/assertions/{edited}", headers=m["contributor_headers"]).json()
    assert (after["current_revision_number"], after["proposition"]) == (1, "Clause 4 limits liability.")


def test_an_edit_may_take_an_ended_assertions_text_and_keep_its_own(client, db_session, matter_with_users):
    from datetime import datetime, timezone

    from app.models.assertion import Assertion

    m = matter_with_users
    ended = _create(client, m, "Old wording.").json()["id"]
    _move_to(client, m, ended, "withdrawn")
    edited = _create(client, m, "New wording.").json()["id"]
    path = f"/api/v1/assertions/{edited}"

    r = client.patch(path, json={"proposition": "Old wording.", "expected_revision_number": 1},
                     headers=m["contributor_headers"])
    assert r.status_code == 200, r.text

    # A live twin left behind by the old unguarded paths does not stop edits
    # that keep the proposition (here: only its case changes).
    now = datetime.now(timezone.utc)
    db_session.add(Assertion(
        id=new_id(), organization_id=m["organization_id"], repository_id=m["repository_id"],
        matter_id=m["matter_id"], assertion_type="CREATES_EXCEPTION_TO", proposition="Old wording.",
        subject_entity_type="Provision", subject_entity_id=new_id(), origin="user_suggested",
        status="proposed", author_user_id=m["rater_id"], created_at=now, updated_at=now,
        current_revision_number=1,
    ))
    db_session.commit()
    r = client.patch(path, json={"proposition": "OLD WORDING.", "expected_revision_number": 2},
                     headers=m["contributor_headers"])
    assert r.status_code == 200, r.text
    r = client.patch(path, json={"proposition": "Fresh wording.", "expected_revision_number": 3},
                     headers=m["contributor_headers"])
    assert r.status_code == 200, r.text
    r = client.patch(path, json={"proposition": "Old wording.", "expected_revision_number": 4},
                     headers=m["contributor_headers"])
    assert r.status_code == 409, r.text
