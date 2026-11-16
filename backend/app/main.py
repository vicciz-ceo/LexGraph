"""FastAPI app factory: `create_app()`, plus the module-level `app` that
`uvicorn app.main:app` serves.

`create_app()` includes every router (see `app/routers/__init__.py` for
per-track ownership). Developer tracks call `app.include_router(...)`
inside this factory, in the append-only R6 zones below; do not scatter
`include_router` calls elsewhere. Around the routers it adds:

- a lifespan that refuses to start on a database this version cannot use
  (no file, no LexGraph tables, or an older schema) and prints the command
  that fixes it (`app.migrate.ensure_schema_current`);
- /docs (Swagger UI) and /redoc (Redoc) served from vendored assets so they
  work offline, and an openapi.json that declares the bearer credential so
  Swagger UI's "Authorize" can call the API;
- the built web app (frontend/dist, or LEXGRAPH_FRONTEND_DIST) on the same
  origin, so `npm --prefix frontend run build` plus uvicorn is the whole
  production deployment.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.db import Base, make_engine, make_session_factory
from app.migrate import ensure_schema_current

# The web app's production build (`npm --prefix frontend run build`), served on
# the API's own origin when it exists. LEXGRAPH_FRONTEND_DIST overrides the
# location; an empty value serves the API only.
DEFAULT_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
FRONTEND_DIST_ENV = "LEXGRAPH_FRONTEND_DIST"
# First path segments the web app never answers for: an unknown path under
# them keeps its own 404 (JSON for the API, not index.html).
_NOT_THE_WEB_APP = frozenset({"api", "docs", "redoc", "assets", "openapi.json", "healthz"})


class _FromEnvironment:
    """Default for create_app(frontend_dist=...): LEXGRAPH_FRONTEND_DIST,
    else the repository's frontend/dist if it has been built."""


_FROM_ENVIRONMENT = _FromEnvironment()

# Swagger UI / Redoc, vendored by scripts/vendor_api_docs.sh: /docs and /redoc
# must work without an internet connection (no CDN, no web fonts).
API_DOCS_ASSETS = Path(__file__).resolve().parent / "static" / "api-docs"
API_DOCS_STATIC_PATH = "/docs/static"
# Same-origin only, for every resource type. Redoc 2 renders its "API docs by
# Redocly" logo from cdn.redoc.ly with no option to turn it off; this makes the
# browser skip that request (Redoc hides the image) so the docs pages never
# contact a third party. Inline scripts/styles stay allowed: FastAPI's
# templates and Redoc's styled-components need them.
API_DOCS_CSP = "default-src 'self' data: blob: 'unsafe-inline' 'unsafe-eval'"
BEARER_SCHEME = "HTTPBearer"  # FastAPI's own name for fastapi.security.HTTPBearer


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Refuse to serve a database this version cannot use (no file, no
    # LexGraph tables, or a schema from an older release) instead of starting
    # "healthy" and answering 500 on every endpoint. The error names the exact
    # `python -m app.bootstrap` / `python -m app.migrate` command to run.
    ensure_schema_current(app.state.engine)
    if app.state.frontend_dist is not None:
        logging.getLogger("uvicorn.error").info("Serving the web app from %s", app.state.frontend_dist)
    yield


def _frontend_dist(requested: str | os.PathLike[str] | None | _FromEnvironment) -> Path | None:
    """The build directory to serve, or None for an API-only server."""
    if isinstance(requested, _FromEnvironment):
        configured = os.environ.get(FRONTEND_DIST_ENV)
        if configured is None:
            built = (DEFAULT_FRONTEND_DIST / "index.html").is_file()
            return DEFAULT_FRONTEND_DIST.resolve() if built else None
        if not configured.strip():
            return None
        requested = configured
    if requested is None:
        return None
    dist = Path(requested).expanduser().resolve()
    if not (dist / "index.html").is_file():
        raise ValueError(
            f"No web app build at {dist} (no index.html). Build it with "
            f"`npm --prefix frontend run build`, or set {FRONTEND_DIST_ENV}= (empty) to serve "
            "the API only."
        )
    return dist


class _HashedAssets(StaticFiles):
    """dist/assets: Vite puts a content hash in every file name there, so a URL
    never changes meaning and browsers may keep the file for good."""

    def file_response(self, *args: Any, **kwargs: Any) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def _route_path(scope: Mapping[str, Any]) -> str:
    """The request path relative to this app. A Mount (e.g. /assets) extends
    root_path for its child; Starlette keeps the app's own in app_root_path."""
    path = scope["path"]
    root = scope.get("app_root_path", scope.get("root_path", ""))
    return path[len(root) :] if root and path.startswith(root) else path


def _serve_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built web app on the API's own origin (one process, no CORS).

    Not a catch-all route: that would turn a wrong method on an API path
    into 404, and an unknown non-GET path into 405. Instead, a GET/HEAD that
    no route matched (404) outside /api, /docs, /redoc, /assets,
    /openapi.json and /healthz gets the app's index.html. The app routes with
    URL hashes (#/assertions/...), so every page is index.html. A path naming
    a file gets that file from the build, or a real 404.
    """
    index = dist / "index.html"
    if (dist / "assets").is_dir():
        app.mount("/assets", _HashedAssets(directory=dist / "assets"), name="frontend-assets")

    def page_or_file(route_path: str) -> FileResponse | None:
        relative = route_path.lstrip("/")
        if "." not in relative.rsplit("/", 1)[-1]:
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
        try:
            target = (dist / relative).resolve(strict=True)
        except (OSError, RuntimeError, ValueError):  # missing, symlink loop, NUL byte
            return None
        if not target.is_file() or not target.is_relative_to(dist):
            return None  # never serve anything outside the build
        return FileResponse(target, headers={"Cache-Control": "no-cache"} if target == index else None)

    async def web_app_fallback(request: Request, exc: StarletteHTTPException) -> Response:
        if exc.status_code == 404 and request.method in ("GET", "HEAD"):
            route_path = _route_path(request.scope)
            if route_path.lstrip("/").split("/", 1)[0] not in _NOT_THE_WEB_APP:
                response = page_or_file(route_path)
                if response is not None:
                    return response
        return await http_exception_handler(request, exc)

    app.add_exception_handler(StarletteHTTPException, web_app_fallback)


# The two docs pages are module-level and read the app from the request. FastAPI
# keeps process-wide caches keyed by endpoint callables, so an endpoint closing
# over `app` would keep every app (and its engine) a test session builds alive.
# Like FastAPI's own docs routes, they are plain routes (add_route), not API
# routes, so no dependency analysis applies.


def _docs_root(request: Request) -> str:
    # Behind a reverse proxy mounted under a sub-path (uvicorn --root-path).
    return request.scope.get("root_path", "").rstrip("/")


async def _swagger_ui_page(request: Request) -> HTMLResponse:
    app, root = request.app, _docs_root(request)
    static = f"{root}{API_DOCS_STATIC_PATH}"
    page = get_swagger_ui_html(
        openapi_url=f"{root}{app.openapi_url}",
        title=f"{app.title} - Swagger UI",
        swagger_js_url=f"{static}/swagger-ui-bundle.js",
        swagger_css_url=f"{static}/swagger-ui.css",
        swagger_favicon_url=f"{static}/favicon-32x32.png",
        # Keep the token across reloads (the web app keeps its own in
        # localStorage the same way); never contact validator.swagger.io.
        swagger_ui_parameters={"persistAuthorization": True, "validatorUrl": None},
    )
    page.headers["Content-Security-Policy"] = API_DOCS_CSP
    return page


async def _redoc_page(request: Request) -> HTMLResponse:
    app, root = request.app, _docs_root(request)
    static = f"{root}{API_DOCS_STATIC_PATH}"
    page = get_redoc_html(
        openapi_url=f"{root}{app.openapi_url}",
        title=f"{app.title} - ReDoc",
        redoc_js_url=f"{static}/redoc.standalone.js",
        redoc_favicon_url=f"{static}/favicon-32x32.png",
        with_google_fonts=False,
    )
    page.headers["Content-Security-Policy"] = API_DOCS_CSP
    return page


def _register_api_docs(app: FastAPI) -> None:
    """Serve /docs and /redoc from the vendored assets (FastAPI's defaults load
    them from cdn.jsdelivr.net, plus fonts.googleapis.com for Redoc)."""
    app.mount(API_DOCS_STATIC_PATH, StaticFiles(directory=API_DOCS_ASSETS), name="api-docs-static")
    app.add_route("/docs", _swagger_ui_page, include_in_schema=False)
    app.add_route("/redoc", _redoc_page, include_in_schema=False)


def _declare_bearer_auth(app: FastAPI) -> None:
    """Declare the bearer credential in openapi.json so Swagger UI's
    "Authorize" sends it.

    The routers read ``Authorization`` from the request themselves (see
    ``app/auth.py``), which FastAPI cannot see, so the generated schema had no
    security scheme. It is declared once at the root: every operation requires
    it (each one answers 401 without it) unless it opts out with
    ``openapi_extra={"security": []}``, as ``/healthz`` does. A route that
    uses ``fastapi.security.HTTPBearer()`` directly shares the same scheme
    name, so the two merge.
    """
    generate = app.openapi

    def openapi() -> dict:
        if app.openapi_schema is None:
            schema = generate()
            schemes = schema.setdefault("components", {}).setdefault("securitySchemes", {})
            schemes.setdefault(
                BEARER_SCHEME,
                {
                    "type": "http",
                    "scheme": "bearer",
                    "description": (
                        "Your LexGraph sign-in credential: what you enter on the web app's "
                        "sign-in page (`python -m app.bootstrap` prints the first admin's). "
                        "Sent as `Authorization: Bearer <credential>`."
                    ),
                },
            )
            schema.setdefault("security", [{BEARER_SCHEME: []}])
            for path_item in schema.get("paths", {}).values():
                for method, operation in path_item.items():
                    if method in {"get", "put", "post", "delete", "options", "head", "patch", "trace"}:
                        if operation.get("security") != []:
                            operation.setdefault("responses", {}).setdefault(
                                "401", {"description": "Missing or invalid bearer credential."}
                            )
        return app.openapi_schema

    app.openapi = openapi


def create_app(
    *, frontend_dist: str | os.PathLike[str] | None | _FromEnvironment = _FROM_ENVIRONMENT
) -> FastAPI:
    """``frontend_dist``: the web app build to serve on this origin; None for
    an API-only server. By default LEXGRAPH_FRONTEND_DIST decides, else the
    repository's frontend/dist when it has been built."""
    from app import models  # register ORM mappings

    dist = _frontend_dist(frontend_dist)
    settings = get_settings()
    app = FastAPI(
        title="LexGraph API",
        version="0.1.0",
        lifespan=_lifespan,
        docs_url=None,  # served offline by _register_api_docs
        redoc_url=None,
    )

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
    from app.routers.assertions import jurisdictions_router
    from app.routers.assertions import router as assertions_router

    app.include_router(assertions_router)
    # Sprint 2026-08-02-us-state-law, item 1 (ruling R5): jurisdiction
    # controlled-vocabulary endpoint, `GET /api/v1/jurisdictions`.
    app.include_router(jurisdictions_router)

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

    # B3 — comments + history + audit (append-only registration, R6).
    from app.audit_middleware import register_audit_hooks
    from app.routers import comments as comments_router
    from app.routers import history as history_router

    app.include_router(comments_router.router)
    app.include_router(history_router.router)
    register_audit_hooks(app)

    # B2 — ratings + aggregates (append-only registration, R6).
    from app.routers import ratings as ratings_router

    app.include_router(ratings_router.router)

    # Consensus UI build-out — workspace/session surface (append-only, R6).
    from app.routers import workspace as workspace_router

    app.include_router(workspace_router.router)

    # Admin provisioning — users API (sprint 2026-07-31-admin-provisioning,
    # item B2, append-only registration, R6).
    from app.routers import users as users_router

    app.include_router(users_router.router)

    from app.routers import agents, sources
    app.include_router(agents.router)
    app.include_router(sources.router)

    @app.get("/healthz", openapi_extra={"security": []})
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    _register_api_docs(app)
    _declare_bearer_auth(app)
    app.state.frontend_dist = dist
    if dist is not None:
        _serve_frontend(app, dist)

    return app


# Zero-argument module-level app for `uvicorn app.main:app` convenience.
app = create_app()
