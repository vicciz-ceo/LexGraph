r"""Cycle-5 Planner, item 27 (Spanish citation grammar, core seam spec v2.3
M12 -- core named this panel explicitly as `CitationRule`'s intended
consumer). Live-path proof via `get_profile("US-PR")` (`profiles.py:256`
maps `"US-PR"` to `USProfile(code="US-PR")`) -- `USProfile.find_citations`
(`us_profile.py:1115`) already unions baseline with every registered
`CitationRule` for its own code; today none is registered for `"US-PR"`.

Reaches a NEW rule module the Developer creates, `backend/app/
definition_links/rules/us_pr_citations.py`:

    register_citation_rule(
        CitationRule(jurisdiction_codes=("US-PR",), find=pr_profile.find_citations)
    )

`pr_profile.find_citations` already exists and is already correct as a
pure function (item 4, prior cycles) -- this item is REGISTRATION only,
mirroring `il_scope_triggers.py`'s "wraps an existing extractor verbatim"
shape, not new extraction logic.

## A real, measured baseline-ordering limitation (documented, not silently
wrong -- flagged here rather than promised away)

`USProfile.find_citations` runs BASELINE FIRST (`_find_citations_with_
positions`), claims its own matched spans, and only THEN unions a
registered `CitationRule`'s output -- discarding any rule match whose span
overlaps an already-baseline-claimed span (`us_profile.py:1123-1136`).
Baseline's own `_SECTION_SYMBOL_RE` (`§\s*\d+(?:\(...\))*`) matches the
BARE `§ N` portion of a PR `N L.P.R.A. § N` citation before the PR
`CitationRule`'s fuller `_LPRA_CITATION_RE` match is even considered --
so `find_citations` on real L.P.R.A. text returns bare `"§ N"` (baseline's
own match), never the fuller `"N L.P.R.A. § N"` form, REGARDLESS of
registration. This is an already-merged, shared-module (`us_profile.py`)
behavior this panel does not touch (core-owned baseline-ordering, out of
this panel's write-set) -- `test_baseline_ordering_means_the_bare_section_
symbol_wins_over_the_fuller_lpra_form_documented` pins this reality so a
future reader does not re-discover it as a surprise. The three PR citation
shapes that DO NOT collide with any baseline pattern (`Ley N-YYYY` dash
form, `Ley Núm. N de <fecha>`, bare `Artículo N`) are this item's clean,
uncollided positive proof.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load(name: str) -> dict[str, dict]:
    rows = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows_cycle1():
    return _load("pr_sample_rows.json")


@pytest.fixture()
def de_rows():
    return _load("de_sample_rows.json")


def test_get_profile_us_pr_finds_the_real_ley_dash_and_ley_num_de_fecha_citations(pr_rows_cycle1):
    """`STATE_PR_LEY_85_2018_ART9_04` (real, already vendored cycle 1)
    carries THREE real PR citation shapes in one row: `Ley Núm. 4 de 23 de
    junio de 1971` (formal date form), `Ley 404-2000` (dash form, TWICE --
    once mid-body, once in a trailing `[Ley 85-2018, según enmendada]`
    bracket), none of which baseline `USProfile.find_citations` recognizes
    (verified: baseline alone returns `[]` for this exact text -- zero
    collision risk to reason about for these three)."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle1["STATE_PR_LEY_85_2018_ART9_04"]
    profile = get_profile("US-PR")
    citations = profile.find_citations(row["text"])

    assert "Ley Núm. 4 de 23 de junio de 1971" in citations, (
        "the 'Ley Núm. N de <fecha>' formal citation form must be reachable "
        f"through the REAL get_profile('US-PR') path -- got {citations!r}"
    )
    assert "Ley 404-2000" in citations, (
        "the 'Ley N-YYYY' dash citation form must be reachable through the "
        f"REAL get_profile('US-PR') path -- got {citations!r}"
    )
    assert "Ley 85-2018" in citations


def test_baseline_ordering_means_the_bare_section_symbol_wins_over_the_fuller_lpra_form_documented():
    """Documented limitation (see module docstring) -- pinned as CURRENT,
    ACCEPTED behavior, not a promise this item breaks. Currently RED for
    the ordinary reason (nothing registered yet, so even the bare `§`
    baseline-only answer is what shows up either way) -- once the
    Developer registers the PR `CitationRule`, this assertion must STILL
    hold (baseline-first ordering is unaffected by registration)."""
    from app.definition_links.profiles import get_profile

    text = "El arbitrio aplicable se dispone en 25 L.P.R.A. § 3121."
    profile = get_profile("US-PR")
    citations = profile.find_citations(text)

    assert "§ 3121" in citations, f"expected baseline's bare § match to survive -- got {citations!r}"
    assert "25 L.P.R.A. § 3121" not in citations, (
        "baseline claims the bare '§ 3121' span FIRST (us_profile.py's own "
        "priority order), so the PR CitationRule's fuller L.P.R.A. match is "
        f"discarded as overlapping -- got {citations!r}"
    )


def test_registering_us_pr_citations_does_not_change_a_real_english_state_row_live(de_rows):
    """P5 (M-R4) two-sided proof, citation half: a REAL English-state row
    (`STATE_DE_T5_C7_SVIII_S796`, working-baseline state) fed through
    `get_profile("US-PR").find_citations` -- the SAME registered PR
    CitationRule, but on genuine English text -- must produce the exact
    SAME citations `USProfile.find_citations` would find via baseline
    alone, proving the Spanish citation grammar (Ley N-YYYY / Ley Núm. de
    fecha / Artículo N / L.P.R.A.) never fires on English prose. A test
    that WOULD fail if the PR citation vocabulary were made language-blind
    (e.g. a careless generic 'CODE number' pattern also matching
    'U.S.C. § 1813')."""
    from app.definition_links.profiles import get_profile
    from app.definition_links.us_profile import find_citations as us_baseline_find_citations

    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    pr_profile = get_profile("US-PR")

    baseline_only = us_baseline_find_citations(row["text"])
    via_us_pr = pr_profile.find_citations(row["text"])

    assert via_us_pr == baseline_only, (
        "get_profile('US-PR').find_citations on real English text must "
        "equal baseline's own answer exactly -- any extra entry would mean "
        f"a Spanish citation pattern fired on English prose. baseline={baseline_only!r} "
        f"via_us_pr={via_us_pr!r}"
    )
