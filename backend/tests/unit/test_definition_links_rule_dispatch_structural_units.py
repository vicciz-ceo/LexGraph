"""I4 RED tests -- `StructuralUnitRule` as ARTICLE-METADATA enrichment
(sprint 2026-08-04-defs-core-dispatch, manager ruling M-D1, seam v2.6 §1).

**Why this file is shaped the way it is.** M-D1 restates `StructuralUnitRule`
back to its original M11 shape: `derive: Callable[[StructuralContext],
tuple[ScopeUnit, ...]]` -- ABOVE-article container units (part/subchapter/
siman/...) stamped onto the owning ARTICLE, union consumption ("core keeps
stamping `ScopeUnit("chapter", article.chapter)` itself, unconditionally;
registered rules ADD to that set, never replace it"). It has explicitly NO
relationship to `resolve_unit_path`/`UnitPath` (that seam is below-article
only, per v2.4 §1 -- see the sibling dispatch files, which correctly never
touch `resolve_unit_path` for this kind).

**The one thing this file deliberately does NOT pin.** The ruling names the
consumption point precisely -- `matcher._in_scope`'s generic-kind branch,
which today reads `getattr(article, "structural_units", ())` -- but
deliberately leaves WHERE `article.structural_units` gets POPULATED
unspecified ("wherever an article's structural metadata is populated (parse
/ pipeline pre-stage)"). No profile method or pipeline call site for this
exists today to call by name (unlike every I7 kind, which each already has
one named call site). Inventing that call site's name/signature here would
be exactly the "invent a shape the Developer will be judged against" trap
this sprint's own rules warn against. Instead, this file proves dispatch
reaches the ACTUAL, ALREADY-NAMED consumption point
(`matcher.definition_covers_mention`, the function `pipeline.py`'s Stage 3
already calls for containment) by building the `structural_units` tuple the
same way `test_definition_links_matcher.py`'s own established convention
does for this exact branch (see that module's docstring: "kept EXACTLY
as-is for the unit-level tests... that build a SimpleNamespace stub carrying
this attribute directly") -- i.e. via a duck-typed stub object, not a real
`MatcherArticle` (which has no `.structural_units` field yet; adding it is
additive Developer work, not something a test needs to presuppose).

Where the union comes from (`registry.structural_unit_rules_for(code)` +
each matching rule's own `.derive(ctx)`, summed) is spelled out explicitly
in every test below, in place of a not-yet-named "population" call --
deliberately not hidden behind a helper, so it is legible as "this is what
UNION means for this kind," not a stand-in for a specific implementation.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.definition_links.matcher import definition_covers_mention
from app.definition_links.rules import registry

_US_CODE = "US-NM"
_IL_CODE = "IL"


def _union_structural_units(code: str, ctx: registry.StructuralContext) -> tuple:
    """Stand-in for the not-yet-named population step: union every matching
    registered `StructuralUnitRule`'s output. Mirrors the ruling's own
    wording ("UNION; registered rules ADD to that set") exactly -- this is
    the SAME operation `EntrySplitterRule`/`TermClauseRule`/`ScopeTriggerRule`
    dispatch already performs (sum every matching rule's contribution), just
    not yet wired into a named profile/pipeline call site for this kind."""
    return tuple(
        unit for rule in registry.structural_unit_rules_for(code) for unit in rule.derive(ctx)
    )


# --- Shape (M-D1): `ScopeUnit`, not `UnitPath`/`UnitStep` -------------------


def test_structural_unit_rule_derive_returns_scope_unit_tuples_us():
    """M-D1: `derive` returns `tuple[ScopeUnit, ...]` -- `ScopeUnit` does not
    exist in `registry.py` at all today (RED via `AttributeError`), distinct
    from `UnitStep`/`UnitPath` (the below-article seam, unaffected by this
    kind per v2.4 §1)."""
    ctx = registry.StructuralContext(article_number="5", heading_breadcrumbs=())
    rule = registry.StructuralUnitRule(
        jurisdiction_codes=(_US_CODE,),
        derive=lambda c: (registry.ScopeUnit(kind="part", value="II"),),
    )
    registry.register_structural_unit_rule(rule)

    result = rule.derive(ctx)
    assert result == (registry.ScopeUnit(kind="part", value="II"),)


# --- Union consumption: rules ADD, never replace ----------------------------


def test_structural_unit_rule_union_of_two_rules_neither_replaces_the_other_us():
    """"registered rules ADD to that set, never replace it" -- two
    independently-registered rules for the same code both contribute."""
    code = _US_CODE + "-UNION"  # own code, distinct from every other test's registrations
    ctx = registry.StructuralContext(article_number="7", heading_breadcrumbs=())
    registry.register_structural_unit_rule(
        registry.StructuralUnitRule(
            jurisdiction_codes=(code,),
            derive=lambda c: (registry.ScopeUnit(kind="part", value="III"),),
        )
    )
    registry.register_structural_unit_rule(
        registry.StructuralUnitRule(
            jurisdiction_codes=(code,),
            derive=lambda c: (registry.ScopeUnit(kind="subchapter", value="B"),),
        )
    )

    units = _union_structural_units(code, ctx)
    assert set(units) == {
        registry.ScopeUnit(kind="part", value="III"),
        registry.ScopeUnit(kind="subchapter", value="B"),
    }


# --- Live-path containment: matcher.definition_covers_mention --------------


def test_structural_unit_rule_dispatch_changes_containment_us():
    """The I4 dispatch proof: registering a `StructuralUnitRule` changes
    what `matcher.definition_covers_mention` (the function `pipeline.py`'s
    Stage 3 already calls) decides for a generic-kind-scoped definition --
    today, with no rule registered, `structural_units` is empty and
    containment is unconditionally False (`_in_scope`'s own documented
    default, "not contained" rather than raising)."""
    code = _US_CODE + "-CONTAIN"  # distinct sub-scope from the union test above
    ctx = registry.StructuralContext(article_number="12", heading_breadcrumbs=())
    definition = SimpleNamespace(
        scope="part", scope_value="II", source_chapter=None, source_article_number=None
    )

    before_units = _union_structural_units(code, ctx)
    article_before = SimpleNamespace(number="12", chapter="IV", structural_units=before_units)
    assert definition_covers_mention(definition, article_before, char_offset=0) is False

    registry.register_structural_unit_rule(
        registry.StructuralUnitRule(
            jurisdiction_codes=(code,),
            derive=lambda c: (registry.ScopeUnit(kind="part", value="II"),),
        )
    )

    after_units = _union_structural_units(code, ctx)
    # "core keeps stamping ScopeUnit('chapter', article.chapter) itself,
    # unconditionally" -- simulated here by prepending it to what the rule
    # contributed, proving the rule's unit ADDS alongside it rather than
    # needing to replace it.
    final_units = (registry.ScopeUnit(kind="chapter", value="IV"),) + after_units
    article_after = SimpleNamespace(number="12", chapter="IV", structural_units=final_units)
    assert definition_covers_mention(definition, article_after, char_offset=0) is True


def test_structural_unit_rule_dispatch_changes_containment_il_motivating_case():
    """Note on scope: `matcher._in_scope`'s generic-kind branch (unlike
    every I7 kind) takes no `profile`/jurisdiction argument at all -- it
    compares `article.structural_units` against `definition.scope`/
    `.scope_value` directly, so it is mechanically identical regardless of
    jurisdiction. This test does not exercise `HebrewProfile` specifically
    (there is no per-profile branch to exercise); it demonstrates the
    mechanism generalizes to IL's own motivating structural kind (`siman`,
    per M11's original "part/subchapter/siman/chelek enforcement" wording),
    not merely a US "part" example."""
    code = _IL_CODE + "-STRUCT-PROBE"  # an arbitrary jurisdiction_codes tag for THIS test only
    ctx = registry.StructuralContext(
        article_number="34", heading_breadcrumbs=((3, "סימן ב"),)
    )
    definition = SimpleNamespace(
        scope="siman", scope_value="ב", source_chapter=None, source_article_number=None
    )

    before_units = _union_structural_units(code, ctx)
    article_before = SimpleNamespace(number="34", chapter="ו", structural_units=before_units)
    assert definition_covers_mention(definition, article_before, char_offset=0) is False

    registry.register_structural_unit_rule(
        registry.StructuralUnitRule(
            jurisdiction_codes=(code,),
            derive=lambda c: (registry.ScopeUnit(kind="siman", value="ב"),),
        )
    )

    after_units = _union_structural_units(code, ctx)
    final_units = (registry.ScopeUnit(kind="chapter", value="ו"),) + after_units
    article_after = SimpleNamespace(number="34", chapter="ו", structural_units=final_units)
    assert definition_covers_mention(definition, article_after, char_offset=0) is True
