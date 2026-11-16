"""Write semantics of assertion creation and edits.

Audit findings review:5 (the length cap runs before the sanitizer) and
review:20 (an explanation is never silently dropped). Every test drives the
real HTTP app.
"""

from __future__ import annotations

import time

import pytest
from sqlalchemy import func, select

from app.models.assertion_comment import AssertionComment
from app.models.audit_event import AuditEvent
from tests.conftest import assertion_payload, seed_document, seed_source_span


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
