"""Database engine/session scaffolding.

Scaffolding only (sprint 2026-07-25-collaborative-assertions, Planner pass).
`Base` is the shared SQLAlchemy declarative base; no ORM model classes are
registered against it yet — that is Developer work, tracked per-item in the
sprint contract (see "Data model reference" section). Until Developer tracks
register models, `Base.metadata.create_all()` creates zero tables, so any
test that queries a domain table (e.g. `assertions`, `assertion_ratings`)
via raw SQL will fail with `sqlalchemy.exc.OperationalError: no such table`
— a legitimate RED-for-missing-behavior signal, not a collection/import
error.

Every engine of every process comes from `make_engine` (the API server, the
agent CLI, the MCP server, migrations, bootstrap and the other command-line
tools), so the connection-pool rules below hold everywhere (review
authoring:0):

* A connection the pool takes back is never left inside a transaction
  (`rollback_leftover_transaction`). On SQLite a COMMIT fails with "database
  is locked" when another connection keeps its SHARED lock past the busy
  timeout. SQLAlchemy then marks the transaction inactive without rolling it
  back, and closing the session hands the connection back flagged as already
  reset, so the pool skips its own rollback. That connection used to keep the
  write lock and the journal: no process could read or write the database
  until a later request happened to draw it, and that request then committed
  the failed request's rows with its own, or answered a retry with a 409
  naming an assertion that was never committed.
* The pool records whether it handed a connection out inside a transaction
  (`TRANSACTION_AT_CHECKOUT`), so `app.services.write_lock` can refuse to
  join a transaction that its session did not open.

The database keeps SQLite's default rollback journal. WAL would let a COMMIT
proceed while readers are active, but it is not safe for every entry point:
a read-only open (`mode=ro`, used by seed_demo and the dev and demo scripts)
cannot create the -shm file it needs, and the documented backup
(`cp dev.db dev.db.bak`) would miss transactions not yet checkpointed from
the -wal file.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

#: Key in a pooled connection's `info` (a `Connection.info` of the session's
#: connection): True when the pool handed the connection out while a
#: transaction was already open on it, i.e. one this checkout did not open.
TRANSACTION_AT_CHECKOUT = "lexgraph.transaction_at_checkout"


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "reset", rollback_leftover_transaction)
        event.listen(engine, "checkout", note_transaction_at_checkout)
    return engine


def rollback_leftover_transaction(dbapi_connection, connection_record, reset_state) -> None:
    """Pool `reset` hook: roll back a transaction still open on a connection
    that is being returned to the pool.

    The pool calls it on every return, including the one after a failed
    COMMIT, where SQLAlchemy reports the transaction as already reset and the
    pool's own rollback does not run (see the module docstring)."""
    if reset_state.asyncio_safe and getattr(dbapi_connection, "in_transaction", False):
        dbapi_connection.rollback()


def note_transaction_at_checkout(dbapi_connection, connection_record, connection_proxy) -> None:
    """Pool `checkout` hook: record `TRANSACTION_AT_CHECKOUT` for this checkout."""
    connection_record.info[TRANSACTION_AT_CHECKOUT] = bool(
        getattr(dbapi_connection, "in_transaction", False)
    )


def make_session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db_dependency(session_factory: sessionmaker[Session]):
    """Return a FastAPI dependency that yields a Session from `session_factory`.

    Not wired into any route by the Planner (there are no routes yet). A
    Developer track wires `Depends(get_db_dependency(...))` — or an
    app.state-based equivalent — into its router.
    """

    def _get_db() -> Iterator[Session]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    return _get_db
