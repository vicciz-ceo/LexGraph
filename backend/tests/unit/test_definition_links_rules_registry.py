"""RED tests for the per-jurisdiction rule registry (sprint
2026-08-04-defs-core-scope, gate C4; seam spec `## Seam spec (published)`
in the sprint contract, FINAL shape as of v2.3 -- v1's 4-tier enum and
v2's `ScopeUnit`/hand-registered rank were both superseded during Stage B
by v2.2's unified `UnitPath` model; this file targets v2.3, the current
published contract, not the intermediate designs).

`app.definition_links.rules.registry` does not exist yet -- RED via
`ImportError` for every test in this file.

Design this file pins down (seam spec v2.2 Seam 1, v2.1 Seam 2, v2.3 M12):

  - Six rule kinds, each a frozen dataclass with a
    `jurisdiction_codes: tuple[str, ...]` field and one kind-specific
    callable: `HeadingRule`, `BodyPreambleRule`, `EntrySplitterRule`,
    `TermClauseRule`, `ScopeTriggerRule`, `StructuralUnitRule`, plus
    (v2.3, M12) `CitationRule`.
  - `jurisdiction_codes` wildcard matching: an exact `JURISDICTION_CODES`
    entry, or the literal `"US-*"` (never `"IL"`). No other wildcard.
  - One `register_*`/`*_rules_for` pair per kind.
  - `UnitStep(kind, value)` / `UnitPath = tuple[UnitStep, ...]` (v2.2) --
    ONE generic path type, replacing v1's `Subsection` and v2's
    `ScopeUnit` entirely. `()` is the law-wide path. No rank registry
    (`register_scope_unit_kind`/`rank_for`) exists any more -- v2.2
    WITHDRAWS it; specificity is path length, not a hand-assigned value.
  - `RuleContext` (M5) / `StructuralContext` (M11) -- the context objects
    a `ScopeTriggerRule`/`StructuralUnitRule` receive instead of bare
    positional args, now carrying `unit_path`/`heading_breadcrumbs`
    fields matching the v2.2 model.
"""

from __future__ import annotations

# RED: this module does not exist yet.
from app.definition_links.rules import registry


def test_register_and_lookup_scope_trigger_rule_by_exact_code():
    def _extract(article_body, ctx):
        return []

    rule = registry.ScopeTriggerRule(jurisdiction_codes=("US-GA",), extract=_extract)
    registry.register_scope_trigger_rule(rule)

    assert rule in registry.scope_trigger_rules_for("US-GA")
    assert rule not in registry.scope_trigger_rules_for("US-DE")
    assert rule not in registry.scope_trigger_rules_for("IL")


def test_register_and_lookup_scope_trigger_rule_by_us_wildcard():
    def _extract(article_body, ctx):
        return []

    rule = registry.ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract)
    registry.register_scope_trigger_rule(rule)

    assert rule in registry.scope_trigger_rules_for("US-DE")
    assert rule in registry.scope_trigger_rules_for("US-FED")
    # The US-* wildcard never matches IL -- it is a US-family-only wildcard.
    assert rule not in registry.scope_trigger_rules_for("IL")


def test_heading_body_preamble_entry_splitter_term_clause_rules_register_and_lookup():
    heading_rule = registry.HeadingRule(jurisdiction_codes=("US-MO",), matches=lambda h: False)
    preamble_rule = registry.BodyPreambleRule(
        jurisdiction_codes=("US-MD",), derive_heading=lambda b: None
    )
    splitter_rule = registry.EntrySplitterRule(jurisdiction_codes=("US-AL",), split=lambda t: [])
    clause_rule = registry.TermClauseRule(jurisdiction_codes=("US-MT",), parse=lambda b: [])

    registry.register_heading_rule(heading_rule)
    registry.register_body_preamble_rule(preamble_rule)
    registry.register_entry_splitter_rule(splitter_rule)
    registry.register_term_clause_rule(clause_rule)

    assert heading_rule in registry.heading_rules_for("US-MO")
    assert preamble_rule in registry.body_preamble_rules_for("US-MD")
    assert splitter_rule in registry.entry_splitter_rules_for("US-AL")
    assert clause_rule in registry.term_clause_rules_for("US-MT")


def test_structural_unit_rule_registers_and_looks_up():
    """v2.1/v2.2 M11 -- the rule kind that derives an article's
    `unit_path`; without it a below-baseline-chapter scope (part/
    subchapter/siman/...) has nothing to compare against."""

    def _derive(ctx):
        return (registry.UnitStep(kind="part", value="II"),)

    rule = registry.StructuralUnitRule(jurisdiction_codes=("US-OR",), derive=_derive)
    registry.register_structural_unit_rule(rule)

    assert rule in registry.structural_unit_rules_for("US-OR")
    assert rule not in registry.structural_unit_rules_for("US-DE")

    ctx = registry.StructuralContext(article_number="153.005", heading_breadcrumbs=())
    path = rule.derive(ctx)
    assert path == (registry.UnitStep(kind="part", value="II"),)


def test_citation_rule_registers_and_looks_up():
    """v2.3 M12 -- `find_citations` becomes rule-extensible (reverses part
    of M7); a jurisdiction with idiosyncratic citation grammar registers
    a `CitationRule` instead of needing a whole new profile class."""

    def _find(text):
        return ["ORS 153.005"] if "ORS" in text else []

    rule = registry.CitationRule(jurisdiction_codes=("US-OR",), find=_find)
    registry.register_citation_rule(rule)

    assert rule in registry.citation_rules_for("US-OR")
    assert rule not in registry.citation_rules_for("US-DE")
    assert rule.find("see ORS 153.005") == ["ORS 153.005"]


def test_unit_step_and_unit_path_construction():
    """v2.2 -- one generic ordered path replaces v1's `Subsection` and
    v2's `ScopeUnit`. `()` is the law-wide path (a prefix of everything)."""
    root = registry.UnitStep(kind="chapter", value="12")
    leaf = registry.UnitStep(kind="article", value="5")
    path: tuple = (root, leaf)
    assert path[0].kind == "chapter"
    assert path[0].value == "12"
    assert path[1] == registry.UnitStep(kind="article", value="5")


def test_rank_for_and_register_scope_unit_kind_no_longer_exist():
    """v2.2 explicitly WITHDRAWS v2's hand-registered rank mechanism --
    specificity is path length now, not a registered integer. Pinning
    their absence so a future edit doesn't silently resurrect a second,
    now-contradictory ranking mechanism alongside `UnitPath`."""
    assert not hasattr(registry, "rank_for")
    assert not hasattr(registry, "register_scope_unit_kind")


def test_rule_context_carries_article_number_chapter_and_unit_path():
    """M5 -- a `ScopeTriggerRule.extract` implementation receives a single
    frozen context object, not positional args, so future context growth
    is additive rather than a six-panel breaking change. v2.2 shape:
    `unit_path` replaces v2's `structural_units`."""
    step = registry.UnitStep(kind="chapter", value="12")
    ctx = registry.RuleContext(article_number="153.005", chapter="12", unit_path=(step,))
    assert ctx.article_number == "153.005"
    assert ctx.chapter == "12"
    assert ctx.unit_path == (step,)


def test_structural_context_carries_article_number_and_heading_breadcrumbs():
    ctx = registry.StructuralContext(
        article_number="34", heading_breadcrumbs=((2, "פרק ו"), (3, "סימן ב"))
    )
    assert ctx.article_number == "34"
    assert ctx.heading_breadcrumbs == ((2, "פרק ו"), (3, "סימן ב"))
