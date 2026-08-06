"""G3-HEAL's deliberately narrow source-order seam.

These are planner-owned contract tests for the repair, not a new parser
feature.  They require an additive, default-false EntrySplitterRule flag and
one explicit US-WA registration.  Most importantly, they use a *real* US-MI
multi-block row after test-locally opting its existing inline rule in: the
profile must still leave the baseline candidate first.  That mutation makes
removing the one-baseline-block guard observable even though production MI is
not opted in.
"""

from __future__ import annotations

from dataclasses import replace

from app.definition_links.rules import registry
from app.definition_links.rules import us_markers_inline_quote
from app.definition_links.us_profile import _split_into_numbered_blocks
from test_us_markers_c5guard_mi import _load_rows, _run


_OTHER_INLINE_QUOTE_CODES = (
    "US-VA",
    "US-FED",
    "US-UT",
    "US-TX",
    "US-SC",
    "US-AZ",
    "US-NJ",
    "US-MI",
    "US-ND",
    "US-NY",
    "US-OK",
)
_MI_ACT_ID = "STATE_MI_C206_AAct-281-of-1967_S206.278"
_MI_TERM = "Qualified investment"
_MI_BASELINE_TEXT = (
    "means, except as otherwise provided under this subdivision, an investment of at least "
    "$20,000.00 certified by the Michigan strategic fund that is made alongside of, or through, "
    "a seed venture capital or angel investor group that is registered with the Michigan strategic "
    "fund and is not in a business in which any member of the investor's family is an employee or "
    "owner of the business or in which the investor or any member of the investor's family has a "
    "preexisting fiduciary relationship with the business. Qualified investment does not include an "
    "investment in a business that engages in life sciences technology unless those activities are "
    "included in the definition of life sciences as that term is defined under section 88a of the "
    "Michigan strategic fund act, 1984 PA 270, MCL 125.2088a."
)


def _inline_quote_rules(code: str):
    return [
        rule
        for rule in registry.entry_splitter_rules_for(code)
        if rule.split is us_markers_inline_quote._split
    ]


def test_priority_opt_in_is_additive_default_false_and_registration_is_exactly_wa_only():
    """The new API cannot change existing rules until a module opts in.

    The module must use two registrations, rather than a mixed-code tuple
    carrying a single flag: only WA receives the true flag and every previous
    non-WA code remains represented by the explicit false registration.
    """
    default_rule = registry.EntrySplitterRule(jurisdiction_codes=("US-ZZ",), split=lambda text: [])
    assert default_rule.priority_before_single_baseline is False

    wa_rules = _inline_quote_rules("US-WA")
    mi_rules = _inline_quote_rules("US-MI")
    assert len(wa_rules) == 1
    assert len(mi_rules) == 1
    assert wa_rules[0].jurisdiction_codes == ("US-WA",)
    assert wa_rules[0].priority_before_single_baseline is True
    assert mi_rules[0].jurisdiction_codes == _OTHER_INLINE_QUOTE_CODES
    assert mi_rules[0].priority_before_single_baseline is False


def test_test_locally_opted_mi_rule_still_leaves_real_multi_block_baseline_first(
    db_session, matter_with_users, monkeypatch
):
    """Removing the one-block gate changes this row, so it must stay explicit.

    The MI rule is modified only in this test's registry lookup result.  It
    exercises the production ingest/persistence path with the exact split
    family the repair uses, while proving that an opted source cannot jump a
    normal multi-block baseline section.
    """
    row = _load_rows()[_MI_ACT_ID]
    assert len(_split_into_numbered_blocks(row["text"].replace("\\n", "\n"))) > 1

    original_rules_for = registry.entry_splitter_rules_for

    def rules_with_test_local_mi_opt_in(code: str):
        rules = original_rules_for(code)
        if code != "US-MI":
            return rules
        return [
            replace(rule, priority_before_single_baseline=True)
            if rule.split is us_markers_inline_quote._split
            else rule
            for rule in rules
        ]

    monkeypatch.setattr(registry, "entry_splitter_rules_for", rules_with_test_local_mi_opt_in)
    persisted = _run(db_session, matter_with_users, _MI_ACT_ID)[_MI_TERM]
    assert persisted.definition_text == _MI_BASELINE_TEXT
