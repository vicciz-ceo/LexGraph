"""Setup instructions and scripts install the frontend with ``npm ci``.

``npm install`` re-resolves the dependency tree and rewrites
``frontend/package-lock.json`` whenever the running npm writes a different
form than the committed one (npm 10 drops the ``libc`` fields npm 11 records,
for example), so following README.md, the RUNBOOK quickstart or
``scripts/demo.sh`` left a modified tracked file. ``npm ci`` installs exactly
the committed lockfile and never writes it (finding ops:6).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

SETUP_DOCS = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    ROOT / "docs" / "RUNBOOK.md",
    ROOT / "docs" / "AGENT_GUIDE.md",
    ROOT / "docs" / "mcp-registration.md",
    *sorted((ROOT / "scripts").glob("*.sh")),
]

# `npm install`, `npm i`, `npm --prefix frontend install`, with or without flags.
NPM_INSTALL = re.compile(r"\bnpm(?:\s+--?[\w-]+(?:[ =](?!install\b|i\b|ci\b)\S+)?)*\s+(?:install|i)\b")


def test_the_pattern_recognizes_both_spellings():
    assert NPM_INSTALL.search("cd .. && npm --prefix frontend install && npm --prefix frontend run dev")
    assert NPM_INSTALL.search("npm install --no-audit")
    assert NPM_INSTALL.search("  npm i")
    assert not NPM_INSTALL.search("npm --prefix frontend ci")
    assert not NPM_INSTALL.search("npm --prefix frontend run build")


def test_no_setup_instruction_runs_npm_install():
    offenders = [
        f"{path.relative_to(ROOT)}:{number}: {line.strip()}"
        for path in SETUP_DOCS
        for number, line in enumerate(path.read_text().splitlines(), start=1)
        if NPM_INSTALL.search(line)
    ]
    assert offenders == []
