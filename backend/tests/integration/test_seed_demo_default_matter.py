"""Every demo account starts on the seeded MSA matter (acceptance run 2, item 2).

GET /me lists a user's matters by name, and the web app opens the first one
when the browser has no matter saved yet (frontend/src/app/session.tsx). The
demo's second matter used to be "Data Processing Addendum — Acme", which sorts
before "MSA — Acme ↔ Blue Ridge Logistics", so admin and reviewer, the two
accounts that belong to both, landed on the nearly empty second matter instead
of the populated workspace README describes. The seed now names its second
matter so that the showcase comes first; GET /me's order is unchanged.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.seed_demo import DEMO_USERS

BACKEND = Path(__file__).resolve().parents[2]
SHOWCASE = "MSA — Acme ↔ Blue Ridge Logistics"


@pytest.fixture(scope="module")
def demo(tmp_path_factory) -> Path:
    db = tmp_path_factory.mktemp("demo") / "demo.db"
    result = subprocess.run(
        [sys.executable, "-m", "app.seed_demo", "--db", str(db), "--quiet"],
        cwd=BACKEND, capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result
    return db


@pytest.fixture()
def client(demo, monkeypatch):
    monkeypatch.setenv("LEXGRAPH_DATABASE_URL", f"sqlite:///{demo}")
    from app.main import create_app

    app = create_app(frontend_dist=None)
    with TestClient(app) as test_client:
        yield test_client
    app.state.engine.dispose()


def _get(client, token: str, path: str, **params) -> dict:
    r = client.get(f"/api/v1{path}", params=params, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("token", [user[0] for user in DEMO_USERS])
def test_every_demo_account_first_lists_the_showcase_matter(client, token):
    matters = _get(client, token, "/me")["matters"]

    assert matters[0]["name"] == SHOWCASE
    # The documented order is kept: by name.
    assert [m["name"] for m in matters] == sorted(m["name"] for m in matters)


def test_admin_and_reviewer_can_still_switch_to_the_second_matter(client):
    for token in ("admin", "reviewer"):
        names = [m["name"] for m in _get(client, token, "/me")["matters"]]
        assert len(names) == 2 and names[0] == SHOWCASE, names


def test_the_matter_opened_first_holds_the_populated_workspace(client):
    """README: the review queue, knowledge base and contested queue are populated."""
    matter_id = _get(client, "reviewer", "/me")["matters"][0]["id"]
    for status in ("proposed", "accepted", "disputed"):
        listed = _get(client, "reviewer", "/assertions", matter_id=matter_id, status=status, limit=1)
        assert listed["total"] > 0, status
