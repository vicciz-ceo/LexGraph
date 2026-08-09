"""Independent QA regressions for M-R118 raw B1 evidence."""

from __future__ import annotations

import pytest

from app.definition_links.profiles import get_profile


CASES = (
    {
        "name": "paired_curly_quote_pseudo_entry_is_filterable",
        "jurisdiction": "US-WA",
        "text": 'In this section: (1) “copper flare”; (2) "signal vault" means a sealed emergency container.',
        "absent": ("copper flare",),
        "expected": {"signal vault": "a sealed emergency container."},
    },
    {
        "name": "curly_open_straight_close_fails_open",
        "jurisdiction": "US-UT",
        "text": 'In this statute:\n(1) “moonlit affidavit"\nAuthorized signature: ________________________________',
        "absent": (),
        "expected": {"moonlit affidavit": "Authorized signature: ________________________________"},
    },
    {
        "name": "repeated_term_with_a_substantive_occurrence_is_preserved",
        "jurisdiction": "US-NV",
        "text": 'In this section: (1) "ember beacon"; (2) "ember beacon" means an approved evacuation marker.',
        "absent": (),
        "expected": {"ember beacon": "an approved evacuation marker."},
    },
    {
        "name": "earlier_b2_winner_is_untouched_despite_b1_overlap",
        "jurisdiction": "US-MD",
        "text": 'In this section, the following words have the meanings indicated: (1) "quartz notice" means an official signal.',
        "absent": (),
        "expected": {"quartz notice": "an official signal."},
        "non_b1_winner": True,
    },
    {
        "name": "plural_anaphora_adds_only_missing_term_without_replacing_existing",
        "jurisdiction": "US-OR",
        "text": 'In this section: (1) "aether relay" means a dedicated alert device; (2) "aether relay"; (3) "boreal signal"; have the meaning set forth for those terms in Section 8.444.',
        "absent": (),
        "expected": {
            "boreal signal": "have the meaning set forth for those terms in Section 8.444.",
        },
        "expected_prefix": {"aether relay": "a dedicated alert device;"},
        "unique_terms": ("aether relay", "boreal signal"),
    },
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_mr118_raw_provenance_controls_direct_profile(case):
    """Raw delimiter evidence is applied only after the real B1 winner is known."""
    profile = get_profile(case["jurisdiction"])
    derived = profile.derive_heading_from_body("M-R118 QA novel section", case["text"])
    assert derived == "Definitions"
    if case.get("non_b1_winner"):
        assert not getattr(derived, "b1_winner", False)
    else:
        assert getattr(derived, "b1_winner", False)

    candidates = profile.extract_definitions_from_section(
        case["text"], scope="law-wide", heading_was_derived=True
    )
    by_term = {term: candidate for candidate in candidates for term in candidate.terms}
    for term in case["absent"]:
        assert term not in by_term
    for term, definition_text in case["expected"].items():
        assert by_term[term].definition_text == definition_text
    for term, definition_prefix in case.get("expected_prefix", {}).items():
        assert by_term[term].definition_text.startswith(definition_prefix)
    for term in case.get("unique_terms", ()):
        assert sum(term in candidate.terms for candidate in candidates) == 1
