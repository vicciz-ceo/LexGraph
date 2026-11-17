"""Open the workspace database for the agent CLI and the MCP server.

Opening a missing SQLite path creates an empty database, so a mistyped or
relative LEXGRAPH_DATABASE_URL used to leave a stray 0-byte file behind and
report "not initialized" (CLI) or start a server whose every tool failed
(MCP). `open_database` checks first and never creates anything. It also runs
the API server's schema check (`app.migrate.check_schema`), so a database from
an older release is refused with the `python -m app.migrate` command instead of
failing halfway through a request with "no such column".
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

from sqlalchemy import inspect
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, DBAPIError, SQLAlchemyError
from sqlalchemy.util import asbool

from app.db import make_engine

_EXAMPLE = "sqlite:////absolute/path/to/LexGraph/backend/dev.db"


class ConfigurationError(Exception):
    """LEXGRAPH_* settings do not lead to a usable workspace (status 500, not a payload problem)."""


def _sqlite_file(url: URL) -> Path | None:
    """The file SQLite would open for `url`, or None for an in-memory database."""
    database = url.database or ""
    if asbool(url.query.get("uri", False)) and database.startswith("file:"):
        if url.query.get("mode") == "memory":
            return None
        database = unquote(urlsplit(database).path)
    if database in ("", ":memory:"):
        return None
    return Path(os.path.abspath(database))  # what the driver resolves: the working directory


def open_database(database_url: str):
    """An engine for an existing, initialized LexGraph database, or ConfigurationError."""
    unset = ConfigurationError(
        "LEXGRAPH_DATABASE_URL is unset or names an in-memory database, which no other process can "
        f"share. Set it to the absolute four-slash URL of the web app's database, e.g. {_EXAMPLE}")
    if not database_url.strip():
        raise unset
    try:
        url = make_url(database_url)
    except ArgumentError as exc:
        raise ConfigurationError(f"LEXGRAPH_DATABASE_URL {database_url!r} is not a database URL") from exc
    where = url.render_as_string(hide_password=True)
    if url.get_backend_name() == "sqlite":
        path = _sqlite_file(url)
        if path is None:
            raise unset
        if not path.is_file():
            problem = "is a directory, not a database file" if path.is_dir() else "not found"
            raise ConfigurationError(
                f"Database file {problem}: {path} (LEXGRAPH_DATABASE_URL={database_url!r}, working directory "
                f"{Path.cwd()}). Nothing was created. A relative sqlite:/// URL resolves against the working "
                f"directory; use the absolute four-slash URL of the web app's database, e.g. {_EXAMPLE}")
        where = str(path)
    engine = None
    try:
        engine = make_engine(database_url)
        initialized = inspect(engine).has_table("assertions")
    except (ImportError, SQLAlchemyError) as exc:
        if engine is not None:
            engine.dispose()
        reason = exc.orig if isinstance(exc, DBAPIError) else str(exc).splitlines()[0]
        raise ConfigurationError(f"Cannot open the database {where}: {reason}") from exc
    if not initialized:
        engine.dispose()
        raise ConfigurationError(
            f"{where} is not an initialized LexGraph database (no assertions table). Point "
            "LEXGRAPH_DATABASE_URL at the database the web app uses; run app.bootstrap only to start a new workspace.")
    from app.migrate import check_schema, upgrade_command

    report, _pending = check_schema(engine)
    if not report.is_current:
        engine.dispose()
        raise ConfigurationError(
            f"{where} was created by an older version of LexGraph and lacks {', '.join(report.problems())}. "
            f"Upgrade it first (safe to re-run): {upgrade_command(url)}")
    return engine
