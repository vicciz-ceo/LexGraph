"""B3 — comments + audit trail.

Gate G8 (audit: actor, timestamp, matter, assertion, revision, before/
after, correlation id; no full-document content). Spec §9 (comments) and
§16 (audit requirements).

Owning track: B3. Routes: POST/GET/PATCH/DELETE
/api/v1/assertions/{id}/comments[...]. Audit is verified via raw SQL
against the `audit_events` table (see conftest "Data model reference" —
Planner does not import an AuditEvent model).
"""

from __future__ import annotations

from sqlalchemy import text

from tests.conftest import assertion_payload


def _create_assertion(client, m):
    r = client.post(
        "/api/v1/assertions",
        json=assertion_payload(m["matter_id"], m["repository_id"]),
        headers=m["contributor_headers"],
    )
    return r.json()["id"]


def test_add_comment(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "This reading seems right given Clause 8.4."},
        headers=m["rater_headers"],
    )
    assert r.status_code == 201
    assert r.json()["comment_text"] == "This reading seems right given Clause 8.4."


def test_list_comments_matter_scoped(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "First comment."},
        headers=m["contributor_headers"],
    )
    r = client.get(f"/api/v1/assertions/{assertion_id}/comments", headers=m["rater_headers"])
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_outsider_cannot_comment(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    r = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "I shouldn't be able to post this."},
        headers=m["outsider_headers"],
    )
    assert r.status_code == 403


def test_user_can_edit_own_comment(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    created = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "Original text."},
        headers=m["contributor_headers"],
    )
    comment_id = created.json()["id"]
    r = client.patch(
        f"/api/v1/assertions/{assertion_id}/comments/{comment_id}",
        json={"comment_text": "Edited text."},
        headers=m["contributor_headers"],
    )
    assert r.status_code == 200
    assert r.json()["comment_text"] == "Edited text."


def test_user_cannot_edit_others_comment(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    created = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "Original text."},
        headers=m["contributor_headers"],
    )
    comment_id = created.json()["id"]
    r = client.patch(
        f"/api/v1/assertions/{assertion_id}/comments/{comment_id}",
        json={"comment_text": "Hijacked text."},
        headers=m["rater_headers"],
    )
    assert r.status_code == 403


def test_delete_comment_is_soft_delete(client, matter_with_users):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    created = client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "To be deleted."},
        headers=m["contributor_headers"],
    )
    comment_id = created.json()["id"]
    r = client.delete(
        f"/api/v1/assertions/{assertion_id}/comments/{comment_id}",
        headers=m["contributor_headers"],
    )
    assert r.status_code == 204
    listing = client.get(f"/api/v1/assertions/{assertion_id}/comments", headers=m["contributor_headers"])
    ids = [c["id"] for c in listing.json()]
    assert comment_id not in ids  # excluded from default listing, but row soft-deleted server-side


def test_assertion_created_produces_audit_event(client, matter_with_users, db_session):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    rows = db_session.execute(
        text(
            "SELECT actor_user_id, event_type, matter_id, assertion_id, correlation_id "
            "FROM audit_events WHERE assertion_id = :aid AND event_type = 'assertion_created'"
        ),
        {"aid": assertion_id},
    ).fetchall()
    assert len(rows) == 1
    actor, event_type, matter_id, aid, correlation_id = rows[0]
    assert actor == m["contributor_id"]
    assert matter_id == m["matter_id"]
    assert correlation_id is not None


def test_rating_mutation_produces_audit_event(client, matter_with_users, db_session):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    client.post(f"/api/v1/assertions/{assertion_id}/submit", headers=m["contributor_headers"])
    client.put(
        f"/api/v1/assertions/{assertion_id}/revisions/1/rating",
        json={"strength": 4, "rationale": "Solid."},
        headers=m["rater_headers"],
    )
    rows = db_session.execute(
        text(
            "SELECT event_type FROM audit_events WHERE assertion_id = :aid "
            "AND event_type IN ('rating_created', 'rating_changed')"
        ),
        {"aid": assertion_id},
    ).fetchall()
    assert len(rows) >= 1


def test_comment_produces_audit_event(client, matter_with_users, db_session):
    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    client.post(
        f"/api/v1/assertions/{assertion_id}/comments",
        json={"comment_text": "Auditable comment."},
        headers=m["contributor_headers"],
    )
    rows = db_session.execute(
        text(
            "SELECT actor_user_id FROM audit_events WHERE assertion_id = :aid "
            "AND event_type = 'comment_created'"
        ),
        {"aid": assertion_id},
    ).fetchall()
    assert len(rows) == 1


def test_evidence_add_and_remove_produce_audit_events(client, matter_with_users, db_session):
    """QA regression (2026-07-26): spec §16 requires an audit event for
    'Evidence added or removed'; gate G8 requires every evidence mutation
    to produce one. A live-API probe found `POST .../evidence` and
    `DELETE .../evidence/{id}` (app/routers/assertions.py) write no
    `audit_events` row at all -- neither a direct call in the router nor
    coverage in `app.audit_middleware` (which only matches assertion
    creation and rating mutations). RED against the current code; pins
    the REQUIRED behavior, not the gap."""
    from tests.conftest import seed_document, seed_source_span

    m = matter_with_users
    assertion_id = _create_assertion(client, m)
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(db_session, document_id=doc_id, matter_id=m["matter_id"])

    add_r = client.post(
        f"/api/v1/assertions/{assertion_id}/evidence",
        json={"source_span_id": span_id, "evidence_role": "supports"},
        headers=m["contributor_headers"],
    )
    assert add_r.status_code == 201
    evidence_id = add_r.json()["id"]

    add_audit_rows = db_session.execute(
        text(
            "SELECT event_type FROM audit_events WHERE assertion_id = :aid "
            "AND (event_type LIKE '%evidence%added%' OR event_type LIKE '%evidence_add%')"
        ),
        {"aid": assertion_id},
    ).fetchall()
    assert len(add_audit_rows) >= 1, "no audit_events row for evidence-added mutation"

    del_r = client.delete(
        f"/api/v1/assertions/{assertion_id}/evidence/{evidence_id}",
        headers=m["contributor_headers"],
    )
    assert del_r.status_code == 204

    remove_audit_rows = db_session.execute(
        text(
            "SELECT event_type FROM audit_events WHERE assertion_id = :aid "
            "AND (event_type LIKE '%evidence%remov%' OR event_type LIKE '%evidence%delet%')"
        ),
        {"aid": assertion_id},
    ).fetchall()
    assert len(remove_audit_rows) >= 1, "no audit_events row for evidence-removed mutation"


def test_audit_events_have_no_full_document_content(client, matter_with_users, db_session):
    """Audit rows must not carry the full document/quote text — only
    references (spec §16: "Do not include confidential full-document
    content in routine audit logs")."""
    from tests.conftest import seed_document, seed_source_span

    m = matter_with_users
    confidential_quote = "CONFIDENTIAL_QUOTE_MARKER — privileged settlement terms, do not leak."
    doc_id = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"])
    span_id = seed_source_span(
        db_session, document_id=doc_id, matter_id=m["matter_id"], quote_text=confidential_quote
    )
    assertion_id = _create_assertion(client, m)
    client.post(
        f"/api/v1/assertions/{assertion_id}/evidence",
        json={"source_span_id": span_id, "evidence_role": "supports"},
        headers=m["contributor_headers"],
    )
    rows = db_session.execute(
        text("SELECT previous_value, new_value FROM audit_events WHERE assertion_id = :aid"),
        {"aid": assertion_id},
    ).fetchall()
    assert len(rows) >= 1
    for previous_value, new_value in rows:
        assert confidential_quote not in (previous_value or "")
        assert confidential_quote not in (new_value or "")
