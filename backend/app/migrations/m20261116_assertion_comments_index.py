"""Index assertion_comments by assertion (review workflow:5).

Comments are read per assertion: GET /assertions/{id}/comments, and the
recipients of every comment, evidence and edit notice, which the
notification hook works out before the response is sent. assertion_comments
had no index on assertion_id, so each of those reads scanned every matter's
comments. The model declares ix_assertion_comments_assertion_id, so
`create_all()` builds it on a fresh database; this migration adds it to an
existing one.

Idempotent, per the migration convention: it creates the index only when no
index of that name exists, touches no row, and returns False on a fresh
`create_all()` database and on an upgraded one.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

MIGRATION_ID = "20261116_assertion_comments_index"

TABLE = "assertion_comments"
INDEX = "ix_assertion_comments_assertion_id"


def _has_index(conn) -> bool:
    return any(index["name"] == INDEX for index in inspect(conn).get_indexes(TABLE))


def upgrade(engine: Engine) -> bool:
    with engine.begin() as conn:
        if not inspect(conn).has_table(TABLE) or _has_index(conn):
            return False
        conn.execute(text(f"CREATE INDEX {INDEX} ON {TABLE} (assertion_id)"))
    return True


def downgrade(engine: Engine) -> bool:
    """Drop the index again (it holds no data). True if it was dropped."""
    with engine.begin() as conn:
        if not inspect(conn).has_table(TABLE) or not _has_index(conn):
            return False
        conn.execute(text(f"DROP INDEX {INDEX}"))
    return True
