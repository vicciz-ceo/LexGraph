"""Track D, item D1 — local-first install runbook (gate G8; gate G3's
backfill documentation requirement). `docs/RUNBOOK.md` does not exist yet --
RED (FileNotFoundError) until the Developer writes it.
"""

from __future__ import annotations

from pathlib import Path

DOC_PATH = Path(__file__).resolve().parents[3] / "docs" / "RUNBOOK.md"

REQUIRED_SECTIONS = (
    "migration",
    "backfill",
    "backend",
    "grading",
    "mcp",
)


def test_runbook_exists_and_covers_every_required_step():
    content = DOC_PATH.read_text().lower()
    for marker in REQUIRED_SECTIONS:
        assert marker in content, f"runbook is missing a section covering {marker!r}"
