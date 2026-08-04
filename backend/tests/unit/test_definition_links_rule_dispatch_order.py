"""Order/zero-miss supporting REDs for the rule-dispatch consumption
contract (sprint 2026-08-04-defs-core-dispatch, item I7's own "add more
only where the dispatch test alone under-specifies the per-kind ORDER"
instruction).

`test_definition_links_rule_dispatch.py` proves each kind fires AT ALL. This
file pins the two shape details a bare "does it fire" test cannot show:

1. **Baseline-first, never overridden (detection kinds).** The seam spec's
   consumption contract (v1 "Consumption contract -- baseline-first,
   registry-second, per kind") is explicit that a registered rule is
   consulted ONLY when baseline returns false/empty -- never that a
   registered rule can override a baseline POSITIVE. This sprint's own
   rules section says it plainly: "Do not pin a shape where a registered
   rule pre-empts working baseline behavior -- that would break the 7
   already-working US states." `HeadingRule`/`BodyPreambleRule` are the two
   detection kinds where this distinction is observable (a registered rule
   that would answer differently from baseline must never be allowed to
   win once baseline already found something).
2. **Zero-miss union (union kinds).** M1/seam spec Seam 2: "ALL matching
   registered rules run, every candidate they produce is kept (union, not
   first-wins) -- zero-miss bias." Registering TWO rules of the same kind,
   each firing on its own distinct probe marker, must yield BOTH rules'
   candidates -- neither may suppress the other.

Same probe-string/jurisdiction-code isolation discipline as the sibling
file: unique `ZZZ_ORDER_...`/`ZZZ_UNION_...` markers, a jurisdiction code
not used by any other test file in this sprint (`US-WY`), so registrations
here can never cross-fire with `test_definition_links_rule_dispatch.py`'s
own probes.
"""

from __future__ import annotations

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.profiles import get_profile
from app.definition_links.rules import registry

_US_CODE = "US-WY"
_IL_CODE = "IL"


# --- Baseline-first, never overridden (I1: HeadingRule) --------------------


def test_heading_rule_never_overrides_a_baseline_positive_us():
    """`"Definitions"` is recognized by baseline alone (no rule needed --
    verified live before registering anything). A registered rule that
    would answer False must never suppress that baseline positive -- this
    is exactly what keeps the 7 already-working US states untouched."""
    profile = get_profile(_US_CODE)
    heading = "Definitions"
    assert profile.is_definitions_heading(heading, "") is True  # baseline alone, no rule yet

    registry.register_heading_rule(
        registry.HeadingRule(jurisdiction_codes=(_US_CODE,), matches=lambda h: False)
    )

    assert profile.is_definitions_heading(heading, "") is True


def test_heading_rule_never_overrides_a_baseline_positive_il():
    profile = get_profile(_IL_CODE)
    heading = "הגדרות"
    assert profile.is_definitions_heading(heading, "") is True  # baseline alone, no rule yet

    registry.register_heading_rule(
        registry.HeadingRule(jurisdiction_codes=(_IL_CODE,), matches=lambda h: False)
    )

    assert profile.is_definitions_heading(heading, "") is True


# --- Baseline-first, never overridden (I2: BodyPreambleRule) ---------------


def test_body_preamble_rule_never_overrides_a_baseline_positive_us():
    """The real Illinois embedded-heading shape: baseline (placeholder gate
    + body scan) ALREADY derives a heading from this body with no rule
    involved. A registered rule returning a DIFFERENT string must never
    win once baseline already found something -- consistent with the
    "registered rules run when baseline yields nothing" ordering (not
    "registered rules always get a say")."""
    profile = get_profile(_US_CODE)
    heading = "Section 15"  # real Illinois bare-placeholder shape
    body = (
        "(325 ILCS 7/15) (Section scheduled to be repealed on January 1, 2027) "
        'Sec. 15. Definitions. As used in this Act: "Bias-free" means to review '
        "a case file."
    )
    baseline_result = profile.derive_heading_from_body(heading, body)
    assert baseline_result is not None  # baseline alone already derives a heading

    registry.register_body_preamble_rule(
        registry.BodyPreambleRule(
            jurisdiction_codes=(_US_CODE,), derive_heading=lambda b: "ZZZ_ORDER_SHOULD_NEVER_WIN"
        )
    )

    assert profile.derive_heading_from_body(heading, body) == baseline_result


# --- Zero-miss union (I3: EntrySplitterRule) --------------------------------


def test_entry_splitter_rule_union_two_rules_neither_suppresses_the_other_us():
    profile = get_profile(_US_CODE)
    text = "ZZZ_UNION_SPLIT_A_US and ZZZ_UNION_SPLIT_B_US both present, no baseline markers at all."
    assert profile.extract_definitions_from_section(text, scope="law-wide") == []

    registry.register_entry_splitter_rule(
        registry.EntrySplitterRule(
            jurisdiction_codes=(_US_CODE,),
            split=lambda t: (
                ['"Union Split Term A" means def A.'] if "ZZZ_UNION_SPLIT_A_US" in t else []
            ),
        )
    )
    registry.register_entry_splitter_rule(
        registry.EntrySplitterRule(
            jurisdiction_codes=(_US_CODE,),
            split=lambda t: (
                ['"Union Split Term B" means def B.'] if "ZZZ_UNION_SPLIT_B_US" in t else []
            ),
        )
    )

    candidates = profile.extract_definitions_from_section(text, scope="law-wide")
    terms = {c.terms for c in candidates}
    assert terms == {("Union Split Term A",), ("Union Split Term B",)}


# --- Zero-miss union (I3: TermClauseRule) -----------------------------------


def test_term_clause_rule_union_two_rules_neither_suppresses_the_other_us():
    profile = get_profile(_US_CODE)
    # Two bare-digit-marker blocks, neither with a leading quote -- baseline
    # finds two blocks, zero candidates.
    text = (
        "(1) ZZZ_UNION_CLAUSE_A_US no leading quote here.\n"
        "(2) ZZZ_UNION_CLAUSE_B_US also no leading quote here."
    )
    assert profile.extract_definitions_from_section(text, scope="law-wide") == []

    registry.register_term_clause_rule(
        registry.TermClauseRule(
            jurisdiction_codes=(_US_CODE,),
            parse=lambda block: (
                [DefinitionCandidate(terms=("Union Clause Term A",), definition_text="def A", scope="law-wide")]
                if "ZZZ_UNION_CLAUSE_A_US" in block
                else []
            ),
        )
    )
    registry.register_term_clause_rule(
        registry.TermClauseRule(
            jurisdiction_codes=(_US_CODE,),
            parse=lambda block: (
                [DefinitionCandidate(terms=("Union Clause Term B",), definition_text="def B", scope="law-wide")]
                if "ZZZ_UNION_CLAUSE_B_US" in block
                else []
            ),
        )
    )

    candidates = profile.extract_definitions_from_section(text, scope="law-wide")
    terms = {c.terms for c in candidates}
    assert terms == {("Union Clause Term A",), ("Union Clause Term B",)}


# --- Zero-miss union (ScopeTriggerRule -- already-live kind, extra guard) --


def test_scope_trigger_rule_union_two_rules_neither_suppresses_the_other_us():
    """`ScopeTriggerRule` is already live (this is a supplementary guard,
    not a dispatch proof -- see the sibling dispatch file for that). Two
    independently-registered rules, each firing on its own marker, must
    both contribute -- a regression here would silently drop a family
    panel's rule whenever another panel's rule also matches the same
    article body."""
    profile = get_profile(_US_CODE)
    body = "ZZZ_UNION_SCOPE_A_US and ZZZ_UNION_SCOPE_B_US both present, no existing trigger phrase."
    assert profile.extract_local_scope_definitions(body, article_number="1") == []

    registry.register_scope_trigger_rule(
        registry.ScopeTriggerRule(
            jurisdiction_codes=(_US_CODE,),
            extract=lambda b, ctx: (
                [DefinitionCandidate(terms=("Union Scope Term A",), definition_text="def A", scope="local")]
                if "ZZZ_UNION_SCOPE_A_US" in b
                else []
            ),
        )
    )
    registry.register_scope_trigger_rule(
        registry.ScopeTriggerRule(
            jurisdiction_codes=(_US_CODE,),
            extract=lambda b, ctx: (
                [DefinitionCandidate(terms=("Union Scope Term B",), definition_text="def B", scope="local")]
                if "ZZZ_UNION_SCOPE_B_US" in b
                else []
            ),
        )
    )

    candidates = profile.extract_local_scope_definitions(body, article_number="1")
    terms = {c.terms for c in candidates}
    assert terms == {("Union Scope Term A",), ("Union Scope Term B",)}
