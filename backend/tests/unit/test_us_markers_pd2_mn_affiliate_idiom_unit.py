"""P-D2 unit RED: Minnesota's quoted relative-idiom definitions.

The real row uses ``"X," when used in reference to ..., means``.  The shared
gate must support that bounded statutory shape without treating ordinary prose
that happens to say ``when used in reference to`` as a definition.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_core3_pd2_real_row_excerpts.json"
)


def _mn_row() -> dict:
    return next(
        row
        for row in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        if row["act_id"] == "STATE_MN_P300_323A_C302A_S302A.011"
    )


def test_real_mn_relative_idioms_emit_the_four_named_clean_entries():
    """The panel-owned engine currently emits a 7,767-char ``Affiliate``
    candidate through the three later definitions.  Each named definition
    below is a distinct entry in the real text and must end at its own Subd.
    marker; this does not assert anything about the separate core marker work.
    """
    entries = dict(extract_quote_anchored_entries(_mn_row()["text"]))

    assert entries["Affiliate"] == (
        "a person that directly or indirectly controls, is controlled by, or is under common "
        "control with, a specified person."
    )
    assert entries["Announcement date"] == (
        "the date of the first public announcement of the final, definitive proposal for the "
        "business combination."
    )
    assert entries["Associate"].startswith("any of the following: (1) any organization")
    assert entries["Associate"].endswith("residing in the home of the person.")
    assert "§ Subd. 46." not in entries["Associate"]
    assert entries["Consummation date"] == (
        "the date of consummation of the business combination or, in the case of a business "
        "combination as to which a shareholder vote is taken, the later of (1) the business day "
        "before the vote or (2) 20 days before the date of consummation of the business combination."
    )


def test_when_used_in_reference_to_prose_without_a_defining_verb_is_not_a_definition():
    """Narrow negative guard: accepting the MN idiom cannot mean accepting
    every quoted discussion followed by the introductory words alone."""
    text = (
        '"Referenced label," when used in reference to this report, is merely a filing label.\n\n'
        '"Actual term" means the only definition in this passage.'
    )

    assert dict(extract_quote_anchored_entries(text)) == {
        "Actual term": "the only definition in this passage."
    }
