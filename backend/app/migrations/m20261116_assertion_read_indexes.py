"""Read indexes for the assertion list, detail page, graph and statistics.

The lists package (findings api:14, ui:1) made GET /assertions, the graph
and assertion-stats read a page's evidence, ratings and audit history with a
fixed number of batched `IN (...)` queries, and filter assertions by matter
and status in SQL. Without these indexes each of those lookups scans its
whole table (XREQ-67). The models declare the same indexes, so
`create_all()` builds them on a fresh database; this migration adds them to
an existing one.

Not repeated here: assertion_revisions(assertion_id, revision_number) is
already covered by the unique index that
`20261116_assertion_revision_number_unique` creates, which serves lookups by
assertion.

Idempotent, per the migration convention: it creates only the indexes that
are missing (by name), touches no row, and returns False on a fresh
`create_all()` database and on an upgraded one.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

MIGRATION_ID = "20261116_assertion_read_indexes"

#: (table, index name, columns): the names the models declare.
INDEXES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("assertions", "ix_assertions_matter_id_status", ("matter_id", "status")),
    ("assertion_evidence", "ix_assertion_evidence_assertion_id", ("assertion_id",)),
    ("assertion_ratings", "ix_assertion_ratings_assertion_revision_id", ("assertion_revision_id",)),
    ("audit_events", "ix_audit_events_assertion_id_event_type", ("assertion_id", "event_type")),
)


def upgrade(engine: Engine) -> bool:
    changed = False
    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        for table, name, columns in INDEXES:
            if table not in tables:
                continue  # an older migration creates the table, with create_all's DDL
            if any(index["name"] == name for index in inspector.get_indexes(table)):
                continue
            conn.execute(text(f"CREATE INDEX {name} ON {table} ({', '.join(columns)})"))
            changed = True
    return changed


def downgrade(engine: Engine) -> bool:
    """Drop the indexes again (they hold no data). True if any was dropped."""
    changed = False
    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        for table, name, _columns in INDEXES:
            if table in tables and any(index["name"] == name for index in inspector.get_indexes(table)):
                conn.execute(text(f"DROP INDEX {name}"))
                changed = True
    return changed
