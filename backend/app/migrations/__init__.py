"""Hand-rolled schema migrations for existing databases (no Alembic -- sprint
2026-07-26-local-first-platform, Track A, item A1).

Migrations operate on a plain SQLAlchemy ``Engine`` (raw DDL via
``sqlalchemy.text`` or a frozen Core snapshot), so they run standalone against
a local SQLite file without any migration-framework dependency, matching this
project's local-first, zero-cloud-dependency posture.

Apply them with ``python -m app.migrate --db PATH`` (``app/migrate.py``). The
runner discovers every module in this package that exposes ``MIGRATION_ID`` and
``upgrade``, and applies them in ``MIGRATION_ID`` order. Nothing else needs
wiring. Fresh databases are still created with ``Base.metadata.create_all()``,
so the ORM models must declare the same schema the migrations produce.

Convention, binding for every module here:

* A new module is ``m<YYYYMMDD>_<slug>.py`` and sets
  ``MIGRATION_ID = "<YYYYMMDD>_<slug>"``. The date orders the runs.
* ``upgrade(engine) -> bool`` is idempotent. It inspects the live schema,
  changes only what is missing and returns ``True`` only if it changed
  something. It is a no-op returning ``False`` on a database
  ``create_all()`` just built and on an already-upgraded one. It never
  silently deletes user data.
* All of a migration's work happens inside ONE ``with engine.begin() as conn:``
  block. The runner's engine makes SQLite DDL transactional (``ALTER TABLE``
  included), so a failure rolls the whole migration back instead of leaving a
  half-applied schema that a re-run would mistake for a finished one.
* Modules whose name starts with ``_`` are helpers and are never run.

The three modules that predate the runner keep their original file names, so
their documented ``from app.migrations.<module> import upgrade`` entry points
keep working. Their ``MIGRATION_ID`` carries the date each one shipped:
``add_raw_text_columns`` (2026-07-26),
``add_assertion_subject_unit_path_column`` (2026-08-04) and
``add_heading_breadcrumbs_column`` (2026-08-05).
"""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Connection


def has_table(conn: Connection, table: str) -> bool:
    """Whether ``table`` exists, as seen inside ``conn``'s transaction."""
    return inspect(conn).has_table(table)


def has_column(conn: Connection, table: str, column: str) -> bool:
    """Whether ``table.column`` exists (``False`` when the table is missing)."""
    if not has_table(conn, table):
        return False
    return any(col["name"] == column for col in inspect(conn).get_columns(table))
