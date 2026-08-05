"""QA scope RED for P-D2's MN-only relative-idiom repair.

The quoted FED phrase below is a genuine statutory definition, not a false
positive.  The P-D2 ruling nonetheless requires the shared quote engine's
*default* behavior to remain byte-for-byte pre-P-D2 outside an explicit
US-MN opt-in.  A later panel may deliberately claim this FED family under its
own acceptance work; this test only prevents MN's repair from silently doing
so through every registered caller.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_pd2_scope_fed_real_excerpt.json"
)


def test_default_quote_engine_preserves_pre_pd2_fed_relative_idiom_behavior():
    """The genuine FED definition is ledgered, not rejected as bad text.

    The frozen pre-P-D2 default result for this byte-verbatim excerpt is no
    emission.  MN's sibling rule must opt in to its qualifier, comma cleanup,
    and Subd boundary behavior explicitly instead of changing this default.
    """
    row = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    provenance = row["_fixture_provenance"]

    assert row["act_id"] == "USC_T38_C17_S1712A"
    assert provenance["text_is_verbatim_excerpt"] is True
    assert provenance["source_file"] == "us_federal_statutes.parquet"
    assert "family member" in row["text"]
    assert "means an individual" in row["text"]
    assert extract_quote_anchored_entries(row["text"]) == []
