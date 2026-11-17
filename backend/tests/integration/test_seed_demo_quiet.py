"""`python -m app.seed_demo --quiet` prints nothing on success (acceptance run, release candidate).

Run by hand, the seeder ends with how to serve the new file: "Serve it:
LEXGRAPH_DATABASE_URL=sqlite:///dev.db .venv/bin/uvicorn app.main:app --port 8000".
scripts/demo.sh and scripts/dev-backend.sh serve the database themselves, on
their own ports, and passed that hint through: `BACKEND_PORT=9854
./scripts/demo.sh` printed `--port 8000` (and a path in its scratch
directory) before starting the backend on 9854. The scripts now pass
`--quiet`; a refusal is still explained, and a seed by hand is unchanged.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.seed_demo import database_kind

BACKEND = Path(__file__).resolve().parents[2]


def _seed(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "app.seed_demo", *args], cwd=BACKEND,
                          capture_output=True, text=True, timeout=180)


def test_quiet_prints_nothing_on_success_and_still_explains_a_refusal(tmp_path):
    db = tmp_path / "demo.db"

    quiet = _seed("--db", str(db), "--quiet")
    assert (quiet.returncode, quiet.stdout) == (0, ""), quiet
    assert database_kind(db) == "demo"

    refused = _seed("--db", str(db), "--quiet")
    assert refused.returncode == 1 and "pass --reset" in refused.stdout, refused


def test_without_quiet_the_seed_still_says_how_to_serve_it(tmp_path):
    db = tmp_path / "demo.db"
    result = _seed("--db", str(db))
    assert result.returncode == 0, result
    assert "Serve it:" in result.stdout and f"sqlite:///{db}" in result.stdout, result.stdout
    assert "Demo sign-in tokens" in result.stdout
