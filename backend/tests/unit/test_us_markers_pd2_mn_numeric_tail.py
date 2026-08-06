"""P-D2 RED: preserve MN numeric citation tails at a real Subd boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_pd2_mn_numeric_tail_real_excerpt.json"
)


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _extract_with_pd2_opt_in(text: str) -> list[tuple[str, str]]:
    """Exercise P-D2's explicit API, with a provenance-only af75322 fallback.

    The handoff SHA predates the keyword signature.  Falling back only on that
    exact signature error lets this new test prove the independent numeric-tail
    behavior RED against af75322.  Once the signature lands, the same test uses
    only the explicit MN opt-in path.
    """
    try:
        return extract_quote_anchored_entries(
            text,
            allow_relative_qualifiers=True,
            clean_trailing_term_commas=True,
            stop_at_mn_subd_headers=True,
        )
    except TypeError as exc:
        if "unexpected keyword argument 'allow_relative_qualifiers'" not in str(exc):
            raise
        return extract_quote_anchored_entries(text)


def test_opted_in_mn_subd_boundary_preserves_terminal_numeric_citation():
    row = _fixture()
    provenance = row["_fixture_provenance"]

    assert row["act_id"] == "STATE_MN_P216_217_C216B_S216B.68"
    assert provenance["text_is_verbatim_excerpt"] is True
    assert hashlib.sha256(row["text"].encode("utf-8")).hexdigest() == (
        provenance["excerpt_text_sha256"]
    )

    entries = dict(_extract_with_pd2_opt_in(row["text"]))
    federal = entries["Federal mercury regulations"]
    next_definition = (
        "the amount of mercury reduced from the emissions of a targeted or supplemental unit, "
        "relative to the emissions baseline from that unit established under section 216B.681, "
        "expressed as a percentage."
    )

    # The real next entry is independently extracted, never swallowed into Subd. 4.
    assert entries["Mercury emissions reduction"] == next_definition
    assert "§ Subd. 5. Mercury emissions reduction." not in federal
    assert next_definition not in federal
    assert federal == (
        "the federal Clean Air Mercury Rule as of January 1, 2006, published in Code of Federal "
        "Regulations, title 40, parts 60, 63, 70, and 72."
    )
