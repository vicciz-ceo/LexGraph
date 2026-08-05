"""P-D1 unit RED: FED trailing annotations must be bounded per entry.

The integration companion uses the real `USC_T8_C12_S1101` excerpt.  These
small mechanism cases isolate the panel-owned `TRAILING_STOP_RE` defect: one
global first match must not erase a later lawful entry, and annotation words
inside an actual definition must not be treated as a trailing note heading.
"""

from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries


def test_trailing_annotation_ceiling_is_recomputed_for_each_later_entry():
    """A first Editorial Notes block closes the first entry only; a later
    References in Text block must close the later entry rather than hiding it.
    The current one-global `TRAILING_STOP_RE.search(text)` ceiling never even
    examines ``Later term``."""
    text = (
        '"Earlier term" means the first lawful definition.\n\n'
        'Editorial Notes\n\nHistorical material.\n\n'
        '"Later term" means the second lawful definition.\n\n'
        'References in Text\n\nHistorical material.'
    )

    assert dict(extract_quote_anchored_entries(text)) == {
        "Earlier term": "the first lawful definition.",
        "Later term": "the second lawful definition.",
    }


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
