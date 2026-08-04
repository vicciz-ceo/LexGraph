"""I8 RED tests -- `ScopeKindRule`, the missing kind behind `determine_scope`
(sprint 2026-08-04-defs-core-dispatch, item I5/I8, manager ruling M-D2, seam
v2.6 §2 -- Planner round-trip after the ruling).

`determine_scope` maps BODY TEXT to a scope-KIND string (`"chapter"` /
`"law-wide"`). No existing registry kind fit that contract -- coercing
`ScopeTriggerRule` (a definition-CANDIDATE producer) into a boolean detector
would mis-scope definitions, which the director's scoped-definitions
constraint forbids. M-D2 adds the missing kind instead:

```python
@dataclass(frozen=True)
class ScopeKindRule:
    jurisdiction_codes: tuple[str, ...]
    detect: Callable[[str], str | None]
```

**Dispatch is baseline-first, then FIRST-non-None-wins (NOT a union)** --
the same shape as `BodyPreambleRule`: a body has exactly one scope kind, so
merging two rules' answers would be meaningless. Baseline
(`_US_CHAPTER_SCOPE_TRIGGERS` for US, the Hebrew trigger set for IL) runs
FIRST and still wins whenever it matches, protecting the 7 already-working
US states and all of IL (G4).

Consumption site: `profile.determine_scope(body_text)` -- the SAME method
`pipeline.py` already calls (`pipeline.py:221`) for the Definitions-SECTION
scope path; nothing new to thread through, this kind is purely additive to
an existing call site (unlike I4).

Motivating case (M-D2): Puerto Rico's Spanish chapter-scope phrase ("A los
fines de este Capítulo") is invisible to English baseline -- exactly the
probe shape used below.
"""

from __future__ import annotations

from app.definition_links.profiles import get_profile
from app.definition_links.rules import registry

_IL_CODE = "IL"

# Each US-side test below uses its OWN distinct real jurisdiction code
# (rather than one shared `_US_CODE`) -- `scope_kind_rules_for` has no
# reset between tests, and this file's own
# `test_scope_kind_rule_baseline_wins_when_it_already_matches_us` registers
# an UNCONDITIONAL rule (`detect=lambda b: "law-wide"`, no marker gate) that
# would otherwise leak into and silently win any later test sharing its
# code. IL-side tests safely reuse `"IL"` (the only valid code for
# `get_profile("IL")`) because each one's registered rule is gated on its
# own unique probe marker, or the test's body already makes baseline win
# outright before any registered rule is even consulted.


# --- Registration + lookup (new kind; does not exist yet) ------------------


def test_scope_kind_rule_registers_and_looks_up():
    code = "US-NM"
    rule = registry.ScopeKindRule(jurisdiction_codes=(code,), detect=lambda b: None)
    registry.register_scope_kind_rule(rule)

    assert rule in registry.scope_kind_rules_for(code)
    assert rule not in registry.scope_kind_rules_for("US-DE")
    assert rule not in registry.scope_kind_rules_for("IL")


# --- Live dispatch: registered rule changes determine_scope's answer -------


def test_scope_kind_rule_dispatch_changes_the_answer_us():
    """The PR motivating case: a Spanish chapter-scope phrase, invisible to
    English baseline (`_US_CHAPTER_SCOPE_TRIGGERS`), has nowhere to
    register into today."""
    code = "US-CO"
    profile = get_profile(code)
    body = "ZZZ_CORE_DISPATCH_SCOPE_KIND_PROBE_US A los fines de este Capitulo, algo."
    assert profile.determine_scope(body) == "law-wide"  # baseline: no English trigger phrase

    registry.register_scope_kind_rule(
        registry.ScopeKindRule(
            jurisdiction_codes=(code,),
            detect=lambda b: (
                "chapter" if "ZZZ_CORE_DISPATCH_SCOPE_KIND_PROBE_US" in b else None
            ),
        )
    )

    assert profile.determine_scope(body) == "chapter"


def test_scope_kind_rule_dispatch_changes_the_answer_il():
    """G3: the same kind must be live for `HebrewProfile` too."""
    profile = get_profile(_IL_CODE)
    body = "ZZZ_CORE_DISPATCH_SCOPE_KIND_PROBE_IL מלל בלי ביטוי הפעלה."
    assert profile.determine_scope(body) == "law-wide"  # baseline: no Hebrew trigger phrase

    registry.register_scope_kind_rule(
        registry.ScopeKindRule(
            jurisdiction_codes=(_IL_CODE,),
            detect=lambda b: (
                "chapter" if "ZZZ_CORE_DISPATCH_SCOPE_KIND_PROBE_IL" in b else None
            ),
        )
    )

    assert profile.determine_scope(body) == "chapter"


# --- Baseline-first: baseline still wins when it matches (G4 protection) ---


def test_scope_kind_rule_baseline_wins_when_it_already_matches_us():
    """A registered rule must never override a baseline positive -- this is
    what keeps the 7 already-working US states (and, symmetrically, IL)
    untouched."""
    code = "US-UT"
    profile = get_profile(code)
    body = "for purposes of this chapter, blah"
    assert profile.determine_scope(body) == "chapter"  # baseline alone, no rule yet

    registry.register_scope_kind_rule(
        registry.ScopeKindRule(jurisdiction_codes=(code,), detect=lambda b: "law-wide")
    )

    assert profile.determine_scope(body) == "chapter"  # baseline still wins


def test_scope_kind_rule_baseline_wins_when_it_already_matches_il():
    profile = get_profile(_IL_CODE)
    body = "לענין פרק זה, blah"
    assert profile.determine_scope(body) == "chapter"  # baseline alone, no rule yet

    registry.register_scope_kind_rule(
        registry.ScopeKindRule(jurisdiction_codes=(_IL_CODE,), detect=lambda b: "law-wide")
    )

    assert profile.determine_scope(body) == "chapter"  # baseline still wins


# --- First-non-None-wins ordering (NOT a union) -----------------------------


def test_scope_kind_rule_first_non_none_wins_across_two_registered_rules_us():
    """Two registered rules BOTH recognize the same probe input but return
    DIFFERENT scope kinds -- the FIRST-REGISTERED rule's answer must win,
    proving this is first-wins (like `BodyPreambleRule`), not a union
    (unioning two scope-kind strings is meaningless) and not last-wins."""
    code = "US-AZ"
    profile = get_profile(code)
    body = "ZZZ_CORE_DISPATCH_SCOPE_KIND_ORDER_PROBE_US some prose."
    assert profile.determine_scope(body) == "law-wide"  # baseline: no trigger phrase

    registry.register_scope_kind_rule(
        registry.ScopeKindRule(
            jurisdiction_codes=(code,),
            detect=lambda b: (
                "chapter" if "ZZZ_CORE_DISPATCH_SCOPE_KIND_ORDER_PROBE_US" in b else None
            ),
        )
    )
    registry.register_scope_kind_rule(
        registry.ScopeKindRule(
            jurisdiction_codes=(code,),
            detect=lambda b: (
                "law-wide" if "ZZZ_CORE_DISPATCH_SCOPE_KIND_ORDER_PROBE_US" in b else None
            ),
        )
    )

    assert profile.determine_scope(body) == "chapter"  # first-registered rule wins
