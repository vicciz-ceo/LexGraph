"""The backend stays clean under `pytest -W error` (review ops-docs:1, audit ops:11).

Two leaks came back after ops:11 was fixed. A ResourceWarning raised at garbage
collection is blamed on whichever later test triggers it, so a static check is
the reliable guard for these two patterns:

* `with sqlite3.connect(...)`: a connection's own `with` block commits or rolls
  back but never closes it. Use `contextlib.closing(sqlite3.connect(...))`.
* an `urllib.error.HTTPError` caught and not closed: it holds the response
  open. Close it (`with error: ...`) before returning from the handler.
"""
from __future__ import annotations

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
SOURCES = sorted(path for root in ("app", "tests") for path in (BACKEND / root).rglob("*.py"))


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    return node.id if isinstance(node, ast.Name) else ""


def _closes(handler: ast.ExceptHandler) -> bool:
    for node in ast.walk(handler):
        if isinstance(node, ast.With) and any(_dotted(item.context_expr) == handler.name for item in node.items):
            return True
        if isinstance(node, ast.Call) and _dotted(node.func) == f"{handler.name}.close":
            return True
    return False


def _leaks(path: Path, root: Path = BACKEND) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), str(path))):
        if isinstance(node, ast.With):
            for item in node.items:
                call = item.context_expr
                if isinstance(call, ast.Call) and _dotted(call.func) == "sqlite3.connect":
                    found.append(f"{path.relative_to(root)}:{node.lineno}: with sqlite3.connect(...) never closes")
        if (isinstance(node, ast.ExceptHandler) and node.type is not None and node.name
                and _dotted(node.type) in ("urllib.error.HTTPError", "HTTPError") and not _closes(node)):
            found.append(f"{path.relative_to(root)}:{node.lineno}: HTTPError {node.name!r} is not closed")
    return found


def test_the_sources_are_scanned():
    names = {path.name for path in SOURCES}
    assert {"test_dev_servers_launch.py", "test_seed_demo_reset.py", "test_demo_script.py", "main.py"} <= names


def test_no_connection_or_http_error_is_left_for_the_garbage_collector():
    assert [leak for path in SOURCES for leak in _leaks(path)] == []


def test_the_check_recognizes_both_leaks(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "import sqlite3, urllib.error\n"
        "def ids(db):\n"
        "    with sqlite3.connect(db) as conn:\n"
        "        return conn.execute('SELECT 1').fetchall()\n"
        "def status(opener, url):\n"
        "    try:\n"
        "        return opener.open(url).status\n"
        "    except urllib.error.HTTPError as error:\n"
        "        return error.code\n"
        "def closed(opener, url):\n"
        "    try:\n"
        "        return opener.open(url).status\n"
        "    except urllib.error.HTTPError as error:\n"
        "        with error:\n"
        "            return error.code\n",
        encoding="utf-8",
    )
    leaks = [leak.split(": ", 1)[1] for leak in _leaks(sample, tmp_path)]
    assert leaks == ["with sqlite3.connect(...) never closes", "HTTPError 'error' is not closed"]

