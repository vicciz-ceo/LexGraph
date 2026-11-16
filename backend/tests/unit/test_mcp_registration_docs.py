"""Track C, item C2 — MCP registration docs (gate G7: "one documented
command registers it in Claude Code; config snippets for Codex, Cursor,
Antigravity"). `docs/mcp-registration.md` does not exist yet -- RED
(FileNotFoundError) until the Developer writes it.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[3] / "docs" / "mcp-registration.md"
RUNBOOK_PATH = DOC_PATH.with_name("RUNBOOK.md")


def test_registration_doc_exists_and_documents_all_four_clients():
    content = DOC_PATH.read_text()
    assert "claude mcp add" in content
    for client_name in ("Codex", "Cursor", "Antigravity"):
        assert client_name in content


def _registration_commands(path: Path) -> list[list[str]]:
    joined = path.read_text(encoding="utf-8").replace("\\\n", " ")
    return [shlex.split(line.strip()) for line in joined.splitlines()
            if re.match(r"\s*(claude|codex) mcp add ", line)]


@pytest.mark.parametrize("path", [DOC_PATH, RUNBOOK_PATH], ids=lambda p: p.name)
def test_every_registration_command_uses_absolute_paths(path):
    """ops:2 / agent:3: a relative interpreter or database URL resolves against
    the client's working directory, giving a server that cannot reach the
    workspace. Clients do not inherit an `export`, so the URL must be an --env."""
    commands = _registration_commands(path)
    assert commands, f"{path.name} documents no registration command"
    for argv in commands:
        options, command = argv[:argv.index("--")], argv[argv.index("--") + 1:]
        assert command[0].startswith(("/", "$(pwd)/", "$PWD/")), argv
        assert command[0].endswith("/backend/.venv/bin/python") and command[1:] == ["-m", "app.mcp.server"], argv
        urls = [value.split("=", 1)[1] for flag, value in zip(options, options[1:])
                if flag in ("--env", "-e") and value.startswith("LEXGRAPH_DATABASE_URL=")]
        assert len(urls) == 1 and urls[0].startswith(("sqlite:////", "sqlite:///$(pwd)/", "sqlite:///$PWD/")), argv
