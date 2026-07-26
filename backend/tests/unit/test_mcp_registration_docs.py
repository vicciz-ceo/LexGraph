"""Track C, item C2 — MCP registration docs (gate G7: "one documented
command registers it in Claude Code; config snippets for Codex, Cursor,
Antigravity"). `docs/mcp-registration.md` does not exist yet -- RED
(FileNotFoundError) until the Developer writes it.
"""

from __future__ import annotations

from pathlib import Path

DOC_PATH = Path(__file__).resolve().parents[3] / "docs" / "mcp-registration.md"


def test_registration_doc_exists_and_documents_all_four_clients():
    content = DOC_PATH.read_text()
    assert "claude mcp add" in content
    for client_name in ("Codex", "Cursor", "Antigravity"):
        assert client_name in content
