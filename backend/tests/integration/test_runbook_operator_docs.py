"""The RUNBOOK's operator instructions match what the commands do.

* review ops-docs:2 -- before huggingface_hub 1.0 a repeated `hf download
  --include` keeps only the last pattern, so the RUNBOOK's one command fetched
  the constitutions only (and bulk ingest still exited 0).
* review ops-docs:4 -- the RUNBOOK said app.seed_demo reads
  LEXGRAPH_DATABASE_URL like the other CLIs; it writes its --db file only.
* review ops-docs:5 -- the "Port already in use" tip moved the backend but
  left the web app's dev server proxying /api to port 8000.
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
RUNBOOK = (ROOT / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")


def _troubleshooting(title: str) -> str:
    match = re.search(rf"^- \*\*{re.escape(title)}\*\*:(.*?)(?=^- \*\*|^## |\Z)", RUNBOOK, re.M | re.S)
    assert match, title
    return match.group(1)


def test_each_dataset_download_command_takes_one_include_pattern():
    commands = re.findall(r"^hf download .*$", RUNBOOK.replace("\\\n", " "), re.M)
    assert len(commands) == 2, commands
    patterns = set()
    for command in commands:
        argv = shlex.split(command)
        assert argv.count("--include") == 1, command
        at = argv.index("--include")
        assert argv[at + 2].startswith("--"), command  # one pattern, not two after one flag
        assert argv[argv.index("--local-dir") + 1] == "/path/to/open-us-law", command
        patterns.add(argv[at + 1])
    assert patterns == {"us_*_statutes.parquet", "us_*_constitutions.parquet"}


def test_seed_demo_ignores_the_database_url_as_the_runbook_says(tmp_path):
    env = {key: value for key, value in os.environ.items() if not key.startswith("LEXGRAPH_")}
    env.update(LEXGRAPH_DATABASE_URL=f"sqlite:///{tmp_path / 'named.db'}", PYTHONPATH=str(BACKEND))

    run = subprocess.run([sys.executable, "-m", "app.seed_demo"], cwd=tmp_path, env=env,
                         capture_output=True, text=True, timeout=180)

    assert run.returncode == 0, run.stdout + run.stderr
    assert sorted(path.name for path in tmp_path.iterdir()) == ["dev.db"]
    initialize = RUNBOOK[RUNBOOK.index("### Initialize the Database"):RUNBOOK.index("### Database Schema")]
    assert "`app.seed_demo` is the exception: it ignores the variable" in initialize
    variable = next(line for line in RUNBOOK.splitlines() if line.startswith("- `LEXGRAPH_DATABASE_URL`:"))
    assert "`app.seed_demo` does not read it" in variable


def test_port_troubleshooting_moves_the_web_app_proxy_with_the_backend():
    vite = (ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")
    proxy = re.search(r'process\.env\.(\w+) \?\? "http://127\.0\.0\.1:8000"', vite)
    assert proxy, "vite.config.ts no longer proxies /api to 127.0.0.1:8000 by default"
    tip = _troubleshooting("Port already in use")
    assert "--port 8001" in tip
    assert f"{proxy.group(1)}=http://127.0.0.1:8001 npm --prefix frontend run dev" in tip, tip
    assert "-- --port 5174 --strictPort" in tip and "BACKEND_PORT" in tip and "FRONTEND_PORT" in tip

