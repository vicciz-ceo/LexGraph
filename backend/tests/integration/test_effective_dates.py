"""Effective dates are UTC instants (audit findings agent:7, api:19, api:20).

A UTC offset used to be dropped on storage: the value was validated in UTC
but stored as its wall-clock part, so a valid range could be stored
inverted and then block every later edit; an instant outside years 1..9999
once in UTC raised OverflowError (a 500, and a traceback from the agent
CLI). Requests go through the real HTTP app and the real CLI process.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

from app.models.assertion import Assertion
from app.models.audit_event import AuditEvent
from tests.conftest import assertion_payload, seed_document

BACKEND = Path(__file__).resolve().parents[2]
ROUTES = ["/api/v1/assertions", "/api/v1/agent/assertions"]


def _body(db_session, m, route: str, **overrides) -> dict:
    body = assertion_payload(m["matter_id"], m["repository_id"], **overrides)
    if route.endswith("agent/assertions"):
        doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
        body.update(subject_entity={"type": "Document", "id": doc}, object_entity=None,
                    agent={"platform": "pytest"})
    return body


def _stored_dates(db_session, assertion_id: str) -> tuple:
    return tuple(db_session.execute(text(
        "SELECT a.effective_from, a.effective_to, r.effective_from, r.effective_to FROM assertions a "
        "JOIN assertion_revisions r ON r.assertion_id = a.id AND r.revision_number = a.current_revision_number "
        "WHERE a.id = :id"), {"id": assertion_id}).one())


def _count(db_session, model) -> int:
    return db_session.scalar(select(func.count()).select_from(model))


# --- Offsets are applied, never dropped -------------------------------------


@pytest.mark.parametrize("route", ROUTES)
def test_an_offset_is_applied_before_storage(client, db_session, matter_with_users, route):
    m = matter_with_users
    body = _body(db_session, m, route, effective_from="2030-01-01T00:00:00+14:00",
                 effective_to="2029-12-31T12:00:00Z")

    created = client.post(route, json=body, headers=m["contributor_headers"])

    assert created.status_code == 201, created.text
    assert (created.json()["effective_from"], created.json()["effective_to"]) == (
        "2029-12-31T10:00:00", "2029-12-31T12:00:00")
    stored = _stored_dates(db_session, created.json()["id"])
    assert stored == ("2029-12-31 10:00:00.000000", "2029-12-31 12:00:00.000000") * 2
    assert db_session.scalar(text("SELECT count(*) FROM assertions WHERE effective_to < effective_from")) == 0
    edit = client.patch(f"/api/v1/assertions/{created.json()['id']}",
                        json={"proposition": "Any later edit still works."}, headers=m["contributor_headers"])
    assert edit.status_code == 200, edit.text


def test_a_patched_offset_is_applied_and_later_edits_keep_working(client, db_session, matter_with_users):
    m = matter_with_users
    created = client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], effective_from="2030-01-01"), headers=m["contributor_headers"]).json()
    path = f"/api/v1/assertions/{created['id']}"

    patched = client.patch(path, json={"effective_to": "2029-12-31T20:00:00-05:00"},
                           headers=m["contributor_headers"])

    assert patched.status_code == 200, patched.text
    assert patched.json()["effective_to"] == "2030-01-01T01:00:00"
    assert _stored_dates(db_session, created["id"])[1::2] == ("2030-01-01 01:00:00.000000",) * 2
    revised = client.post(path + "/revisions", json={"proposition": "A later edit."},
                          headers=m["contributor_headers"])
    assert revised.status_code == 201, revised.text


def test_a_range_inverted_once_offsets_are_applied_is_rejected(client, matter_with_users):
    m = matter_with_users
    # Wall-clock 00:00 < 03:00, but 03:00+05:00 is 22:00 UTC the day before.
    body = assertion_payload(m["matter_id"], m["repository_id"], effective_from="2025-01-01T00:00:00Z",
                             effective_to="2025-01-01T03:00:00+05:00")
    response = client.post("/api/v1/assertions", json=body, headers=m["contributor_headers"])
    assert (response.status_code, response.json()["detail"]) == (
        422, "effective_to cannot be before effective_from")


def test_an_assertion_stored_inverted_before_this_fix_stays_editable(client, db_session, matter_with_users):
    """Rows written while offsets were dropped may hold an inverted range; an
    edit that does not touch the dates must not be blocked by them."""
    m = matter_with_users
    created = client.post("/api/v1/assertions", json=assertion_payload(m["matter_id"], m["repository_id"]),
                          headers=m["contributor_headers"]).json()
    db_session.execute(text("UPDATE assertions SET effective_from = '2025-01-01 03:00:00.000000', "
                            "effective_to = '2025-01-01 00:00:00.000000' WHERE id = :id"), {"id": created["id"]})
    db_session.commit()
    path = f"/api/v1/assertions/{created['id']}"

    assert client.patch(path, json={"proposition": "Edited despite the legacy range."},
                        headers=m["contributor_headers"]).status_code == 200
    still_inverted = client.patch(path, json={"effective_to": "2025-01-01T01:00:00Z"},
                                  headers=m["contributor_headers"])
    assert still_inverted.status_code == 422
    fixed = client.patch(path, json={"effective_to": "2025-01-02T00:00:00Z"}, headers=m["contributor_headers"])
    assert fixed.status_code == 200, fixed.text


# --- Extreme values are 422, never 500 --------------------------------------


EXTREMES = [
    {"effective_from": "0001-01-01T00:00:00+14:00", "effective_to": "9999-12-31T23:59:59-12:00"},
    {"effective_to": "9999-12-31T23:59:59-05:00"},
    {"effective_from": "0001-01-01T00:00:00+00:01"},
]


@pytest.mark.parametrize("dates", EXTREMES)
@pytest.mark.parametrize("route", ROUTES)
def test_an_out_of_range_instant_is_a_422_on_create(client, db_session, matter_with_users, route, dates):
    m = matter_with_users
    response = client.post(route, json=_body(db_session, m, route, **dates), headers=m["contributor_headers"])
    assert response.status_code == 422, response.text
    assert "outside the supported date range" in response.json()["detail"]
    assert _count(db_session, Assertion) == 0
    assert _count(db_session, AuditEvent) == 0


@pytest.mark.parametrize("dates", EXTREMES)
def test_an_out_of_range_instant_is_a_422_on_edit(client, db_session, matter_with_users, dates):
    m = matter_with_users
    created = client.post("/api/v1/assertions", json=assertion_payload(
        m["matter_id"], m["repository_id"], effective_from="2030-01-01"), headers=m["contributor_headers"]).json()
    path = f"/api/v1/assertions/{created['id']}"
    for method, suffix in ((client.patch, ""), (client.post, "/revisions")):
        response = method(path + suffix, json=dates, headers=m["contributor_headers"])
        assert response.status_code == 422, response.text
    assert client.get(path, headers=m["contributor_headers"]).json()["current_revision_number"] == 1


def test_the_agent_cli_reports_an_out_of_range_instant_as_json(app, db_session, matter_with_users):
    m = matter_with_users
    body = _body(db_session, m, "/api/v1/agent/assertions", **EXTREMES[0])
    env = {**os.environ, "LEXGRAPH_DATABASE_URL": str(app.state.engine.url),
           "LEXGRAPH_AGENT_USER_ID": m["contributor_id"]}
    cli = subprocess.run([sys.executable, "-m", "app.agent_cli", "suggest"], input=json.dumps(body),
                         capture_output=True, text=True, env=env, cwd=BACKEND, timeout=120)
    assert cli.returncode == 1, cli.stderr
    assert cli.stdout == ""
    error = json.loads(cli.stderr.strip().splitlines()[-1])
    assert error["status"] == 422 and "outside the supported date range" in error["error"]
    assert _count(db_session, Assertion) == 0
