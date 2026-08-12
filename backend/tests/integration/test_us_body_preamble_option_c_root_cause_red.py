"""Causal option-(c) REDs for the US body-preamble B1 recognizer.

Each RED calls the real production ``_b1_trigger_colon_or_quote_means``
function, not a copied regex or a test-local stand-in.  The input is a
byte-exact contiguous slice of a vendored real row.  Its boundaries are real
section/list boundaries chosen to exclude the unrelated occurrence that makes
the complete row pass today; the paired full ingest+link guards remain in
``test_us_body_preamble_defining_verb_narrowing_red.py``.

The PA ``References to`` example is not a B1 Developer gate.  Core-2 G12 has
now shipped its shared inline-extraction vocabulary and targeted
``_preceded_by_references_to`` guard.  The green integration pin below drives
that actual extraction path in both directions: the PA construction clause is
suppressed and a genuine USC ``includes`` definition is emitted.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _positive_row(act_id: str) -> dict:
    data = json.loads((FIXTURES / "cycle8_defining_verb_positive_rows.json").read_text(encoding="utf-8"))
    return data[act_id]


def _optionc_row(act_id: str) -> dict:
    data = json.loads((FIXTURES / "optionc_root_cause_rows.json").read_text(encoding="utf-8"))
    return data[act_id]


def _bounded_real_body(body: str, *, start: str, end: str | None) -> str:
    """Return one untouched real statutory span, bounded at known structure.

    ``end`` is deliberately excluded when supplied.  It is the next
    list/article marker (or the PA list-introducing colon), so a later rescue
    occurrence cannot make a causal RED pass by accident. ``None`` means the
    real section ends at end-of-body (the OH fixture's final subsection).
    """
    start_index = body.find(start)
    assert start_index >= 0, f"fixture drift: missing structural start {start!r}"
    if end is None:
        end_index = len(body)
    else:
        end_index = body.find(end, start_index)
        assert end_index > start_index, f"fixture drift: missing structural end {end!r}"
    bounded = body[start_index:end_index]
    assert bounded == body[start_index:end_index]
    return bounded


def _expect_real_b1_recognition(body: str, *, act_id: str, cause: str) -> None:
    from app.definition_links.rules.us_body_preamble import _b1_trigger_colon_or_quote_means

    assert _b1_trigger_colon_or_quote_means(body) == "Definitions", (
        f"expected the genuine occurrence in byte-exact bounded {act_id} text "
        f"to make the production B1 recognition function return 'Definitions'; "
        f"it did not, so {cause} remains live. The complete-row ingest guard is "
        "separate and intentionally stays green because it has a rescuing occurrence."
    )


def test_pa_association_greedy_tail_genuine_occurrence_reaches_production_b1_red():
    """PA's real ``association ... means`` clause must itself recognize.

    The bounded span stops before the colon that introduces the numbered list;
    that leaves the real defining clause intact while ensuring a mere shorter
    trigger regex is insufficient.  A Developer must make the production B1
    function consume the genuine ``means`` occurrence, not only stop swallowing
    it.  The full ingest+link guard is
    ``test_state_pa_association_still_captured_despite_the_trigger_regexs_own_greedy_tail_swallowing_means``.
    """
    body = _positive_row("STATE_PA_T15_C75_S7502")["text"]
    bounded = _bounded_real_body(body, start="(a) General rule.--", end=":\n\n(1)")
    assert 'the word "association" in this chapter means a corporation' in bounded, (
        "fixture drift: the byte-exact PA clause must retain its genuine term and "
        "defining verb; this structural pin is intentionally independent of the "
        "pre-fix trigger-match span"
    )
    _expect_real_b1_recognition(
        bounded,
        act_id="STATE_PA_T15_C75_S7502",
        cause="the trigger tail swallows the real defining verb and B1 has no right-occurrence path",
    )


def test_usc_united_states_includes_genuine_occurrence_reaches_production_b1_red():
    """D-INCLUDES widens B1 recognition, not the held extraction fallback.

    The end is the real statutory-note boundary.  The complete row's earlier
    prohibition-list rescue is outside the slice.  Its full ingest+link guard
    is ``test_usc_united_states_includes_still_captured_the_d_includes_cascading_gap``.
    """
    body = _positive_row("USC_T15_C1_S26a")["text"]
    bounded = _bounded_real_body(body, start="As used in this section", end="\n\n(Oct. 15, 1914")
    _expect_real_b1_recognition(
        bounded,
        act_id="USC_T15_C1_S26a",
        cause="_B1_QUOTE_MEANS_RE omits the genuine D-INCLUDES verb 'includes'",
    )


def test_ar_singular_purpose_genuine_occurrence_reaches_production_b1_red():
    """AR's real compact preamble must reach B1 without a later rescue.

    The span ends at the duplicated numbered-list boundary, before the later
    unrelated occurrence that makes the full row recognize today.  Its full
    ingest+link guard is
    ``test_state_ar_interstate_compact_still_captured_the_singular_purpose_trigger_gap``.
    """
    body = _positive_row("STATE_AR_T8_C8_S1_S8-8-102")["text"]
    bounded = _bounded_real_body(body, start="For the purpose of this compact", end="\n\n(a) \"State\"")
    _expect_real_b1_recognition(
        bounded,
        act_id="STATE_AR_T8_C8_S1_S8-8-102",
        cause="_B1_TRIGGER_RE accepts plural 'purposes' but not the real singular 'purpose'",
    )


def test_oh_intervening_divisions_genuine_occurrence_reaches_production_b1_red():
    """OH's intervening divisions clause must reach B1 on its own section.

    The bounded section runs from final subsection (H) to the real end of this
    body; the unrelated complete-row rescue is excluded. Its full ingest+link guard is
    ``test_state_oh_child_still_captured_despite_a_spurious_winning_occurrence_elsewhere_in_the_body``.
    """
    body = _positive_row("STATE_OH_T45_C4510_S4510.17")["text"]
    bounded = _bounded_real_body(body, start="(H) As used in divisions (C) and (D) of this section", end=None)
    _expect_real_b1_recognition(
        bounded,
        act_id="STATE_OH_T45_C4510_S4510.17",
        cause="the bounded intervening 'divisions (C) and (D) of' clause blocks the real trigger",
    )


def test_d_includes_shipped_g12_suppresses_pa_references_to_and_emits_genuine_usc_definition():
    """Pin shipped G12 on real PA and USC rows through its inline extractor."""
    from app.definition_links.us_profile import (
        USProfile,
        _extract_inline_quoted_definitions,
        _preceded_by_references_to,
        _QUOTE_TERM_RE,
    )

    pa_text = USProfile(code="US-PA").normalize_for_parsing(
        _optionc_row("STATE_PA_T15_C57_S5749")["text"]
    )
    pa_quotes = {match.group(1): match for match in _QUOTE_TERM_RE.finditer(pa_text)}
    assert _preceded_by_references_to(pa_text, pa_quotes["other enterprises"].start())
    assert _preceded_by_references_to(
        pa_text, pa_quotes["serving at the request of the corporation"].start()
    )
    pa_candidates = _extract_inline_quoted_definitions(pa_text, scope="law-wide")
    assert pa_candidates == [], (
        "G12 must prevent the PA 'References to \"X\" shall include Y' construction "
        "clause from becoming an inline-definition boundary or candidate"
    )

    us_text = USProfile(code="US").normalize_for_parsing(
        _positive_row("USC_T15_C1_S26a")["text"]
    )
    us_quotes = [
        match for match in _QUOTE_TERM_RE.finditer(us_text) if match.group(1) == "United States"
    ]
    assert us_quotes and all(
        not _preceded_by_references_to(us_text, match.start()) for match in us_quotes
    )
    us_candidates = _extract_inline_quoted_definitions(us_text, scope="law-wide")
    by_term = {term: candidate for candidate in us_candidates for term in candidate.terms}
    assert by_term["United States"].definition_text.startswith(
        "the several States, the District of Columbia"
    ), "G12 must retain and emit the genuine USC 'United States includes ...' definition"
