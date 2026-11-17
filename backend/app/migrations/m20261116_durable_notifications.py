"""Migration: create the durable in-app notification tables (findings
pipeline:9 and ui:7).

Notifications used to be a Python list on each app instance
(`app.state.notification_store`): a restart emptied every feed, each API
worker had its own feed, the agent CLI and MCP server could never reach it,
and nothing could be marked as read. They are now rows in `notifications`
(one per recipient, with `read_at`), plus per-user switches in
`notification_preferences` (see `app.models.notification`).

The tables are created from a frozen Core snapshot of the 2026-11-16
models, not from today's ORM classes, so this module's output never drifts
when a model changes later.

Idempotent, per the migration convention (`MIGRATION_ID` + `upgrade`):

- fresh `Base.metadata.create_all()` database: both tables and their
  indexes exist, nothing to do, returns False;
- older LexGraph database: creates whichever table or index is missing,
  returns True;
- already-migrated database: returns False;
- a database without the LexGraph tables the new ones reference (users,
  matters, assertions): nothing to attach them to, returns False
  (`app.bootstrap` / `create_all()` build new databases).

The new tables start empty: the old in-process notices died with their
process, so there is nothing to carry over. No existing row is touched.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    inspect,
)
from sqlalchemy.engine import Engine

MIGRATION_ID = "20261116_durable_notifications"

# Tables the new ones point at. Only their names matter here (for compiling
# REFERENCES clauses); they are never created by this module.
_REQUIRED_TABLES = ("users", "matters", "assertions")

_SNAPSHOT = MetaData()
for _parent in _REQUIRED_TABLES:
    Table(_parent, _SNAPSHOT, Column("id", String(36), primary_key=True))

_NOTIFICATIONS = Table(
    "notifications",
    _SNAPSHOT,
    Column("id", String(36), primary_key=True),
    Column("recipient_user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("actor_user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("event_type", String(64), nullable=False),
    Column("matter_id", String(36), ForeignKey("matters.id"), nullable=True),
    Column("assertion_id", String(36), ForeignKey("assertions.id"), nullable=True),
    Column("payload", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("read_at", DateTime(timezone=True), nullable=True),
    Index("ix_notifications_recipient_created", "recipient_user_id", "created_at"),
    Index("ix_notifications_recipient_read", "recipient_user_id", "read_at"),
    Index("ix_notifications_assertion", "assertion_id"),
)

_NOTIFICATION_PREFERENCES = Table(
    "notification_preferences",
    _SNAPSHOT,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("event_type", String(64), nullable=False),
    Column("enabled", Boolean, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("user_id", "event_type", name="uq_notification_preferences_user_event"),
)

_TABLES = (_NOTIFICATIONS, _NOTIFICATION_PREFERENCES)


def upgrade(engine: Engine) -> bool:
    """Create whichever notification table or index is missing.

    Returns whether anything was created.
    """
    changed = False
    with engine.begin() as conn:
        inspector = inspect(conn)
        existing = set(inspector.get_table_names())
        if not set(_REQUIRED_TABLES) <= existing:
            return False
        for table in _TABLES:
            if table.name not in existing:
                table.create(conn)  # also creates the table's indexes
                changed = True
                continue
            # A table that exists but lost (or never got) an index, e.g. a
            # run interrupted between CREATE TABLE and CREATE INDEX on a
            # driver that commits DDL immediately.
            present = {index["name"] for index in inspector.get_indexes(table.name)}
            for index in sorted(table.indexes, key=lambda ix: ix.name):
                if index.name not in present:
                    index.create(conn)
                    changed = True
    return changed


def downgrade(engine: Engine) -> None:
    """Drop the notification tables, refusing to drop one that holds rows
    (never silently delete users' notifications or preferences)."""
    with engine.begin() as conn:
        existing = set(inspect(conn).get_table_names())
        for table in reversed(_TABLES):
            if table.name not in existing:
                continue
            if conn.execute(table.select().limit(1)).first() is not None:
                raise RuntimeError(f"refusing to drop non-empty table {table.name!r}")
            table.drop(conn)
