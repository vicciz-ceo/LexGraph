"""G2 non-regression guard -- sprint 2026-08-05-defs-core-follow-on-2, gate
G2. Split out of `test_definition_links_core_follow_on_2_g2_period_style_
markers.py` (which carries the full defect writeup and the positive REDs)
purely to respect this program's 300-line-per-file style gate -- see that
sibling module's docstring for the complete G2 design rationale.

Gate text requirement: "No regression on paren-style states (the 3-ladder
selection stays intact)". Both tests below are GREEN today (neither real
row contains any period-style token) and must stay green, with the
IDENTICAL resolved value, once G2's period-style marker widening ships --
proof that widening the marker vocabulary does not touch a row that never
uses the new vocabulary at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.profiles import get_profile
from app.definition_links.sections import Article as MatcherArticle

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load_rows(filename: str) -> dict[str, dict]:
    rows = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def core_rows() -> dict[str, dict]:
    return _load_rows("core_follow_on_2_g2_g4_rows.json")


@pytest.fixture()
def us_sc():
    return get_profile("US-SC")


@pytest.fixture()
def us_tx():
    return get_profile("US-TX")


def test_sc_clean_paren_style_row_unaffected_by_period_marker_widening(core_rows, us_sc):
    """Real `STATE_SC_T14_C7_A7_S14-7-845` -- pure `(A)(B)(C)` upper_alpha-
    outermost paren-style row, no period-style token anywhere (byte-
    verified: this row is also used, unmodified, by the scoped-inline
    panel's own non-regression fixture on a sibling branch). Must resolve
    to `(upper_alpha, 'B')` at the "school employee" definition -- BEFORE
    and (once implemented) AFTER this item, identically."""
    row = core_rows["STATE_SC_T14_C7_A7_S14-7-845"]
    text = row["text"]
    assert "school employee" in text
    article = MatcherArticle(number="14-7-845", heading="Jury service", body=text, chapter="7")

    path = us_sc.resolve_unit_path(article, char_offset=text.index("school employee"))

    assert len(path) == 1
    assert path[0].kind == "upper_alpha"
    assert path[0].value == "B"


def test_tx_clean_paren_style_row_unaffected_by_period_marker_widening(core_rows, us_tx):
    """Real `STATE_TX_Coc_C2301_S2301.551` -- pure `(a)(b)(c)` federal
    lower_alpha-outermost paren-style row, no period-style token anywhere.
    Must resolve to `(lower_alpha, 'a')` at the "fee" definition -- BEFORE
    and AFTER this item, identically."""
    row = core_rows["STATE_TX_Coc_C2301_S2301.551"]
    text = row["text"]
    anchor = '"fee" does not include'
    assert anchor in text
    article = MatcherArticle(
        number="2301.551", heading="Vehicle lessor fees", body=text, chapter="2301"
    )

    path = us_tx.resolve_unit_path(article, char_offset=text.index(anchor))

    assert len(path) == 1
    assert path[0].kind == "lower_alpha"
    assert path[0].value == "a"
