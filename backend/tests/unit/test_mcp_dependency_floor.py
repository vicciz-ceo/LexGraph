"""Sprint 2026-07-29-mcp2-migration — dependency-floor guard (gate G1).

PyPI `mcp` 2.0.0 removed `mcp.server.fastmcp` (mcp 1.x's high-level server
API), breaking `app.mcp.server`. Gate G1 requires a fresh `pip install -e
'.[dev]'` of this backend to resolve `mcp` to the 2.x line -- this test
turns that gate into a live, environment-level check: whatever venv is
running this suite must have `mcp>=2` installed. It is a floor guard, not
an API check -- see the integration tests under tests/integration/test_mcp_*
for behavioral coverage of the ported server itself.

RED today: the venv's installed `mcp` distribution is 1.29.0 (the last 1.x
release) because `backend/pyproject.toml` still declares `mcp>=1.0` and no
one has rebuilt the venv against a floor that forces 2.x. GREEN once the
Developer raises the floor (e.g. `mcp>=2.0`) in `backend/pyproject.toml`
and the venv is (re)installed from it.
"""

from __future__ import annotations

from importlib.metadata import version


def test_installed_mcp_distribution_is_2x_or_newer():
    installed = version("mcp")
    major = int(installed.split(".", 1)[0])
    assert major >= 2, (
        f"expected an installed `mcp` distribution >= 2.0 (gate G1), found {installed}"
    )
