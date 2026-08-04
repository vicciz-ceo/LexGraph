"""QA cycle 1 (sprint 2026-08-04-defs-core-dispatch), gate A3 -- INDEPENDENT
probe that Hebrew/IL subsection containment was NOT silently changed by this
sprint's shared-file edit to `matcher.py` (I10, M-D3, seam v2.7).

`matcher.py` is shared by both profiles; this sprint added
`_strip_scope_value_format`/`_normalize_scope_value` and the
`scope_unit_kind` level-matching branch to `_subsection_contains_offset`.
`HebrewProfile.resolve_unit_path` (`profiles.py`) was DELIBERATELY left
untouched (per the sprint's own contract) -- but "the profile method wasn't
edited" does not by itself prove "the SHARED containment function still
treats its output correctly". This file does not infer that from the green
full suite; it calls `matcher.definition_covers_mention` directly against a
real (non-stub) Hebrew-shaped article and the real, unmodified
`HebrewProfile`, exercising the NEW normalization/level-matching code paths
this sprint added, in both directions.

Side finding (recorded here, not silently absorbed): grep of
`backend/app/definition_links/rules/il_scope_triggers.py` shows BOTH
core-authored IL `ScopeTriggerRule`s stamp `scope="local"` unconditionally
-- no live IL producer emits `scope="subsection"` today, so this
containment path is reachable-but-currently-unused on the real live path
for Hebrew (the mechanism exists for a future IL rule module to use, same
as the US side before I10/I11). The live end-to-end test below registers a
throwaway IL `ScopeTriggerRule` to prove the full path is genuinely usable,
not merely that the two isolated functions compose correctly in the
abstract.
"""

from __future__ import annotations

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.matcher import definition_covers_mention
from app.definition_links.profiles import HebrewProfile
from app.definition_links.sections import Article as MatcherArticle

_BODY = (
    "פתיחת הסעיף.\n"
    'סעיף קטן (א) קובע כי מונח החלון תקף.\n'
    'סעיף קטן (ב) קובע כי מונח החלון אינו תקף כאן.\n'
)


def _offset(anchor: str) -> int:
    return _BODY.index(anchor)


def test_il_bare_stamp_links_its_own_subsection_and_excludes_the_sibling():
    """Baseline behavior (pre-existing, unchanged mechanism) -- a bare
    label ('א', no parens, no declared scope_unit_kind) covers a mention
    inside its own סעיף קטן and excludes the sibling. This is the CONTROL:
    if this regresses, the shared matcher.py edit broke IL."""
    profile = HebrewProfile()
    article = MatcherArticle(number="1", heading="כותרת", body=_BODY, chapter=None)
    candidate = DefinitionCandidate(
        terms=("חלון",),
        definition_text="הגדרה",
        scope="subsection",
        source_article_number="1",
        scope_value="א",
    )
    assert definition_covers_mention(
        candidate, article, _offset("מונח החלון תקף"), profile=profile
    ), "a bare IL subsection stamp must cover a mention inside its own סעיף קטן (א)"
    assert not definition_covers_mention(
        candidate, article, _offset("מונח החלון אינו תקף"), profile=profile
    ), "a bare IL subsection stamp must NOT cover a mention inside sibling סעיף קטן (ב)"


def test_il_parenthesized_stamp_normalizes_identically_new_code_path():
    """Exercises the NEW `_strip_scope_value_format`/`_normalize_scope_value`
    code this sprint added to `matcher.py` -- a rule that (against the
    bare-label contract) stamps `scope_value='(א)'` must be defensively
    normalized to behave identically to the bare case above. This is the
    shared-file code path this sprint's own I10 item introduced; it must
    work correctly for Hebrew values too, not only ASCII ones."""
    profile = HebrewProfile()
    article = MatcherArticle(number="1", heading="כותרת", body=_BODY, chapter=None)
    candidate = DefinitionCandidate(
        terms=("חלון",),
        definition_text="הגדרה",
        scope="subsection",
        source_article_number="1",
        scope_value="(א)",
    )
    assert definition_covers_mention(
        candidate, article, _offset("מונח החלון תקף"), profile=profile
    ), "a parenthesized IL subsection stamp must normalize and still cover its own subsection"
    assert not definition_covers_mention(
        candidate, article, _offset("מונח החלון אינו תקף"), profile=profile
    ), "a parenthesized IL subsection stamp must still exclude the sibling subsection"


def test_il_declared_scope_unit_kind_is_never_consulted_falls_back_to_outermost():
    """`HebrewProfile.resolve_unit_path`'s own convention has no
    below-article kind vocabulary beyond a single `"subsection"` step
    (`profiles.py`'s own docstring: "IL's observed convention has no
    deeper nesting"). This sprint's `scope_unit_kind` search
    (`_subsection_contains_offset`) looks for a step whose `.kind` MATCHES
    the declared string -- IL's own single step is always `kind="subsection"`
    (see `HebrewProfile.resolve_unit_path`'s own `UnitStep(kind="subsection",
    ...)` construction), so declaring `scope_unit_kind="subsection"`
    explicitly must behave identically to leaving it unset (both find the
    same, only, step) -- proving the new field is harmless for IL rather
    than silently inert or silently broken."""
    profile = HebrewProfile()
    article = MatcherArticle(number="1", heading="כותרת", body=_BODY, chapter=None)
    candidate_explicit = DefinitionCandidate(
        terms=("חלון",),
        definition_text="הגדרה",
        scope="subsection",
        source_article_number="1",
        scope_value="א",
        scope_unit_kind="subsection",
    )
    assert definition_covers_mention(
        candidate_explicit, article, _offset("מונח החלון תקף"), profile=profile
    ), "declaring scope_unit_kind='subsection' explicitly must still cover the (א) mention"
    assert not definition_covers_mention(
        candidate_explicit, article, _offset("מונח החלון אינו תקף"), profile=profile
    ), "declaring scope_unit_kind='subsection' explicitly must still exclude the (ב) mention"

    # A declared kind that IL's own resolver never emits (e.g. "paragraph",
    # a below-article level that only exists in the US ladder vocabulary)
    # must NOT silently match -- absent-from-path means out of scope, same
    # invariant the US side pins.
    candidate_wrong_kind = DefinitionCandidate(
        terms=("חלון",),
        definition_text="הגדרה",
        scope="subsection",
        source_article_number="1",
        scope_value="א",
        scope_unit_kind="paragraph",
    )
    assert not definition_covers_mention(
        candidate_wrong_kind, article, _offset("מונח החלון תקף"), profile=profile
    ), "a scope_unit_kind IL's resolver never emits must not silently match"


def test_il_live_subsection_scope_via_a_throwaway_scope_trigger_rule_links_only_its_own_subsection(
    db_session, matter_with_users
):
    """Goes beyond the QA brief's unit-level requirement: proves the FULL
    live `run_definition_linking` path also works correctly for IL
    subsection scope -- via a throwaway QA-registered IL `ScopeTriggerRule`
    (since neither shipped core IL rule stamps `scope="subsection"` today,
    see this file's module docstring). Same directional-proof discipline as
    the US live tests: the out-of-scope mention (סעיף קטן ב) is placed
    FIRST in the fixture's own text."""
    import re

    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import get_mention_unit_paths, run_definition_linking
    from app.definition_links.rules.registry import (
        RuleContext,  # noqa: F401
        ScopeTriggerRule,
        register_scope_trigger_rule,
    )
    from app.models.assertion import Assertion

    def _extract(article_body, ctx):
        pattern = re.compile(
            r'"([^"]+)" תקף רק בסעיף קטן \(א\) של סעיף זה, ופירושו (.*?)(?=\.\s|$)',
            re.DOTALL,
        )
        return [
            DefinitionCandidate(
                terms=(match.group(1).strip(),),
                definition_text=match.group(2).strip(),
                scope="subsection",
                source_article_number=ctx.article_number,
                scope_value="א",
            )
            for match in pattern.finditer(article_body)
        ]

    register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))

    m = matter_with_users
    term = "רכיב מוגדר"
    wiki_text = (
        f'@ 9. סעיף לבדיקת תחום סעיף קטן\n'
        f'"{term}" תקף רק בסעיף קטן (א) של סעיף זה, ופירושו רכיב מוסדר במיוחד.\n'
        f"סעיף קטן (ב) מזכיר כאן {term}, בסעיף קטן ב -- מחוץ לתחום.\n"
        f"סעיף קטן (א) מזכיר כאן {term} גם כן, בסעיף קטן א -- בתוך התחום בפועל.\n"
    )
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="QA Test IL Subsection Scope Statute",
        wiki_text=wiki_text,
        jurisdiction="IL",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    assert uses_edges, (
        "an IL scope='subsection' definition must link AT LEAST the "
        f"mention inside its own סעיף קטן (א). created_assertions={result['created_assertions']!r}"
    )
    assert len(uses_edges) == 1, f"expected exactly ONE USES_DEFINITION assertion. Got {uses_edges!r}"

    assertion_row = db_session.get(Assertion, uses_edges[0]["id"])
    paths = get_mention_unit_paths(db_session, assertion_row.id)
    assert len(paths) == 1 and paths[0], f"expected a non-empty unit path; got {paths!r}"
    resolved_path = paths[0]
    assert resolved_path[0].kind == "subsection" and resolved_path[0].value == "א", (
        "the surviving assertion must be anchored at סעיף קטן (א) -- the "
        "ONLY in-scope sibling. If this resolves to 'ב' (which appears "
        "FIRST in the fixture's own text), IL containment is "
        f"over-inclusive. Got resolved_path={resolved_path!r}"
    )
