"""Migrations m20261116_assertion_revision_number_unique (api:0) and
m20261116_backfill_initial_assertion_revisions (api:1, pipeline:2,
pipeline:3, ui:4).

Old databases are built from the current schema with the new parts taken
away (the unique index dropped) or with rows written by raw SQL the way the
old code left them (the ORM hook never sees raw SQL), then upgraded, checked
through the database and the HTTP API, and upgraded again (no-op).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.db import Base
from app.migrations import m20261116_assertion_revision_number_unique as unique_numbers
from app.migrations import m20261116_backfill_initial_assertion_revisions as backfill
from app.models.assertion_revision import REVISION_NUMBER_UNIQUE_INDEX

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


def _current_number(conn, assertion_id):
    return conn.execute(text("SELECT current_revision_number FROM assertions WHERE id = :a"),
                        {"a": assertion_id}).scalar_one()


def test_both_migrations_are_no_ops_on_a_fresh_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    import app.models  # noqa: F401  -- register every table

    Base.metadata.create_all(engine)
    assert unique_numbers.upgrade(engine) is False
    assert backfill.upgrade(engine) is False
    engine.dispose()


def test_migration_ids_follow_the_convention():
    assert unique_numbers.MIGRATION_ID == "20261116_assertion_revision_number_unique"
    assert backfill.MIGRATION_ID == "20261116_backfill_initial_assertion_revisions"
    assert unique_numbers.INDEX_NAME == REVISION_NUMBER_UNIQUE_INDEX


def test_unique_numbers_migration_renumbers_duplicates_and_adds_the_index(app, client, matter_with_users):
    m = matter_with_users
    engine = app.state.engine
    author = m["reviewer_id"]
    with engine.begin() as conn:
        conn.execute(text(f"DROP INDEX {REVISION_NUMBER_UNIQUE_INDEX}"))  # the pre-migration schema
        # The api:0 race: two edits of revision 1 both stored revision 2; the
        # edit that committed last ("edit A") is what the assertion holds,
        # although its row was created first.
        raced = _insert_assertion(conn, m, proposition="edit A", current=2, origin="user_suggested",
                                  status="proposed", object_type=None)
        _insert_revision(conn, raced, 1, "original", created_at="2026-09-01 10:00:00", author=author)
        a_row = _insert_revision(conn, raced, 2, "edit A", created_at="2026-09-01 11:00:00", author=author)
        b_row = _insert_revision(conn, raced, 2, "edit B", created_at="2026-09-01 11:00:01", author=author)
        conn.execute(text(
            "INSERT INTO assertion_ratings (id, organization_id, repository_id, matter_id, assertion_id, "
            "assertion_revision_id, user_id, strength, created_at, updated_at) VALUES (:id, :org, :repo, "
            ":matter, :aid, :rid, :uid, 2, '2026-09-02 00:00:00', '2026-09-02 00:00:00')"),
            {"id": _id(), "org": m["organization_id"], "repo": m["repository_id"], "matter": m["matter_id"],
             "aid": raced, "rid": b_row, "uid": m["rater_id"]})
        # A later edit on top of a duplicate pair: every number above moves up.
        stacked = _insert_assertion(conn, m, proposition="third", current=2, origin="user_suggested",
                                    status="proposed", object_type=None)
        _insert_revision(conn, stacked, 1, "first", created_at="2026-09-01 10:00:00", author=author)
        _insert_revision(conn, stacked, 1, "first again", created_at="2026-09-01 10:00:05", author=author)
        _insert_revision(conn, stacked, 2, "third", created_at="2026-09-01 12:00:00", author=author)
        clean = _insert_assertion(conn, m, proposition="two", current=2, origin="user_suggested",
                                  status="proposed", object_type=None)
        _insert_revision(conn, clean, 1, "one", created_at="2026-09-01 10:00:00", author=author)
        _insert_revision(conn, clean, 2, "two", created_at="2026-09-01 10:30:00", author=author)

    assert unique_numbers.upgrade(engine) is True

    with engine.begin() as conn:
        assert _revisions(conn, raced) == [(1, "original"), (2, "edit B"), (3, "edit A")]
        assert _current_number(conn, raced) == 3
        assert conn.execute(text("SELECT revision_number FROM assertion_revisions WHERE id = :id"),
                            {"id": a_row}).scalar_one() == 3
        rated = conn.execute(text("SELECT assertion_revision_id FROM assertion_ratings WHERE assertion_id = :a"),
                             {"a": raced}).scalar_one()
        assert rated == b_row  # the rating stays with the row it rated (now revision 2)
        assert _revisions(conn, stacked) == [(1, "first"), (2, "first again"), (3, "third")]
        assert _current_number(conn, stacked) == 3
        assert _revisions(conn, clean) == [(1, "one"), (2, "two")] and _current_number(conn, clean) == 2
    index = next(i for i in inspect(engine).get_indexes("assertion_revisions")
                 if i["name"] == REVISION_NUMBER_UNIQUE_INDEX)
    assert index["unique"] and index["column_names"] == ["assertion_id", "revision_number"]
    with pytest.raises(IntegrityError), engine.begin() as conn:
        _insert_revision(conn, clean, 2, "again", created_at="2026-09-03 00:00:00", author=author)

    detail = client.get(f"/api/v1/assertions/{raced}", headers=m["reviewer_headers"])
    assert detail.status_code == 200
    assert (detail.json()["current_revision_number"], detail.json()["proposition_raw"]) == (3, "edit A")
    listing = client.get("/api/v1/assertions", params={"matter_id": m["matter_id"]}, headers=m["reviewer_headers"])
    assert listing.status_code == 200 and listing.json()["total"] == 3
    summary = client.get(f"/api/v1/assertions/{raced}/revisions/2/ratings/summary", headers=m["reviewer_headers"])
    assert summary.status_code == 200 and summary.json()["count"] == 1

    assert unique_numbers.upgrade(engine) is False


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
