"""Write semantics of assertion creation and edits.

Audit findings api:18, review:3, review:8, ui:11 (an edit that changes
nothing material creates nothing), review:5 (the length cap runs before the
sanitizer) and review:20 (an explanation is never silently dropped). Every
test drives the real HTTP app.
"""

from __future__ import annotations

import time

import pytest
from sqlalchemy import func, select

from app.models.assertion_comment import AssertionComment
from app.models.assertion_revision import AssertionRevision
from app.models.audit_event import AuditEvent
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


def _create(client, m, headers=None, **overrides) -> dict:
    response = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], **overrides),
        headers=headers or m["contributor_headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()


def _accepted_rated(client, db_session, m) -> dict:
    """A contributor's proposed assertion with evidence and one rating, accepted."""
    created = _create(client, m, save_as="proposed",
                      evidence=[{"source_span_id": _span(db_session, m), "evidence_role": "supports"}])
    path = f"/api/v1/assertions/{created['id']}"
    rated = client.put(path + "/revisions/1/rating", json={"strength": 5}, headers=m["rater_headers"])
    assert rated.status_code in (200, 201), rated.text
    accepted = client.post(path + "/accept", headers=m["reviewer_headers"])
    assert (accepted.status_code, accepted.json()["status"]) == (200, "accepted"), accepted.text
    return client.get(path, headers=m["reviewer_headers"]).json()


def _revision_count(db_session, assertion_id: str) -> int:
    return db_session.scalar(select(func.count()).select_from(AssertionRevision).where(
        AssertionRevision.assertion_id == assertion_id))


def _revised_events(db_session, assertion_id: str) -> int:
    return db_session.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.assertion_id == assertion_id, AuditEvent.event_type == "assertion_revised"))


_UNCHANGED_KEYS = ("status", "current_revision_number", "reviewed_by", "reviewed_at", "updated_at",
                   "proposition", "proposition_raw", "standing")


# --- An edit that changes nothing material creates nothing (api:18 et al.) --


@pytest.mark.parametrize("route", ["patch", "revisions"])
def test_resaving_an_accepted_rated_assertion_unchanged_changes_nothing(client, db_session,
                                                                        matter_with_users, route):
    m = matter_with_users
    before = _accepted_rated(client, db_session, m)
    path = f"/api/v1/assertions/{before['id']}"
    body = {"proposition": before["proposition_raw"], "revision_reason": "Tightened wording",
            "expected_revision_number": 1}

    if route == "patch":
        response = client.patch(path, json=body, headers=m["reviewer_headers"])
        assert response.status_code == 200, response.text
    else:
        response = client.post(path + "/revisions", json=body, headers=m["reviewer_headers"])
        # POST /revisions answers 201 only when it created a revision.
        assert response.status_code == 200, response.text
        assert response.json()["revision_number"] == 1
        assert response.json()["revision_reason"] == "initial creation"

    after = client.get(path, headers=m["reviewer_headers"]).json()
    assert {k: after[k] for k in _UNCHANGED_KEYS} == {k: before[k] for k in _UNCHANGED_KEYS}
    assert after["ratings_summary"]["count"] == 1
    assert _revision_count(db_session, before["id"]) == 1
    assert _revised_events(db_session, before["id"]) == 0
    edges = client.get(f"/api/v1/matters/{m['matter_id']}/graph", headers=m["reviewer_headers"]).json()["edges"]
    assert [e["assertion_id"] for e in edges] == [before["id"]]


def test_resending_every_current_value_is_a_no_op(client, db_session, matter_with_users):
    m = matter_with_users
    created = _create(client, m, save_as="proposed", jurisdiction="US-CA",
                      effective_from="2030-01-01T00:00:00", effective_to="2031-06-30T12:00:00Z")
    path = f"/api/v1/assertions/{created['id']}"
    body = {
        "proposition": created["proposition_raw"],
        "assertion_type": created["assertion_type"],
        "subject_entity": created["subject_entity"],
        "object_entity": created["object_entity"],
        "jurisdiction": "US-CA",
        # The same instants, written with other offsets.
        "effective_from": "2030-01-01T05:30:00+05:30",
        "effective_to": "2031-06-30T07:00:00-05:00",
        "revision_reason": "no real change",
    }
    for method, suffix in ((client.patch, ""), (client.post, "/revisions")):
        response = method(path + suffix, json=body, headers=m["contributor_headers"])
        assert response.status_code == 200, response.text
    after = client.get(path, headers=m["contributor_headers"]).json()
    assert after["current_revision_number"] == 1
    assert after["updated_at"] == created["updated_at"]
    assert _revision_count(db_session, created["id"]) == 1


def test_an_authors_unchanged_save_keeps_ratings_and_standing(client, db_session, matter_with_users):
    m = matter_with_users
    created = _create(client, m, save_as="proposed")
    path = f"/api/v1/assertions/{created['id']}"
    extra_rater = seed_user(db_session)
    seed_matter_role(db_session, user_id=extra_rater, matter_id=m["matter_id"], role="contributor")
    for headers in (m["rater_headers"], auth_header(extra_rater)):
        assert client.put(path + "/revisions/1/rating", json={"strength": 2},
                          headers=headers).status_code in (200, 201)
    before = client.get(path, headers=m["contributor_headers"]).json()
    assert before["standing"] == "weak"

    response = client.patch(path, json={"proposition": created["proposition_raw"],
                                        "revision_reason": "shed the weak ratings"},
                            headers=m["contributor_headers"])

    assert response.status_code == 200, response.text
    after = client.get(path, headers=m["contributor_headers"]).json()
    assert (after["standing"], after["current_revision_number"]) == ("weak", 1)
    assert after["ratings_summary"]["count"] == 2
    assert [r["revision_reason"] for r in after["revision_history"]] == ["initial creation"]


@pytest.mark.parametrize("body", [{}, {"revision_reason": "annotating only"},
                                  {"jurisdiction": None}, {"object_entity": None},
                                  {"effective_to": None}])
def test_post_revisions_without_a_material_change_answers_200_and_creates_nothing(
        client, db_session, matter_with_users, body):
    m = matter_with_users
    created = _create(client, m, object_entity=None)
    path = f"/api/v1/assertions/{created['id']}"

    response = client.post(path + "/revisions", json=body, headers=m["contributor_headers"])
    assert response.status_code == 200, response.text
    assert response.json()["revision_number"] == 1
    patched = client.patch(path, json=body, headers=m["contributor_headers"])
    assert (patched.status_code, patched.json()["current_revision_number"]) == (200, 1)
    assert [r["revision_number"] for r in client.get(path + "/revisions",
                                                     headers=m["contributor_headers"]).json()] == [1]


@pytest.mark.parametrize("change", [
    {"proposition": "A different proposition."},
    {"proposition": "  Clause 8.4 creates a limited exception to the notification obligation in Clause 8.2."},
    {"assertion_type": "MODIFIES"},
    {"subject_entity": {"type": "Provision", "id": "00000000-0000-4000-8000-000000000001"}},
    {"object_entity": None},
    {"jurisdiction": "US-NY"},
    {"effective_from": "2030-01-01"},
])
def test_each_real_change_still_creates_a_revision(client, matter_with_users, change):
    m = matter_with_users
    created = _create(client, m)
    path = f"/api/v1/assertions/{created['id']}"

    response = client.post(path + "/revisions", json={**change, "revision_reason": "real change"},
                           headers=m["contributor_headers"])

    assert response.status_code == 201, response.text
    assert (response.json()["revision_number"], response.json()["revision_reason"]) == (2, "real change")


def test_a_material_edit_of_an_accepted_assertion_still_returns_it_to_review(client, db_session,
                                                                            matter_with_users):
    m = matter_with_users
    before = _accepted_rated(client, db_session, m)

    response = client.patch(f"/api/v1/assertions/{before['id']}",
                            json={"proposition": before["proposition_raw"] + " (as amended)",
                                  "expected_revision_number": 1},
                            headers=m["reviewer_headers"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["status"], body["current_revision_number"], body["reviewed_by"]) == ("proposed", 2, None)
    assert _revised_events(db_session, before["id"]) == 1


def test_a_no_op_body_is_still_validated_and_stale_checked(client, matter_with_users):
    m = matter_with_users
    created = _create(client, m)
    path = f"/api/v1/assertions/{created['id']}"
    same = {"proposition": created["proposition_raw"]}

    assert client.patch(path, json={**same, "jurisdiction": "NOT-A-CODE"},
                        headers=m["contributor_headers"]).status_code == 422
    client.patch(path, json={"proposition": "Moves the assertion to revision 2."},
                 headers=m["contributor_headers"])
    stale = client.patch(path, json={"proposition": "Moves the assertion to revision 2.",
                                     "expected_revision_number": 1},
                         headers=m["contributor_headers"])
    assert stale.status_code == 409
    assert client.patch(path, json=same, headers=m["rater_headers"]).status_code == 403


# --- The length cap runs before the sanitizer (review:5) --------------------


_HOSTILE_OVER_CAP = "<title>" * 16_000 + "x"  # 112,001 characters; ~10 s to sanitize


def test_an_over_cap_hostile_proposition_is_rejected_before_it_is_sanitized(client, db_session,
                                                                            matter_with_users):
    m = matter_with_users
    created = _create(client, m)
    path = f"/api/v1/assertions/{created['id']}"
    span = _span(db_session, m)
    agent_body = {**assertion_payload(m["matter_id"], m["repository_id"], proposition=_HOSTILE_OVER_CAP,
                                      object_entity=None),
                  "subject_entity": {"type": "SourceSpan", "id": span}, "agent": {"platform": "pytest"}}
    calls = [
        lambda: client.patch(path, json={"proposition": _HOSTILE_OVER_CAP}, headers=m["contributor_headers"]),
        lambda: client.post(path + "/revisions", json={"proposition": _HOSTILE_OVER_CAP},
                            headers=m["contributor_headers"]),
        lambda: client.post("/api/v1/assertions", json=assertion_payload(
            m["matter_id"], m["repository_id"], proposition=_HOSTILE_OVER_CAP), headers=m["contributor_headers"]),
        lambda: client.post("/api/v1/assertions", json=assertion_payload(
            m["matter_id"], m["repository_id"], explanation=_HOSTILE_OVER_CAP), headers=m["contributor_headers"]),
        lambda: client.post("/api/v1/agent/assertions", json=agent_body, headers=m["contributor_headers"]),
    ]
    for call in calls:
        started = time.perf_counter()
        response = call()
        elapsed = time.perf_counter() - started
        assert response.status_code == 422, response.text
        assert "100,000" in response.json()["detail"]
        assert elapsed < 2.0, f"over-cap input was sanitized before the cap check ({elapsed:.1f}s)"


# --- An explanation is never silently dropped (review:20) -------------------


@pytest.mark.parametrize("explanation", [
    "<script>var why = 'the basis is clause 4';</script>",
    "<see clause 4>",
])
@pytest.mark.parametrize("route", ["/api/v1/assertions", "/api/v1/agent/assertions"])
def test_an_explanation_that_sanitizes_to_nothing_is_kept_as_the_initial_comment(
        client, db_session, matter_with_users, explanation, route):
    m = matter_with_users
    body = assertion_payload(m["matter_id"], m["repository_id"], explanation=explanation)
    if route.endswith("agent/assertions"):
        body.update(subject_entity={"type": "SourceSpan", "id": _span(db_session, m)}, object_entity=None,
                    agent={"platform": "pytest"})

    response = client.post(route, json=body, headers=m["contributor_headers"])

    assert response.status_code == 201, response.text
    comments = client.get(f"/api/v1/assertions/{response.json()['id']}/comments",
                          headers=m["contributor_headers"]).json()
    assert [(c["comment_text_raw"], c["user_id"]) for c in comments] == [(explanation, m["contributor_id"])]
    assert comments[0]["comment_text"] == ""  # exactly what POST /comments stores for this text
    assert db_session.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.assertion_id == response.json()["id"], AuditEvent.event_type == "comment_created")) == 1


@pytest.mark.parametrize("explanation", [None, "", "   \n"])
def test_a_blank_explanation_creates_no_comment(client, db_session, matter_with_users, explanation):
    m = matter_with_users
    created = _create(client, m, explanation=explanation)
    assert db_session.scalar(select(func.count()).select_from(AssertionComment).where(
        AssertionComment.assertion_id == created["id"])) == 0
