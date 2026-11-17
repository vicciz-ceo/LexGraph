"""Operator CLI `python -m app.rotate_sign_in_token` (lockouts and legacy
credentials, finding api:2). Drives the real commands via subprocess
against a tmp SQLite file, then checks sign-in through the real app."""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import token_header

BACKEND_DIR = Path(__file__).resolve().parents[2]
TARGETS = [("--email", "root@acme.test"), ("--user-id", "some-user"), ("--list-legacy",)]


def _run(module: str, *args: str, url: str | None = None, cwd: Path = BACKEND_DIR) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("LEXGRAPH_")}
    env["PYTHONPATH"] = str(BACKEND_DIR)  # `app` importable from any cwd
    if url is not None:
        env["LEXGRAPH_DATABASE_URL"] = url
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=cwd,
        env=env,
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


def test_rotating_by_email_ignores_letter_case_and_padding(tmp_path, monkeypatch):
    # Emails are compared normalized (findings api:24 / ui:25), here too.
    db_path = tmp_path / "case.db"
    boot = _run("app.bootstrap", "--db", str(db_path), "--user-email", "root@acme.test")
    assert boot.returncode == 0, boot.stderr

    rotated = _run("app.rotate_sign_in_token", "--db", str(db_path), "--email", "  ROOT@Acme.TEST ")

    assert rotated.returncode == 0, rotated.stderr
    assert _signs_in(db_path, monkeypatch, rotated.stdout.strip().splitlines()[-1])


def test_a_database_that_predates_sign_in_tokens_is_refused_with_the_upgrade_command(tmp_path):
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, email VARCHAR(255) NOT NULL, "
                 "display_name VARCHAR(255) NOT NULL)")
    conn.execute("INSERT INTO users VALUES ('u1', 'a@example.test', 'A')")
    conn.commit()
    conn.close()
    before = db_path.read_bytes()

    result = _run("app.rotate_sign_in_token", "--db", str(db_path), "--list-legacy")

    assert result.returncode == 1, result
    assert "predates sign-in tokens" in result.stderr
    assert f"-m app.migrate --db {db_path}" in result.stderr, result.stderr
    assert db_path.read_bytes() == before


# review identity:3: connecting to a mistyped path created a 0-byte file there,
# which scripts/dev-backend.sh and the server then refused as "not initialized".


@pytest.mark.parametrize("target", TARGETS, ids=lambda target: target[0])
@pytest.mark.parametrize("where", ["typo.db", "no-dir/typo.db"])
def test_a_missing_database_file_is_refused_and_never_created(tmp_path, target, where):
    missing = tmp_path / where
    result = _run("app.rotate_sign_in_token", "--db", str(missing), *target)
    assert result.returncode == 1, result
    assert result.stderr.startswith(f"error: no database file at {missing} (nothing was created)"), result.stderr
    assert "Traceback" not in result.stderr and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("url", ["sqlite:///typo.db", "sqlite:///{tmp}/typo.db"])
def test_a_missing_file_named_by_the_environment_is_refused_and_never_created(tmp_path, url):
    result = _run("app.rotate_sign_in_token", "--list-legacy", url=url.format(tmp=tmp_path), cwd=tmp_path)
    assert result.returncode == 1, result
    assert result.stderr.startswith(f"error: no database file at {tmp_path / 'typo.db'} "), result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("url", ["sqlite://", "sqlite:///", "sqlite:///:memory:", "sqlite+pysqlite:///:memory:",
                                 "sqlite:///file::memory:?uri=true", "sqlite:///file:x?mode=memory&uri=true"])
def test_an_in_memory_database_is_refused(tmp_path, url):
    result = _run("app.rotate_sign_in_token", "--list-legacy", url=url, cwd=tmp_path)
    assert result.returncode == 1, result
    assert result.stderr.startswith("error: pass --db PATH or set LEXGRAPH_DATABASE_URL"), result.stderr
    assert list(tmp_path.iterdir()) == []


def test_a_file_that_is_not_a_database_is_one_line_not_a_traceback(tmp_path):
    notes = tmp_path / "notes.db"
    notes.write_text("not a database\n" * 100)
    before = notes.read_bytes()
    result = _run("app.rotate_sign_in_token", "--db", str(notes), "--list-legacy")
    assert result.returncode == 1, result
    assert result.stderr.startswith(f"error: cannot use the database at {notes}: "), result.stderr
    assert "Traceback" not in result.stderr and len(result.stderr.splitlines()) == 1, result.stderr
    assert notes.read_bytes() == before
