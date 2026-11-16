"""Every paged endpoint bounds `offset` (XREQ-28).

An offset beyond SQLite's 64-bit integer range made the driver raise
OverflowError while binding it, so `?offset=99999999999999999999` answered
HTTP 500 on the source pickers, the assertion list, the graph and the
notification feed, and the agent CLI's `context --offset` failed the same
way. Each now answers 422 above app.services.paging.MAX_OFFSET, and an
offset up to it past the last row is an ordinary empty page.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services.paging import MAX_OFFSET
from tests.conftest import seed_article, seed_document, seed_source_span
from tests.integration.agent_surface_helpers import agent_env, cli_error, cli_json, run_cli

HUGE = "99999999999999999999"


def _paths(m: dict) -> list[str]:
    matter = m["matter_id"]
    return [
        f"/api/v1/matters/{matter}/entities",
        f"/api/v1/matters/{matter}/source-spans",
        f"/api/v1/assertions?matter_id={matter}",
        f"/api/v1/matters/{matter}/graph",
        "/api/v1/notifications",
    ]


@pytest.fixture
def sourced(db_session, matter_with_users) -> dict:
    """A matter with a document, an article and a span, so every query runs."""
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"], title="Act")
    span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"])
    seed_article(db_session, document_id=doc, matter_id=m["matter_id"], source_span_id=span, number="1")
    return m


@pytest.mark.parametrize("offset", [HUGE, str(MAX_OFFSET + 1), "-1"])
def test_an_offset_out_of_range_is_a_422_on_every_paged_route(app, sourced, offset):
    raw = TestClient(app, raise_server_exceptions=False)
    for path in _paths(sourced):
        separator = "&" if "?" in path else "?"
        response = raw.get(f"{path}{separator}offset={offset}", headers=sourced["reviewer_headers"])
        assert response.status_code == 422, (path, response.status_code, response.text)


def test_the_largest_offset_is_an_empty_page(client, sourced):
    for path in _paths(sourced):
        separator = "&" if "?" in path else "?"
        response = client.get(f"{path}{separator}offset={MAX_OFFSET}", headers=sourced["reviewer_headers"])
        assert response.status_code == 200, (path, response.text)
        body = response.json()
        page = body if isinstance(body, list) else body.get("items", body.get("edges"))
        assert page == [], (path, body)


def test_the_agent_cli_reports_an_out_of_range_offset_as_422(app, sourced):
    env = agent_env(f"sqlite:///{app.state.engine.url.database}", sourced["contributor_id"])
    body = cli_error(run_cli("context", "--matter-id", sourced["matter_id"], "--offset", HUGE, env=env))
    assert body == {"error": f"limit must be 1..100 and offset 0..{MAX_OFFSET}", "status": 422}
    page = cli_json(run_cli("context", "--matter-id", sourced["matter_id"], "--offset", str(MAX_OFFSET), env=env))
    assert page["entities"]["items"] == [] and page["source_spans"]["items"] == [] and page["assertions"] == []
