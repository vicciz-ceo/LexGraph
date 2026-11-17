"""Working out who to notify is a per-assertion index lookup (review workflow:5).

Every comment, evidence and edit notice asks who has worked on the
assertion. The raters were read with ``WHERE assertion_id = ?``, but
assertion_ratings has no index on assertion_id, so SQLite answered
DISTINCT user_id by walking its whole (user_id, assertion_revision_id)
index; assertion_comments had no index on assertion_id at all. The middleware waits for the notices
before answering, so every POST /comments, POST /evidence and PATCH paid
for scans of every matter's ratings and comments (about 210 ms at 200,000
of each). Raters are now read through the assertion's revisions
(ix_assertion_ratings_assertion_revision_id) and commenters through
ix_assertion_comments_assertion_id.

The statements checked here are the ones the notification hook really
issues on the live HTTP path, captured while it derives the notices.
"""

from __future__ import annotations

import re

import pytest
from sqlalchemy import event

from app import notification_hooks
from tests.conftest import (
    assertion_payload,
    auth_header,
    seed_document,
    seed_matter_role,
    seed_source_span,
    seed_user,
)

# A full pass over one of these tables (``SCAN t`` or ``SCAN t USING [COVERING] INDEX i``).
_FULL_SCAN = re.compile(r"^SCAN (assertion_ratings|assertion_comments|assertion_evidence|assertion_revisions)\b")


@pytest.fixture()
def recorded(app, monkeypatch):
    """Every SELECT the notification hook issues while deriving notices."""
    statements: list[tuple[str, tuple]] = []
    engine = app.state.engine

    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append((statement, parameters))

    emit = notification_hooks._emit

    def emit_recording(*args, **kwargs):
        event.listen(engine, "before_cursor_execute", record)
        try:
            return emit(*args, **kwargs)
        finally:
            event.remove(engine, "before_cursor_execute", record)

    monkeypatch.setattr(notification_hooks, "_emit", emit_recording)
    return statements


def _plans(app, statements) -> list[tuple[str, list[str]]]:
    with app.state.engine.connect() as conn:
        return [
            (statement, [row[-1] for row in conn.exec_driver_sql(f"EXPLAIN QUERY PLAN {statement}", parameters)])
            for statement, parameters in statements
        ]


def _worked_on(client, m) -> dict:
    """A proposed assertion with two revisions, evidence, a comment and a
    rating of revision 1 (by the rater, who has done nothing else to it)."""
    created = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed"),
        headers=m["contributor_headers"],
    ).json()
    url = f"/api/v1/assertions/{created['id']}"
    assert client.put(f"{url}/revisions/1/rating", json={"strength": 4}, headers=m["rater_headers"]).status_code == 201
    assert client.post(f"{url}/comments", json={"comment_text": "First."},
                       headers=m["reviewer_headers"]).status_code == 201
    revised = client.patch(url, json={"proposition": "Clause 8.4 limits clause 8.2.", "expected_revision_number": 1},
                           headers=m["contributor_headers"])
    assert revised.status_code == 200 and revised.json()["current_revision_number"] == 2, revised.text
    return created


def test_comment_evidence_and_edit_notices_use_indexed_lookups(app, client, db_session, matter_with_users, recorded):
    m = matter_with_users
    document = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span = seed_source_span(db_session, document_id=document, matter_id=m["matter_id"])
    created = _worked_on(client, m)
    url = f"/api/v1/assertions/{created['id']}"
    recorded.clear()

    assert client.post(f"{url}/comments", json={"comment_text": "Second."},
                       headers=m["reviewer_headers"]).status_code == 201
    assert client.post(f"{url}/evidence", json={"source_span_id": span, "evidence_role": "supports"},
                       headers=m["reviewer_headers"]).status_code == 201
    assert client.patch(url, json={"proposition": "Clause 8.4 narrows clause 8.2.", "expected_revision_number": 2},
                        headers=m["reviewer_headers"]).status_code == 200

    plans = _plans(app, recorded)
    tables = " ".join(statement for statement, _ in plans)
    assert "assertion_ratings" in tables and "assertion_comments" in tables  # the lookups did run
    for statement, plan in plans:
        for detail in plan:
            assert not _FULL_SCAN.match(detail), (detail, statement)


def test_a_rater_of_an_earlier_revision_is_still_a_participant(client, db_session, matter_with_users):
    """Raters are found through the assertion's revisions, every one of them."""
    m = matter_with_users
    created = _worked_on(client, m)  # the rater rated revision 1; revision 2 is current
    bystander = seed_user(db_session, display_name="Rated another assertion")
    seed_matter_role(db_session, user_id=bystander, matter_id=m["matter_id"], role="contributor")
    other = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"], save_as="proposed", proposition="Another."),
        headers=m["contributor_headers"],
    ).json()
    assert client.put(f"/api/v1/assertions/{other['id']}/revisions/1/rating", json={"strength": 2},
                      headers=auth_header(bystander)).status_code == 201

    comment = client.post(f"/api/v1/assertions/{created['id']}/comments", json={"comment_text": "Thoughts?"},
                          headers=m["contributor_headers"])
    assert comment.status_code == 201

    def notices_of_this_comment(headers):
        feed = client.get("/api/v1/notifications", headers=headers).json()
        return [n for n in feed if n["event_type"] == "comment_added"
                and n["payload"].get("comment_id") == comment.json()["id"]]

    assert len(notices_of_this_comment(m["rater_headers"])) == 1  # rated revision 1 only
    assert len(notices_of_this_comment(m["reviewer_headers"])) == 1  # commented earlier
    assert notices_of_this_comment(auth_header(bystander)) == []  # rated a different assertion
    assert notices_of_this_comment(m["contributor_headers"]) == []  # the actor
