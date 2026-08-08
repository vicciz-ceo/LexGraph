"""M-R107 future-law controls for structural B1 recognition and extraction."""

from __future__ import annotations

import pytest

from app.definition_links.profiles import get_profile


CASES = (
    {
        "name": "ordinary_manner_is_not_a_legal_unit",
        "jurisdiction": "US-AR",
        "section_title": "87-14-912 New disclosure",
        "text": '(k) In this manner, the insurer shall provide: "NOTICE THAT IS OPERATIVE ONLY"; and',
        "heading": None,
    },
    {
        "name": "disclosure_noun_is_not_a_legal_unit",
        "jurisdiction": "US-ID",
        "section_title": "73-44-209 Consumer communication",
        "text": '(m) IN THIS DISCLOSURE STATEMENT: "AN UNRELATED CAPITALIZED NOTICE"; (n) A statement follows.',
        "heading": None,
    },
    {
        "name": "later_quote_definition_skips_earlier_operative_quote",
        "jurisdiction": "US-TX",
        "section_title": "§ 401.927. MUNICIPAL REPORT.",
        "text": 'In this section, "prelude bond" means an earlier independently defined obligation.\n'
        '(A) "This notice changes a revenue estimate."; (B) "This notice preserves the estimate.";\n'
        '(d) In this section, "harbor instrument" means a security secured by municipal revenue.',
        "heading": "Definitions",
        "false_terms": (
            "This notice changes a revenue estimate.",
            "This notice preserves the estimate.",
        ),
        "term": "harbor instrument",
        "definition_text": "a security secured by municipal revenue.",
        "additional_terms": {
            "prelude bond": "an earlier independently defined obligation.",
        },
    },
    {
        "name": "colon_list_legal_unit_remains_genuine",
        "jurisdiction": "US-GA",
        "section_title": "14-99-314 Novel relay requirement",
        "text": 'For purposes of this Act: (1) "sunset relay" means a licensed communication device.',
        "heading": "Definitions",
        "false_terms": (),
        "term": "sunset relay",
        "definition_text": "a licensed communication device.",
    },
    {
        "name": "clause_group_alias_forwarding_and_exclusion",
        "jurisdiction": "US-TX",
        "section_title": "§ 402.118. NOVEL GROUPS.",
        "text": 'In this section, "quartz relay" or "relay certificate" shall have the same meaning as in Section 402.117; '
        '"harbor notice" expressly excludes a filing receipt; "plain conduit" means a described conduit.',
        "heading": "Definitions",
        "false_terms": (),
        "term": "plain conduit",
        "definition_text": "a described conduit.",
        "additional_terms": {
            "quartz relay": "shall have the same meaning as in Section 402.117;",
            "relay certificate": "shall have the same meaning as in Section 402.117;",
            "harbor notice": "expressly excludes a filing receipt;",
        },
    },
    {
        "name": "multi_aliases_share_a_later_reference_relation",
        "jurisdiction": "US-WA",
        "section_title": "19.88.741 NOVEL HARBOR TERMINOLOGY.",
        "text": 'In this section, "dawn registry", "registry seal", and "registry ledger" shall have the definition set forth in Section 19.88.740; ',
        "heading": "Definitions",
        "false_terms": (),
        "term": "dawn registry",
        "definition_text": "shall have the definition set forth in Section 19.88.740;",
        "additional_terms": {
            "registry seal": "shall have the definition set forth in Section 19.88.740;",
            "registry ledger": "shall have the definition set forth in Section 19.88.740;",
        },
    },
    {
        "name": "ellipted_terms_share_one_later_relation",
        "jurisdiction": "US-WA",
        "section_title": "19.88.742 Novel works terms",
        "text": 'For purposes of this Act, "water works", "sewer works", and "drainage works" mean the public facilities described in this Act; ',
        "heading": "Definitions",
        "false_terms": (),
        "term": "water works",
        "definition_text": "mean the public facilities described in this Act;",
        "additional_terms": {
            "sewer works": "mean the public facilities described in this Act;",
            "drainage works": "mean the public facilities described in this Act;",
        },
    },
    {
        "name": "bare_descriptive_copular_clause_is_a_definition",
        "jurisdiction": "US-NJ",
        "section_title": "26:4-91. Novel turf term.",
        "text": 'In this section, "shore turf" is a planted vegetative surface maintained for public access; ',
        "heading": "Definitions",
        "false_terms": (),
        "term": "shore turf",
        "definition_text": "is a planted vegetative surface maintained for public access;",
    },
    {
        "name": "negative_colon_list_clause_is_a_definition",
        "jurisdiction": "US-VT",
        "section_title": "10-341 Novel exclusions.",
        "text": 'For purposes of this Act: "winter conveyance" does not include a manually propelled sled; ',
        "heading": "Definitions",
        "false_terms": (),
        "term": "winter conveyance",
        "definition_text": "does not include a manually propelled sled;",
    },
    {
        "name": "numbered_colon_list_preserves_unlisted_relation_word",
        "jurisdiction": "US-ME",
        "section_title": "14-742 Novel signal vocabulary.",
        "text": 'For purposes of this Act: (1) "cobalt signal" denotes a secure, time-stamped emergency transmission.',
        "heading": "Definitions",
        "false_terms": (),
        "term": "cobalt signal",
        "definition_text": "denotes a secure, time-stamped emergency transmission.",
    },
    {
        "name": "numbered_alias_list_uses_shared_trailing_forwarding_relation",
        "jurisdiction": "US-OR",
        "section_title": "9.742 Novel shared terms.",
        "text": 'As used in this Act: (1) "alpha"; and (2) "beta"; have the meaning set forth in Section 9.741.',
        "heading": "Definitions",
        "false_terms": (),
        "term": "alpha",
        "definition_text": "have the meaning set forth in Section 9.741.",
        "additional_terms": {
            "beta": "have the meaning set forth in Section 9.741.",
        },
    },
    {
        "name": "numbered_quoted_duty_list_has_no_shared_definition_relation",
        "jurisdiction": "US-OR",
        "section_title": "9.743 Novel duty list.",
        "text": 'As used in this Act: (1) "alpha"; and (2) "beta"; the department shall publish both notices.',
        "heading": None,
    },
    {
        "name": "operative_duty_and_bare_citation_do_not_form_a_group",
        "jurisdiction": "US-OH",
        "section_title": "3912.441 Notice requirement.",
        "text": 'In this section, "a notice shall be mailed within ten days"; "Section 3912.440"; the superintendent shall publish the notice.',
        "heading": None,
    },
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_b1_future_law_structure_at_direct_profile_altitude(case):
    """Identifiers, quoted words, and definition prose are deliberately novel."""
    profile = get_profile(case["jurisdiction"])
    derived = profile.derive_heading_from_body(case["section_title"], case["text"])
    assert derived == case["heading"]
    if derived is None:
        return

    candidates = profile.extract_definitions_from_section(
        case["text"], scope="law-wide", heading_was_derived=True
    )
    by_term = {term: candidate for candidate in candidates for term in candidate.terms}
    for false_term in case["false_terms"]:
        assert false_term not in by_term
    candidate = by_term.get(case["term"])
    assert candidate is not None
    assert candidate.definition_text == case["definition_text"]
    assert candidate.scope == "law-wide"
    for term, definition_text in case.get("additional_terms", {}).items():
        assert by_term.get(term) is not None
        assert by_term[term].definition_text == definition_text
