"""/docs and /redoc work offline and can make authenticated calls (api:28).

Before: both pages pulled Swagger UI / Redoc from cdn.jsdelivr.net (plus
fonts.googleapis.com and a fastapi.tiangolo.com favicon), so on a machine
without internet they rendered blank. openapi.json declared no security
scheme (the routers read ``Authorization`` from ``request.headers``), so
Swagger UI showed no Authorize button and every "Try it out" call got 401.
"""

from __future__ import annotations

import gc
import hashlib
import re
import weakref

from fastapi.testclient import TestClient

from app.main import API_DOCS_ASSETS, create_app

_HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def _assets(html: str) -> list[str]:
    return re.findall(r'(?:src|href)="([^"]+)"', html)


def test_docs_pages_load_every_asset_from_this_server(client):
    expected_types = {".js": "javascript", ".css": "text/css", ".png": "image/png"}
    for page in ("/docs", "/redoc"):
        response = client.get(page)
        assert response.status_code == 200
        html = response.text
        assert not re.search(r"https?://", html), f"{page} still references an external URL"
        assets = _assets(html)
        assert assets, page
        for url in assets:
            assert url.startswith("/docs/static/"), url
            asset = client.get(url)
            assert asset.status_code == 200, url
            suffix = url[url.rindex(".") :]
            assert expected_types[suffix] in asset.headers["content-type"], url
            assert len(asset.content) > 500, url


def test_swagger_ui_is_the_bundled_v5_and_redoc_the_bundled_v2(client):
    bundle = client.get("/docs/static/swagger-ui-bundle.js").text
    assert "SwaggerUIBundle" in bundle
    # FastAPI emits OpenAPI 3.1, which Swagger UI only renders from v5 on.
    assert client.get("/openapi.json").json()["openapi"].startswith("3.1")
    assert "redoc" in client.get("/docs/static/redoc.standalone.js").text[:2000].lower()


def _operations(spec):
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if method in _HTTP_METHODS:
                yield path, method, operation


def _requires_bearer(spec, operation) -> bool:
    """Root-level security applies unless the operation opts out with []."""
    return operation.get("security", spec["security"]) != []


def test_openapi_declares_the_bearer_scheme_so_authorize_works(client):
    spec = client.get("/openapi.json").json()
    assert spec["components"]["securitySchemes"]["HTTPBearer"]["type"] == "http"
    assert spec["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    # Root level: every operation inherits it unless it opts out explicitly
    # (openapi_extra={"security": []}), as the health check does.
    assert spec["security"] == [{"HTTPBearer": []}]

    secured = 0
    for path, method, operation in _operations(spec):
        if path == "/healthz":
            assert operation["security"] == [], "the health check needs no credential"
        if not _requires_bearer(spec, operation):
            continue
        secured += 1
        assert operation.get("security", spec["security"]) == [{"HTTPBearer": []}], (method, path)
        assert "401" in operation["responses"], (method, path)
    assert secured >= 40


def test_documented_security_matches_what_every_route_enforces(client):
    """Without a credential, every operation documented as secured answers
    401 and every operation documented as public does not."""
    spec = client.get("/openapi.json").json()
    for path, method, operation in _operations(spec):
        concrete = re.sub(r"\{[^}]+\}", "x", path)
        response = client.request(method.upper(), concrete, json={})
        if _requires_bearer(spec, operation):
            assert response.status_code == 401, (method, path, response.status_code)
        else:
            assert response.status_code != 401, (method, path)


def test_swagger_ui_keeps_the_credential_across_reloads_and_never_calls_a_validator(client):
    html = client.get("/docs").text
    assert '"persistAuthorization": true' in html
    assert '"validatorUrl": null' in html


def test_docs_follow_the_root_path_behind_a_reverse_proxy(app):
    with TestClient(app, root_path="/lexgraph") as proxied:
        swagger = proxied.get("/docs").text
        redoc = proxied.get("/redoc").text
    assert "url: '/lexgraph/openapi.json'" in swagger
    assert 'src="/lexgraph/docs/static/swagger-ui-bundle.js"' in swagger
    assert 'spec-url="/lexgraph/openapi.json"' in redoc
    assert 'src="/lexgraph/docs/static/redoc.standalone.js"' in redoc


REDOC_LOGO_URL = b'"https://cdn.redoc.ly/redoc/logo-mini.svg"'


def test_redoc_is_served_without_the_url_of_its_cdn_logo(client):
    """Acceptance run (release candidate): Redoc 2 renders its "API docs by
    Redocly" footer logo from cdn.redoc.ly, with no option to turn it off. The
    page's Content-Security-Policy refused the request, but every load of
    /redoc still made the browser try it and log a CSP violation as a console
    error. The bundle is served with that URL emptied, so no request starts."""
    served = client.get("/docs/static/redoc.standalone.js")
    assert served.status_code == 200
    assert "javascript" in served.headers["content-type"]
    assert b"cdn.redoc.ly" not in served.content
    assert not re.search(rb'src:"https?:', served.content)

    # Nothing else differs, and the vendored file itself stays as published.
    vendored = (API_DOCS_ASSETS / "redoc.standalone.js").read_bytes()
    assert vendored.count(REDOC_LOGO_URL) == 1
    assert served.content == vendored.replace(REDOC_LOGO_URL, b'""')
    readme = (API_DOCS_ASSETS / "README.md").read_text(encoding="utf-8")
    assert f"{hashlib.sha256(vendored).hexdigest()}  redoc.standalone.js" in readme


def test_the_served_redoc_bundle_is_revalidated_like_the_other_assets(client):
    url = "/docs/static/redoc.standalone.js"
    first = client.get(url)
    etag = first.headers["etag"]
    assert client.get(url, headers={"If-None-Match": etag}).status_code == 304
    assert client.get(url, headers={"If-None-Match": '"something-else"'}).status_code == 200
    head = client.head(url)
    assert (head.status_code, head.headers["etag"], head.content) == (200, etag, b"")
    assert client.post(url).status_code == 405
    # Every other file is served from disk as before.
    assert client.get("/docs/static/swagger-ui.css").content == (API_DOCS_ASSETS / "swagger-ui.css").read_bytes()


def test_operation_ids_make_deep_links_swagger_ui_can_read(client):
    """Acceptance run (release candidate): Swagger UI writes #/<tag>/<operationId>
    into the URL when an operation is opened, and on loading such a link it
    reads an underscore as an escaped space: it logged "Deprecated: escaping
    deep link whitespace with `_` is unsupported" for every one of FastAPI's
    default operationIds (`me_api_v1_me_get`). They are camelCase now
    (`meApiV1MeGet`), unique, and the tags have no underscore either."""
    spec = client.get("/openapi.json").json()
    operations = list(_operations(spec))
    ids = [operation["operationId"] for _, _, operation in operations]
    assert [i for i in ids if not re.fullmatch(r"[a-z][A-Za-z0-9]*", i)] == []
    assert len(set(ids)) == len(ids) >= 40
    assert spec["paths"]["/api/v1/me"]["get"]["operationId"] == "meApiV1MeGet"
    assert [t for _, _, op in operations for t in op.get("tags", []) if "_" in t] == []


def test_docs_pages_forbid_every_third_party_origin(client):
    """Redoc 2 always renders its attribution logo from cdn.redoc.ly; a
    same-origin-only policy makes the browser refuse that request (verified
    in Chromium: the request fails with reason "csp" and never leaves)."""
    for page in ("/docs", "/redoc"):
        policy = client.get(page).headers["content-security-policy"]
        sources = policy.split(";")[0].split()
        assert sources[0] == "default-src"
        assert "'self'" in sources
        assert not [s for s in sources if "." in s or s.endswith(":") and s not in ("data:", "blob:")], policy


def _build_and_use_an_app(dist) -> weakref.ref:
    application = create_app(frontend_dist=dist)
    try:
        with TestClient(application) as client:
            for path in ("/docs", "/redoc", "/openapi.json", "/", "/api/v1/nope", "/healthz"):
                client.get(path)
    finally:
        application.state.engine.dispose()
    return weakref.ref(application)


def test_apps_built_by_create_app_are_garbage_collected(app, tmp_path):
    """FastAPI caches endpoint callables process-wide (an lru_cache keyed by the
    callable). Docs endpoints that closed over the app kept every app a test
    session built alive, with its engine: 264 apps after 300 tests, about 2M
    extra objects by the end of the suite."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>LexGraph</title>")
    refs = [_build_and_use_an_app(dist) for _ in range(3)]
    gc.collect()
    assert [ref() for ref in refs] == [None, None, None]
