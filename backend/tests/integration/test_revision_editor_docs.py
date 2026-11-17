"""The guides describe the revision editor the web app ships (review agent:3,
fe-review-detail:6, fe-shell-authoring:6, ops-docs:3).

The spec and AGENT_GUIDE said Edit assertion's Save waits for a proposition
change. Since XREQ-50 the editor also changes the assertion type, jurisdiction
and effective dates, saves a change to any of them on its own, and refuses an
end date before the start date (frontend/src/components/AssertionEditor.tsx).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GUIDE = (ROOT / "docs" / "AGENT_GUIDE.md").read_text(encoding="utf-8")
SPEC = (ROOT / "docs" / "specs" / "collaborative-assertions.md").read_text(encoding="utf-8")


def test_the_guides_describe_what_the_revision_editor_saves():
    bullet = next(line for line in SPEC.splitlines() if line.startswith("- The revision editor "))
    section = GUIDE[GUIDE.index("In **Edit assertion**"):]
    for text in (bullet, section):
        lowered = " ".join(text.split()).lower()
        assert all(field in lowered for field in ("proposition", "assertion type", "jurisdiction", "effective from"))
        assert "subject and object" in lowered and "end date" in lowered and "before the start date" in lowered
    assert "effective_to is before effective_from" in bullet and "returns an accepted assertion to proposed" in bullet
    assert "until the proposition differs" not in SPEC + GUIDE
