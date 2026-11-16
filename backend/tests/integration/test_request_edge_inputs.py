"""Edge inputs are 4xx, never 500 (audit finding api:20, review persistence:2).

An escaped lone surrogate in any text field of a JSON body answered 500 (it
cannot be encoded as UTF-8: neither bound to SQLite nor echoed in a 422
body), and so did a revision number too large for an SQLite INTEGER.
Requests go through the real HTTP app.
"""

from __future__ import annotations

import asyncio
import codecs
import json

import pytest
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.audit_event import AuditEvent
from app.models.notification import NotificationPreference
from app.models.user import User
from app.request_guards import contains_unpaired_surrogate, validation_error_response
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


# --- ... in every encoding the JSON parser accepts (review persistence:2) ----
#
# Starlette parses a JSON body with json.loads(bytes), which detects UTF-8,
# UTF-16 and UTF-32 (with or without a byte-order mark) and decodes with
# "surrogatepass". The guard matched UTF-8 byte patterns only, so the same
# lone surrogate sent as UTF-16 or UTF-32 got through and answered 500 (the
# 422 that echoed it could not be rendered, and POST /users failed binding
# it), while U+A0ED, whose UTF-16-LE bytes are ED A0, was refused as a
# surrogate.

JSON_ENCODINGS = {
    "utf-8 with BOM": lambda text: codecs.BOM_UTF8 + text.encode("utf-8", "surrogatepass"),
    "utf-16-le": lambda text: text.encode("utf-16-le", "surrogatepass"),
    "utf-16-be": lambda text: text.encode("utf-16-be", "surrogatepass"),
    "utf-16-le with BOM": lambda text: codecs.BOM_UTF16_LE + text.encode("utf-16-le", "surrogatepass"),
    "utf-16-be with BOM": lambda text: codecs.BOM_UTF16_BE + text.encode("utf-16-be", "surrogatepass"),
    "utf-32-le": lambda text: text.encode("utf-32-le", "surrogatepass"),
    "utf-32-be": lambda text: text.encode("utf-32-be", "surrogatepass"),
    "utf-32-le with BOM": lambda text: codecs.BOM_UTF32_LE + text.encode("utf-32-le", "surrogatepass"),
    "utf-32-be with BOM": lambda text: codecs.BOM_UTF32_BE + text.encode("utf-32-be", "surrogatepass"),
}


def _encoded_surrogate_cases(m, assertion_id: str) -> list[tuple[str, str, str]]:
    """(method, path, JSON text): each carries a lone surrogate, raw or escaped."""
    payload = json.dumps(assertion_payload(m["matter_id"], m["repository_id"], proposition="@P@"))
    agent = json.dumps({**assertion_payload(m["matter_id"], m["repository_id"], proposition="ok"),
                        "agent": {"platform": "pytest", "model": "@P@"}})
    cases = []
    for lone in ("\ud800", "\\ud800", "\udfff", "\\uDBFF"):
        cases += [
            ("POST", "/api/v1/assertions", payload.replace("@P@", f"x {lone} y")),
            ("POST", "/api/v1/agent/assertions", agent.replace("@P@", lone)),
            ("PATCH", f"/api/v1/assertions/{assertion_id}", f'{{"proposition": "edit {lone}"}}'),
            ("POST", f"/api/v1/assertions/{assertion_id}/revisions", f'{{"proposition": "rev {lone}"}}'),
            ("POST", "/api/v1/users", f'{{"email": "u@example.test", "display_name": "{lone}"}}'),
            ("PUT", "/api/v1/notifications/preferences", f'{{"preferences": {{"{lone}": true}}}}'),
        ]
    return cases


@pytest.mark.parametrize("encoding", JSON_ENCODINGS)
def test_a_lone_surrogate_is_a_422_in_every_json_encoding(app, db_session, matter_with_users, encoding):
    m = matter_with_users
    raw = TestClient(app, raise_server_exceptions=False)  # a 500 must show as a status, not raise
    created = raw.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"]),
                       headers=m["contributor_headers"]).json()
    before = (_count(db_session, Assertion), _count(db_session, AssertionComment), _count(db_session, AuditEvent),
              _count(db_session, User), _count(db_session, NotificationPreference))

    for method, path, text in _encoded_surrogate_cases(m, created["id"]):
        response = raw.request(method, path, content=JSON_ENCODINGS[encoding](text),
                               headers={**m["reviewer_headers"], "Content-Type": "application/json"})
        assert response.status_code == 422, (encoding, method, path, text, response.text)
        assert "surrogate" in response.json()["detail"], (encoding, method, path, text)

    after = (_count(db_session, Assertion), _count(db_session, AssertionComment), _count(db_session, AuditEvent),
             _count(db_session, User), _count(db_session, NotificationPreference))
    assert after == before
    assert raw.get(f"/api/v1/assertions/{created['id']}",
                   headers=m["reviewer_headers"]).json()["current_revision_number"] == 1


@pytest.mark.parametrize("encoding", JSON_ENCODINGS)
def test_valid_text_is_accepted_in_every_json_encoding(client, matter_with_users, encoding):
    """No false positive: U+A0ED and U+EDA0 are the bytes ED A0 in little- and
    big-endian UTF-16/32, an astral character is a surrogate *pair* in UTF-16,
    and an escaped pair is one character once parsed."""
    m = matter_with_users
    proposition = "Clause \ua0ed and \ueda0, \U0001F600 and @PAIR@ as text"
    body = json.dumps(assertion_payload(m["matter_id"], m["repository_id"], proposition=proposition),
                      ensure_ascii=False).replace("@PAIR@", "\\ud83d\\ude00")
    response = client.post("/api/v1/assertions", content=JSON_ENCODINGS[encoding](body),
                           headers={**m["contributor_headers"], "Content-Type": "application/json"})
    assert response.status_code == 201, (encoding, response.text)
    assert response.json()["proposition_raw"] == "Clause \ua0ed and \ueda0, \U0001F600 and \U0001F600 as text"


def test_the_guard_reads_a_body_exactly_as_the_json_parser_does():
    for encoding, encode in {"utf-8": lambda text: text.encode("utf-8", "surrogatepass"), **JSON_ENCODINGS}.items():
        for text in ('{"a": "\ud800"}', '{"a": "\\ud800"}', '{"\\udc00": 1}', '["\\ud83d"]'):
            assert contains_unpaired_surrogate(encode(text)), (encoding, text)
        for text in ('{"a": "\ua0ed\ueda0"}', '{"a": "\\ud83d\\ude00"}', '{"a": "\U0001F600"}',
                     '{"a": "\\\\ud800"}'):
            assert not contains_unpaired_surrogate(encode(text)), (encoding, text)
    # Bodies the parser cannot read are left to the route, which answers 400 or 422.
    for body in (b"\xff\xfe\xfd", '{"a": 1}'.encode("utf-16-le")[:-1], b"not json \\ud800"):
        assert not contains_unpaired_surrogate(body), body


# --- A 422 can always be rendered, whatever the body (review persistence:2) ---


@pytest.mark.parametrize("content_type,body", [
    ("text/plain", b"\xff\xfe\xfd"),                    # not UTF-8, so never parsed as JSON
    ("text/plain", "caf\xe9".encode("latin-1")),
    (None, b"\xff\xfd{"),                              # no Content-Type: not parsed either
    ("application/octet-stream", b"\x00\xd8\x00\xd8"),  # UTF-16 code units, not UTF-8
])
def test_a_body_that_is_not_utf8_json_is_a_4xx_never_a_500(app, matter_with_users, content_type, body):
    m = matter_with_users
    raw = TestClient(app, raise_server_exceptions=False)
    headers = {**m["contributor_headers"]}
    if content_type:
        headers["Content-Type"] = content_type
    for path in ("/api/v1/assertions", "/api/v1/notifications/preferences"):
        method = "PUT" if "preferences" in path else "POST"
        response = raw.request(method, path, content=body, headers=headers)
        assert response.status_code == 422, (path, content_type, body, response.text)
        assert isinstance(response.json()["detail"], list)


def test_the_validation_422_spells_undecodable_input_safely():
    """Defence in depth: whatever a validation error echoes, the 422 renders."""
    errors = [
        {"type": "model_attributes_type", "loc": ("body",), "msg": "m", "input": b"\xff\x00"},
        {"type": "string_type", "loc": ("body", "\ud800"), "msg": "m", "input": {"k\udc00": ["x\ud800", 1e999]}},
    ]
    response = asyncio.run(validation_error_response(None, RequestValidationError(errors)))
    detail = json.loads(response.body)["detail"]
    assert response.status_code == 422
    assert detail[0]["input"] == "\\xff\x00"
    assert detail[1]["loc"] == ["body", "\\ud800"]
    assert detail[1]["input"] == {"k\\udc00": ["x\\ud800", "Infinity"]}


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
