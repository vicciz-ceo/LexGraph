"""Terminal-notes negative control for the US markers boundary engine.

`USC_T33_C11_S511` is a compact, provenance-recorded real statute row.  Its
terminal ``Editorial Notes`` amendment history repeats quoted, defining-looking
language.  That commentary must never become a statutory definition.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.rules.us_markers_boundary import TRAILING_STOP_RE, extract_quote_anchored_entries


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_terminal_notes_real_row.json"
)


def _terminal_notes_row() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_real_terminal_notes_stop_before_amendment_history_commentary():
    """The first terminal annotation is a terminal boundary, not an entry
    separator.  The post-notes amendment history contains ``"Secretary"
    means ...`` language, but emits no definition from the quote engine."""
    row = _terminal_notes_row()
    text = row["text"]
    stop = TRAILING_STOP_RE.search(text)

    assert row["act_id"] == "USC_T33_C11_S511"
    assert stop is not None and stop.group() == "Editorial Notes"
    # The amendment prose is deliberately definition-like, but is outside
    # the operative section and is not emitted as an entry.
    assert '"Secretary" means the Secretary of Transportation' in text[stop.end() :]
    entries = dict(extract_quote_anchored_entries(text))
    assert list(entries) == ["bridge", "bridge owner", "Secretary"]
    assert all("Secretary of Transportation" not in definition for definition in entries.values())


def test_annotation_words_and_citations_inside_a_definition_are_not_global_stops():
    """Negative guard: lowercase annotation vocabulary is substantive here,
    not a standalone appended annotation heading."""
    text = (
        '"Citation term" means references in text to Section 552.003 remain part '
        'of this definition.\n\n'
        '"Sibling" means a separate lawful definition.'
    )

    assert dict(extract_quote_anchored_entries(text)) == {
        "Citation term": "references in text to Section 552.003 remain part of this definition.",
        "Sibling": "a separate lawful definition.",
    }
