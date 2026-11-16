"""The RUNBOOK's Python snippets run as written, in document order (ops:9, api:27).

docs/RUNBOOK.md carries ``.venv/bin/python -c "..."`` snippets: "Database
Schema" creates an empty schema and "Backfill: Historical Rows" downgrades the
raw-text columns. Their predecessors ran with ``python3.13 -c``, a system
interpreter that lacks the backend's packages and, on most hosts, does not
exist. These tests extract the code of every such snippet and run it with the
backend's own interpreter against a scratch database, so a snippet that no
longer imports or runs fails here. They also check what the RUNBOOK says the
downgrade leaves behind: a database the server refuses until
``python -m app.migrate`` has run again.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from sqlalchemy import inspect

from app.db import make_engine
from app.migrate import SchemaNotCurrentError, ensure_schema_current

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
RUNBOOK = ROOT / "docs" / "RUNBOOK.md"

# `[VAR=value ...] .venv/bin/python -c "` on its own line, the code, then a
# line holding only the closing quote at the same indentation.
SNIPPET = re.compile(
    r'^(?P<indent>[ \t]*)(?:\S+=\S+ )*\.venv/bin/python -c "\n(?P<code>.*?)\n(?P=indent)"$',
    re.M | re.S,
)
RAW_TEXT_COLUMNS = {
    "assertion_revisions": "proposition_raw",
    "assertion_comments": "comment_text_raw",
    "assertion_ratings": "rationale_raw",
}


def runbook_snippets() -> list[str]:
    return [textwrap.dedent(match.group("code")) for match in SNIPPET.finditer(RUNBOOK.read_text())]


def _run(args: list[str], db: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "LEXGRAPH_DATABASE_URL": f"sqlite:///{db}"}
    return subprocess.run(args, cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120)


def _missing_raw_columns(db: Path) -> set[str]:
    engine = make_engine(f"sqlite:///{db}")
    try:
        inspector = inspect(engine)
        return {
            f"{table}.{column}"
            for table, column in RAW_TEXT_COLUMNS.items()
            if column not in {c["name"] for c in inspector.get_columns(table)}
        }
    finally:
        engine.dispose()


def _server_accepts(db: Path) -> bool:
    engine = make_engine(f"sqlite:///{db}")
    try:
        ensure_schema_current(engine)
        return True
    except SchemaNotCurrentError:
        return False
    finally:
        engine.dispose()


def test_the_runbook_still_documents_both_schema_snippets():
    snippets = runbook_snippets()
    assert any("create_all" in code for code in snippets), snippets
    assert any("downgrade(" in code for code in snippets), snippets


def test_every_runbook_python_snippet_runs_with_the_backend_interpreter(tmp_path):
    db = tmp_path / "lexgraph.db"
    for code in runbook_snippets():
        result = _run([sys.executable, "-c", code], db)
        assert result.returncode == 0, f"snippet failed:\n{code}\n--- stderr:\n{result.stderr}"

    # "Database Schema" built the current schema; the downgrade snippet then
    # dropped exactly the raw-text columns, and the server refuses the file.
    assert _missing_raw_columns(db) == {f"{t}.{c}" for t, c in RAW_TEXT_COLUMNS.items()}
    assert not _server_accepts(db)

    # The RUNBOOK's way back: the documented upgrade command restores them.
    upgrade = _run([sys.executable, "-m", "app.migrate", "--db", str(db)], db)
    assert upgrade.returncode == 0, upgrade.stderr
    assert _missing_raw_columns(db) == set()
    assert _server_accepts(db)


@pytest.mark.parametrize("prefix", ["", "  "], ids=["top-level", "indented"])
def test_the_extractor_reads_snippets_at_any_indentation(prefix):
    text = f'{prefix}A=1 .venv/bin/python -c "\n{prefix}print(1)\n{prefix}"\n'
    assert [textwrap.dedent(m.group("code")) for m in SNIPPET.finditer(text)] == ["print(1)"]
