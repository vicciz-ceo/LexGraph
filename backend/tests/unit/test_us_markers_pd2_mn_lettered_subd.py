"""P-D2 RED: a real lettered MN Subd heading bounds the prior entry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_pd2_mn_lettered_subd_real_excerpt.json"
)


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _extract_with_pd2_opt_in(text: str) -> list[tuple[str, str]]:
    """Exercise P-D2's explicit API, with a provenance-only bcc529c fallback.

    The handoff SHA predates the keyword signature. Falling back only on that
    exact signature error lets this test prove the independent lettered-Subd
    behavior RED against bcc529c. Once the signature lands, the same test uses
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


def test_opted_in_mn_lettered_subd_bounds_and_extracts_enterprise_risk():
    row = _fixture()
    provenance = row["_fixture_provenance"]

    assert row["act_id"] == "STATE_MN_P59A_79A_C60D_S60D.15"
    assert provenance["text_is_verbatim_excerpt"] is True
    assert hashlib.sha256(row["text"].encode("utf-8")).hexdigest() == (
        provenance["excerpt_text_sha256"]
    )

    entries = dict(_extract_with_pd2_opt_in(row["text"]))
    enterprise_definition = (
        "an activity, circumstance, event, or series of events involving one or more affiliates "
        "of an insurer that, if not remedied promptly, is likely to have a material adverse "
        "effect upon the financial condition or liquidity of the insurer or its insurance holding "
        "company system as a whole, including, but not limited to, anything that would cause the "
        "insurer's risk-based capital to fall into company action level as set forth in sections "
        "60A.50 to 60A.696 or would cause the insurer to be in hazardous financial condition in "
        "accordance with the standards of section 60G.20 ."
    )

    # The lettered entry must be independently extracted, not swallowed by Subd. 4.
    assert entries["Enterprise risk"] == enterprise_definition
    preceding = entries["under common control with"]
    assert enterprise_definition not in preceding
    assert "§ Subd. 4a. Enterprise risk." not in preceding
    assert preceding.endswith("notwithstanding the absence of a presumption to that effect.")
