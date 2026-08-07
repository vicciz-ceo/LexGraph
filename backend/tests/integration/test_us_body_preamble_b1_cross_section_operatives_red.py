"""Source-faithful M-R104 RED controls for quoted operative text after a B1 section."""

from __future__ import annotations

import pytest

from app.definition_links.profiles import get_profile


@pytest.mark.parametrize(
    ("family", "operative"),
    [
        ("AR certification", "My loan arrangement for this policy provides funds sufficient to pay premiums."),
        ("FED review", "the review either did not identify any covered violations"),
        ("ID notice", "THIS IS AN ESTIMATE. UTILITY RATES MAY GO UP OR DOWN."),
        ("TX budget", "This budget will raise more revenue from property taxes than last year's budget."),
    ],
)
def test_b1_source_section_span_excludes_cross_section_quoted_operative_text(family, operative):
    """These are source-verified non-definitional quotes, not terms."""
    body = (
        "§1 Definitions.\nAs used in this chapter, the term:\n"
        '(1) "kept term" means a genuine definition.\n\n'
        f"§2 {family}.\n(i) \"{operative}\"; and"
    )
    profile = get_profile("US-HI")
    assert profile.derive_heading_from_body("Placeholder", body) == "Definitions"
    candidates = profile.extract_definitions_from_section(body, scope="law-wide", heading_was_derived=True)
    terms = {term for candidate in candidates for term in candidate.terms}
    assert "kept term" in terms
    assert operative not in terms, family
