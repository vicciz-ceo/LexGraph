"""Install instructions run as written from the directory they name (agent:16).

pyproject.toml lives in backend/, a pip outside a virtualenv is refused on PEP 668
systems, and pyproject accepts any Python >= 3.12. So an install command has to create
the venv with `python3`, install with that venv's pip, and run both in backend/. The
agent-facing docs give the one command that was run from the repository root of a
fresh checkout, and no doc names a minor interpreter or a bare pip. docs/RUNBOOK.md
is held to the same rules since the ops package replaced its `python3.13` lines
(ops:9) and the integration gave its installs the one command.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
INSTALL = "(cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]')"
AGENT_DOCS = ("AGENTS.md", "docs/AGENT_GUIDE.md", "docs/mcp-registration.md")
DOCS = (*AGENT_DOCS, "CLAUDE.md", "README.md", "docs/RUNBOOK.md")


def _line_of(text: str, offset: int) -> str:
    return text[text.rfind("\n", 0, offset) + 1: text.find("\n", offset)]


@pytest.mark.parametrize("name", AGENT_DOCS)
def test_agent_docs_give_the_install_command_verified_from_the_repository_root(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    assert INSTALL in text, f"{name} must give the install command {INSTALL}"


@pytest.mark.parametrize("name", DOCS)
def test_install_commands_use_python3_and_the_backend_venv_pip(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    pinned = sorted(set(re.findall(r"\bpython3\.\d+\b", text)))
    assert not pinned, f"{name} names {pinned}; pyproject accepts any Python >= 3.12, use python3"
    for match in re.finditer(r"\bpip3? install\b", text):
        line = _line_of(text, match.start())
        assert text[:match.start()].endswith(".venv/bin/"), f"{name}: pip outside the venv: {line}"
        if " -e " in text[match.start():match.start() + 20]:
            assert "cd backend" in line[:line.find(match.group())], f"{name}: run the editable install in backend/: {line}"
