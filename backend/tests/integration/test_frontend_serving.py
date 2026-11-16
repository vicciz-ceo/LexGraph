"""The backend serves the built web app on its own origin (ui:17).

Before: RUNBOOK's "Building for Production" ended at
``npm --prefix frontend run build`` and nothing could serve the result. A
static host answered the app's ``/api/v1/me`` with 404 ("Unknown user ID"), a
cross-origin API base was blocked by CORS, and file:// rendered a blank page.
``GET /`` on the backend was a 404.

Now ``uvicorn app.main:app`` serves ``frontend/dist`` when it has been built
(or ``LEXGRAPH_FRONTEND_DIST``): ``/`` and other page paths get index.html,
``/assets/*`` the hashed build files. ``/api``, the docs and the health check
answer exactly as without the web app.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import create_app
from tests.conftest import auth_header

INDEX = "<!doctype html><title>LexGraph</title><div id=\"root\"></div>" \
    "<script type=\"module\" src=\"/assets/index-AbC123.js\"></script>"


@pytest.fixture()
def dist(tmp_path) -> Path:
    """A minimal Vite build: index.html plus content-hashed assets."""
    build = tmp_path / "dist"
    (build / "assets").mkdir(parents=True)
    (build / "index.html").write_text(INDEX)
    (build / "assets" / "index-AbC123.js").write_text("document.title = 'LexGraph';")
    (build / "assets" / "index-AbC123.css").write_text("body { margin: 0 }")
    (build / "robots.txt").write_text("User-agent: *\nDisallow:\n")
    return build


@pytest.fixture()
def web(app, dist):
    """The same database as the `app` fixture, served together with a build."""
    application = create_app(frontend_dist=dist)
    try:
        with TestClient(application) as client:
            yield client
    finally:
        application.state.engine.dispose()


def test_root_and_page_paths_serve_the_web_app(web):
    for path in ("/", "/review", "/assertions/123/history", "/index.html"):
        response = web.get(path)
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith("text/html"), path
        assert response.text == INDEX, path
        # Always revalidated, so a rebuild is picked up on the next load.
        assert response.headers["cache-control"] == "no-cache", path
    head = web.head("/")
    assert head.status_code == 200 and head.content == b""


def test_built_files_are_served_and_hashed_assets_cached_for_good(web):
    script = web.get("/assets/index-AbC123.js")
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]
    assert script.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert web.get("/assets/index-AbC123.css").headers["content-type"].startswith("text/css")
    robots = web.get("/robots.txt")
    assert robots.status_code == 200 and robots.text.startswith("User-agent")
    # A missing file is a real 404, never index.html served as JS/an icon.
    for missing in ("/assets/index-Gone99.js", "/favicon.ico", "/assets/"):
        response = web.get(missing)
        assert response.status_code == 404, missing
        assert not response.headers["content-type"].startswith("text/html"), missing


def test_api_docs_and_health_answer_exactly_as_without_the_web_app(app, web, matter_with_users):
    """Every probe gets the same status, content type and JSON body with and
    without the web app mounted (method mismatches stay 405, unknown API
    paths stay JSON 404s)."""
    headers = matter_with_users["reviewer_headers"]
    probes = [
        ("GET", "/api/v1/nope", None),
        ("POST", "/api/v1/nope", None),
        ("GET", "/api", None),
        ("POST", "/nope", None),
        ("DELETE", "/api/v1/assertions", None),
        ("GET", "/api/v1/me", None),
        ("GET", "/api/v1/me", headers),
        ("GET", "/api/v1/assertions/does-not-exist", headers),
        ("GET", "/healthz", None),
        ("GET", "/openapi.json", None),
        ("GET", "/docs", None),
        ("GET", "/redoc", None),
        ("GET", "/docs/static/swagger-ui.css", None),
        ("GET", "/docs/static/missing.js", None),
        ("GET", "/docs/unknown", None),
    ]
    api_only_app = create_app(frontend_dist=None)  # same database as `app`
    try:
        with TestClient(api_only_app) as api_only:
            for method, path, auth in probes:
                expected = api_only.request(method, path, headers=auth)
                actual = web.request(method, path, headers=auth)
                assert (actual.status_code, actual.headers.get("content-type")) == (
                    expected.status_code,
                    expected.headers.get("content-type"),
                ), (method, path)
                if expected.headers.get("content-type") == "application/json":
                    assert actual.json() == expected.json(), (method, path)
    finally:
        api_only_app.state.engine.dispose()
    assert web.get("/api/v1/nope").json() == {"detail": "Not Found"}
    assert web.post("/api/v1/nope").status_code == 404  # not 405: no catch-all route
    assert web.get("/api/v1/me", headers=headers).status_code == 200


def test_paths_outside_the_build_are_never_served(web, dist, tmp_path):
    (tmp_path / "secret.txt").write_text("outside the build")
    os.symlink(tmp_path / "secret.txt", dist / "linked.txt")
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/..%2f..%2fsecret.txt", "/linked.txt"):
        response = web.get(path)
        assert response.status_code == 404, path
        assert "outside the build" not in response.text, path


def test_without_a_build_the_backend_serves_the_api_only(tmp_path, monkeypatch, app):
    monkeypatch.setattr(main_module, "DEFAULT_FRONTEND_DIST", tmp_path / "not-built")
    monkeypatch.delenv("LEXGRAPH_FRONTEND_DIST", raising=False)
    application = create_app()
    try:
        with TestClient(application) as client:
            response = client.get("/")
            assert response.status_code == 404
            assert response.json() == {"detail": "Not Found"}
    finally:
        application.state.engine.dispose()


def test_a_build_in_the_repository_is_served_by_default(monkeypatch, app, dist):
    monkeypatch.setattr(main_module, "DEFAULT_FRONTEND_DIST", dist)
    monkeypatch.delenv("LEXGRAPH_FRONTEND_DIST", raising=False)
    application = create_app()
    try:
        with TestClient(application) as client:
            assert client.get("/").text == INDEX
    finally:
        application.state.engine.dispose()


def test_LEXGRAPH_FRONTEND_DIST_selects_or_disables_the_build(monkeypatch, app, dist, tmp_path):
    monkeypatch.setattr(main_module, "DEFAULT_FRONTEND_DIST", dist)
    monkeypatch.setenv("LEXGRAPH_FRONTEND_DIST", "")
    disabled = create_app()
    other = tmp_path / "other-build"
    other.mkdir()
    (other / "index.html").write_text("<!doctype html><title>other</title>")
    monkeypatch.setenv("LEXGRAPH_FRONTEND_DIST", str(other))
    selected = create_app()
    try:
        with TestClient(disabled) as client:
            assert client.get("/").status_code == 404
        with TestClient(selected) as client:
            assert "other" in client.get("/").text
    finally:
        disabled.state.engine.dispose()
        selected.state.engine.dispose()


def test_a_configured_build_without_index_html_is_refused(monkeypatch, tmp_path):
    empty = tmp_path / "empty-dist"
    empty.mkdir()
    monkeypatch.setenv("LEXGRAPH_FRONTEND_DIST", str(empty))
    with pytest.raises(ValueError, match="npm --prefix frontend run build"):
        create_app()


def test_web_app_and_api_share_one_origin(web, matter_with_users):
    """What the browser does: load the page, its script, then the API with
    the stored credential, all from the same host and port."""
    page = web.get("/")
    script_src = page.text.split('src="', 1)[1].split('"', 1)[0]
    assert web.get(script_src).status_code == 200
    me = web.get("/api/v1/me", headers=auth_header(matter_with_users["contributor_id"]))
    assert me.status_code == 200
    assert me.json()["user"]["id"] == matter_with_users["contributor_id"]
