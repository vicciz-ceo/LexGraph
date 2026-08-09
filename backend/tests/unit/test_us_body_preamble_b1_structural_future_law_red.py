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
        "name": "numbered_colon_list_preserves_unlisted_relation_word",
        "jurisdiction": "US-ME",
        "section_title": "14-742 Novel signal vocabulary.",
        "text": 'For purposes of this Act:\n(1) "cobalt signal" denotes a secure, time-stamped emergency transmission.',
        "heading": "Definitions",
        "false_terms": (),
        "term": "cobalt signal",
        "definition_text": "denotes a secure, time-stamped emergency transmission.",
    },
    {
        "name": "repeated_quoted_term_keeps_later_genuine_definition",
        "jurisdiction": "US-NV",
        "section_title": "23-9-812 Novel marker.",
        "text": '(a) The board shall post: (1) "ember relay"; and (2) "daily bulletin";\n'
        '(e) As used in this section, "ember relay"\nmeans a certified emergency marker.',
        "heading": "Definitions",
        "false_terms": ("daily bulletin",),
        "term": "ember relay",
        "definition_text": "a certified emergency marker.",
        "persistence_scope": "local",
    },
    {
        "name": "wv_source_pin_mismatched_delimiters_survives_normalized_capture",
        "jurisdiction": "US-WV",
        "source_row_id": "STATE_WV_C49_A8_S4",
        "section_title": "4 Power of attorney form.",
        "text": 'In this article:\n(5) “This power of attorney is effective for a period not to exceed one year, beginning,\n'
        '_____________, ___, and ending _______, ____. I reserve the right to revoke this authority at any time."\n'
        'By: ________________________________ (Parent/Legal Custodian signature)',
        "heading": "Definitions",
        "false_terms": (),
        "term": "This power of attorney is effective for a period not to exceed one year, beginning,\n_____________, ___, and ending _______, ____. I reserve the right to revoke this authority at any time.",
        "definition_text": "By: ________________________________ (Parent/Legal Custodian signature)",
    },
    {
        "name": "novel_mismatched_delimiter_preserves_current_tuple",
        "jurisdiction": "US-UT",
        "section_title": "31-8-407 Future authorization form.",
        "text": 'In this statute:\n(1) “violet credential"\nAuthorized signature: ________________________________',
        "heading": "Definitions",
        "false_terms": (),
        "term": "violet credential",
        "definition_text": "Authorized signature: ________________________________",
    },
    {
        "name": "novel_ordinary_direct_definition_remains_parseable",
        "jurisdiction": "US-MT",
        "section_title": "7-6-918 Future communications.",
        "text": 'For purposes of this statute, "solar docket" means a filed electronic notice.',
        "heading": "Definitions",
        "false_terms": (),
        "term": "solar docket",
        "definition_text": "a filed electronic notice.",
    },
    {
        "name": "numbered_alias_list_uses_shared_trailing_forwarding_relation",
        "jurisdiction": "US-OR",
        "section_title": "9.742 Novel shared terms.",
        "text": 'In this section:\n(1) "alpha"; and (2) "beta"; have the meaning set forth for those terms in Section 9.741.',
        "heading": "Definitions",
        "false_terms": (),
        "term": "alpha",
        "definition_text": "have the meaning set forth for those terms in Section 9.741.",
        "additional_terms": {
            "beta": "have the meaning set forth for those terms in Section 9.741.",
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
        "name": "quoted_definition_index_is_not_a_numbered_list",
        "jurisdiction": "US-CO",
        "section_title": "5-1-901 Novel index.",
        "text": 'Definitions in this Act:\n\n"alpha" section 9.741 (1)\n\n"beta" section 9.741 (2)',
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
    assert candidate.scope == case.get("scope", "law-wide")
    for term, definition_text in case.get("additional_terms", {}).items():
        assert by_term.get(term) is not None
        assert by_term[term].definition_text == definition_text
