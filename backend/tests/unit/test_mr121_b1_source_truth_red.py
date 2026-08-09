"""M-R121 uniform source-truth REDs and controls at direct-profile altitude."""

from __future__ import annotations

import pytest

from app.definition_links.normalize import strip_wikilinks
from app.definition_links.profiles import get_profile


CASES = (
    {
        "family": "F1_terminal_period_pseudo_entry",
        "jurisdiction": "US-AZ",
        "text": 'As used in this section:\n(1) "cerulean placard".\n(2) Administration continues.',
        "absent": ("cerulean placard",),
    },
    {
        "family": "F2_punctuation_inside_quote_occurrence",
        "jurisdiction": "US-NC",
        "text": 'As used in this section:\n(1) Cerulean Plate.--Issuable to an eligible owner. The plate shall bear the phrase "Cerulean Plate."\n(2) Amber Plate.--Issuable to another owner.',
        "absent": ("Cerulean Plate",),
    },
    {
        "family": "F3_bare_citation_pseudo_entry",
        "jurisdiction": "US-MD",
        "text": 'As used in this section:\n(1) "cerulean pointer" § 1-201.\n(2) Administration continues.',
        "absent": ("cerulean pointer",),
    },
    {
        "family": "F4a_empty_named_item",
        "jurisdiction": "US-CA",
        "text": 'As used in this section:\n(1) "Cerulean savings association."\n(2) Administration continues.',
        "absent": ("Cerulean savings association.",),
    },
    {
        "family": "F4b_normalized_repeated_direct_definition",
        "jurisdiction": "US-FED",
        "text": 'As used in this section:\n(1) "Former Cerulean Entity";\nFor purposes of this chapter, the term "former cerulean entity" means an entity whose prior election has ended.\n(2) Administration continues.',
        "expected": {
            "Former Cerulean Entity": ';\nFor purposes of this chapter, the term "former cerulean entity" means an entity whose prior election has ended.',
        },
    },
    {
        "family": "F5_colon_enumerated_direct_definition",
        "jurisdiction": "US-TX",
        "text": 'As used in this section:\n(1) "Domestic cerulean use":\n(A) means household use of stored water; and\n(B) does not include a commercial sale.',
        "expected": {
            "Domestic cerulean use": ":\n(A) means household use of stored water; and\n(B) does not include a commercial sale.",
        },
    },
    {
        "family": "F6_bounded_plural_relation",
        "jurisdiction": "US-IN",
        "text": 'As used in this section:\n(1) "cerulean utility"; and\n(2) "cerulean works";\nhave the meaning set forth for those terms in section 8.1 of this chapter.\n\n(c) A later subsection governs rates.',
        "expected": {
            "cerulean utility": "have the meaning set forth for those terms in section 8.1 of this chapter.",
            "cerulean works": "have the meaning set forth for those terms in section 8.1 of this chapter.",
        },
        "unique": ("cerulean utility", "cerulean works"),
        "forbidden_text": "A later subsection governs rates.",
    },
    {
        "family": "F7_form_template_pseudo_entry",
        "jurisdiction": "US-WV",
        "text": 'As used in this form:\n(1) "I appoint the following cerulean agent: ____________."\nBy: ____________________ (principal signature)',
        "absent": ("I appoint the following cerulean agent: ____________.",),
    },
    {
        "family": "A_indexed_forwarding_definition",
        "jurisdiction": "US-MD",
        "text": 'In this title: the following definitions in this article apply to this title:\n(1) "Cerulean applicant" § 28:5-102.\n(2) "Cerulean beneficiary" § 28:5-102.',
        "expected": {
            "Cerulean applicant": "§ 28:5-102.",
            "Cerulean beneficiary": "§ 28:5-102.",
        },
    },
    {
        "family": "A_dash_newline_definition",
        "jurisdiction": "US-FED",
        "text": 'As used in this section:\n(1) "cerulean disruption"—\n\n(A) means a material reduction in supply; and\n(B) does not include routine maintenance.',
        "expected": {
            "cerulean disruption": "—\n\n(A) means a material reduction in supply; and\n(B) does not include routine maintenance.",
        },
    },
    {
        "family": "A_alias_name_introduction",
        "jurisdiction": "US-FED",
        "text": 'As used in this section:\n(1) "Cerulean Director".\n\nThe head of the office is referred to in this chapter as the "cerulean director".',
        "expected": {
            "Cerulean Director": '.\n\nThe head of the office is referred to in this chapter as the "cerulean director".',
        },
    },
    {
        "family": "R1_alias_name_is_jurisdiction_neutral",
        "jurisdiction": "US-AZ",
        "text": 'As used in this section:\n(1) "Cerulean Plan".\nThe package is commonly referred to as the "cerulean plan".\n(2) Administration continues.',
        "expected": {
            "Cerulean Plan": '.\nThe package is commonly referred to as the "cerulean plan".',
        },
    },
    {
        "family": "R2_dotted_term_uses_normalized_explicit_relation",
        "jurisdiction": "US-GA",
        "text": 'As used in this section:\n(1) "cerulean population bill.".\nFor purposes of this section, "cerulean population bill" means a bill classified by population.\n(2) Administration continues.',
        "expected": {
            "cerulean population bill.": '.\nFor purposes of this section, "cerulean population bill" means a bill classified by population.',
        },
    },
    {
        "family": "R3_dotted_term_ignores_normalized_ordinary_reference",
        "jurisdiction": "US-CA",
        "text": 'As used in this section:\n(1) "cerulean savings bank.".\nThis section refers to the term "cerulean savings bank" in ordinary prose.\n(2) Administration continues.',
        "absent": ("cerulean savings bank.",),
    },
    {
        "family": "R4_colon_enumerated_subject_relation",
        "jurisdiction": "US-MD",
        "text": 'As used in this section:\n(1) "Consequential cerulean damages":\n(A) Resulting from breach of contract includes incidental loss; and\n(B) Resulting from misuse includes mitigation costs.',
        "expected": {
            "Consequential cerulean damages": ':\n(A) Resulting from breach of contract includes incidental loss; and\n(B) Resulting from misuse includes mitigation costs.',
        },
    },
    {
        "family": "R5_plural_group_preserves_independent_definition",
        "jurisdiction": "US-OR",
        "text": 'In this section:\n(1) "cerulean relay" means a dedicated alert device;\n(2) "cerulean relay";\n(3) "boreal works";\nhave the meaning set forth for those terms in section 8.1 of this chapter.',
        "expected": {
            "boreal works": "have the meaning set forth for those terms in section 8.1 of this chapter.",
        },
        "expected_prefix": {"cerulean relay": "means a dedicated alert device;"},
        "unique": ("cerulean relay", "boreal works"),
    },
    {
        "family": "R6_legislative_history_is_structural_not_payload",
        "jurisdiction": "US-HI",
        "text": 'As used in this section:\n(1) "Cerulean intoxicants: coverage is excluded." [L 1987, c 347, pt of §2; am L 2002, c 155, §53]\n(2) Administration continues.',
        "absent": ("Cerulean intoxicants: coverage is excluded.",),
    },
    {
        "family": "R7_reciprocal_respectively_designation",
        "jurisdiction": "US-KS",
        "text": 'In this compact:\n1. The State of Cerulea and the State of Borealia are designated, respectively, as "Cerulea" and "Borealia".\n2. The provisions respecting each named state shall include and bind its citizens.\n3. The term "upper cerulean reach" means the northern channel.',
        "expected": {
            "Borealia": "and bind its citizens.\n3. The term",
            "upper cerulean reach": "the northern channel.",
        },
    },
    {
        "family": "A_malformed_raw_delimiter_fails_open",
        "jurisdiction": "US-UT",
        "text": 'As used in this section:\n(1) “cerulean sunset clause“.\nNext provision.',
        "expected": {"cerulean sunset clause": ".\nNext provision."},
    },
    {
        "family": "A_safe_editorial_substitution",
        "jurisdiction": "US-FED",
        "text": 'As used in this section: the amendment substitutes the following references:\n(1) "section 46(a)(2)(C)".\n(2) Administration continues.',
        "absent": ("section 46(a)(2)(C)",),
    },
    {
        "family": "A_safe_prescribed_statement_list",
        "jurisdiction": "US-FED",
        "text": 'As used in this disclosure: the creditor shall print the statements:\n(1) "Cerulean rates may change"; and\n(2) "Consult your agreement".',
        "absent": ("Cerulean rates may change", "Consult your agreement"),
    },
    {
        "family": "A_safe_rating_list",
        "jurisdiction": "US-FED",
        "text": 'As used in this rating form: the institution shall receive one rating:\n(1) "Outstanding cerulean record".\n(2) "Satisfactory cerulean record".',
        "absent": ("Outstanding cerulean record", "Satisfactory cerulean record"),
    },
    {
        "family": "A_safe_policy_objective_list",
        "jurisdiction": "US-FED",
        "text": 'As used in this plan: the mechanisms shall:\n(1) "ensure cerulean accountability"; and\n(2) "link cerulean spending to performance".',
        "absent": ("ensure cerulean accountability", "link cerulean spending to performance"),
    },
)


def direct_candidates(case):
    """Exercise the same normalized parser/raw-source split as persistence."""
    profile = get_profile(case["jurisdiction"])
    parser_body, _ = strip_wikilinks(profile.normalize_for_parsing(case["text"]))
    derived = profile.derive_heading_from_body(
        "M-R121 novel source-truth section",
        parser_body,
        raw_source=case["text"],
        article_number="121.901",
        chapter="qa-future",
    )
    if derived is None:
        return []
    assert derived == "Definitions"
    assert getattr(derived, "b1_winner", False)
    return profile.extract_definitions_from_section(
        parser_body,
        scope="law-wide",
        heading_was_derived=True,
        raw_source=case["text"],
        b1_winner=True,
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["family"])
def test_mr121_source_truth_at_direct_profile_altitude(case):
    candidates = direct_candidates(case)
    by_term = {}
    for candidate in candidates:
        for term in candidate.terms:
            by_term.setdefault(term, candidate)
    for term in case.get("absent", ()):
        assert term not in by_term
    for term, definition_text in case.get("expected", {}).items():
        assert by_term[term].definition_text == definition_text
        assert by_term[term].scope == "law-wide"
    for term, definition_prefix in case.get("expected_prefix", {}).items():
        assert by_term[term].definition_text.startswith(definition_prefix)
        assert by_term[term].scope == "law-wide"
    for term in case.get("unique", ()):
        assert sum(term in candidate.terms for candidate in candidates) == 1
    if forbidden := case.get("forbidden_text"):
        assert all(forbidden not in candidate.definition_text for candidate in candidates)
