"""Edges of the agent submission contract.

* agent:11 -- the documented agent JSON posted to the lawyer endpoint
  (POST /api/v1/assertions, one path segment away from the agent endpoint)
  used to be stored as a lawyer's user_suggested assertion, its `agent`
  provenance and `confidence` silently dropped; its exact-duplicate then
  blocked the correct submission forever. Undeclared keys are now a 422, and
  the agent-only ones point to POST /api/v1/agent/assertions.
"""

from __future__ import annotations

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
