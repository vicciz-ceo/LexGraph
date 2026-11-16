"""Edge inputs are 4xx, never 500 (audit finding api:20).

An escaped lone surrogate in any text field of a JSON body answered 500 (it
cannot be encoded as UTF-8: neither bound to SQLite nor echoed in a 422
body), and so did a revision number too large for an SQLite INTEGER.
Requests go through the real HTTP app.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.audit_event import AuditEvent
from tests.conftest import assertion_payload


def _count(db_session, model) -> int:
    return db_session.scalar(select(func.count()).select_from(model))


# --- Lone surrogates are refused up front, in every JSON body ---------------


def _surrogate_cases(m, assertion_id: str) -> list[tuple[str, str, str]]:
    payload = json.dumps(assertion_payload(m["matter_id"], m["repository_id"], proposition="@P@"))
    agent = json.dumps({**assertion_payload(m["matter_id"], m["repository_id"], proposition="@P@"),
                        "agent": {"platform": "@P@"}})
    return [
        ("POST", "/api/v1/assertions", payload.replace("@P@", "lone \\ud800 surrogate")),
        ("POST", "/api/v1/assertions", payload.replace('"draft"', '"\\udfff"')),  # echoed by a 422
        ("POST", "/api/v1/agent/assertions", agent.replace('"@P@"}', '"\\udbff"}')),
        ("PATCH", f"/api/v1/assertions/{assertion_id}", '{"proposition": "x \\udc00 y"}'),
        ("PATCH", f"/api/v1/assertions/{assertion_id}", '{"assertion_type": "T\\ud800"}'),
        ("POST", f"/api/v1/assertions/{assertion_id}/revisions", '{"revision_reason": "\\ud800"}'),
        ("POST", f"/api/v1/assertions/{assertion_id}/evidence",
         '{"source_span_id": "\\ud800", "evidence_role": "supports"}'),
        ("POST", f"/api/v1/assertions/{assertion_id}/comments", '{"comment_text": "lone \\ud800 surrogate"}'),
        ("PUT", f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
         '{"strength": 4, "rationale": "\\ud800"}'),
        ("POST", "/api/v1/users", '{"email": "a\\ud800@example.test", "display_name": "x"}'),
        ("POST", f"/api/v1/assertions/{assertion_id}/comments", '{"\\ud800": "key"}'),
    ]


def test_a_lone_surrogate_anywhere_in_a_json_body_is_a_422(client, db_session, matter_with_users):
    m = matter_with_users
    created = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"]),
                          headers=m["contributor_headers"]).json()
    before = (_count(db_session, Assertion), _count(db_session, AssertionComment), _count(db_session, AuditEvent))

    for method, path, raw in _surrogate_cases(m, created["id"]):
        response = client.request(method, path, content=raw.encode("ascii"),
                                  headers={**m["reviewer_headers"], "Content-Type": "application/json"})
        assert response.status_code == 422, (method, path, raw, response.text)
        assert "surrogate" in response.json()["detail"]

    after = (_count(db_session, Assertion), _count(db_session, AssertionComment), _count(db_session, AuditEvent))
    assert after == before
    assert client.get(f"/api/v1/assertions/{created['id']}",
                      headers=m["reviewer_headers"]).json()["current_revision_number"] == 1


def test_raw_surrogate_bytes_are_refused_too(client, matter_with_users):
    m = matter_with_users
    raw = json.dumps(assertion_payload(m["matter_id"], m["repository_id"], proposition="@P@")).encode()
    raw = raw.replace(b"@P@", b"lone \xed\xa0\x80 surrogate")  # what json.loads decodes to U+D800
    for content_type in ("application/json", "text/plain"):
        response = client.post("/api/v1/assertions", content=raw,
                               headers={**m["contributor_headers"], "Content-Type": content_type})
        assert response.status_code == 422, response.text


def test_escaped_surrogate_pairs_and_other_escapes_are_ordinary_text(client, matter_with_users):
    m = matter_with_users
    raw = json.dumps(assertion_payload(m["matter_id"], m["repository_id"],
                                       proposition="Clause 4 \U0001F600 סעיף \\ud800 as text"),
                     ensure_ascii=True)
    response = client.post("/api/v1/assertions", content=raw.encode("ascii"),
                           headers={**m["contributor_headers"], "Content-Type": "application/json"})
    assert response.status_code == 201, response.text
    assert response.json()["proposition_raw"] == "Clause 4 \U0001F600 סעיף \\ud800 as text"


# --- Oversized revision numbers are 404, never 500 --------------------------


@pytest.mark.parametrize("method,suffix", [
    ("GET", "rating"), ("PUT", "rating"), ("DELETE", "rating"), ("GET", "ratings/summary"),
    ("GET", "ratings"),
])
@pytest.mark.parametrize("number", ["99999999999999999999", "9223372036854775808", "0", "-1"])
def test_a_revision_number_no_revision_can_have_is_a_404(client, matter_with_users, method, suffix, number):
    m = matter_with_users
    created = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"]),
                          headers=m["contributor_headers"]).json()
    response = client.request(method, f"/api/v1/assertions/{created['id']}/revisions/{number}/{suffix}",
                              json={"strength": 4} if method == "PUT" else None,
                              headers=m["rater_headers"])
    assert response.status_code == 404, response.text


def test_an_oversized_expected_revision_number_is_a_stale_conflict(client, matter_with_users):
    m = matter_with_users
    created = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"]),
                          headers=m["contributor_headers"]).json()
    response = client.patch(f"/api/v1/assertions/{created['id']}",
                            json={"proposition": "x", "expected_revision_number": 99999999999999999999},
                            headers=m["contributor_headers"])
    assert response.status_code == 409, response.text
