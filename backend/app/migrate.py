"""Upgrade an existing LexGraph database to the current schema.

Usage (from ``backend/``, after ``pip install -e '.[dev]'``):

    .venv/bin/python -m app.migrate --db dev.db
    LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/python -m app.migrate

Discovers every module in ``app.migrations`` that exposes ``MIGRATION_ID`` and
``upgrade(engine) -> bool`` and applies them in ``MIGRATION_ID`` order,
printing what each one did. It is safe to re-run: every migration changes only
what is missing, so a current database is left untouched. Each migration runs
in its own transaction (on SQLite the runner's engine makes ``ALTER TABLE``
transactional too), so a failure rolls that migration back and stops the run.
After the last migration the result is checked against the ORM models with
``inspect_schema``. The API server runs the same check at startup and refuses
to serve an out-of-date database (``ensure_schema_current``).

The runner never creates a database. A missing file or a file without LexGraph
tables is refused; ``python -m app.bootstrap`` creates new workspaces.

A migration never deletes or merges rows to make room for a unique index. When
stored rows violate one (accounts sharing an email address), it leaves that
index out and its optional ``pending_uniques(engine)`` says what an operator
must resolve. Such a database is still usable: the runner and the server's
startup check report the pending index instead of refusing it, and the next
run creates the index once the rows are resolved.

Exit status: 0 when the schema is current, or lacks only unique indexes that
wait for an operator (they are listed); 1 when the run was refused or failed.
"""

from __future__ import annotations

import argparse
import importlib
import os
import pkgutil
import re
import shlex
import sys
from collections.abc import Callable, Collection, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import Column, MetaData, UniqueConstraint, event, inspect
from sqlalchemy.engine import URL, Connection, Engine, make_url

import app.models  # noqa: F401  (register every mapped table on Base.metadata)
from app.db import Base, make_engine

MIGRATIONS_PACKAGE = "app.migrations"
_MIGRATION_ID = re.compile(r"\d{8}_[A-Za-z0-9_]+")


class MigrationError(RuntimeError):
    """The migrations package cannot be applied safely (bad or duplicate IDs)."""


class SchemaNotCurrentError(RuntimeError):
    """The database cannot serve this version of LexGraph. The message says
    exactly which command fixes it."""


@dataclass(frozen=True)
class Migration:
    id: str
    module: str
    upgrade: Callable[[Engine], bool]
    #: Optional ``pending_uniques(engine) -> {index name: what to resolve}``:
    #: declared unique indexes this migration leaves out while stored rows
    #: violate them, until an operator resolves those rows.
    pending_uniques: Callable[[Engine], dict[str, str]] | None = None


def discover_migrations(package: str = MIGRATIONS_PACKAGE) -> list[Migration]:
    """Every module of ``package`` that exposes ``MIGRATION_ID`` and
    ``upgrade()``, sorted by ``MIGRATION_ID``.

    Modules whose name starts with ``_``, and modules defining neither name,
    are skipped. A malformed or duplicated ID, an ID without ``upgrade()``, or
    a ``pending_uniques`` that is not a function raises ``MigrationError``
    before anything runs.
    """
    root = importlib.import_module(package)
    found: list[Migration] = []
    for info in pkgutil.iter_modules(root.__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{package}.{info.name}")
        migration_id = getattr(module, "MIGRATION_ID", None)
        upgrade = getattr(module, "upgrade", None)
        if migration_id is None and upgrade is None:
            continue
        if not isinstance(migration_id, str) or not _MIGRATION_ID.fullmatch(migration_id):
            raise MigrationError(
                f"{module.__name__}: MIGRATION_ID must look like 'YYYYMMDD_slug', got {migration_id!r}"
            )
        if not callable(upgrade):
            raise MigrationError(f"{module.__name__}: {migration_id} has no upgrade(engine) function")
        pending = getattr(module, "pending_uniques", None)
        if pending is not None and not callable(pending):
            raise MigrationError(f"{module.__name__}: pending_uniques must be a function of the engine")
        found.append(
            Migration(id=migration_id, module=module.__name__, upgrade=upgrade, pending_uniques=pending)
        )

    modules_by_id: dict[str, list[str]] = {}
    for migration in found:
        modules_by_id.setdefault(migration.id, []).append(migration.module)
    duplicates = {mid: sorted(mods) for mid, mods in modules_by_id.items() if len(mods) > 1}
    if duplicates:
        raise MigrationError(
            "duplicate MIGRATION_ID: "
            + "; ".join(f"{mid} in {', '.join(mods)}" for mid, mods in sorted(duplicates.items()))
        )
    return sorted(found, key=lambda migration: migration.id)


def make_migration_engine(database_url: str | URL) -> Engine:
    """The engine every ``upgrade()`` receives from the runner.

    pysqlite manages transactions itself: it opens one before INSERT/UPDATE/
    DELETE but not before DDL, so inside ``engine.begin()`` an ``ALTER TABLE``
    is committed on the spot and survives a later rollback. A migration that
    failed halfway would then look finished to its own idempotency check on
    the next run. Here the driver is put in autocommit mode and every
    transaction is an explicit ``BEGIN IMMEDIATE`` (taking the write lock up
    front, so two concurrent runs serialize instead of racing), which makes
    a migration's DDL and data changes commit or roll back together.
    """
    if isinstance(database_url, URL):  # str(URL) would mask the password
        database_url = database_url.render_as_string(hide_password=False)
    engine = make_engine(database_url)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _driver_autocommit(dbapi_connection, _connection_record):
            dbapi_connection.isolation_level = None

        @event.listens_for(engine, "begin")
        def _begin_immediate(conn):
            conn.exec_driver_sql("BEGIN IMMEDIATE")

    return engine


# --- schema check -------------------------------------------------------------


@dataclass
class _LiveTable:
    columns: set[str] = field(default_factory=set)
    unique_sets: set[frozenset[str]] = field(default_factory=set)
    unique_index_names: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class SchemaReport:
    """How the live database falls short of the current ORM models.

    Only what the application needs is compared: every model table, every
    column, and every declared uniqueness (as a unique constraint or a unique
    index, whichever way it was created). Extra tables, columns and indexes,
    column types and plain indexes are not compared.

    ``pending_uniques`` lists the missing unique indexes that a migration left
    out until an operator resolves the rows violating them (see
    ``check_schema``); they do not make the database unusable.
    """

    missing_tables: tuple[str, ...]
    missing_columns: tuple[str, ...]
    missing_uniques: tuple[str, ...]
    model_table_count: int
    pending_uniques: tuple[str, ...] = ()

    @property
    def is_current(self) -> bool:
        """Usable by this version: nothing missing except pending uniques."""
        return not (self.missing_tables or self.missing_columns or self.missing_uniques)

    @property
    def is_empty(self) -> bool:
        """No model table exists at all: not a LexGraph database (yet)."""
        return len(self.missing_tables) == self.model_table_count

    def problems(self) -> list[str]:
        return (
            [f"table {name}" for name in self.missing_tables]
            + [f"column {name}" for name in self.missing_columns]
            + [f"unique {name}" for name in self.missing_uniques]
        )


def _live_schema_sqlite(conn: Connection) -> dict[str, _LiveTable]:
    # Two queries over SQLite's table-valued pragmas instead of one
    # inspector round trip per table: the check runs on every server start
    # and every TestClient lifespan in the test suite.
    live: dict[str, _LiveTable] = {}
    for table, column in conn.exec_driver_sql(
        "SELECT m.name, p.name FROM sqlite_master AS m, pragma_table_info(m.name) AS p "
        "WHERE m.type = 'table'"
    ):
        live.setdefault(table, _LiveTable()).columns.add(column)
    indexes: dict[tuple[str, str], list[str | None]] = {}
    for table, index, unique, column in conn.exec_driver_sql(
        'SELECT m.name, il.name, il."unique", ii.name FROM sqlite_master AS m, '
        "pragma_index_list(m.name) AS il, pragma_index_info(il.name) AS ii "
        "WHERE m.type = 'table' AND il.\"unique\" = 1"
    ):
        indexes.setdefault((table, index), []).append(column)
    for (table, index), columns in indexes.items():
        found = live.setdefault(table, _LiveTable())
        found.unique_index_names.add(index)
        if all(columns):  # an expression column has no name
            found.unique_sets.add(frozenset(columns))
    return live


def _live_schema_inspector(conn: Connection, wanted: set[str]) -> dict[str, _LiveTable]:
    insp = inspect(conn)
    live: dict[str, _LiveTable] = {}
    for table in set(insp.get_table_names()) & wanted:
        found = live[table] = _LiveTable(columns={c["name"] for c in insp.get_columns(table)})
        for constraint in insp.get_unique_constraints(table):
            found.unique_sets.add(frozenset(constraint["column_names"]))
            if constraint.get("name"):
                found.unique_index_names.add(constraint["name"])
        for index in insp.get_indexes(table):
            if not index.get("unique"):
                continue
            if index.get("name"):
                found.unique_index_names.add(index["name"])
            columns = index.get("column_names") or []
            if columns and all(columns):
                found.unique_sets.add(frozenset(columns))
    return live


def _declared_uniques(table) -> Iterator[tuple[frozenset[str] | None, str | None]]:
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            yield frozenset(column.name for column in constraint.columns), constraint.name
    for index in table.indexes:
        if index.unique:
            plain = all(isinstance(expr, Column) for expr in index.expressions)
            yield (frozenset(column.name for column in index.columns) if plain else None), index.name


def inspect_schema(
    engine: Engine,
    *,
    fast: bool = True,
    metadata: MetaData | None = None,
    pending: Collection[str] = (),
) -> SchemaReport:
    """Compare the live database with ``metadata`` (default: the app's
    ``Base.metadata``; see SchemaReport).

    ``fast`` uses SQLite's pragmas directly; other dialects (and ``fast=False``)
    go through SQLAlchemy's inspector. A missing declared uniqueness whose name
    is in ``pending`` is reported in ``pending_uniques`` instead of
    ``missing_uniques``.
    """
    model_tables = (metadata if metadata is not None else Base.metadata).sorted_tables
    with engine.connect() as conn:
        if fast and conn.dialect.name == "sqlite":
            live = _live_schema_sqlite(conn)
        else:
            live = _live_schema_inspector(conn, {table.name for table in model_tables})

    missing_tables: list[str] = []
    missing_columns: list[str] = []
    missing_uniques: list[str] = []
    pending_uniques: list[str] = []
    for table in model_tables:
        found = live.get(table.name)
        if found is None:
            missing_tables.append(table.name)
            continue
        missing_columns += [f"{table.name}.{col.name}" for col in table.columns if col.name not in found.columns]
        for columns, name in _declared_uniques(table):
            if columns is not None and columns in found.unique_sets:
                continue
            if name and name in found.unique_index_names:
                continue
            what = f"({', '.join(sorted(columns))})" if columns is not None else str(name)
            (pending_uniques if name in pending else missing_uniques).append(f"{what} on {table.name}")
    return SchemaReport(
        missing_tables=tuple(missing_tables),
        missing_columns=tuple(missing_columns),
        missing_uniques=tuple(missing_uniques),
        model_table_count=len(model_tables),
        pending_uniques=tuple(pending_uniques),
    )


def pending_uniques(engine: Engine, migrations: list[Migration] | None = None) -> dict[str, str]:
    """Unique indexes a migration left out until an operator resolves the rows
    that violate them: ``{index name: what to resolve}`` (``Migration.pending_uniques``)."""
    pending: dict[str, str] = {}
    for migration in discover_migrations() if migrations is None else migrations:
        if migration.pending_uniques is not None:
            pending.update(migration.pending_uniques(engine))
    return pending


def check_schema(
    engine: Engine, migrations: list[Migration] | None = None
) -> tuple[SchemaReport, dict[str, str]]:
    """``inspect_schema`` that also accounts for pending uniques.

    Returns the report and ``{index name: what to resolve}`` for the unique
    indexes that only wait for an operator. Those are consulted only when
    every table and column exists, so a migration's check can rely on them.
    """
    report = inspect_schema(engine)
    if report.is_current or report.missing_tables or report.missing_columns:
        return report, {}
    pending = pending_uniques(engine, migrations)
    if not pending:
        return report, {}
    return inspect_schema(engine, pending=pending), pending


# --- messages -------------------------------------------------------------------


def _is_memory(url: URL) -> bool:
    return url.get_backend_name() == "sqlite" and (
        url.database in (None, "", ":memory:") or url.query.get("mode") == "memory"
    )


def _sqlite_file(url: URL) -> Path | None:
    if url.get_backend_name() != "sqlite" or _is_memory(url) or url.database.startswith("file:"):
        return None
    return Path(os.path.abspath(os.path.expanduser(url.database)))


def _where(url: URL) -> str:
    path = _sqlite_file(url)
    return str(path) if path is not None else url.render_as_string(hide_password=True)


def _command(module: str, url: URL) -> str:
    """The exact command for ``module`` against the database at ``url``."""
    python = shlex.quote(sys.executable or "python")
    path = _sqlite_file(url)
    if path is not None:
        return f"{python} -m {module} --db {shlex.quote(str(path))}"
    shown = shlex.quote(url.render_as_string(hide_password=True))
    return f"LEXGRAPH_DATABASE_URL={shown} {python} -m {module}"


def upgrade_command(url: URL | str) -> str:
    """The exact ``python -m app.migrate`` command that upgrades the database at ``url``."""
    return _command("app.migrate", make_url(url) if isinstance(url, str) else url)


def _usability(engine: Engine) -> tuple[str | None, dict[str, str]]:
    """(why the server cannot serve this database, with the fix, or None;
    the unique indexes pending an operator, see ``check_schema``)."""
    url = engine.url
    path = _sqlite_file(url)
    if path is not None and not path.exists():
        # Checked before connecting: SQLite would create an empty file.
        return (
            f"LexGraph cannot start: there is no database file at {path}.\n"
            f"Create a workspace there:\n    {_command('app.bootstrap', url)}\n"
            "or point LEXGRAPH_DATABASE_URL at an existing LexGraph database."
        ), {}
    report, pending = check_schema(engine)
    if report.is_current:
        return None, pending
    return _unusable_message(url, report), {}


def _unusable_message(url: URL, report: SchemaReport) -> str:
    if _is_memory(url):
        python = shlex.quote(sys.executable or "python")
        return (
            "LexGraph cannot start: LEXGRAPH_DATABASE_URL is not set (or names an in-memory "
            "database), so the server would run on an empty database that no other process "
            "can fill. Create a workspace and point the server at it:\n"
            f"    {python} -m app.bootstrap --db dev.db\n"
            f"    LEXGRAPH_DATABASE_URL=sqlite:///dev.db {python} -m uvicorn app.main:app"
        )
    if report.is_empty:
        return (
            f"LexGraph cannot start: the database at {_where(url)} has no LexGraph tables.\n"
            f"Create a workspace in it:\n    {_command('app.bootstrap', url)}"
        )
    missing = "\n".join(f"  - {problem}" for problem in report.problems())
    return (
        f"LexGraph cannot start: the database at {_where(url)} was created by an older "
        f"version of LexGraph. It is missing:\n{missing}\n"
        "Upgrade it in place (safe to re-run; each migration runs in its own transaction):\n"
        f"    {_command('app.migrate', url)}"
    )


def unusable_database_message(engine: Engine) -> str | None:
    """Why the server cannot serve this database, with the fix; None if it can."""
    return _usability(engine)[0]


def ensure_schema_current(engine: Engine) -> dict[str, str]:
    """Raise SchemaNotCurrentError, naming the fix, unless the server can use
    this database. Called from the API server's lifespan (app/main.py).

    Returns the unique indexes that only wait for an operator, ``{index name:
    what to resolve}`` (usually empty), for the server to report."""
    message, pending = _usability(engine)
    if message is not None:
        raise SchemaNotCurrentError(message)
    return pending


# --- command line ---------------------------------------------------------------


def _error(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.migrate",
        description="Upgrade an existing LexGraph database to the current schema (safe to re-run).",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite file to upgrade (same convention as app.bootstrap). "
        "If omitted, LEXGRAPH_DATABASE_URL is read from the environment.",
    )
    args = parser.parse_args(argv)

    if args.db:
        url = make_url(f"sqlite:///{args.db}")
    else:
        from app.config import get_settings

        url = make_url(get_settings().database_url)
    if _is_memory(url):
        return _error(
            "Nothing to upgrade: pass --db PATH, or set LEXGRAPH_DATABASE_URL to the database "
            "you want to upgrade (an in-memory database always starts empty)."
        )
    path = _sqlite_file(url)
    if path is not None and not path.exists():
        return _error(
            f"There is no database file at {path} (nothing was created). "
            f"To start a new workspace there instead, run:\n    {_command('app.bootstrap', url)}"
        )

    try:
        migrations = discover_migrations()
    except MigrationError as exc:
        return _error(f"Cannot upgrade: {exc}")

    engine = make_migration_engine(url)
    try:
        if inspect_schema(engine).is_empty:
            return _error(
                f"The database at {_where(url)} has no LexGraph tables, so there is nothing to "
                f"upgrade. Create a workspace in it with:\n    {_command('app.bootstrap', url)}"
            )
        print(f"Upgrading {_where(url)}")
        width = max((len(migration.id) for migration in migrations), default=0)
        applied = 0
        for position, migration in enumerate(migrations):
            try:
                changed = migration.upgrade(engine)
            except Exception as exc:  # report, then stop: later migrations may depend on it
                print(f"  {migration.id:<{width}}  FAILED", flush=True)
                later = len(migrations) - position - 1
                return _error(
                    f"Migration {migration.id} ({migration.module}) failed and was rolled back: "
                    f"{type(exc).__name__}: {exc}\n"
                    f"{applied} migration(s) applied earlier in this run were kept; the {later} "
                    "after it did not run. Fix the cause and re-run the same command."
                )
            applied += bool(changed)
            print(f"  {migration.id:<{width}}  {'applied' if changed else 'already applied'}", flush=True)
        report, pending = check_schema(engine, migrations)
    finally:
        engine.dispose()

    if not report.is_current:
        missing = "\n".join(f"  - {problem}" for problem in report.problems())
        return _error(
            f"The database is still missing:\n{missing}\n"
            "Either it is not a LexGraph database, or a model change shipped without a "
            "migration module in app/migrations, so it cannot be upgraded yet."
        )
    done = (
        f"Applied {applied} of {len(migrations)} migrations"
        if applied
        else f"Nothing to do: all {len(migrations)} migrations were already applied"
    )
    if pending:
        waiting = "\n".join(f"  - unique index {name}: {action}" for name, action in sorted(pending.items()))
        print(
            f"{done}. LexGraph can use the database, but {len(pending)} unique index(es) wait "
            f"for an operator:\n{waiting}\nResolve that, then run this command again."
        )
    else:
        print(f"{done}; the schema is current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
