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
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


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
