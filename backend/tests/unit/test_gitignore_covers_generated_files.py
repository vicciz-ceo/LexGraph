"""Files that the documented commands create must not show up as untracked.

``.gitignore`` ignored only ``backend/dev.db``, while the RUNBOOK's own examples
use ``sqlite:///lexgraph.db`` from ``backend/``, a relative URL used from the
repository root creates ``dev.db`` or ``lexgraph.db`` there, the RUNBOOK
suggests ``cp dev.db dev.db.bak`` before migrating, and ``pytest --cov``
(pytest-cov is a declared dev dependency) writes ``.coverage``. A LexGraph
database holds user ids, which are the sign-in credentials, so committing
one by accident publishes them (finding ops:5).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or not (ROOT / ".git").exists(), reason="needs a git checkout"
)

GENERATED = [
    # SQLite databases: README/RUNBOOK use dev.db and lexgraph.db, from backend/ or the root.
    "backend/dev.db",
    "backend/lexgraph.db",
    "dev.db",
    "lexgraph.db",
    "backend/demo.db",
    # SQLite side files next to an open or interrupted database.
    "backend/dev.db-journal",
    "backend/dev.db-wal",
    "backend/dev.db-shm",
    # RUNBOOK "Upgrading an existing database": cp dev.db dev.db.bak.
    "backend/dev.db.bak",
    # pytest --cov, from the root or from backend/, plus the parallel-mode and HTML outputs.
    ".coverage",
    "backend/.coverage",
    "backend/.coverage.ci-host.1234.XyZ",
    "htmlcov/index.html",
    "backend/htmlcov/index.html",
    # Install and build outputs that were already covered.
    "backend/.venv/bin/python",
    "frontend/node_modules/vite/package.json",
    "frontend/dist/index.html",
    "backend/lexgraph_backend.egg-info/PKG-INFO",
]


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=60)


def test_every_file_the_documented_commands_create_is_ignored():
    result = _git("check-ignore", "--no-index", "--verbose", "--non-matching", *GENERATED)
    not_ignored = [line.split("\t", 1)[1] for line in result.stdout.splitlines() if line.startswith("::")]
    assert not_ignored == []


def test_no_tracked_file_is_ignored():
    """Guards the patterns against being too broad: nothing in the repository matches them."""
    result = _git("ls-files", "--cached", "--ignored", "--exclude-standard")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == []
