"""Bare FastAPI app factory (R2 scaffolding — no routes registered).

`create_app()` returns a working FastAPI instance with NO business routers
included. Every `/api/v1/...` request therefore currently 404s — that is
the intended RED signal for every backend integration test until a
Developer track includes its router (see `app/routers/__init__.py` for
per-track ownership).

Developer tracks call `app.include_router(...)` inside this factory (or
register via an `app.state`-based composition the track introduces) —
do not scatter `include_router` calls elsewhere.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.config import get_settings
from app.db import Base, make_engine, make_session_factory


def create_app() -> FastAPI:
    from app import models  # register ORM mappings

    settings = get_settings()
    app = FastAPI(title="LexGraph API", version="0.1.0")

    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    # Per-track include_router calls go here (R6 append-only zone — each
    # track appends only its own line(s); merge conflicts are resolved by
    # concatenating both sides, then a full evaluator run).
    from app.routers import review as review_router

    app.include_router(review_router.router)

    # Append-only zone (R6): each track appends only its own registration
    # line(s); merge conflicts here are resolved by concatenating both
    # sides, then a full evaluator run.
    from app.routers.assertions import router as assertions_router

    app.include_router(assertions_router)

    # B6 — graph projection + notifications (append-only registration, R6).
    from app.graph_projection import InMemoryGraphProjection
    from app.notification_hooks import register_notification_hooks
    from app.routers import graph as graph_router
    from app.routers import notifications as notifications_router

    app.state.graph_projection = InMemoryGraphProjection()
    app.state.notification_store = []
    app.include_router(graph_router.router)
    app.include_router(notifications_router.router)
    register_notification_hooks(app)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


# Zero-argument module-level app for `uvicorn app.main:app` convenience.
app = create_app()
