"""Database-level write lock for assertion writes that must re-check state
(audit findings agent:1, api:17, api:0).

Duplicate detection and revision numbering read the database and then
write. Without a lock two writers can read the same state, both pass their
check and both insert, so N identical submissions stored N rows and two
edits of one revision stored two rows with the same revision number. The
writers are separate processes (API server workers, the agent CLI, each MCP
server) sharing one database file, so a `threading.Lock` would not help.

`lock_assertion_writes` takes a lock that lasts until the caller's
transaction commits or rolls back; callers take it after their (possibly
slow) unlocked validation, then re-read what they depend on, then write:

* SQLite: `BEGIN IMMEDIATE` takes the database's write lock, so writers
  serialize across processes and every read after it sees all committed
  writes. The sqlite3 module's legacy transaction control opens no
  transaction for the earlier SELECTs, so the statement is legal there; if
  a transaction is already open, a no-op write claims the same lock (it is
  already held when an earlier write opened the transaction).
* Other databases (PostgreSQL): `SELECT ... FOR UPDATE` on the matter row
  serializes the writers of that matter; READ COMMITTED reads issued after
  it see the rows committed by the writer that held the lock before. This
  branch is untested here: only SQLite is installed and exercised.

The lock only ever joins a transaction this session opened (review
authoring:0). A connection the pool hands out inside a transaction carries
another session's uncommitted writes; claiming the lock in it would commit
them with this session's. `app.db` makes the pool roll such a transaction
back when the connection is returned, and records it if a connection is
ever handed out inside one anyway; the lock then rolls that transaction
back and raises `ForeignTransactionError` instead of joining it.

Waiting is bounded by the driver's busy timeout (5 s for sqlite3), after
which the database reports "database is locked" as before.
"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import TRANSACTION_AT_CHECKOUT
from app.models.matter import Matter


class ForeignTransactionError(RuntimeError):
    """The session's connection was handed out inside a transaction that
    another session opened and never ended."""


def lock_assertion_writes(session: Session, matter_id: str) -> None:
    """Serialize assertion writers of `matter_id` until the transaction ends."""
    if session.get_bind().dialect.name != "sqlite":
        session.execute(select(Matter.id).where(Matter.id == matter_id).with_for_update())
        return
    connection = session.connection()
    dbapi_connection = connection.connection.dbapi_connection
    if not getattr(dbapi_connection, "in_transaction", True):
        session.execute(text("BEGIN IMMEDIATE"))
        return
    if connection.info.get(TRANSACTION_AT_CHECKOUT):
        # Its writes belong to a request that has already ended; they must
        # never become durable. Whatever this session read in it is suspect.
        dbapi_connection.rollback()
        raise ForeignTransactionError(
            "the database connection was handed out inside a transaction another session left "
            "open; that transaction was rolled back and this write was refused"
        )
    session.execute(text("UPDATE matters SET id = id WHERE id = :id"), {"id": matter_id})
