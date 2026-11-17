"""``python -m app.migrate``: one idempotent upgrade path for every older
database (findings api:3, ops:1, pipeline:7).

Before this runner, the RUNBOOK documented one of three migration modules,
``documents.jurisdiction`` and the ``articles``/``definitions`` tables had no
migration at all, and a re-run of any module crashed on ``duplicate column``.
A workspace created before 2026-08-05 answered HTTP 500 on its core endpoints
and no documented step could repair it.

Every file under ``tests/fixtures/schema_history/`` is the exact DDL an older
tree's ``Base.metadata.create_all()`` produced, generated from that commit's
own ORM models. These tests replay it, seed rows, and require the runner to
bring the database to the schema a fresh ``create_all()`` builds today,
without losing or rewriting a stored value, and to change nothing when run
again.
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from app import migrate
from app.db import make_engine

from tests.schema_history import (
    HISTORICAL_SCHEMAS,
    OLDEST,
    PRE_AUGUST,
    SEED_ROWS,
    build_fresh_db,
    build_historical_db,
)
from tests.schema_history import rows as _rows

BACKEND = Path(__file__).resolve().parents[2]

# The schema changes this repository shipped before the runner existed, in the
# order they happened. Other modules may follow (any MIGRATION_ID), but these
# must be discovered, in this relative order.
SHIPPED_MIGRATIONS = [
    "20260726_add_raw_text_columns",
    "20260729_add_definition_link_tables",
    "20260802_add_document_jurisdiction_column",
    "20260804_add_assertion_subject_unit_path_column",
    "20260805_add_heading_breadcrumbs_column",
]
# Shipped after the runner by other packages (authoring-core's revision
# invariants, notifications, identity), each found by convention with no
# wiring. The backfill is data-only: these fixtures' one assertion already
# has revision 1, so the upgrade tests below do not expect it to apply.
LATER_MIGRATIONS = [
    "20261116_assertion_read_indexes",
    "20261116_assertion_revision_number_unique",
    "20261116_backfill_initial_assertion_revisions",
    "20261116_durable_notifications",
    "20261116_sign_in_tokens",
    "20261116_users_email_unique",
]


def _schema_shape(path: Path) -> dict:
    """Tables, column nullability and unique column sets, independent of how
    a constraint was spelled (inline UNIQUE vs. CREATE UNIQUE INDEX)."""
    engine = create_engine(f"sqlite:///{path}")
    try:
        insp = inspect(engine)
        shape = {}
        for table in insp.get_table_names():
            uniques = {tuple(sorted(u["column_names"])) for u in insp.get_unique_constraints(table)}
            uniques |= {
                tuple(sorted(i["column_names"])) for i in insp.get_indexes(table) if i["unique"]
            }
            shape[table] = {
                "columns": {c["name"]: c["nullable"] for c in insp.get_columns(table)},
                "unique": sorted(uniques),
            }
        return shape
    finally:
        engine.dispose()


def _dump(path: Path) -> list[str]:
    conn = sqlite3.connect(path)
    try:
        return list(conn.iterdump())
    finally:
        conn.close()


# --- discovery ----------------------------------------------------------------


def test_runner_discovers_the_shipped_migrations_in_historical_order():
    ids = [migration.id for migration in migrate.discover_migrations()]
    assert ids == sorted(ids), "migrations must run in MIGRATION_ID order"
    assert len(ids) == len(set(ids))
    expected = SHIPPED_MIGRATIONS + LATER_MIGRATIONS
    assert [i for i in ids if i in expected] == expected


def _fake_migrations_package(tmp_path: Path, name: str, modules: dict[str, str]) -> str:
    package = tmp_path / name
    package.mkdir()
    (package / "__init__.py").write_text("")
    for module, source in modules.items():
        (package / f"{module}.py").write_text(textwrap.dedent(source))
    return name


def test_discovery_rejects_duplicate_and_malformed_ids_and_skips_helpers(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    ok = _fake_migrations_package(
        tmp_path,
        "fake_migs_ok",
        {
            "m20990102_second": 'MIGRATION_ID = "20990102_second"\ndef upgrade(engine):\n    return False\n',
            "m20990101_first": 'MIGRATION_ID = "20990101_first"\ndef upgrade(engine):\n    return False\n',
            "_helpers": "VALUE = 1\n",
        },
    )
    assert [m.id for m in migrate.discover_migrations(ok)] == ["20990101_first", "20990102_second"]

    dup = _fake_migrations_package(
        tmp_path,
        "fake_migs_dup",
        {
            "m20990101_a": 'MIGRATION_ID = "20990101_same"\ndef upgrade(engine):\n    return False\n',
            "m20990101_b": 'MIGRATION_ID = "20990101_same"\ndef upgrade(engine):\n    return False\n',
        },
    )
    with pytest.raises(migrate.MigrationError, match="20990101_same.*m20990101_a.*m20990101_b"):
        migrate.discover_migrations(dup)

    bad = _fake_migrations_package(
        tmp_path,
        "fake_migs_bad",
        {"m2099_bad": 'MIGRATION_ID = "2099-bad"\ndef upgrade(engine):\n    return False\n'},
    )
    with pytest.raises(migrate.MigrationError, match="2099-bad"):
        migrate.discover_migrations(bad)


# --- the upgrade path -----------------------------------------------------------


@pytest.mark.parametrize("schema", HISTORICAL_SCHEMAS)
def test_runner_upgrades_every_historical_schema_to_the_current_models(tmp_path, schema, capsys):
    old = build_historical_db(tmp_path / "old.db", schema)
    fresh = build_fresh_db(tmp_path / "fresh.db")
    assert _schema_shape(old) != _schema_shape(fresh), "fixture is not actually out of date"

    assert migrate.main(["--db", str(old)]) == 0
    out = capsys.readouterr().out

    assert _schema_shape(old) == _schema_shape(fresh)
    assert "schema is current" in out
    engine = make_engine(f"sqlite:///{old}")
    try:
        assert migrate.inspect_schema(engine).is_current
    finally:
        engine.dispose()


def test_runner_keeps_every_existing_row_and_backfills_the_new_columns(tmp_path):
    db = build_historical_db(tmp_path / "old.db", OLDEST)
    counts_before = {table: _rows(db, f"SELECT count(*) FROM {table}")[0][0] for table, _ in SEED_ROWS}

    assert migrate.main(["--db", str(db)]) == 0

    assert {table: _rows(db, f"SELECT count(*) FROM {table}")[0][0] for table, _ in SEED_ROWS} == counts_before
    # Raw-text columns are backfilled from their sanitized siblings (issue #2).
    assert _rows(db, "SELECT proposition, proposition_raw FROM assertion_revisions") == [
        ("Clause 8.4 limits clause 8.2.", "Clause 8.4 limits clause 8.2.")
    ]
    assert _rows(db, "SELECT comment_text_raw FROM assertion_comments") == [("Agreed, see 8.4.",)]
    assert _rows(db, "SELECT rationale_raw FROM assertion_ratings") == [("Strong textual support.",)]
    # Every pre-2026-08-02 document is Israeli law (models/document.py).
    assert _rows(db, "SELECT id, jurisdiction FROM documents") == [("doc-1", "IL")]
    assert _rows(db, "SELECT subject_unit_path FROM assertions") == [(None,)]
    assert _rows(db, "SELECT count(*) FROM articles") == [(0,)]
    assert _rows(db, "SELECT count(*) FROM definitions") == [(0,)]


def test_second_run_changes_nothing_and_reports_it(tmp_path, capsys):
    db = build_historical_db(tmp_path / "old.db", OLDEST)
    assert migrate.main(["--db", str(db)]) == 0
    first = capsys.readouterr().out
    for migration_id in SHIPPED_MIGRATIONS:
        assert re.search(rf"{migration_id}\s+applied", first), first
    before = _dump(db)

    assert migrate.main(["--db", str(db)]) == 0
    second = capsys.readouterr().out

    assert _dump(db) == before
    assert "applied" not in second.replace("already applied", "")
    for migration_id in SHIPPED_MIGRATIONS:
        assert re.search(rf"{migration_id}\s+already applied", second), second


def test_every_migration_is_a_no_op_on_a_freshly_created_database(tmp_path):
    db = build_fresh_db(tmp_path / "fresh.db")
    before = _dump(db)
    engine = migrate.make_migration_engine(f"sqlite:///{db}")
    try:
        for migration in migrate.discover_migrations():
            assert migration.upgrade(engine) is False, (
                f"{migration.id} changed a database create_all() just built"
            )
    finally:
        engine.dispose()
    assert _dump(db) == before


def test_definition_link_tables_are_created_in_their_2026_07_29_shape(tmp_path):
    """The new module recreates exactly what create_all() built on 2026-07-29;
    later columns arrive through their own migrations."""
    from app.migrations import m20260729_add_definition_link_tables as module

    db = build_historical_db(tmp_path / "old.db", "2026-07-26_raw_text_columns.sql")
    engine = make_engine(f"sqlite:///{db}")
    try:
        assert module.upgrade(engine) is True
        assert module.upgrade(engine) is False
    finally:
        engine.dispose()
    reference = build_historical_db(tmp_path / "ref.db", PRE_AUGUST)
    query = "SELECT name, sql FROM sqlite_master WHERE name IN ('articles', 'definitions') ORDER BY name"
    normalize = lambda rows: [(name, " ".join(sql.split())) for name, sql in rows]  # noqa: E731
    assert normalize(_rows(db, query)) == normalize(_rows(reference, query))


def test_document_jurisdiction_migration_matches_the_model_and_is_idempotent(tmp_path):
    from app.migrations import m20260802_add_document_jurisdiction_column as module

    db = build_historical_db(tmp_path / "old.db", PRE_AUGUST)
    engine = make_engine(f"sqlite:///{db}")
    try:
        assert module.upgrade(engine) is True
        assert module.upgrade(engine) is False
        column = next(c for c in inspect(engine).get_columns("documents") if c["name"] == "jurisdiction")
        assert column["nullable"] is False
        assert column["default"] == "'IL'"
        with engine.begin() as conn:
            # The raw-SQL insert shape tests/conftest.py's seed_document uses.
            conn.execute(
                text(
                    "INSERT INTO documents (id, repository_id, matter_id, title) "
                    "VALUES ('doc-2', 'repo-1', 'matter-1', 'Later act')"
                )
            )
    finally:
        engine.dispose()
    assert _rows(db, "SELECT id, jurisdiction FROM documents ORDER BY id") == [
        ("doc-1", "IL"),
        ("doc-2", "IL"),
    ]


@pytest.mark.parametrize(
    "module_name, schema",
    [
        ("add_raw_text_columns", OLDEST),
        ("add_assertion_subject_unit_path_column", "2026-08-02_document_jurisdiction.sql"),
        ("add_heading_breadcrumbs_column", "2026-08-04_assertion_subject_unit_path.sql"),
    ],
)
def test_pre_runner_modules_keep_their_entry_points_and_are_now_idempotent(tmp_path, module_name, schema):
    """The RUNBOOK's historical ``from app.migrations.<module> import upgrade``
    command still works, and a second call reports False instead of crashing
    with ``duplicate column name``."""
    import importlib

    module = importlib.import_module(f"app.migrations.{module_name}")
    db = build_historical_db(tmp_path / "old.db", schema)
    engine = make_engine(f"sqlite:///{db}")
    try:
        assert module.upgrade(engine) is True
        assert module.upgrade(engine) is False
        module.downgrade(engine)
        module.downgrade(engine)  # nothing left to drop: still no error
        assert module.upgrade(engine) is True
    finally:
        engine.dispose()


def test_heading_breadcrumbs_module_skips_a_database_without_articles(tmp_path):
    """Run alone against a pre-2026-07-29 database it used to crash with
    ``no such table: articles``; the runner creates the table first."""
    from app.migrations import add_heading_breadcrumbs_column as module

    db = build_historical_db(tmp_path / "old.db", "2026-07-26_raw_text_columns.sql")
    engine = make_engine(f"sqlite:///{db}")
    try:
        assert module.upgrade(engine) is False
    finally:
        engine.dispose()


# --- failure handling -------------------------------------------------------------


def test_a_failing_migration_is_rolled_back_whole_and_stops_the_run(tmp_path, monkeypatch, capsys):
    db = build_historical_db(tmp_path / "old.db", PRE_AUGUST)
    real = migrate.discover_migrations()

    def boom(engine):
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE documents ADD COLUMN half_done TEXT"))
            conn.execute(text("UPDATE documents SET half_done = no_such_column"))
        return True

    failing = migrate.Migration(id="20260801_fails_halfway", module="test.boom", upgrade=boom)
    monkeypatch.setattr(migrate, "discover_migrations", lambda *a, **k: sorted([*real, failing], key=lambda m: m.id))

    assert migrate.main(["--db", str(db)]) == 1
    captured = capsys.readouterr()
    assert "20260801_fails_halfway" in captured.err
    assert "rolled back" in captured.err
    columns = {c[1] for c in _rows(db, "PRAGMA table_info(documents)")}
    assert "half_done" not in columns, "the failed migration's ALTER TABLE was not rolled back"
    assert "jurisdiction" not in columns, "migrations after the failure must not run"

    monkeypatch.setattr(migrate, "discover_migrations", lambda *a, **k: real)
    assert migrate.main(["--db", str(db)]) == 0
    assert "jurisdiction" in {c[1] for c in _rows(db, "PRAGMA table_info(documents)")}


def test_runner_reports_a_model_change_that_has_no_migration(tmp_path, monkeypatch, capsys):
    db = build_historical_db(tmp_path / "old.db", PRE_AUGUST)
    real = migrate.discover_migrations()
    monkeypatch.setattr(
        migrate,
        "discover_migrations",
        lambda *a, **k: [m for m in real if m.id != "20260802_add_document_jurisdiction_column"],
    )
    assert migrate.main(["--db", str(db)]) == 1
    assert "column documents.jurisdiction" in capsys.readouterr().err


def test_refuses_a_missing_database_file_and_does_not_create_it(tmp_path, capsys):
    missing = tmp_path / "typo.db"
    assert migrate.main(["--db", str(missing)]) == 1
    assert not missing.exists()
    assert "app.bootstrap" in capsys.readouterr().err


def test_refuses_a_database_without_lexgraph_tables(tmp_path, capsys):
    empty = tmp_path / "empty.db"
    empty.touch()
    assert migrate.main(["--db", str(empty)]) == 1
    assert "app.bootstrap" in capsys.readouterr().err
    assert _rows(empty, "SELECT count(*) FROM sqlite_master") == [(0,)]


def test_refuses_to_run_without_a_database(monkeypatch, capsys):
    monkeypatch.delenv("LEXGRAPH_DATABASE_URL", raising=False)
    assert migrate.main([]) == 1
    assert "--db" in capsys.readouterr().err


# --- the real command ---------------------------------------------------------------


def test_cli_reads_LEXGRAPH_DATABASE_URL_and_reports_what_ran(tmp_path):
    db = build_historical_db(tmp_path / "old.db", PRE_AUGUST)
    env = {**os.environ, "LEXGRAPH_DATABASE_URL": f"sqlite:///{db}"}
    first = subprocess.run(
        [sys.executable, "-m", "app.migrate"], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120
    )
    assert first.returncode == 0, first.stderr
    assert re.search(r"20260729_add_definition_link_tables\s+already applied", first.stdout)
    for migration_id in SHIPPED_MIGRATIONS[2:]:
        assert re.search(rf"{migration_id}\s+applied", first.stdout), first.stdout

    second = subprocess.run(
        [sys.executable, "-m", "app.migrate", "--db", str(db)],
        cwd=BACKEND, capture_output=True, text=True, timeout=120,
    )
    assert second.returncode == 0, second.stderr
    assert "Nothing to do" in second.stdout


# --- the schema check the server runs at startup ------------------------------------


@pytest.mark.parametrize("fast", [True, False], ids=["sqlite-pragmas", "sqlalchemy-inspector"])
def test_schema_check_names_every_missing_table_and_column(tmp_path, fast):
    expected = {
        "2026-07-26_raw_text_columns.sql": {"table articles", "table definitions"},
        PRE_AUGUST: {
            "column documents.jurisdiction",
            "column assertions.subject_unit_path",
            "column articles.heading_breadcrumbs",
        },
    }
    for schema, missing in expected.items():
        db = build_historical_db(tmp_path / f"{schema}.db", schema)
        engine = make_engine(f"sqlite:///{db}")
        try:
            report = migrate.inspect_schema(engine, fast=fast)
        finally:
            engine.dispose()
        assert not report.is_current and not report.is_empty
        assert missing <= set(report.problems()), report.problems()

    fresh = build_fresh_db(tmp_path / "fresh.db")
    engine = make_engine(f"sqlite:///{fresh}")
    try:
        assert migrate.inspect_schema(engine, fast=fast).problems() == []
    finally:
        engine.dispose()


@pytest.mark.parametrize("fast", [True, False], ids=["sqlite-pragmas", "sqlalchemy-inspector"])
def test_schema_check_requires_declared_uniqueness_however_it_is_spelled(tmp_path, fast):
    db = build_fresh_db(tmp_path / "fresh.db")
    conn = sqlite3.connect(db)
    try:
        conn.executescript(
            """
            CREATE TABLE matter_roles_rebuilt (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                matter_id VARCHAR(36) NOT NULL,
                role VARCHAR(32) NOT NULL
            );
            DROP TABLE matter_roles;
            ALTER TABLE matter_roles_rebuilt RENAME TO matter_roles;
            """
        )
    finally:
        conn.close()
    engine = make_engine(f"sqlite:///{db}")
    try:
        assert migrate.inspect_schema(engine, fast=fast).problems() == [
            "unique (matter_id, user_id) on matter_roles"
        ]
        with engine.begin() as c:
            c.execute(text("CREATE UNIQUE INDEX ix_roles_once ON matter_roles (user_id, matter_id)"))
        assert migrate.inspect_schema(engine, fast=fast).is_current
    finally:
        engine.dispose()


@pytest.mark.parametrize("fast", [True, False], ids=["sqlite-pragmas", "sqlalchemy-inspector"])
def test_schema_check_recognizes_every_way_a_model_declares_uniqueness(tmp_path, fast):
    """Other modules add unique indexes through migrations while create_all()
    renders the same rule inline; both spellings must satisfy the check.

    SQLAlchemy's SQLite inspector skips expression-based indexes, so that case
    is only checked on the pragma path, which is what SQLite databases use."""
    from sqlalchemy import Index, MetaData, String, Table, UniqueConstraint, func
    from sqlalchemy import Column as C

    metadata = MetaData()
    table = Table(
        "things",
        metadata,
        C("id", String(36), primary_key=True),
        C("token", String(64), unique=True),
        C("slug", String(64), index=True, unique=True),
        C("owner", String(36)),
        C("name", String(64)),
        C("email", String(255)),
        UniqueConstraint("owner", "name", name="uq_things_owner_name"),
    )
    if fast:
        Index("uq_things_email_ci", func.lower(table.c.email), unique=True)
    created = tmp_path / "created.db"
    engine = create_engine(f"sqlite:///{created}")
    try:
        metadata.create_all(engine)
        assert migrate.inspect_schema(engine, fast=fast, metadata=metadata).is_current
    finally:
        engine.dispose()

    migrated = tmp_path / "migrated.db"
    engine = create_engine(f"sqlite:///{migrated}")
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE things (id VARCHAR(36) PRIMARY KEY, token VARCHAR(64), "
                    "slug VARCHAR(64), owner VARCHAR(36), name VARCHAR(64), email VARCHAR(255))"
                )
            )
        expected = [
            "unique (name, owner) on things",
            "unique (slug) on things",
            "unique (token) on things",
        ] + (["unique uq_things_email_ci on things"] if fast else [])
        assert sorted(migrate.inspect_schema(engine, fast=fast, metadata=metadata).problems()) == expected
        with engine.begin() as conn:
            # How a migration module would add the same rules to an existing table.
            conn.execute(text("CREATE UNIQUE INDEX ix_token ON things (token)"))
            conn.execute(text("CREATE UNIQUE INDEX ix_slug_once ON things (slug)"))
            conn.execute(text("CREATE UNIQUE INDEX uq_owner_name ON things (name, owner)"))
            if fast:
                conn.execute(text("CREATE UNIQUE INDEX uq_things_email_ci ON things (lower(email))"))
        assert migrate.inspect_schema(engine, fast=fast, metadata=metadata).is_current
    finally:
        engine.dispose()
