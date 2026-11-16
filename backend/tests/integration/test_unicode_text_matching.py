"""Query filters match like REST assertion search on every agent/source surface
(agent:10, review:13, review:14).

REST `GET /assertions?q=` compares Python-lowercased text, so "übergabe"
finds "ÜBERGABE". SQLite's lower()/LIKE fold ASCII only, which made MCP
search/explore, CLI `context --query`, `/entities` and `/source-spans`
miss cased non-ASCII letters. The context query also filtered the sanitized
proposition, missing raw text the sanitizer dropped (REST matches raw text).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.agent_cli import context
from app.db import make_engine
from app.mcp.server import create_server
from app.services.text_search import contains_text, natural_key
from tests.conftest import seed_document, seed_source_span
from tests.integration.agent_surface_helpers import agent_env, cli_json, run_cli, tool_json

PROPOSITION = "Case probe: the ÜBERGABE clause governs RÉSILIATION (ΑΡΘΡΟ 5, СТАТЬЯ 7) — 50% of fees_paid."
NEEDLES = ["übergabe", "ÜBERGABE", "Übergabe", "résiliation", "RÉSILIATION", "αρθρο", "статья", "case probe",
           "50% of", "fees_paid"]
# `%` and `_` are literal characters, not LIKE wildcards.
MISSES = ["uebergabe", "fees%paid", "50_ of", "straße"]


@pytest.fixture
def corpus(client, db_session, matter_with_users):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"],
                        title="Mietvertrag Case Probe ÜBERGABE RÉSILIATION ΑΡΘΡΟ СТАТЬЯ — 50% of fees_paid")
    seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"],
                     quote_text="Die ÜBERGABE erfolgt nach RÉSILIATION; ΑΡΘΡΟ, СТАТЬЯ, case probe, 50% of fees_paid.")
    created = client.post("/api/v1/assertions", headers=m["contributor_headers"], json={
        "repository_id": m["repository_id"], "matter_id": m["matter_id"], "assertion_type": "SURVIVES_TERMINATION",
        "proposition": PROPOSITION, "subject_entity": {"type": "Document", "id": doc}, "save_as": "proposed"})
    assert created.status_code == 201, created.text
    return {**m, "assertion_id": created.json()["id"]}


def _rest_total(client, m, needle) -> int:
    return client.get("/api/v1/assertions", params={"matter_id": m["matter_id"], "q": needle},
                      headers=m["reviewer_headers"]).json()["total"]


@pytest.mark.parametrize("needle", NEEDLES + MISSES)
def test_every_surface_agrees_with_rest_search(app, client, db_session, corpus, needle):
    m = corpus
    expected = 1 if needle in NEEDLES else 0
    assert _rest_total(client, m, needle) == expected  # the reference behaviour
    for actor in (None, m["contributor_id"]):
        server = create_server(app.state.session_factory, agent_user_id=actor)
        for tool in ("search", "explore"):
            assert tool_json(server, tool, {"query": needle})["count"] == expected, (tool, actor)
    found = context(db_session, m["contributor_id"], m["matter_id"], needle)
    assert len(found["assertions"]) == expected
    assert found["entities"]["total"] == expected and found["source_spans"]["total"] == expected
    for resource in ("entities", "source-spans"):
        page = client.get(f"/api/v1/matters/{m['matter_id']}/{resource}", params={"q": needle},
                          headers=m["reviewer_headers"]).json()
        assert page["total"] == expected == len(page["items"]), resource


def test_cli_context_query_is_unicode_case_insensitive(app, corpus):
    env = agent_env(str(app.state.engine.url), corpus["contributor_id"])
    result = cli_json(run_cli("context", "--matter-id", corpus["matter_id"], "--query", "übergabe", env=env))
    assert [a["id"] for a in result["assertions"]] == [corpus["assertion_id"]]
    assert result["entities"]["total"] == result["source_spans"]["total"] == 1


def test_hebrew_needles_still_match(client, db_session, matter_with_users):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"], title="חוק הגנת הפרטיות")
    seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"], quote_text="הודעה על פגיעה בפרטיות")
    for resource, needle in (("entities", "הפרטיות"), ("source-spans", "הודעה")):
        page = client.get(f"/api/v1/matters/{m['matter_id']}/{resource}", params={"q": needle},
                          headers=m["reviewer_headers"]).json()
        assert page["total"] == 1, resource


def test_context_query_matches_raw_text_the_sanitizer_dropped(app, client, db_session, matter_with_users):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    created = client.post("/api/v1/assertions", headers=m["contributor_headers"], json={
        "repository_id": m["repository_id"], "matter_id": m["matter_id"], "assertion_type": "SURVIVES_TERMINATION",
        "proposition": "The survival list is exhaustive, see <appendix Q7> for details.",
        "subject_entity": {"type": "Document", "id": doc}})
    assert created.status_code == 201, created.text
    assert "appendix Q7" not in created.json()["proposition"]  # sanitized column lost it
    assert _rest_total(client, m, "appendix Q7") == 1
    assert tool_json(create_server(app.state.session_factory), "search", {"query": "appendix q7"})["count"] == 1
    server = create_server(app.state.session_factory, agent_user_id=m["contributor_id"])
    found = tool_json(server, "agent_context", {"matter_id": m["matter_id"], "query": "APPENDIX Q7"})
    assert [a["id"] for a in found["assertions"]] == [created.json()["id"]]
    env = agent_env(str(app.state.engine.url), m["contributor_id"])
    result = cli_json(run_cli("context", "--matter-id", m["matter_id"], "--query", "appendix Q7", env=env))
    assert [a["id"] for a in result["assertions"]] == [created.json()["id"]]


def test_sqlite_connections_get_the_unicode_functions():
    engine = make_engine("sqlite://")
    with engine.connect() as connection:
        assert connection.execute(text("select lexgraph_unicode_lower('ÜBERGABE É Ω Я')")).scalar() == "übergabe é ω я"
        assert connection.execute(text("select lexgraph_unicode_lower(NULL)")).scalar() is None
        assert connection.execute(text("select lexgraph_natural_key('9-20')")).scalar() == natural_key("9-20")
    engine.dispose()


def test_ascii_and_caseless_needles_keep_the_native_sql():
    from sqlalchemy import column
    from sqlalchemy.dialects import sqlite
    for needle, uses_function in (("termination", False), ("הודעה", False), ("50%", False), ("übergabe", True)):
        sql = str(contains_text(column("quote_text"), needle).compile(dialect=sqlite.dialect()))
        assert ("lexgraph_unicode_lower" in sql) is uses_function, (needle, sql)
