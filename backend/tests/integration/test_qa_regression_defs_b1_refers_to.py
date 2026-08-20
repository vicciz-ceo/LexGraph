"""QA regression coverage -- sprint 2026-08-12-defs-b1-refers-to (issue #19).

Independent QA pass (separate agent from the Planner/Developer on this
sprint) pinning the corrected-certificate shape from a fresh angle,
following the existing pattern in `test_qa_regression_definition_links.py`
and `test_qa_regression_us_state_law.py`. All identifiers below (jurisdictions,
act_id-shaped strings, terms) are novel -- never seen in the real corpus, the
mandate's Indiana row, or the Developer's own `CASES` tuple in
`tests.unit.test_us_body_preamble_b1_refers_to_relation_red` (M-R107).

Three altitudes, each adding coverage the Developer's own tests do not
already provide:

1. Direct regex-level pin on `_POST_RELATION` itself -- the cheapest
   possible check that the exact fix (widening the verb alternation to
   `refers?\\s+to`) is present and correctly bounded: case-insensitive
   "refers to"/"refer to" match, but the gerund "referring to", the
   unrelated phrase "with reference to", and a partial-word neighbour
   ("refers toon") do NOT match. This isolates the regex from the rest of
   the extraction pipeline, so a future refactor that keeps the higher
   -altitude tests green by accident (e.g. via a different code path)
   cannot silently regress the actual widened pattern.
2. Direct-profile altitude (`get_profile(...).derive_heading_from_body` /
   `.extract_definitions_from_section`), mirroring the Developer's own
   unit-test shape but with entirely fresh jurisdictions/terms, confirming
   the fix generalizes beyond the two cases the Developer happened to pick.
3. Live-persistence altitude (`ingest_us_statute_rows` +
   `run_definition_linking`), confirming both a positive "refer to" recovery
   and the bounded gerund negative control survive the real ingest + dedup
   + persistence path with fresh identifiers.

Every case here was verified empirically against the current (post-fix)
production code before being committed, per this sprint's own M-R107/no
flip-to-red-trap discipline: each assertion below asserts the REQUIRED
(already-passing) behavior, not a still-broken one.
"""

from __future__ import annotations

import pytest

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.profiles import get_profile
from app.definition_links.rules.us_body_preamble_b1 import _POST_RELATION
from app.models.definition import Definition


# --- 1. Direct regex-level pin -------------------------------------------


@pytest.mark.parametrize(
    "tail,expect_match,name",
    [
        (
            ":\n\n(1) refers to a benefit conferred by the office; and\n\n"
            "(2) includes a related credit.",
            True,
            "refers_to_colon_enumerated_tail_matches",
        ),
        (
            ":\n\n(1) refer to a benefit conferred by the office; and\n\n"
            "(2) includes a related credit.",
            True,
            "refer_to_singular_verb_form_matches",
        ),
        (
            ":\n\n(1) REFERS TO a benefit conferred by the office.",
            True,
            "refers_to_is_case_insensitive",
        ),
        (
            ":\n\n(1) referring to a benefit conferred by the office.",
            False,
            "referring_to_gerund_stays_unmatched_bounded_fix",
        ),
        (
            ":\n\n(1) with reference to a benefit conferred by the office.",
            False,
            "with_reference_to_unrelated_phrase_stays_unmatched",
        ),
        (
            ":\n\n(1) refers toon a benefit conferred by the office.",
            False,
            "refers_toon_partial_word_neighbour_stays_unmatched",
        ),
    ],
    ids=[
        "refers_to_colon_enumerated_tail_matches",
        "refer_to_singular_verb_form_matches",
        "refers_to_is_case_insensitive",
        "referring_to_gerund_stays_unmatched_bounded_fix",
        "with_reference_to_unrelated_phrase_stays_unmatched",
        "refers_toon_partial_word_neighbour_stays_unmatched",
    ],
)
def test_post_relation_refers_to_widening_is_present_and_bounded(tail, expect_match, name):
    """Pins the exact one-line fix (`86fccfb`) at the regex level, isolated
    from the rest of the extraction pipeline: `_POST_RELATION` must accept
    "refers to"/"refer to" (case-insensitively) and must NOT accept the
    gerund, an unrelated "reference to" phrase, or a partial-word neighbour
    -- gate 5's boundedness (`_POST_RELATION` widened, nothing broader)."""
    matched = bool(_POST_RELATION.match(tail))
    assert matched == expect_match, (
        f"{name!r}: expected _POST_RELATION.match to be {expect_match} for "
        f"tail {tail!r}, got {matched}"
    )


# --- 2. Direct-profile altitude, fresh jurisdictions/terms ----------------


def test_refers_to_relation_recovered_at_direct_profile_altitude_novel_case():
    """Fresh jurisdiction (US-OR) and term ("credit voucher"), never used by
    the Developer's own `CASES` or the Indiana acceptance row -- confirms
    the fix generalizes beyond the two cases the Developer happened to pick."""
    profile = get_profile("US-OR")
    text = (
        'As used in this article, "credit voucher":\n\n'
        "(1) refers to a voucher issued by the office, regardless of "
        "whether the voucher is transferable; and\n\n"
        "(2) includes a voucher extension issued by the office."
    )
    derived = profile.derive_heading_from_body('"Credit voucher"', text)
    assert derived == "Definitions", (
        f"expected 'Definitions', got {derived!r} -- the colon-list shape "
        "should recognize this body regardless of this sprint's fix"
    )
    candidates = profile.extract_definitions_from_section(text, scope="law-wide", heading_was_derived=True)
    by_term = {term: candidate for candidate in candidates for term in candidate.terms}
    assert "credit voucher" in by_term, (
        f"expected 'credit voucher' among {sorted(by_term)} -- the '(1) refers "
        "to...' relation must survive `_candidate_is_substantive` post-fix"
    )
    assert by_term["credit voucher"].definition_text == "a voucher extension issued by the office."


def test_refer_to_singular_relation_recovered_at_direct_profile_altitude_novel_case():
    """Fresh jurisdiction (US-ME) and term ("service credit"), singular verb
    agreement ("refer to") -- distinct from the Developer's own NM case."""
    profile = get_profile("US-ME")
    text = (
        'In this section, "service credit":\n\n'
        "(1) refer to a credit accrued by an enrolled member; and\n\n"
        "(2) includes a transferred credit recognized by the board."
    )
    derived = profile.derive_heading_from_body('"Service credit"', text)
    assert derived == "Definitions"
    candidates = profile.extract_definitions_from_section(text, scope="law-wide", heading_was_derived=True)
    by_term = {term: candidate for candidate in candidates for term in candidate.terms}
    assert "service credit" in by_term, f"expected 'service credit' among {sorted(by_term)}"
    assert by_term["service credit"].definition_text == "a transferred credit recognized by the board."


def test_referring_to_gerund_negative_control_at_direct_profile_altitude_novel_case():
    """Fresh jurisdiction (US-OR) and term ("audit referral") repeating the
    Developer's bounded-fix guardrail (gate 5: only 'refers to'/'refer to'
    widen, not the gerund 'referring to') with entirely new identifiers."""
    profile = get_profile("US-OR")
    text = (
        'As used in this article, "audit referral":\n\n'
        "(1) referring to a matter forwarded by the office; and\n\n"
        "(2) includes a related compliance notice."
    )
    derived = profile.derive_heading_from_body('"Audit referral"', text)
    assert derived is None, (
        f"expected None (row must stay unrecognized), got {derived!r} -- the "
        "gerund 'referring to' is out of this sprint's bounded fix"
    )


# --- 3. Live-persistence altitude, fresh jurisdictions/terms --------------


def _persisted_definition_text_by_term(db_session, result: dict) -> dict[str, str]:
    persisted = []
    for created in result["created_definitions"]:
        definition = db_session.get(Definition, created["id"])
        assert definition is not None, f"pipeline returned missing Definition id {created['id']}"
        persisted.append(definition)
    return {term: definition.definition_text for definition in persisted for term in definition.terms}


def test_refers_to_relation_recovered_at_live_persistence_altitude_novel_case(db_session, matter_with_users):
    """Same 'credit voucher' shape as the direct-profile case above, driven
    through the real ingest + dedup + persistence pipeline -- not merely a
    direct function call -- with a fresh act_id-shaped identifier never seen
    in the real corpus or in the Developer's own tests."""
    matter = matter_with_users
    row = {
        "act_id": "FUTURE_QA_REGRESSION_CREDIT_VOUCHER",
        "section_number": "12",
        "chapter": "4",
        "section_title": '"Credit voucher"',
        "text": (
            'As used in this article, "credit voucher":\n\n'
            "(1) refers to a voucher issued by the office, regardless of "
            "whether the voucher is transferable; and\n\n"
            "(2) includes a voucher extension issued by the office."
        ),
    }
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title="QA regression refers-to novel case (US-OR)",
        rows=[row],
        jurisdiction="US-OR",
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    persisted = _persisted_definition_text_by_term(db_session, result)
    assert "credit voucher" in persisted, f"expected 'credit voucher' among {sorted(persisted)}"
    assert persisted["credit voucher"] == "a voucher extension issued by the office."


def test_referring_to_gerund_negative_control_at_live_persistence_altitude_novel_case(db_session, matter_with_users):
    """The bounded-fix guardrail (gate 5), driven through the real
    persistence path with a fresh act_id-shaped identifier: the gerund
    'referring to' must persist nothing."""
    matter = matter_with_users
    row = {
        "act_id": "FUTURE_QA_REGRESSION_AUDIT_REFERRAL",
        "section_number": "9",
        "chapter": "2",
        "section_title": '"Audit referral"',
        "text": (
            'As used in this article, "audit referral":\n\n'
            "(1) referring to a matter forwarded by the office; and\n\n"
            "(2) includes a related compliance notice."
        ),
    }
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title="QA regression gerund negative control (US-OR)",
        rows=[row],
        jurisdiction="US-OR",
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    persisted = _persisted_definition_text_by_term(db_session, result)
    assert "audit referral" not in persisted, (
        f"'audit referral' must not persist through the real pipeline -- got "
        f"{sorted(persisted)}"
    )
