"""Operator CLI `python -m app.rotate_sign_in_token` (lockouts and legacy
credentials, finding api:2). Drives the real commands via subprocess
against a tmp SQLite file, then checks sign-in through the real app."""

from __future__ import annotations

import re
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import token_header

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _run(module: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _signs_in(db_path: Path, monkeypatch, token: str) -> bool:
    monkeypatch.setenv("LEXGRAPH_DATABASE_URL", f"sqlite:///{db_path}")
    app = create_app()
    try:
        with TestClient(app) as client:
            return client.get("/api/v1/me", headers=token_header(token)).status_code == 200
    finally:
        app.state.engine.dispose()


def test_rotating_by_email_replaces_a_lost_admin_token(tmp_path, monkeypatch):
    db_path = tmp_path / "lockout.db"
    boot = _run("app.bootstrap", "--db", str(db_path), "--user-email", "root@acme.test")
    assert boot.returncode == 0, boot.stderr
    old_token = re.search(r"sign-in token[^:\n]*:\s*(\S+)", boot.stdout).group(1)

    rotated = _run("app.rotate_sign_in_token", "--db", str(db_path), "--email", "root@acme.test")
    assert rotated.returncode == 0, rotated.stderr
    new_token = rotated.stdout.strip().splitlines()[-1]
    assert new_token != old_token and len(new_token) >= 32

    assert _signs_in(db_path, monkeypatch, new_token)
    assert not _signs_in(db_path, monkeypatch, old_token)


def test_rotating_by_user_id_and_listing_legacy_accounts(tmp_path, monkeypatch):
    db_path = tmp_path / "demo.db"
    assert _run("app.seed_demo", "--db", str(db_path)).returncode == 0

    listed = _run("app.rotate_sign_in_token", "--db", str(db_path), "--list-legacy")
    assert listed.returncode == 0, listed.stderr
    assert "4 account(s) still sign in with their public user id" in listed.stdout
    for user_id in ("admin", "reviewer", "contributor", "viewer"):
        assert f"  {user_id}  " in listed.stdout

    rotated = _run("app.rotate_sign_in_token", "--db", str(db_path), "--user-id", "viewer")
    assert rotated.returncode == 0, rotated.stderr
    new_token = rotated.stdout.strip().splitlines()[-1]
    assert _signs_in(db_path, monkeypatch, new_token)
    assert not _signs_in(db_path, monkeypatch, "viewer")

    listed = _run("app.rotate_sign_in_token", "--db", str(db_path), "--list-legacy")
    assert "3 account(s)" in listed.stdout and "  viewer  " not in listed.stdout


def test_cli_errors_are_explicit(tmp_path):
    db_path = tmp_path / "boot.db"
    assert _run("app.bootstrap", "--db", str(db_path)).returncode == 0

    missing = _run("app.rotate_sign_in_token", "--db", str(db_path), "--user-id", "nobody")
    assert missing.returncode == 1 and "no such user account" in missing.stderr

    none_legacy = _run("app.rotate_sign_in_token", "--db", str(db_path), "--list-legacy")
    assert none_legacy.returncode == 0
    assert "No accounts sign in with their public user id." in none_legacy.stdout

    usage = _run("app.rotate_sign_in_token", "--db", str(db_path))
    assert usage.returncode == 2  # one of --user-id / --email / --list-legacy is required

    old = tmp_path / "old.db"
    conn = sqlite3.connect(old)
    conn.execute(
        "CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, email VARCHAR(255) NOT NULL, "
        "display_name VARCHAR(255) NOT NULL)"
    )
    conn.commit()
    conn.close()
    unmigrated = _run("app.rotate_sign_in_token", "--db", str(old), "--list-legacy")
    assert unmigrated.returncode == 1 and "upgrade it first" in unmigrated.stderr
