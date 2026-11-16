"""`python -m app.seed_demo --reset` replaces only a demo database (XREQ-102).

`--reset` used to unlink whatever file it was given, and the seeder's own
refusal on an existing file said "pass --reset to reseed from scratch", so
following that hint on a workspace created by `app.bootstrap` deleted it
(ops new:seed-reset-warning). The seeder now classifies the file the way
scripts/demo.sh does: a demo database or an empty file may be reseeded,
anything else is refused and left byte-identical.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from app.seed_demo import DEMO_USERS, database_kind

BACKEND = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=BACKEND, capture_output=True, text=True, timeout=180)


def _user_ids(db: Path) -> set[str]:
    with sqlite3.connect(db) as conn:
        return {row[0] for row in conn.execute("SELECT id FROM users")}


@pytest.fixture
def workspace(tmp_path) -> Path:
    db = tmp_path / "dev.db"
    assert _run("-m", "app.bootstrap", "--db", str(db)).returncode == 0
    return db


@pytest.mark.parametrize("reset", [False, True])
def test_a_bootstrapped_workspace_is_never_replaced(workspace, reset):
    before = workspace.read_bytes()
    result = _run("-m", "app.seed_demo", "--db", str(workspace), *(["--reset"] if reset else []))
    assert result.returncode == 1, result
    assert "left untouched" in result.stdout and "--db demo.db" in result.stdout, result.stdout
    assert "pass --reset" not in result.stdout
    assert workspace.read_bytes() == before


def test_a_file_that_is_not_a_lexgraph_database_is_never_replaced(tmp_path):
    other = tmp_path / "notes.db"
    other.write_bytes(b"not a database at all\n")
    result = _run("-m", "app.seed_demo", "--db", str(other), "--reset")
    assert result.returncode == 1 and "not a LexGraph database" in result.stdout, result
    assert other.read_bytes() == b"not a database at all\n"


def test_a_demo_database_is_reseeded_only_with_reset(tmp_path):
    db = tmp_path / "demo.db"
    assert _run("-m", "app.seed_demo", "--db", str(db)).returncode == 0
    assert database_kind(db) == "demo"

    again = _run("-m", "app.seed_demo", "--db", str(db))
    assert again.returncode == 1 and "pass --reset" in again.stdout, again

    reset = _run("-m", "app.seed_demo", "--db", str(db), "--reset")
    assert reset.returncode == 0, reset
    assert {user[0] for user in DEMO_USERS} <= _user_ids(db)


def test_an_empty_file_is_replaced_with_reset(tmp_path):
    empty = tmp_path / "dev.db"
    empty.touch()
    assert database_kind(empty) == "empty"
    assert _run("-m", "app.seed_demo", "--db", str(empty)).returncode == 1
    assert _run("-m", "app.seed_demo", "--db", str(empty), "--reset").returncode == 0
    assert database_kind(empty) == "demo"
