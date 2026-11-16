"""Migration m20261116_backfill_initial_assertion_revisions (api:1,
pipeline:2, pipeline:3, ui:4).

Old databases are built from the current schema with rows written by raw
SQL the way the old code left them (the ORM hook never sees raw SQL), then
upgraded, checked through the database and the HTTP API, and upgraded again
(no-op).
"""

from __future__ import annotations

import uuid

from sqlalchemy import create_engine, text

from app.db import Base
from app.migrations import m20261116_backfill_initial_assertion_revisions as backfill

_ASSERTION_COLUMNS = (
    "id, organization_id, repository_id, matter_id, assertion_type, proposition, subject_entity_type, "
    "subject_entity_id, object_entity_type, object_entity_id, origin, status, author_user_id, "
    "jurisdiction, created_at, updated_at, current_revision_number"
)


def _id() -> str:
    return str(uuid.uuid4())


def _insert_assertion(conn, m, *, proposition, current=1, origin="system_generated", status="accepted",
                      created_at="2026-09-01 10:00:00.000000", object_type="Definition"):
    assertion_id = _id()
    conn.execute(text(
        f"INSERT INTO assertions ({_ASSERTION_COLUMNS}) VALUES (:id, :org, :repo, :matter, 'USES_DEFINITION', "
        ":proposition, 'Article', :subject, :object_type, :object_id, :origin, :status, :author, 'IL', "
        ":created_at, :created_at, :current)"),
        {"id": assertion_id, "org": m["organization_id"], "repo": m["repository_id"], "matter": m["matter_id"],
         "proposition": proposition, "subject": _id(), "object_type": object_type,
         "object_id": _id() if object_type else None,
         "origin": origin, "status": status, "author": m["reviewer_id"], "created_at": created_at,
         "current": current})
    return assertion_id


def _insert_revision(conn, assertion_id, number, proposition, *, created_at, author):
    revision_id = _id()
    conn.execute(text(
        "INSERT INTO assertion_revisions (id, assertion_id, revision_number, proposition, proposition_raw, "
        "assertion_type, subject_entity_type, subject_entity_id, object_entity_type, object_entity_id, "
        "jurisdiction, effective_from, effective_to, edited_by_user_id, created_at) "
        "SELECT :id, a.id, :number, :proposition, :proposition, a.assertion_type, a.subject_entity_type, "
        "a.subject_entity_id, a.object_entity_type, a.object_entity_id, a.jurisdiction, a.effective_from, "
        "a.effective_to, :author, :created_at FROM assertions a WHERE a.id = :aid"),
        {"id": revision_id, "aid": assertion_id, "number": number, "proposition": proposition,
         "author": author, "created_at": created_at})
    return revision_id


def _revisions(conn, assertion_id):
    return [tuple(r) for r in conn.execute(text(
        "SELECT revision_number, proposition FROM assertion_revisions WHERE assertion_id = :a "
        "ORDER BY revision_number"), {"a": assertion_id})]


def test_the_backfill_is_a_no_op_on_a_fresh_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    import app.models  # noqa: F401  -- register every table

    Base.metadata.create_all(engine)
    assert backfill.upgrade(engine) is False
    engine.dispose()


def test_migration_id_follows_the_convention():
    assert backfill.MIGRATION_ID == "20261116_backfill_initial_assertion_revisions"


def test_backfill_creates_revision_one_and_a_creation_event_for_unrevisioned_rows(app, client, matter_with_users):
    m = matter_with_users
    engine = app.state.engine
    with engine.begin() as conn:
        # What the old definition-links pass left behind.
        linked = _insert_assertion(conn, m, proposition='Article 3 uses the definition of "bank".')
        # Same, but a creation event was already recorded for it.
        audited = _insert_assertion(conn, m, proposition='Article 4 uses the definition of "bank".')
        conn.execute(text(
            "INSERT INTO audit_events (id, actor_user_id, event_type, timestamp, repository_id, matter_id, "
            "assertion_id, new_value) VALUES (:id, :uid, 'assertion_created', '2026-09-01 10:00:00', :repo, "
            ":matter, :aid, 'accepted')"),
            {"id": _id(), "uid": m["reviewer_id"], "repo": m["repository_id"], "matter": m["matter_id"],
             "aid": audited})
        # Edited before the fix: revision 2 only. The original text is gone.
        edited = _insert_assertion(conn, m, proposition="edited text", current=2, status="proposed")
        _insert_revision(conn, edited, 2, "edited text", created_at="2026-09-02 00:00:00", author=m["reviewer_id"])
        # A current revision above 1 is missing: cannot be reconstructed.
        broken = _insert_assertion(conn, m, proposition="broken", current=3)
        # A healthy user assertion.
        healthy = _insert_assertion(conn, m, proposition="healthy", origin="user_suggested", status="proposed")
        _insert_revision(conn, healthy, 1, "healthy", created_at="2026-09-01 10:00:00", author=m["reviewer_id"])

    assert backfill.upgrade(engine) is True

    with engine.begin() as conn:
        revision = conn.execute(text(
            "SELECT r.id, r.revision_number, r.proposition, r.proposition_raw, r.assertion_type, "
            "r.subject_entity_type, r.subject_entity_id, r.object_entity_type, r.object_entity_id, "
            "r.jurisdiction, r.revision_reason, r.edited_by_user_id, r.created_at, a.subject_entity_id, "
            "a.object_entity_id, a.created_at FROM assertion_revisions r JOIN assertions a "
            "ON a.id = r.assertion_id WHERE r.assertion_id = :a"), {"a": linked}).one()
        assert revision[1:11] == (1, 'Article 3 uses the definition of "bank".',
                                  'Article 3 uses the definition of "bank".', "USES_DEFINITION", "Article",
                                  revision[13], "Definition", revision[14], "IL",
                                  "initial creation (system-generated, backfilled)")
        assert (revision[11], revision[12]) == (m["reviewer_id"], revision[15])
        events = conn.execute(text(
            "SELECT event_type, actor_user_id, assertion_revision_id, new_value, correlation_id, timestamp "
            "FROM audit_events WHERE assertion_id = :a"), {"a": linked}).all()
        assert [tuple(e) for e in events] == [("assertion_created", m["reviewer_id"], revision[0], None,
                                               "migration:20261116_backfill_initial_assertion_revisions",
                                               revision[15])]
        assert _revisions(conn, audited) == [(1, 'Article 4 uses the definition of "bank".')]
        assert conn.execute(text("SELECT COUNT(*) FROM audit_events WHERE assertion_id = :a"),
                            {"a": audited}).scalar_one() == 1
        assert _revisions(conn, edited) == [(2, "edited text")]
        assert _revisions(conn, broken) == []
        assert _revisions(conn, healthy) == [(1, "healthy")]

    rated = client.put(f"/api/v1/assertions/{linked}/revisions/1/rating", json={"strength": 4},
                       headers=m["rater_headers"])
    assert rated.status_code == 201, rated.text
    history = client.get(f"/api/v1/assertions/{linked}/history", headers=m["rater_headers"]).json()
    assert (history[0]["event_type"], history[0]["assertion_revision_number"]) == ("assertion_created", 1)

    assert backfill.upgrade(engine) is False


def test_backfill_runs_on_a_database_without_raw_text_columns(app, matter_with_users):
    """Raw-text columns came from an older, separate migration; the backfill
    must not require it to have run."""
    m = matter_with_users
    engine = app.state.engine
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE assertion_revisions DROP COLUMN proposition_raw"))
        linked = _insert_assertion(conn, m, proposition="Article 9 uses the definition of \"fee\".")

    assert backfill.upgrade(engine) is True
    with engine.begin() as conn:
        assert _revisions(conn, linked) == [(1, 'Article 9 uses the definition of "fee".')]
    assert backfill.upgrade(engine) is False
