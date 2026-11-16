"""/docs and /redoc work offline and can make authenticated calls (api:28).

Before: both pages pulled Swagger UI / Redoc from cdn.jsdelivr.net (plus
fonts.googleapis.com and a fastapi.tiangolo.com favicon), so on a machine
without internet they rendered blank. openapi.json declared no security
scheme (the routers read ``Authorization`` from ``request.headers``), so
Swagger UI showed no Authorize button and every "Try it out" call got 401.
"""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

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
