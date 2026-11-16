"""README.md and docs/RUNBOOK.md commands run as written (ops:9, ops:14, ops:15, api:27).

Each check below was a real failure when the documents were followed literally:

- ``python3.13 -m venv`` (RUNBOOK quickstart, setup and end-to-end steps) is
  "command not found" on any host without that exact minor version, although
  ``backend/pyproject.toml`` allows 3.12+ and CI tests 3.12 and 3.13. A bare
  ``python3 -c`` or ``pip install`` reaches a system interpreter that lacks the
  backend's dependencies, or is refused under PEP 668.
- The README's test one-liner came before its setup step and never installed
  the frontend, so on a fresh clone it exited 127 (``vitest: not found``).
- RUNBOOK started the backend with ``--host 0.0.0.0``, publishing a server
  whose sign-in is built for a trusted local machine on every interface.
- End-to-End step 7 registered the MCP server with a relative interpreter and
  no database URL. Claude Code showed it as Connected while every database
  tool failed with ``no such table``, because the client starts the server
  from its own working directory and passes only the stored environment.

The RUNBOOK's Python snippets are executed in
``tests/integration/test_runbook_python_snippets.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
README = ROOT / "README.md"
RUNBOOK = ROOT / "docs" / "RUNBOOK.md"
DOCS = [README, RUNBOOK]

FENCE = re.compile(r"^\s*```")
# An absolute path as a shell command line writes it: /..., $PWD/..., $(pwd)/...
ABSOLUTE_PATH = r"(?:/|\$PWD/|\$\(pwd\)/)"


def commands(path: Path) -> list[tuple[int, str]]:
    """(first line number, command) for every fenced shell line, with
    backslash continuations joined into one command."""
    inside, joined = False, []
    pending: tuple[int, str] | None = None
    for number, raw in enumerate(path.read_text().splitlines(), start=1):
        if FENCE.match(raw):
            inside = not inside
            continue
        if not inside:
            continue
        line = raw.strip()
        if pending is not None:
            number, line = pending[0], f"{pending[1]} {line}"
            pending = None
        if line.endswith("\\"):
            pending = (number, line[:-1].rstrip())
        else:
            joined.append((number, line))
    return joined


def _section_span(path: Path, heading: str) -> tuple[int, int]:
    """1-based (heading line, last line) of one ``## `` section."""
    lines = path.read_text().splitlines()
    start = lines.index(f"## {heading}") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return start, end


def section_commands(path: Path, heading: str) -> list[str]:
    """The commands inside one ``## `` section."""
    start, end = _section_span(path, heading)
    return [command for number, command in commands(path) if start < number <= end]


def _where(path: Path, number: int, line: str) -> str:
    return f"{path.relative_to(ROOT)}:{number}: {line}"


def test_no_document_pins_a_python_minor_version():
    """`python3` is what every supported host has; `python3.13` is not."""
    pinned = re.compile(r"\bpython3\.\d+\b")
    offenders = [
        _where(path, number, line)
        for path in DOCS
        for number, line in enumerate(path.read_text().splitlines(), start=1)
        if pinned.search(line)
    ]
    assert offenders == []


def test_backend_installs_and_snippets_use_the_backend_venv():
    """In commands and in prose alike: the backend's dependencies live only in
    ``backend/.venv``."""
    bare_pip = re.compile(r"(?<!\.venv/bin/)\bpip install -e\b")
    bare_python = re.compile(r"(?<![\w./-])python3?(?:\.\d+)? -c\b")
    offenders = [
        _where(path, number, line)
        for path in DOCS
        for number, line in enumerate(path.read_text().splitlines(), start=1)
        if bare_pip.search(line) or bare_python.search(line)
    ]
    assert offenders == []


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_no_documented_command_binds_every_interface(path):
    """uvicorn's default bind is 127.0.0.1; the RUNBOOK explains how to reach
    the server from another computer without widening it."""
    wide = re.compile(r"--host[ =](?:0\.0\.0\.0|::|\[::\])(?:\s|$)")
    assert [_where(path, n, line) for n, line in commands(path) if wide.search(line)] == []


def test_mcp_registrations_pass_absolute_paths_and_the_database():
    """`claude mcp add` stores only its own arguments, and the client starts the
    server from its own working directory, so relative paths and an exported
    variable are both lost.

    The RUNBOOK's "MCP Server Registration" section and docs/mcp-registration.md
    belong to the agent package's docs and are left to its checks; every other
    registration these two documents show is checked here."""
    agent_section = _section_span(RUNBOOK, "MCP Server Registration")
    assert any(c.startswith("claude mcp add ") for _n, c in commands(RUNBOOK)), "parser found no registration"
    registrations = [
        command
        for path in DOCS
        for number, command in commands(path)
        if command.startswith("claude mcp add ")
        and not (path == RUNBOOK and agent_section[0] < number <= agent_section[1])
    ]
    for command in registrations:
        assert re.search(rf'--env LEXGRAPH_DATABASE_URL="?sqlite:///{ABSOLUTE_PATH}', command), command
        interpreter = command.split(" -- ", 1)[1].split()[0]
        assert re.match(rf'"?{ABSOLUTE_PATH}', interpreter), command


def test_readme_commands_leave_the_shell_at_the_repository_root():
    """The README's blocks are all run from the repository root, one after
    another: a bare `cd backend && ...` left the shell in backend/, so the
    next block's `cd backend` failed."""
    moves = [_where(README, n, line) for n, line in commands(README)
             if re.search(r"(?:^|[;&|]\s*)cd ", line) and not line.startswith("(")]
    assert moves == []


def test_readme_test_instructions_install_both_halves_before_running_them():
    """Followed top to bottom in one shell from a fresh clone, the README's
    test section must reach its one-liner with both halves installed and the
    shell still at the repository root."""
    lines = section_commands(README, "Running the tests")
    test_line = next(i for i, line in enumerate(lines) if "backend/.venv/bin/pytest" in line)
    assert "npm --prefix frontend run test" in lines[test_line]
    setup = lines[:test_line]
    assert any("-m venv .venv" in line and ".venv/bin/pip install -e" in line for line in setup), setup
    assert any(re.search(r"\bnpm --prefix frontend ci\b", line) for line in setup), setup
    moves = [line for line in setup if re.search(r"(?:^|[;&|(]\s*)cd ", line)]
    assert all(line.startswith("(") for line in moves), (
        f"{moves}: changes directory outside a subshell, so the root-relative test command fails"
    )
