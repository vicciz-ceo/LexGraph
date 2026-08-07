"""M-R104 RED contract for a backward-compatible, trigger-owned B1 span."""

from __future__ import annotations

from app.definition_links.rules import registry
from app.definition_links.rules.us_body_preamble_b1 import _b1_trigger_colon_or_quote_means


def test_body_preamble_rule_keeps_heading_only_rules_compatible_and_exposes_optional_span():
    """Existing rule constructions stay valid; only B1 opts into a span."""
    rule = registry.BodyPreambleRule(jurisdiction_codes=("US-TEST",), derive_heading=lambda body: None)
    assert rule.derive_span is None


def test_b1_span_is_the_validated_source_section_containing_its_winning_trigger():
    """The span is source-section bounded, never a list/quote/punctuation heuristic."""
    body = (
        "§1 Definitions.\nAs used in this chapter, the term:\n"
        '(1) "kept" means kept text.\n\n'
        "§2 Required notices.\n(i) \"not a definition\"; and"
    )
    b1_rule = next(
        rule for rule in registry.body_preamble_rules_for("US-HI")
        if rule.derive_heading is _b1_trigger_colon_or_quote_means
    )
    span = b1_rule.derive_span(body)
    assert span is not None
    assert body[span.start:span.end].endswith('"kept" means kept text.\n\n')
    assert "not a definition" not in body[span.start:span.end]


def test_b1_span_declines_delimiter_free_body_so_legacy_extraction_remains_available():
    body = 'As used in this chapter, the term: (1) "kept" means kept text.'
    b1_rule = next(
        rule for rule in registry.body_preamble_rules_for("US-HI")
        if rule.derive_heading is _b1_trigger_colon_or_quote_means
    )
    assert b1_rule.derive_span(body) is None
