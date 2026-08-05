"""G10 RED tests -- `TermClauseRule.parse` receives the section's REAL
determined scope (sprint 2026-08-05-defs-core-follow-on-2, gate G10:
"TermClauseRule scope threading", seam v2.9).

**The defect, proven from source (byte-read, not inferred):**

    backend/app/definition_links/rules/registry.py:139-145
    class TermClauseRule:
        jurisdiction_codes: tuple[str, ...]
        parse: Callable[[str], list[DefinitionCandidate]]   # <-- block ONLY

    backend/app/definition_links/us_profile.py:1450-1452 (USProfile)
    backend/app/definition_links/profiles.py:220-221 (HebrewProfile)
        for rule in registry.term_clause_rules_for(self.code):
            candidates.extend(rule.parse(block))            # <-- scope NOT passed

    backend/app/definition_links/us_profile.py:1422-1423
        def extract_definitions_from_section(self, text, *, scope, ...)
                                                              # <-- scope EXISTS
                                                              #     here and is
                                                              #     dropped two
                                                              #     lines below
                                                              #     baseline's OWN
                                                              #     correct use of
                                                              #     it, `_leading_
                                                              #     quote_candidate
                                                              #     (block, scope=
                                                              #     scope)`.

This is program-wide (`registry.py` serves BOTH `USProfile` and
`HebrewProfile` -- profiles.py:220-221 has the byte-identical shape), and
was independently found and escalated by the multiterm family panel
(`claude/defs-us-multiterm`, QA ruling M-R15, `docs/sprint/sprints/
2026-08-04-defs-us-multiterm-log.md` line ~2957): their real, working
`TermClauseRule` module (`rules/us_multiterm_shared_clause.py::
_leading_multiterm_candidate`) is FORCED to hardcode `scope="law-wide"`
because, verified by direct read of that branch, the seam offers no
alternative. QA there confirmed the SEVERE consequence live, on a real
row: `STATE_IN_T4_A3_C9_S4-3-9-1` ("Title"/"interest in land", Ind. Code
Section 4-3-9-1, chapter "9") -- a chapter-scoped definition stamped
`"law-wide"` is not merely imprecise, it is a false-positive generator
across the ENTIRE law (seam v2.1/M9's own standing principle) AND, per
the "narrowest governs" ranking (v2.2 Section 3), lets a WRONG, degenerate
baseline candidate silently win the in-chapter case too (M10's already-
published rank comparison: chapter, depth 1, beats law-wide, depth 0,
outright -- no tie, no signal that anything is wrong).

**Why this is dormant on `main`/this branch today, not already visibly
broken (P-R10):** verified by `grep -rn register_term_clause_rule
app/definition_links/rules/*.py` (excluding registry.py itself) --
ZERO real rule modules registered here. `registry.term_clause_rules_for`
returns `[]` for every code, so the buggy dispatch line never executes a
loop body in production on this branch; the bug is fully latent until the
FIRST family panel's `TermClauseRule` (multiterm's, or any of the three
other panels blocked on this gate) merges -- exactly why the panel
manager accepted this gate as "unblocks correctness for FOUR panels."

**Vendored fixture, byte-verified this session** (not read from the
corpus by any committed test -- P-R8/corpus discipline): `_IN_SECTION_
TEXT` below is character-for-character the real `text` column of
`act_id="STATE_IN_T4_A3_C9_S4-3-9-1"` in `us_in_statutes.parquet`
(`/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/
snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/`), confirmed via a
direct `pyarrow.parquet.read_table` read this session (`repr()` diffed
byte-for-byte against the literal below); `chapter="9"` likewise read
from that row's own `chapter` column.

**Design under test (seam v2.9, see the seam doc for the full writeup):**
`TermClauseRule` gains ONE new, OPTIONAL, defaulted-`None` companion
callable field, `parse_scoped: Callable[[str, TermClauseContext],
list[DefinitionCandidate]] | None = None` -- the SAME "additive companion
field, dispatched instead of the original when present" convention v2.8
established for `ScopeKindRule.detect_value` alongside `detect`.
`TermClauseContext` is a new one-field frozen dataclass (`scope: str`),
following the same "context object, not a bare positional, so a future
field never forces a second signature break" reasoning that produced
`RuleContext`/`StructuralContext` (M5/M11) -- composing with, not
duplicating, G5's own established convention. Dispatch (both
`us_profile.py` and `profiles.py`, mirrored):

    for rule in registry.term_clause_rules_for(self.code):
        if rule.parse_scoped is not None:
            candidates.extend(rule.parse_scoped(block, registry.TermClauseContext(scope=scope)))
        else:
            candidates.extend(rule.parse(block))

`parse` stays REQUIRED and untouched -- every existing `TermClauseRule(
jurisdiction_codes=..., parse=<fn>)` construction (including the real,
currently-unmerged multiterm/PR/headings/preamble panel modules) keeps
dispatching via `parse(block)` exactly as today, unconditionally, with
zero edits.

**None of the tests below construct `registry.TermClauseContext` or
import it** -- deliberately, mirroring `test_definition_links_g5_rule_
context_unit_path.py`'s own convention: the probe callables below accept
`ctx` as an opaque second positional argument and read `ctx.scope`,
exactly as a real rule module would: the PRODUCTION dispatcher is what
must construct and pass it. This is what makes the RED a live-path
dispatch proof (P-R8) rather than a registry-shape unit test -- the only
call this file makes is `profile.extract_definitions_from_section(...)`,
the exact method `pipeline.py` calls at its own Stage-2 site
(`us_profile.py`/`profiles.py`, `pipeline.py:262-268`), never the
registry or a rule directly.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.matcher import link_articles_to_definitions
from app.definition_links.profiles import get_profile
from app.definition_links.rules import registry
from app.definition_links.us_profile import determine_scope

# Distinct, unused-elsewhere test codes (probe markers gate every rule
# below anyway -- this codebase's established no-reset-between-tests
# discipline, see test_definition_links_rule_dispatch.py's own module
# docstring for the same convention). US-IN doubles as the real
# jurisdiction of the vendored fixture below; the "before" test and the
# centerpiece RED test both register a `TermClauseRule` that fires on the
# SAME real block's identical trigger phrase ('"Title" and "interest in
# land" means') -- since TermClauseRule is a UNION kind (every matching
# rule's candidates are kept, module-level registry never reset between
# tests), giving them the SAME exact jurisdiction code would let BOTH
# probes fire on the SAME call and produce two candidates instead of one.
# `_US_CODE_RED` is a second, distinct exact code (not "US-*", so it never
# collides via the wildcard) used ONLY by the centerpiece RED test, purely
# for this test-isolation reason -- USProfile is one shared class for
# every US-* code (module docstring), so this has no bearing on the real
# defect, which is jurisdiction-code-independent.
_US_CODE = "US-IN"
_US_CODE_RED = "US-ND"
_IL_CODE = "IL"

# Byte-vendored, verified this session against the real parquet row (see
# module docstring). jurisdiction=US-IN, act_id=STATE_IN_T4_A3_C9_S4-3-9-1,
# citation "Ind. Code Section 4-3-9-1", chapter="9".
_IN_ACT_ID = "STATE_IN_T4_A3_C9_S4-3-9-1"
_IN_CHAPTER = "9"
_IN_SECTION_TEXT = (
    'Sec. 1. As used in this chapter:\n\n'
    '(1) "Agency of the state" means any officer, agency, department, board, '
    'bureau, commission, division or institution of the state of Indiana, the '
    'trustees or board of directors of any corporation of the state or body '
    'politic of the state supported in whole or in part by appropriations from '
    'the state, and the trustees of any state-supported university.\n\n'
    '(2) "Land" means both unimproved and improved land.\n\n'
    '(3) "Title" and "interest in land" means both legal and equitable title '
    'and interest in land.\n\n'
    '(4) "Transfer" means a gift, grant, conveying, exchange, lease, or sale.\n\n'
    '(5) "United States of America" shall include the United States government '
    'and any agency or entity thereof.\n\n'
    'As added by Acts 1977, P.L.25, SEC.1.'
)


def _mirror_pipeline_source_chapter_stamping(candidates, scope):
    """Mirrors pipeline.py's own (unmodified, out of this gate's write-set)
    post-extraction line -- `candidate.source_chapter = art.chapter if
    scope == "chapter" else None` -- so the matcher-level checks below
    exercise the SAME two-step production shape (extraction, then this
    stamp) rather than a shortcut."""
    for c in candidates:
        c.source_chapter = _IN_CHAPTER if scope == "chapter" else None
    return candidates


# --- "Before": today's confirmed bug, reproduced live (NOT a RED) --------
#
# Pinned as an executable fact, not prose -- the measured "before" half of
# this gate's before/after. Uses a probe rule in TODAY's only available
# shape (`parse=`, single arg) hardcoding "law-wide" -- exactly what the
# real (unmerged) `us_multiterm_shared_clause.py::_leading_multiterm_
# candidate` does, because that is genuinely all it can do today.


def test_g10_today_dispatcher_manufactures_a_cross_chapter_false_positive_real_in_row():
    profile = get_profile(_US_CODE)

    def _probe_parse(block: str) -> list[DefinitionCandidate]:
        if '"Title" and "interest in land" means' not in block:
            return []
        return [
            DefinitionCandidate(
                terms=("Title", "interest in land"),
                definition_text="both legal and equitable title and interest in land.",
                scope="law-wide",  # the confirmed bug -- should be "chapter"
            )
        ]

    registry.register_term_clause_rule(
        registry.TermClauseRule(jurisdiction_codes=(_US_CODE,), parse=_probe_parse)
    )

    scope = determine_scope(_IN_SECTION_TEXT)
    assert scope == "chapter", (
        f"P-R10 sanity: real row {_IN_ACT_ID} must determine_scope to "
        f"'chapter' ('as used in this chapter' triggers the baseline "
        f"_US_CHAPTER_SCOPE_TRIGGERS 'in this chapter' match); got {scope!r}"
    )

    candidates = profile.extract_definitions_from_section(_IN_SECTION_TEXT, scope=scope)
    multiterm = [c for c in candidates if c.terms == ("Title", "interest in land")]
    assert len(multiterm) == 1, f"expected the probe's candidate to survive union dispatch; got {candidates!r}"
    assert multiterm[0].scope == "law-wide", (
        "today's dispatcher (us_profile.py:1450-1452) gives the rule no way "
        f"to see the real 'chapter' scope; got {multiterm[0].scope!r} -- "
        "this discrepancy (block genuinely inside a chapter-scoped section, "
        "candidate stamped law-wide anyway) IS the confirmed bug"
    )

    candidates = _mirror_pipeline_source_chapter_stamping(candidates, scope)

    defining_article = SimpleNamespace(number="4-3-9-1", chapter=_IN_CHAPTER, body=_IN_SECTION_TEXT)
    outside_article = SimpleNamespace(
        number="4-3-12-1",
        chapter="12",
        body="A conveyance transferring any interest in land shall be recorded.",
    )
    edges = link_articles_to_definitions(candidates, [defining_article, outside_article])
    outside_edges = [e for e in edges if e.article_index == 1]
    assert outside_edges, (
        "expected today's law-wide-scoped candidate to WRONGLY reach and "
        "match the out-of-chapter article via matcher.link_articles_to_"
        "definitions (production code, not a shortcut) -- if this ever "
        "stops holding, re-verify before trusting the RED below, since "
        "both share the same fixture and mechanism (P-R10)"
    )


# --- THE RED: seam v2.9's `parse_scoped` closes the gap, live -------------


def test_g10_term_clause_rule_scope_threading_eliminates_cross_chapter_false_positive_live_us():
    """P-R8 live-path dispatch proof. Same real IN row, same production
    call chain as the "before" test above -- `profile.extract_definitions_
    from_section(...)` then `matcher.link_articles_to_definitions(...)`,
    both production code, never the registry directly. The probe below
    supplies `parse_scoped`, stamping `scope=ctx.scope` -- exactly what a
    FIXED `us_multiterm_shared_clause.py` would do once this gate lands.

    TODAY's failure (quoted in the Planner's report, reproduce by running
    this test against the unmodified `main`/this branch): `TypeError:
    TermClauseRule.__init__() got an unexpected keyword argument
    'parse_scoped'` -- the field does not exist yet, so the seam cannot
    even be OFFERED a scope-aware rule, let alone dispatch to one. Once
    the Developer adds `parse_scoped`/`TermClauseContext` to registry.py
    and threads `scope` through both dispatch loops (us_profile.py,
    profiles.py), this SAME test -- unedited -- exercises the full chain
    and must pass: the probe's candidate is stamped `scope="chapter"`
    (not "law-wide"), and the out-of-chapter false positive the "before"
    test above proved is real disappears from `link_articles_to_
    definitions`'s own output, while the genuinely in-chapter mention
    still matches. This is the "reaches persistence/matching, not merely
    that the parameter exists" proof: the assertions are on matcher
    output, not on the candidate's field alone.
    """
    profile = get_profile(_US_CODE_RED)

    def _probe_parse_scoped(block: str, ctx) -> list[DefinitionCandidate]:
        if '"Title" and "interest in land" means' not in block:
            return []
        return [
            DefinitionCandidate(
                terms=("Title", "interest in land"),
                definition_text="both legal and equitable title and interest in land.",
                scope=ctx.scope,  # the fix -- real threaded value, no hardcode
            )
        ]

    registry.register_term_clause_rule(
        registry.TermClauseRule(
            jurisdiction_codes=(_US_CODE_RED,),
            parse=lambda block: [],  # required field; never the winner when parse_scoped fires
            parse_scoped=_probe_parse_scoped,
        )
    )

    scope = determine_scope(_IN_SECTION_TEXT)
    assert scope == "chapter"

    candidates = profile.extract_definitions_from_section(_IN_SECTION_TEXT, scope=scope)
    multiterm = [c for c in candidates if c.terms == ("Title", "interest in land")]
    assert len(multiterm) == 1, f"expected the probe's candidate to survive union dispatch; got {candidates!r}"
    assert multiterm[0].scope == "chapter", (
        f"the threaded scope must reach the rule's own candidate; got {multiterm[0].scope!r}"
    )

    candidates = _mirror_pipeline_source_chapter_stamping(candidates, scope)

    defining_article = SimpleNamespace(number="4-3-9-1", chapter=_IN_CHAPTER, body=_IN_SECTION_TEXT)
    outside_article = SimpleNamespace(
        number="4-3-12-1",
        chapter="12",
        body="A conveyance transferring any interest in land shall be recorded.",
    )
    inside_article = SimpleNamespace(
        number="4-3-9-5",
        chapter=_IN_CHAPTER,
        body="No interest in land acquired under this chapter may be transferred without notice.",
    )
    edges = link_articles_to_definitions(
        candidates, [defining_article, outside_article, inside_article]
    )
    outside_edges = [e for e in edges if e.article_index == 1]
    inside_edges = [e for e in edges if e.article_index == 2]

    assert not outside_edges, (
        "the false positive at the out-of-chapter article (proven real by "
        f"the 'before' test above) must be ELIMINATED once scope is "
        f"correctly threaded; got {outside_edges!r}"
    )
    assert inside_edges, "the genuinely in-chapter mention must still match once correctly scoped"


def test_g10_term_clause_rule_scope_threading_live_il():
    """Parity/regression-surface proof (registry.py is SHARED -- Hebrew is
    a regression surface). `TermClauseRule` is dispatched by BOTH
    `USProfile.extract_definitions_from_section` (us_profile.py:1450-1452)
    and `HebrewProfile.extract_definitions_from_section` (profiles.py:
    220-221) through the identical registry kind and the identical
    byte-for-byte dispatch shape -- so the scope-dropping bug is symmetric
    and the fix must thread through both, not just USProfile's.

    Synthetic marker text, not a real IL corpus row: this test proves the
    DISPATCH MECHANISM (a fact about registry.py + profiles.py, not about
    any specific Hebrew statute), matching test_definition_links_rule_
    dispatch.py's own established convention for exactly this reason
    (its `test_term_clause_rule_dispatch_changes_the_answer_il` uses
    synthetic marker text too) -- and israeli-laws-wiki is read-only /
    off-limits per this program's standing constraint, so a real-row IL
    fixture is neither available nor needed for a mechanism proof.

    TODAY's failure: the same `TypeError` as the US test above --
    `parse_scoped` does not exist on `TermClauseRule` yet, for either
    jurisdiction (one shared dataclass).
    """
    profile = get_profile(_IL_CODE)
    marker = "ZZZ_G10_PROOF_IL"
    text = f":- {marker} מלל בלי מקף חלוקה."

    def _probe_parse_scoped(block: str, ctx) -> list[DefinitionCandidate]:
        if marker not in block:
            return []
        return [
            DefinitionCandidate(terms=("מונח בדיקה G10",), definition_text="הגדרת בדיקה", scope=ctx.scope)
        ]

    registry.register_term_clause_rule(
        registry.TermClauseRule(
            jurisdiction_codes=(_IL_CODE,),
            parse=lambda block: [],
            parse_scoped=_probe_parse_scoped,
        )
    )

    candidates = profile.extract_definitions_from_section(text, scope="chapter")
    matching = [c for c in candidates if c.terms == ("מונח בדיקה G10",)]
    assert len(matching) == 1, f"expected the probe's candidate to survive union dispatch; got {candidates!r}"
    assert matching[0].scope == "chapter", (
        f"HebrewProfile's dispatch must thread scope identically to USProfile's; got {matching[0].scope!r}"
    )


# --- Backward compatibility: proven, not asserted (hard requirement) ------
#
# GREEN both BEFORE and AFTER the Developer's change -- neither test below
# touches `parse_scoped` at all, matching every real pre-G10 rule module
# (including the currently-unmerged multiterm/PR/headings/preamble panel
# branches) byte-for-byte. Regression anchor: if either of these ever goes
# red, the additive field was implemented as a breaking change, not
# additively.


def test_g10_backward_compat_old_style_single_arg_parse_still_dispatches_unchanged_us():
    profile = get_profile(_US_CODE)
    marker = "ZZZ_G10_BACKWARD_COMPAT_US"

    registry.register_term_clause_rule(
        registry.TermClauseRule(
            jurisdiction_codes=(_US_CODE,),
            parse=lambda block: (
                [DefinitionCandidate(terms=("Old Style Term US",), definition_text="old style def", scope="law-wide")]
                if marker in block
                else []
            ),
        )
    )

    text = f"(1) {marker} some text with no leading quote."
    candidates = profile.extract_definitions_from_section(text, scope="law-wide")
    assert [c.terms for c in candidates] == [("Old Style Term US",)]


def test_g10_backward_compat_old_style_single_arg_parse_still_dispatches_unchanged_il():
    profile = get_profile(_IL_CODE)
    marker = "ZZZ_G10_BACKWARD_COMPAT_IL"

    registry.register_term_clause_rule(
        registry.TermClauseRule(
            jurisdiction_codes=(_IL_CODE,),
            parse=lambda block: (
                [DefinitionCandidate(terms=("מונח ישן",), definition_text="הגדרה ישנה", scope="law-wide")]
                if marker in block
                else []
            ),
        )
    )

    text = f":- {marker} מלל בלי מקף חלוקה."
    candidates = profile.extract_definitions_from_section(text, scope="law-wide")
    assert [c.terms for c in candidates] == [("מונח ישן",)]
