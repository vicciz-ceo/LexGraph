"""Per-kind LIVE-PATH dispatch tests for the rule registry (sprint
2026-08-04-defs-core-dispatch, item I7 -- the centerpiece of this sprint,
program ruling P-R8).

**Why this file exists.** The previous sprint's own gate C4 ("the rule
registry itself, working end-to-end") was proven live using ONE rule kind
(`ScopeTriggerRule`) and that single-kind proof was silently generalized to
all seven kinds. It was false: `HeadingRule`, `BodyPreambleRule`,
`EntrySplitterRule`, `TermClauseRule` register and look up correctly but are
consumed by NOTHING in `backend/app` (verified independently by two family
panels with positive-control probes -- `claude/defs-us-pr@5b177b7`,
`claude/defs-us-headings@341fb50` -- and by this sprint's own manager).
`test_definition_links_rules_registry.py` (the registry's own test file)
only asserts registration + lookup; it never asserts that a registered rule
changes a profile's ANSWER. That is the exact gap this file closes,
permanently: every test below registers a probe rule, then calls **the
profile method `pipeline.py` actually calls** (never the registry, never the
rule directly) and asserts the OUTPUT changes.

**What "live" means here, precisely:** calling `get_profile(code)` (the same
entry point `pipeline.py` uses), calling the SAME method `pipeline.py`
calls at its own Stage-2/3 call sites
(`is_definitions_heading` -- pipeline.py:198/216; `derive_heading_from_body`
-- pipeline.py:215; `extract_definitions_from_section` -- pipeline.py:222;
`extract_local_scope_definitions` -- pipeline.py:229; `find_citations`,
reached transitively via `detect_cross_law_derivations`'s citation grammar
and directly by `USProfile.find_citations`/`HebrewProfile.find_citations`),
with a BASELINE input the profile's own unregistered logic already proves
returns nothing/False/None -- then registering a probe rule and asserting
the SAME call now returns something the probe rule alone could have
produced. No test in this file calls `registry.*_rules_for(...)` or a rule's
own callable directly -- that would only prove registration+lookup, exactly
the insufficient proof this file exists to stop being mistaken for a live
path proof.

**Coverage matrix (G3: both `USProfile` and `HebrewProfile` surfaces).**
Six of the seven registry kinds are covered below, each with one US test and
one IL test (12 tests total), plus two additional tests for I6
(`HeadingRule.body_confirms`):

| Kind               | Consumption site (pipeline.py call)      | Expected today |
|--------------------|-------------------------------------------|-----------------|
| `HeadingRule`       | `is_definitions_heading` (I1, I6)         | DEAD            |
| `BodyPreambleRule`  | `derive_heading_from_body` (I2)           | DEAD            |
| `EntrySplitterRule` | `extract_definitions_from_section` (I3)   | DEAD            |
| `TermClauseRule`    | `extract_definitions_from_section` (I3)   | DEAD            |
| `ScopeTriggerRule`  | `extract_local_scope_definitions`         | **LIVE**        |
| `CitationRule`      | `find_citations`                          | **LIVE**        |

`ScopeTriggerRule`/`CitationRule` are expected GREEN on arrival -- they are
the permanent regression guard (a future edit that silently un-wires their
dispatch must turn these RED) AND they validate the probe TECHNIQUE itself:
if these two also came back RED, the harness would be broken, not the
production code (see the Planner's report for the mutation-proof that
confirms these are genuinely green, not vacuously so).

**Held, not tested here (escalated to the sprint manager, not guessed at):**
`StructuralUnitRule` (I4) and a `determine_scope` (I5) rule seam. Both have a
genuine, unresolved shape ambiguity in the published seam spec -- see the
Planner's report for the exact passages and options. Per this sprint's own
rule ("do not resolve it by inventing a shape the Developer will then be
judged against"), no test below assumes a consumption shape for either.

**Probe-string discipline:** every probe uses a `ZZZ_CORE_DISPATCH_...`
marker unique to its own test, so a registered probe rule can never
accidentally fire against another test's input (the registry has no
reset/teardown between tests -- registrations accumulate for the whole
pytest session, matching this codebase's existing convention in
`test_definition_links_rules_registry.py`).
"""

from __future__ import annotations

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.profiles import get_profile
from app.definition_links.rules import registry

_US_CODE = "US-MT"
_IL_CODE = "IL"


# --- HeadingRule (I1) ------------------------------------------------------
#
# Consumption site: `profile.is_definitions_heading(heading, body)` --
# `pipeline.py:198`/`:216`. `body` is a NEW positional parameter (I6,
# `body_confirms`); every call below passes it explicitly, which is itself
# part of the RED signal today (`is_definitions_heading` currently takes
# only `heading`).


def test_heading_rule_dispatch_changes_the_answer_us():
    """I1/I7 -- US: a registered `HeadingRule` fires only after the
    profile's own baseline detector has already returned False for a
    heading it doesn't recognize."""
    profile = get_profile(_US_CODE)
    heading = "ZZZ_CORE_DISPATCH_HEADING_PROBE_US"
    assert profile.is_definitions_heading(heading, "") is False  # baseline: no "Definitions" word

    registry.register_heading_rule(
        registry.HeadingRule(jurisdiction_codes=(_US_CODE,), matches=lambda h: h == heading)
    )

    assert profile.is_definitions_heading(heading, "") is True


def test_heading_rule_dispatch_changes_the_answer_il():
    """I1/I7 -- IL (G3): the same kind must be live for `HebrewProfile`
    too, or a family panel building an IL `HeadingRule` would silently ship
    dead code."""
    profile = get_profile(_IL_CODE)
    heading = "ZZZ_CORE_DISPATCH_HEADING_PROBE_IL"
    assert profile.is_definitions_heading(heading, "") is False  # baseline: not a Hebrew הגדרות form

    registry.register_heading_rule(
        registry.HeadingRule(jurisdiction_codes=(_IL_CODE,), matches=lambda h: h == heading)
    )

    assert profile.is_definitions_heading(heading, "") is True


# --- I6: additive `HeadingRule.body_confirms` -------------------------------


def test_heading_rule_without_body_confirms_field_stays_backward_compatible():
    """I6 -- pin HALF: every `HeadingRule` written before this sprint (no
    `body_confirms` kwarg at all, e.g. every rule already registered by
    `test_definition_links_rules_registry.py`) keeps dispatching exactly as
    before, regardless of what `body` holds. This is the same shape as
    `test_heading_rule_dispatch_changes_the_answer_us` above but stated as
    its own explicit pin per the sprint's "Pin BOTH" instruction, and
    exercised with two DIFFERENT bodies to prove `body`'s content plays no
    role when `body_confirms` is absent."""
    profile = get_profile(_US_CODE)
    heading = "ZZZ_CORE_DISPATCH_HEADING_PROBE_US_NOBC"

    registry.register_heading_rule(
        registry.HeadingRule(jurisdiction_codes=(_US_CODE,), matches=lambda h: h == heading)
    )

    assert profile.is_definitions_heading(heading, "any body at all") is True
    assert profile.is_definitions_heading(heading, "") is True


def test_heading_rule_body_confirms_suppresses_an_otherwise_matching_heading():
    """I6 -- pin the OTHER half: `matches(heading) and (body_confirms is
    None or body_confirms(body))`. A `body_confirms` that returns False
    suppresses an otherwise-matching heading; the SAME rule fires once the
    body satisfies it."""
    profile = get_profile(_US_CODE)
    heading = "ZZZ_CORE_DISPATCH_HEADING_PROBE_US_BC"

    registry.register_heading_rule(
        registry.HeadingRule(
            jurisdiction_codes=(_US_CODE,),
            matches=lambda h: h == heading,
            body_confirms=lambda b: "ZZZ_CONFIRM_TOKEN" in b,
        )
    )

    assert profile.is_definitions_heading(heading, "no confirming token in this body") is False
    assert profile.is_definitions_heading(heading, "body carries ZZZ_CONFIRM_TOKEN here") is True


# --- BodyPreambleRule (I2) --------------------------------------------------
#
# Consumption site: `profile.derive_heading_from_body(heading, body)` --
# pipeline.py:215. `heading` is deliberately NOT a placeholder heading
# below, so today's code (`if not _is_placeholder_heading(heading): return
# None`) early-returns before ever trying a registered rule -- exactly the
# bug I2 exists to fix (seam v2 M6: registered rules are ALWAYS tried next
# once baseline yields nothing, including when the heading isn't a
# placeholder).


def test_body_preamble_rule_dispatch_changes_the_answer_us():
    profile = get_profile(_US_CODE)
    heading = "Ordinary Heading That Is Not A Placeholder"
    body = "ZZZ_CORE_DISPATCH_PREAMBLE_PROBE_US some filler prose."
    assert profile.derive_heading_from_body(heading, body) is None  # baseline: gate blocks it

    registry.register_body_preamble_rule(
        registry.BodyPreambleRule(
            jurisdiction_codes=(_US_CODE,),
            derive_heading=lambda b: (
                "Probe Definitions" if "ZZZ_CORE_DISPATCH_PREAMBLE_PROBE_US" in b else None
            ),
        )
    )

    assert profile.derive_heading_from_body(heading, body) == "Probe Definitions"


def test_body_preamble_rule_dispatch_changes_the_answer_il():
    """G3: `HebrewProfile.derive_heading_from_body` is unconditionally
    `None` today (documented as "IL has no placeholder-heading concept" --
    a true fact about baseline, not a reason the seam itself should stay
    unreachable). A family panel building IL-specific body-derived-heading
    coverage needs this seam live too."""
    profile = get_profile(_IL_CODE)
    heading = "כותרת רגילה"
    body = "ZZZ_CORE_DISPATCH_PREAMBLE_PROBE_IL מלל בדיקה."
    assert profile.derive_heading_from_body(heading, body) is None  # baseline: always None for IL

    registry.register_body_preamble_rule(
        registry.BodyPreambleRule(
            jurisdiction_codes=(_IL_CODE,),
            derive_heading=lambda b: (
                "הגדרות בדיקה" if "ZZZ_CORE_DISPATCH_PREAMBLE_PROBE_IL" in b else None
            ),
        )
    )

    assert profile.derive_heading_from_body(heading, body) == "הגדרות בדיקה"


# --- EntrySplitterRule (I3, union kind) -------------------------------------
#
# Consumption site: `profile.extract_definitions_from_section(text,
# scope=...)` -- pipeline.py:222. Baseline input below has NO recognizable
# entry markers at all (no "(N)"-style chain for US, no ":-" for IL), so
# baseline's own splitter produces zero blocks and therefore zero
# candidates. A registered `EntrySplitterRule` contributes an ADDITIONAL raw
# block (a quoted-term entry, the SAME shape baseline already knows how to
# turn into a candidate) that baseline's splitter alone could never produce
# from this input.


def test_entry_splitter_rule_dispatch_changes_the_answer_us():
    profile = get_profile(_US_CODE)
    text = "ZZZ_CORE_DISPATCH_ENTRY_SPLIT_PROBE_US some prose with no parenthesized markers at all."
    assert profile.extract_definitions_from_section(text, scope="law-wide") == []

    registry.register_entry_splitter_rule(
        registry.EntrySplitterRule(
            jurisdiction_codes=(_US_CODE,),
            split=lambda t: (
                ['"Probe Split Term US" means a probe definition text.']
                if "ZZZ_CORE_DISPATCH_ENTRY_SPLIT_PROBE_US" in t
                else []
            ),
        )
    )

    candidates = profile.extract_definitions_from_section(text, scope="law-wide")
    assert [c.terms for c in candidates] == [("Probe Split Term US",)]


def test_entry_splitter_rule_dispatch_changes_the_answer_il():
    profile = get_profile(_IL_CODE)
    text = "ZZZ_CORE_DISPATCH_ENTRY_SPLIT_PROBE_IL מלל בלי סימוני כניסה."
    assert profile.extract_definitions_from_section(text, scope="law-wide") == []

    registry.register_entry_splitter_rule(
        registry.EntrySplitterRule(
            jurisdiction_codes=(_IL_CODE,),
            split=lambda t: (
                [':- "מונח בדיקה IL" - הגדרת בדיקה.']
                if "ZZZ_CORE_DISPATCH_ENTRY_SPLIT_PROBE_IL" in t
                else []
            ),
        )
    )

    candidates = profile.extract_definitions_from_section(text, scope="law-wide")
    assert [c.terms for c in candidates] == [("מונח בדיקה IL",)]


# --- TermClauseRule (I3, union kind) ----------------------------------------
#
# Consumption site: same as `EntrySplitterRule` above. Baseline input below
# DOES produce one entry BLOCK (a bare digit marker for US / a `:-` marker
# for IL -- both unconditional block boundaries in baseline's own splitter),
# but that block's content does not match baseline's own leading-quote
# term-parsing rule, so baseline turns it into zero candidates. A registered
# `TermClauseRule.parse` recognizes a DIFFERENT pattern inside that same
# block and contributes a candidate baseline's own per-block parsing could
# never produce.


def test_term_clause_rule_dispatch_changes_the_answer_us():
    profile = get_profile(_US_CODE)
    # A bare "(1)" marker unconditionally starts a new block in baseline's
    # own splitter (see us_profile.py's `_BARE_DIGIT_MARKER_RE` -- this is
    # the ORIGINAL, unconditional entry-boundary rule); the block's own
    # text has no leading quote, so baseline's block->candidate parsing
    # yields nothing for it.
    text = "(1) ZZZ_CORE_DISPATCH_TERM_CLAUSE_PROBE_US some text with no leading quote."
    assert profile.extract_definitions_from_section(text, scope="law-wide") == []

    registry.register_term_clause_rule(
        registry.TermClauseRule(
            jurisdiction_codes=(_US_CODE,),
            parse=lambda block: (
                [
                    DefinitionCandidate(
                        terms=("Probe Clause Term US",),
                        definition_text="probe clause definition",
                        scope="law-wide",
                    )
                ]
                if "ZZZ_CORE_DISPATCH_TERM_CLAUSE_PROBE_US" in block
                else []
            ),
        )
    )

    candidates = profile.extract_definitions_from_section(text, scope="law-wide")
    assert [c.terms for c in candidates] == [("Probe Clause Term US",)]


def test_term_clause_rule_dispatch_changes_the_answer_il():
    profile = get_profile(_IL_CODE)
    # ":-" unconditionally starts a new block in baseline's own splitter;
    # this block has no standalone "-" outside quotes, so baseline's own
    # `_find_split_dash`-based parsing yields nothing for it.
    text = ":- ZZZ_CORE_DISPATCH_TERM_CLAUSE_PROBE_IL מלל בלי מקף חלוקה."
    assert profile.extract_definitions_from_section(text, scope="law-wide") == []

    registry.register_term_clause_rule(
        registry.TermClauseRule(
            jurisdiction_codes=(_IL_CODE,),
            parse=lambda block: (
                [
                    DefinitionCandidate(
                        terms=("מונח סעיף בדיקה",),
                        definition_text="הגדרת בדיקה",
                        scope="law-wide",
                    )
                ]
                if "ZZZ_CORE_DISPATCH_TERM_CLAUSE_PROBE_IL" in block
                else []
            ),
        )
    )

    candidates = profile.extract_definitions_from_section(text, scope="law-wide")
    assert [c.terms for c in candidates] == [("מונח סעיף בדיקה",)]


# --- ScopeTriggerRule -- expected LIVE ON ARRIVAL ---------------------------
#
# Consumption site: `profile.extract_local_scope_definitions(article_body,
# article_number=..., chapter=...)` -- pipeline.py:229. Already wired for
# both profiles (`rules/us_scope_trigger_proof.py`,
# `rules/il_scope_triggers.py`). This is one of the program's two positive
# controls (the OTHER kind that already worked is exactly what let the
# five-kind gap go unnoticed for two QA cycles) -- kept here, GREEN, as the
# permanent regression guard. See the Planner's report for the mutation
# proof that this green is genuine.


def test_scope_trigger_rule_dispatch_changes_the_answer_us():
    profile = get_profile(_US_CODE)
    body = "ZZZ_CORE_DISPATCH_SCOPE_TRIGGER_PROBE_US marker, no baseline trigger phrase present."
    assert profile.extract_local_scope_definitions(body, article_number="1") == []

    registry.register_scope_trigger_rule(
        registry.ScopeTriggerRule(
            jurisdiction_codes=(_US_CODE,),
            extract=lambda b, ctx: (
                [
                    DefinitionCandidate(
                        terms=("Probe Scope Term US",), definition_text="probe def", scope="local"
                    )
                ]
                if "ZZZ_CORE_DISPATCH_SCOPE_TRIGGER_PROBE_US" in b
                else []
            ),
        )
    )

    candidates = profile.extract_local_scope_definitions(body, article_number="1")
    assert [c.terms for c in candidates] == [("Probe Scope Term US",)]


def test_scope_trigger_rule_dispatch_changes_the_answer_il():
    profile = get_profile(_IL_CODE)
    body = "ZZZ_CORE_DISPATCH_SCOPE_TRIGGER_PROBE_IL מלל בלי ביטוי הפעלה."
    assert profile.extract_local_scope_definitions(body, article_number="1") == []

    registry.register_scope_trigger_rule(
        registry.ScopeTriggerRule(
            jurisdiction_codes=(_IL_CODE,),
            extract=lambda b, ctx: (
                [
                    DefinitionCandidate(
                        terms=("מונח היקף בדיקה IL",), definition_text="probe def", scope="local"
                    )
                ]
                if "ZZZ_CORE_DISPATCH_SCOPE_TRIGGER_PROBE_IL" in b
                else []
            ),
        )
    )

    candidates = profile.extract_local_scope_definitions(body, article_number="1")
    assert [c.terms for c in candidates] == [("מונח היקף בדיקה IL",)]


# --- CitationRule -- expected LIVE ON ARRIVAL -------------------------------
#
# Consumption site: `profile.find_citations(text)`. Wired for both profiles
# already (`USProfile.find_citations` unions `citation_rules_for`;
# `HebrewProfile.find_citations` -- trivially `[]` at baseline, C5-safe --
# does the same). The program's OTHER positive control; kept here, GREEN,
# as the permanent regression guard.


def test_citation_rule_dispatch_changes_the_answer_us():
    profile = get_profile(_US_CODE)
    text = "see ZZZ_CORE_DISPATCH_CITATION_PROBE_US 42 for details"
    assert profile.find_citations(text) == []

    registry.register_citation_rule(
        registry.CitationRule(
            jurisdiction_codes=(_US_CODE,),
            find=lambda t: (
                ["ZZZ_CORE_DISPATCH_CITATION_PROBE_US 42"]
                if "ZZZ_CORE_DISPATCH_CITATION_PROBE_US" in t
                else []
            ),
        )
    )

    assert profile.find_citations(text) == ["ZZZ_CORE_DISPATCH_CITATION_PROBE_US 42"]


def test_citation_rule_dispatch_changes_the_answer_il():
    profile = get_profile(_IL_CODE)
    text = "ראו ZZZ_CORE_DISPATCH_CITATION_PROBE_IL 7 לפרטים"
    assert profile.find_citations(text) == []

    registry.register_citation_rule(
        registry.CitationRule(
            jurisdiction_codes=(_IL_CODE,),
            find=lambda t: (
                ["ZZZ_CORE_DISPATCH_CITATION_PROBE_IL 7"]
                if "ZZZ_CORE_DISPATCH_CITATION_PROBE_IL" in t
                else []
            ),
        )
    )

    assert profile.find_citations(text) == ["ZZZ_CORE_DISPATCH_CITATION_PROBE_IL 7"]
