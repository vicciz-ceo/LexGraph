"""Sprint `2026-08-12-defs-b1-refers-to` (issue #19): M-R107 structural
controls proving `_POST_RELATION` (`backend/app/definition_links/rules/
us_body_preamble_b1.py`, lines 73-77) drops "refers to"/"refer to" post-quote
defining relations before any fix exists.

Mandate: the Indiana row `STATE_IN_T5_A28_C28_S5-28-28-3` defines "loan" as
"(1) refers to a loan made by the corporation..." -- with no relation match
in `_POST_RELATION`'s verb alternation, `_candidate_is_substantive` falls
through to `_bounded_payload` (which stops at the colon right after the
quoted term) and drops the candidate. Director decision: widen ONLY
`_POST_RELATION`; the sibling `_ENUM_RELATION` and `_B1_QUOTE_MEANS_RE`
vocabularies stay untouched.

M-R107 (controls must be structural, not keyed on the known row's own
ID/hash/section/term): every CASE below uses a jurisdiction, act_id-shaped
identifier, and defined term never seen in the real corpus or in any other
test file, exercising the EXACT SAME colon-list / enumerated-relation shape
as the real Indiana row (verified against the real row's own text by this
Planner, both before AND after simulating the widening locally -- see this
commit's Planner report for the verification transcript). The KNOWN Indiana
row itself is acceptance EVIDENCE for gate 1, not a control here; it is
exercised at live-persistence altitude in
`tests.integration.test_us_body_preamble_b1_refers_to_relation_persistence_red`.

Verified today (2026-08-12, this Planner, current HEAD): `_POST_RELATION`
does not match "refers to"/"refer to" in any of these tails, so
`derive_heading_from_body` returns `None` for every positive case below (the
row is not even recognized as a Definitions body, since `derive_heading_
from_body`'s B1 winner gate requires at least one non-empty local/section
candidate list, and the sole "loan"-shaped candidate is the one
`_candidate_is_substantive` drops). RED for the right reason: a missing-
capture assertion, not a collection error.

The third case is a bounded NEGATIVE control (gate 5: only `_POST_RELATION`
widens, and only for "refers to"/"refer to" -- not the gerund "referring
to"). It is GREEN today and MUST stay green after the fix; a Developer
widening the verb alternation too broadly (e.g. `refer\\w*\\s+to`) would flip
it RED, which is exactly the guardrail this control exists to provide.
"""

from __future__ import annotations

import pytest

from app.definition_links.profiles import get_profile


CASES = (
    {
        "name": "novel_refers_to_relation_recovered",
        "jurisdiction": "US-WY",
        "section_title": '"Grant credit"',
        "text": (
            'As used in this chapter, "grant credit":\n\n'
            "(1) refers to a credit extended by the agency, regardless of "
            "whether the credit is repayable; and\n\n"
            "(2) includes a credit guarantee extended by the agency."
        ),
        "heading": "Definitions",
        "false_terms": (),
        "term": "grant credit",
        "definition_text": "a credit guarantee extended by the agency.",
    },
    {
        "name": "novel_refer_to_singular_relation_recovered",
        "jurisdiction": "US-NM",
        "section_title": '"Joint account"',
        "text": (
            'In this section, "joint account":\n\n'
            "(1) refer to an account maintained jointly by two account "
            "holders; and\n\n"
            "(2) includes a payable-on-death designation for that account."
        ),
        "heading": "Definitions",
        "false_terms": (),
        "term": "joint account",
        "definition_text": "a payable-on-death designation for that account.",
    },
    {
        "name": "novel_referring_to_gerund_stays_unrecognized_bounded_control",
        "jurisdiction": "US-VT",
        "section_title": '"Transfer notice"',
        "text": (
            'As used in this chapter, "transfer notice":\n\n'
            "(1) referring to a notice issued by the agency; and\n\n"
            "(2) includes a supplemental filing by the agency."
        ),
        "heading": None,
        "false_terms": ("transfer notice",),
    },
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_b1_refers_to_relation_at_direct_profile_altitude(case):
    """Identifiers, jurisdictions, and defined terms are deliberately novel
    and never appear in the real corpus or in any other test file (M-R107).
    """
    profile = get_profile(case["jurisdiction"])
    derived = profile.derive_heading_from_body(case["section_title"], case["text"])
    assert derived == case["heading"], (
        f"expected derive_heading_from_body to return {case['heading']!r} for "
        f"{case['name']!r}, got {derived!r}"
    )
    if case["heading"] is None:
        candidates = profile.extract_definitions_from_section(
            case["text"], scope="law-wide", heading_was_derived=True
        )
        by_term = {term: candidate for candidate in candidates for term in candidate.terms}
        for false_term in case["false_terms"]:
            assert false_term not in by_term, (
                f"{case['name']!r} must stay excluded (gerund 'referring to' is out of "
                f"this sprint's bounded fix), but {false_term!r} was captured"
            )
        return

    candidates = profile.extract_definitions_from_section(
        case["text"], scope="law-wide", heading_was_derived=True
    )
    by_term = {term: candidate for candidate in candidates for term in candidate.terms}
    for false_term in case["false_terms"]:
        assert false_term not in by_term
    candidate = by_term.get(case["term"])
    assert candidate is not None, (
        f"expected {case['term']!r} among {sorted(by_term)} -- {case['name']!r}'s "
        "post-quote defining relation uses 'refers to'/'refer to', which "
        "`_POST_RELATION` must recognize for this candidate to survive "
        "`_candidate_is_substantive` (issue #19's own recognition shape, "
        "reproduced with entirely novel identifiers per M-R107)"
    )
    assert candidate.definition_text == case["definition_text"], (
        f"expected definition_text {case['definition_text']!r}, got "
        f"{candidate.definition_text!r}"
    )
