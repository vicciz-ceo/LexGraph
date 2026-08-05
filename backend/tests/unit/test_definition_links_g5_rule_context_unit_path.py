"""G5 RED tests -- `RuleContext` delivers a REAL unit path through the seam
(sprint 2026-08-05-defs-core-follow-on-2, gate G5: "RuleContext.unit_path.
No longer hardcoded (), rules receive the real unit path through the seam
instead of importing resolve_unit_path directly").

**Byte-verified finding, reported honestly (this is NOT the naive bug the
gate's one-line summary suggests).** Both hardcode sites --
`profiles.py:256` (`HebrewProfile.extract_local_scope_definitions`) and
`us_profile.py:1421` (`USProfile.extract_local_scope_definitions`) -- build
their `RuleContext` with a literal `unit_path=()`. But `resolve_unit_path`'s
OWN documented contract (`us_profile.py:1145`, v2.4 correction) is
`char_offset=None` ALWAYS returns `()` -- verified directly:

    resolve_unit_path(SimpleNamespace(body=<anything>), None) == ()

`extract_local_scope_definitions` builds its `RuleContext` ONCE, BEFORE any
rule has run, scanning the WHOLE article body -- no match offset exists yet
at that point, for any rule. So a literal `unit_path=()` and a "real"
`profile.resolve_unit_path(article, char_offset=None)` are BEHAVIORALLY
IDENTICAL in this call shape -- the hardcoded value was never factually
wrong for the field it occupies.

**The genuine gap is different: no rule can ever get a NON-empty unit path
through `ctx` at all**, because a static, pre-match `unit_path` field
structurally cannot represent "the path AT the position where THIS rule's
OWN regex match lands" -- that position isn't known until the rule itself
finds it, one call after `ctx` is built. The only way to close that gap
without inventing a second, parallel resolver mechanism a rule would have
to import directly (the exact anti-pattern the gate names) is to hand the
rule a BOUND RESOLVER it can call with ITS OWN match offset -- reusing the
SAME `resolve_unit_path` production code path plan1 (gates G2/G4) is
actively evolving, never a copy of its internals.

**Design (additive, does not touch `resolve_unit_path` internals -- plan1
safe):** `RuleContext` gains one new, defaulted field,
`resolve_unit_path: Callable[[int], UnitPath] | None = None`. At both real
construction sites, it is bound to a closure over the SAME `article_body`
string already passed to the rule, calling the profile's own
`resolve_unit_path` (`HebrewProfile`/`USProfile` respectively) -- so
`ctx.resolve_unit_path(offset)` for any `offset` is byte-identical to
calling `profile.resolve_unit_path(article, offset)` directly, with zero
duplicated logic. `unit_path` itself stays -- also no longer a bare
literal, computed via the same bound resolver at `char_offset=None` -- so
IF `resolve_unit_path`'s None-handling ever changes, `ctx.unit_path` tracks
it instead of silently going stale.

`resolve_unit_path` defaults to `None` (not made required) specifically so
`test_definition_links_rules_registry.py::
test_rule_context_carries_article_number_chapter_and_unit_path` (which
constructs a bare `RuleContext(article_number=..., chapter=...,
unit_path=(step,))` with no 4th kwarg) keeps passing UNCHANGED -- this is
additive plumbing, not a signature break.

**RED signal for both tests below:** `AttributeError: 'RuleContext' object
has no attribute 'resolve_unit_path'` -- the field does not exist on
`main` yet. This is the P-R8-shaped dispatch proof for G5: the probe rule's
own ANSWER (its candidate's `scope_value`) changes from "cannot be
computed at all" to a real, non-empty tuple, once the seam delivers a real
resolver -- proven through `profile.extract_local_scope_definitions`, the
exact method `pipeline.py:270`/`pipeline.py:264`(IL) calls, never the
registry or the rule directly.

Both fixtures were empirically run against the CURRENT, unmodified
`resolve_unit_path`/`HebrewProfile.resolve_unit_path` before being pinned
here (not guessed):

    US: resolve_unit_path(SimpleNamespace(body=body), offset)
        == (UnitStep(kind='digit', value='1'),)
    IL: HebrewProfile().resolve_unit_path(SimpleNamespace(body=body), offset)
        == (UnitStep(kind='subsection', value='א'),)

Each test's assertion compares `ctx.resolve_unit_path(offset)` against an
INDEPENDENT direct call to `profile.resolve_unit_path(article_stub, offset)`
for the SAME body+offset -- an equivalence check, not a hardcoded value --
so a future, legitimate change to the resolver's own ladder/marker logic
(plan1's G2/G4 work) can never manufacture a false failure here.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.profiles import get_profile
from app.definition_links.rules import registry

# Distinct, unused-elsewhere test codes (probe markers gate every rule
# below anyway, matching this codebase's established no-reset-between-
# tests discipline -- see test_definition_links_rule_dispatch.py's own
# module docstring for the same convention).
_US_CODE = "US-ND"
_IL_CODE = "IL"


def test_g5_rule_context_delivers_a_real_nonempty_unit_path_to_a_scope_trigger_rule_us():
    profile = get_profile(_US_CODE)
    marker = "ZZZ_G5_PROOF_US"
    body = f"(1) opening text.\n{marker} comes after marker (1)."

    def _extract(article_body: str, ctx):
        offset = article_body.find(marker)
        if offset == -1:
            return []
        path = ctx.resolve_unit_path(offset)
        return [
            DefinitionCandidate(
                terms=("Probe G5 Term US",),
                definition_text="probe def",
                scope="subsection",
                scope_value=tuple(step.value for step in path) if path else None,
            )
        ]

    registry.register_scope_trigger_rule(
        registry.ScopeTriggerRule(jurisdiction_codes=(_US_CODE,), extract=_extract)
    )

    candidates = profile.extract_local_scope_definitions(body, article_number="1")
    assert [c.terms for c in candidates] == [("Probe G5 Term US",)], (
        f"expected the probe rule's candidate to survive; got {candidates!r}"
    )
    got_scope_value = candidates[0].scope_value
    assert got_scope_value, (
        "ctx.resolve_unit_path must deliver a REAL, NON-EMPTY path when the "
        f"rule's own match genuinely follows a real marker; got {got_scope_value!r}"
    )

    # Equivalence, not a pinned literal: must match an INDEPENDENT direct
    # call to the profile's own resolve_unit_path for the SAME body+offset.
    offset = body.find(marker)
    expected_path = profile.resolve_unit_path(SimpleNamespace(body=body), offset)
    assert got_scope_value == tuple(step.value for step in expected_path), (
        f"ctx.resolve_unit_path(offset) must be byte-identical to "
        f"profile.resolve_unit_path(article, offset) for the same inputs -- "
        f"got {got_scope_value!r}, expected {tuple(s.value for s in expected_path)!r}"
    )


def test_g5_rule_context_delivers_a_real_nonempty_unit_path_to_a_scope_trigger_rule_il():
    profile = get_profile(_IL_CODE)
    marker = "ZZZ_G5_PROOF_IL"
    body = f"סעיף קטן (א) פותח.\n{marker} מופיע אחרי הסימון."

    def _extract(article_body: str, ctx):
        offset = article_body.find(marker)
        if offset == -1:
            return []
        path = ctx.resolve_unit_path(offset)
        return [
            DefinitionCandidate(
                terms=("מונח בדיקה G5",),
                definition_text="הגדרת בדיקה",
                scope="subsection",
                scope_value=tuple(step.value for step in path) if path else None,
            )
        ]

    registry.register_scope_trigger_rule(
        registry.ScopeTriggerRule(jurisdiction_codes=(_IL_CODE,), extract=_extract)
    )

    candidates = profile.extract_local_scope_definitions(body, article_number="1")
    assert [c.terms for c in candidates] == [("מונח בדיקה G5",)], (
        f"expected the probe rule's candidate to survive; got {candidates!r}"
    )
    got_scope_value = candidates[0].scope_value
    assert got_scope_value, (
        "ctx.resolve_unit_path must deliver a REAL, NON-EMPTY path when the "
        f"rule's own match genuinely follows a real marker; got {got_scope_value!r}"
    )

    offset = body.find(marker)
    expected_path = profile.resolve_unit_path(SimpleNamespace(body=body), offset)
    assert got_scope_value == tuple(step.value for step in expected_path), (
        f"ctx.resolve_unit_path(offset) must be byte-identical to "
        f"profile.resolve_unit_path(article, offset) for the same inputs -- "
        f"got {got_scope_value!r}, expected {tuple(s.value for s in expected_path)!r}"
    )


def test_g5_rule_context_unit_path_field_still_correctly_empty_for_the_whole_body_call():
    """Pins the OTHER half of the finding honestly: the static `ctx.unit_path`
    field (no offset -- the WHOLE article body scan, before any rule has
    matched anything) is CORRECTLY `()`, not a bug -- `resolve_unit_path`'s
    own contract says `char_offset=None` always returns `()` (v2.4). This
    test exists so nobody reads G5 as "make ctx.unit_path itself non-empty"
    -- that would require fabricating a position that does not exist yet.
    The real fix (proven above) is the bound resolver, not this field."""
    profile = get_profile(_US_CODE)
    marker = "ZZZ_G5_STATIC_FIELD_PROOF_US"
    body = f"(1) opening text.\n{marker} appears after a real marker too."
    seen_unit_path = []

    def _extract(article_body: str, ctx):
        if marker not in article_body:
            return []
        seen_unit_path.append(ctx.unit_path)
        return []

    registry.register_scope_trigger_rule(
        registry.ScopeTriggerRule(jurisdiction_codes=(_US_CODE,), extract=_extract)
    )

    profile.extract_local_scope_definitions(body, article_number="1")
    assert seen_unit_path == [()], (
        f"ctx.unit_path for the whole-body call must legitimately be (); "
        f"got {seen_unit_path!r}"
    )
