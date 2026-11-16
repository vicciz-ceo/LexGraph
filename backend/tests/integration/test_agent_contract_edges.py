"""Edges of the agent submission contract.

* agent:11 -- the documented agent JSON posted to the lawyer endpoint
  (POST /api/v1/assertions, one path segment away from the agent endpoint)
  used to be stored as a lawyer's user_suggested assertion, its `agent`
  provenance and `confidence` silently dropped; its exact-duplicate then
  blocked the correct submission forever. Undeclared keys are now a 422, and
  the agent-only ones point to POST /api/v1/agent/assertions.
* review:6 -- a non-finite confidence (`1e999`, `NaN`, `Infinity`, all valid
  JSON numbers for Python) answered 500: FastAPI's 422 echoes the input,
  which a JSON response cannot carry. Now a 422 with the value spelled as a
  string; the same holds for any field on any route.
* review:19 -- self-reported provenance (platform, model, run_id) was stored
  and echoed with its markup; it is now sanitized like other submitted text.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from app.models.assertion import Assertion
from app.models.audit_event import AuditEvent
from tests.conftest import assertion_payload, seed_document, seed_source_span


@pytest.fixture
def suggestion(db_session, matter_with_users):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"], title="MSA")
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"],
                            quote_text="Confidentiality shall survive termination.")
    return dict(repository_id=m["repository_id"], matter_id=m["matter_id"], assertion_type="SURVIVES_TERMINATION",
                proposition="The confidentiality obligation survives termination.",
                subject_entity={"type": "Document", "id": doc},
                evidence=[{"source_span_id": span, "evidence_role": "primary_basis"}],
                explanation="The survival sentence supplies the basis.",
                agent={"platform": "claude-code", "model": "test-model", "run_id": "test-run"}, confidence=0.8)


def _counts(db_session) -> tuple[int, int]:
    return (db_session.scalar(select(func.count()).select_from(Assertion)),
            db_session.scalar(select(func.count()).select_from(AuditEvent)))


# --- agent:11 ---------------------------------------------------------------


@pytest.mark.parametrize("sent", [("agent", "confidence"), ("agent",), ("confidence",)])
def test_the_lawyer_endpoint_refuses_agent_fields_and_points_to_the_agent_endpoint(client, db_session,
                                                                                   matter_with_users, suggestion,
                                                                                   sent):
    m = matter_with_users
    body = {key: value for key, value in suggestion.items() if key not in ("agent", "confidence") or key in sent}

    r = client.post("/api/v1/assertions", json=body, headers=m["contributor_headers"])

    assert r.status_code == 422, r.text
    (error,) = r.json()["detail"]
    assert error["type"] == "agent_endpoint_required"
    assert error["ctx"] == {"fields": list(sent)}
    assert "POST /api/v1/agent/assertions" in error["msg"]
    assert _counts(db_session) == (0, 0)
    # The mistake leaves nothing behind that would block the correct submission.
    agent = client.post("/api/v1/agent/assertions", json=suggestion, headers=m["contributor_headers"])
    assert agent.status_code == 201, agent.text
    assert (agent.json()["origin"], agent.json()["confidence"], agent.json()["agent_provenance"]) == (
        "model_suggested", 0.8, suggestion["agent"])


def test_the_lawyer_endpoint_refuses_any_undeclared_key(client, db_session, matter_with_users):
    m = matter_with_users
    body = assertion_payload(m["matter_id"], m["repository_id"], origin="model_suggested")

    r = client.post("/api/v1/assertions", json=body, headers=m["contributor_headers"])

    assert r.status_code == 422, r.text
    assert [(e["type"], e["loc"]) for e in r.json()["detail"]] == [("extra_forbidden", ["body", "origin"])]
    assert _counts(db_session) == (0, 0)


def test_a_lawyer_payload_is_still_a_user_suggestion(client, matter_with_users):
    m = matter_with_users
    r = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"]),
                    headers=m["contributor_headers"])

    assert r.status_code == 201, r.text
    assert (r.json()["origin"], r.json()["confidence"], r.json()["agent_provenance"]) == (
        "user_suggested", None, None)


# --- review:6 ---------------------------------------------------------------


def _raw_body(fields: dict, key: str, literal: str) -> str:
    """`fields` as JSON with `key` set to a raw JSON number literal."""
    return json.dumps(fields)[:-1] + f', "{key}": {literal}}}'


@pytest.mark.parametrize(("literal", "spelled"), [
    ("1e999", "Infinity"), ("-1e999", "-Infinity"), ("Infinity", "Infinity"), ("-Infinity", "-Infinity"),
    ("NaN", "NaN"),
])
def test_a_non_finite_confidence_is_a_422_that_names_the_value(client, db_session, matter_with_users,
                                                               suggestion, literal, spelled):
    fields = {key: value for key, value in suggestion.items() if key != "confidence"}

    r = client.post("/api/v1/agent/assertions", content=_raw_body(fields, "confidence", literal),
                    headers={**matter_with_users["contributor_headers"], "Content-Type": "application/json"})

    assert r.status_code == 422, r.text
    (error,) = r.json()["detail"]
    assert (error["type"], error["loc"], error["input"]) == ("finite_number", ["body", "confidence"], spelled)
    assert _counts(db_session) == (0, 0)


def test_non_finite_numbers_are_422_on_every_route(client, db_session, matter_with_users):
    m = matter_with_users
    headers = {**m["contributor_headers"], "Content-Type": "application/json"}
    fields = {key: value for key, value in assertion_payload(m["matter_id"], m["repository_id"]).items()
              if key != "effective_from"}

    created = client.post("/api/v1/assertions", content=_raw_body(fields, "effective_from", "1e999"),
                          headers=headers)
    assert created.status_code == 422, created.text
    assert created.json()["detail"][0]["input"] == "Infinity"
    assert _counts(db_session) == (0, 0)

    assertion = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"]),
                            headers=m["contributor_headers"]).json()
    rating = client.put(f"/api/v1/assertions/{assertion['id']}/revisions/1/rating",
                        content='{"strength": NaN, "rationale": null}',
                        headers={**m["rater_headers"], "Content-Type": "application/json"})
    assert rating.status_code == 422, rating.text
    assert rating.json()["detail"][0]["input"] == "NaN"


# --- review:19 --------------------------------------------------------------


def test_provenance_markup_is_removed_wherever_it_is_stored_or_shown(client, db_session, matter_with_users,
                                                                     suggestion):
    m = matter_with_users
    agent = {"platform": "<img src=x onerror=alert(1)>codex", "model": "<script>alert(2)</script>gpt-x",
             "run_id": "run <b>42</b>"}
    clean = {"platform": "codex", "model": "gpt-x", "run_id": "run 42"}

    r = client.post("/api/v1/agent/assertions", json={**suggestion, "agent": agent}, headers=m["contributor_headers"])

    assert r.status_code == 201, r.text
    assert r.json()["agent_provenance"] == clean
    path = f"/api/v1/assertions/{r.json()['id']}"
    assert client.get(path, headers=m["reviewer_headers"]).json()["agent_provenance"] == clean
    history = client.get(path + "/history", headers=m["reviewer_headers"]).json()
    assert [json.loads(e["new_value"]) for e in history if e["event_type"] == "assertion_agent_provenance"] == [clean]


@pytest.mark.parametrize("field", ["platform", "model", "run_id"])
def test_provenance_that_is_only_markup_is_refused(client, db_session, matter_with_users, suggestion, field):
    agent = {**suggestion["agent"], field: "<script>alert(1)</script> <b></b>"}

    r = client.post("/api/v1/agent/assertions", json={**suggestion, "agent": agent},
                    headers=matter_with_users["contributor_headers"])

    assert r.status_code == 422, r.text
    (error,) = r.json()["detail"]
    assert (error["type"], error["loc"]) == ("provenance_without_text", ["body", "agent", field])
    assert _counts(db_session) == (0, 0)


def test_plain_provenance_is_stored_as_sent(client, matter_with_users, suggestion):
    agent = {"platform": "Claude Code", "model": "claude-opus-5-5 (2026)", "run_id": "2026-11-16/run#42 & retry"}

    r = client.post("/api/v1/agent/assertions", json={**suggestion, "agent": agent},
                    headers=matter_with_users["contributor_headers"])

    assert r.status_code == 201, r.text
    assert r.json()["agent_provenance"] == agent
