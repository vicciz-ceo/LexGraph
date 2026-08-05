"""G6 RED tests -- the scope-VALUE seam, dispatch-proof level (sprint
2026-08-05-defs-core-follow-on-2, gate G6).

**The byte-verified gap.** `ScopeKindRule.detect: Callable[[str], str | None]`
(seam v2.6 M-D2) returns a KIND STRING ONLY. `us_profile.determine_scope`/
`HebrewProfile.determine_scope` (the Definitions-SECTION scope path) has an
unconditional 2-way baseline contract (`"chapter"` / `"law-wide"`) and,
critically, `pipeline.py`'s OWN stamping line --

    candidate.source_chapter = art.chapter if scope == "chapter" else None

-- NEVER reads anything from a registered rule for the VALUE; it always
uses the CURRENT article's OWN chapter. Confirmed directly against the
headings panel's own escalation (`claude/defs-us-headings-plan5@8cd3829`,
`test_definition_links_us_heading_variants_cycle5_scope_parse.py`'s module
docstring): "even a `ScopeKindRule` returning `'local'` would still need
`pipeline.py` ... to know how to fill `source_article_number` with more
than 'this article's own number' for the enumerated case." That is exactly
right, and it is what this seam closes.

**Design (append-only, additive -- zero existing consumers to break,
verified: no branch in this repo registers a real `ScopeKindRule` instance
today, `git grep register_scope_kind_rule` across every remote branch's
`rules/*.py` returns nothing outside `registry.py` itself):**

1. `ScopeKindRule` gains one new, defaulted field:
   `detect_value: Callable[[str], "ScopeAssignment | tuple[ScopeAssignment, ...] | None"] | None = None`.
   `None` (the default) is exactly today's behavior -- no existing
   `ScopeKindRule(...)` construction anywhere supplies this field.
2. New frozen dataclass `ScopeAssignment(kind: str, value: str | tuple[str, ...] | None)`.
3. New `JurisdictionProfile` method,
   `determine_scope_assignments(self, body_text, *, scope, article_number, chapter) -> tuple[ScopeAssignment, ...]`
   -- ADDITIVE, does not change `determine_scope`'s own signature/contract
   at all. Re-runs the EXACT SAME baseline-first, first-non-None-wins
   dispatch `determine_scope` already performs (so "the winning rule" is
   always identical between the two methods, by construction -- no drift
   possible), then asks THAT SAME rule's `detect_value` for an override.
   Default (no override anywhere): `ScopeAssignment(kind="chapter",
   value=chapter)` for `scope=="chapter"`, `ScopeAssignment(kind="local",
   value=article_number)` for `scope=="local"`, `ScopeAssignment(kind=scope,
   value=None)` otherwise -- always the article's OWN narrow, self-
   referential identity, NEVER a broadening default (M9's own standing
   rule: a wrong-but-wider scope manufactures false assertions across
   every other unit of the law).
4. `pipeline.py`'s Definitions-SECTION stamping loop calls this new method
   and FANS OUT one `DefinitionCandidate` copy per returned
   `ScopeAssignment` (1 assignment in the overwhelming common case --
   byte-identical to today; >1 only for a body naming more than one
   co-equal scope, e.g. TN's "as used in this part and Section 6-51-301" --
   resolved by the ALREADY-SHIPPED, ALREADY-NAMED M10 tie-class ("both
   survive, both get an assertion"), not a new resolution mechanism).

**This file proves the DISPATCH shape (P-R8): a probe rule's own ANSWER
changes `determine_scope_assignments`'s real output**, called the same way
`pipeline.py` will call it -- never the registry, never the rule directly.
The ONE full live-path proof (real KY corpus text, through
`run_definition_linking`, to a real `USES_DEFINITION` assertion) is in
`backend/tests/integration/test_definition_links_g6_scope_value_seam_live.py`.

**RED signal for every test below:** `AttributeError` -- `ScopeAssignment`
does not exist on `registry` yet, and `determine_scope_assignments` does
not exist on either profile yet.
"""

from __future__ import annotations

from app.definition_links.profiles import get_profile
from app.definition_links.rules import registry

_US_CODE = "US-SD"
_IL_CODE = "IL"


def test_g6_determine_scope_assignments_default_matches_todays_chapter_stamping_us():
    """No registered rule at all (or none fires): the default assignment
    for scope=="chapter" must be exactly `art.chapter` -- byte-identical to
    today's `candidate.source_chapter = art.chapter if scope == "chapter"
    else None` pipeline.py line. Uses a body/code combination no other test
    in this file registers a rule for, so baseline-only behavior is
    genuinely exercised."""
    profile = get_profile("US-SD")
    assignments = profile.determine_scope_assignments(
        "plain law-wide body, no chapter trigger, no registered rule",
        scope="law-wide",
        article_number="9",
        chapter="4",
    )
    assert assignments == (registry.ScopeAssignment(kind="law-wide", value=None),)


def test_g6_scope_kind_rule_detect_value_overrides_the_chapter_value_with_an_enumerated_tuple_us():
    """AK-shaped proof: a probe `ScopeKindRule` detects "chapter" scope AND
    supplies a NINE-member enumerated chapter tuple as the VALUE -- the
    exact shape AK's real multi-chapter range needs (real chapter
    membership `13.06, 13.12, 13.16, 13.21, 13.26, 13.27, 13.28, 13.33,
    13.36`, manager-measured, `defs-us-headings-log.md` 2026-08-04 'U2
    gap' entry)."""
    profile = get_profile(_US_CODE)
    marker = "ZZZ_G6_CHAPTER_TUPLE_PROOF_US"
    ak_chapters = ("13.06", "13.12", "13.16", "13.21", "13.26", "13.27", "13.28", "13.33", "13.36")

    def _detect(body_text: str):
        return "chapter" if marker in body_text else None

    def _detect_value(body_text: str):
        return registry.ScopeAssignment(kind="chapter", value=ak_chapters)

    registry.register_scope_kind_rule(
        registry.ScopeKindRule(
            jurisdiction_codes=(_US_CODE,), detect=_detect, detect_value=_detect_value
        )
    )

    body = f"{marker} General definitions for AS 13.06 -- AS 13.36."
    scope = profile.determine_scope(body)
    assert scope == "chapter", f"precondition: probe rule must win the KIND dispatch; got {scope!r}"

    assignments = profile.determine_scope_assignments(
        body, scope=scope, article_number="13.06.050", chapter="13.06"
    )
    assert assignments == (registry.ScopeAssignment(kind="chapter", value=ak_chapters),), (
        f"expected the probe's 9-member chapter tuple to override the "
        f"article's own single chapter ('13.06'); got {assignments!r}"
    )


def test_g6_scope_kind_rule_detect_value_overrides_the_local_value_with_an_enumerated_tuple_il():
    """KY-156.106-shaped proof, IL side: a probe `ScopeKindRule` detects
    "local" scope AND supplies a two-member enumerated article tuple (the
    definition's own article PLUS one named cross-reference) -- exactly
    what `determine_scope`'s 2-way `"chapter"`/`"law-wide"` contract has no
    slot for at all today (`"local"` is not a legal `determine_scope`
    output on `main`)."""
    profile = get_profile(_IL_CODE)
    marker = "ZZZ_G6_LOCAL_TUPLE_PROOF_IL"

    def _detect(body_text: str):
        return "local" if marker in body_text else None

    def _detect_value(body_text: str):
        return registry.ScopeAssignment(kind="local", value=("34", "40"))

    registry.register_scope_kind_rule(
        registry.ScopeKindRule(
            jurisdiction_codes=(_IL_CODE,), detect=_detect, detect_value=_detect_value
        )
    )

    body = f"{marker} לענין סעיף זה וסעיף 40."
    scope = profile.determine_scope(body)
    assert scope == "local", f"precondition: probe rule must win the KIND dispatch; got {scope!r}"

    assignments = profile.determine_scope_assignments(
        body, scope=scope, article_number="34", chapter=None
    )
    assert assignments == (registry.ScopeAssignment(kind="local", value=("34", "40")),), (
        f"expected the probe's 2-member article tuple to override the "
        f"article's own bare number ('34'); got {assignments!r}"
    )


def test_g6_scope_kind_rule_declining_a_value_falls_back_to_the_narrow_default_never_broadens():
    """A rule may win the KIND dispatch (`detect` returns non-None) but
    decline to supply a value (`detect_value` is `None`, or returns
    `None`) -- the fallback MUST be the article's own narrow,
    self-referential identity (this article's own chapter), never
    `"law-wide"` or any other broadening default. M9's own standing rule:
    a silently-broadening fallback is a false-positive generator, never an
    acceptable default."""
    profile = get_profile(_US_CODE)
    marker = "ZZZ_G6_DECLINE_PROOF_US"

    def _detect(body_text: str):
        return "chapter" if marker in body_text else None

    registry.register_scope_kind_rule(
        registry.ScopeKindRule(jurisdiction_codes=(_US_CODE,), detect=_detect, detect_value=None)
    )

    body = f"{marker} some chapter-scoped body with no parseable enumeration."
    scope = profile.determine_scope(body)
    assert scope == "chapter", f"precondition: probe rule must win the KIND dispatch; got {scope!r}"

    assignments = profile.determine_scope_assignments(
        body, scope=scope, article_number="7", chapter="3"
    )
    assert assignments == (registry.ScopeAssignment(kind="chapter", value="3"),), (
        f"a rule declining to supply a value must fall back to the article's "
        f"OWN chapter ('3'), never a broadened default; got {assignments!r}"
    )


def test_g6_scope_kind_rule_can_supply_two_coequal_assignments_tn_dual_scope_shaped():
    """TN-shaped proof: `STATE_TN_T6_C51_S6-51-101`'s real body ("As used
    in this part and Section 6-51-301, unless the context otherwise
    requires: (1) 'Larger' and 'smaller' ...") declares TWO co-equal
    scopes for the SAME set of terms simultaneously -- a "part"-level
    container scope AND a specific named "local" cross-reference. One
    `DefinitionCandidate` has exactly one `.scope`, so this needs the
    seam's multi-assignment fan-out: `detect_value` may return a TUPLE of
    `ScopeAssignment`s, not just one. `pipeline.py` fans this out into TWO
    `DefinitionCandidate` copies (one per assignment) -- resolved by the
    ALREADY-SHIPPED M10 tie-class (both survive, both get an assertion),
    not a new mechanism this Planner invented."""
    profile = get_profile(_US_CODE)
    marker = "ZZZ_G6_DUAL_SCOPE_PROOF_US"

    def _detect(body_text: str):
        return "part" if marker in body_text else None

    def _detect_value(body_text: str):
        return (
            registry.ScopeAssignment(kind="part", value="6"),
            registry.ScopeAssignment(kind="local", value="6-51-301"),
        )

    registry.register_scope_kind_rule(
        registry.ScopeKindRule(
            jurisdiction_codes=(_US_CODE,), detect=_detect, detect_value=_detect_value
        )
    )

    body = f"{marker} As used in this part and Section 6-51-301, unless the context otherwise requires:"
    scope = profile.determine_scope(body)
    assert scope == "part", f"precondition: probe rule must win the KIND dispatch; got {scope!r}"

    assignments = profile.determine_scope_assignments(
        body, scope=scope, article_number="6-51-101", chapter="51"
    )
    assert assignments == (
        registry.ScopeAssignment(kind="part", value="6"),
        registry.ScopeAssignment(kind="local", value="6-51-301"),
    ), f"expected BOTH co-equal assignments to survive, unchanged; got {assignments!r}"
