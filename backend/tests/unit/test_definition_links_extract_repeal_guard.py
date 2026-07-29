"""Sprint 2026-07-29-definition-links, cycle 2, item DL12 (G6, POC finding 2,
ruling M9(b)).

`extract_definitions_from_section` (`app/definition_links/extract.py`) has
no guard against a definitions-entry whose ENTIRE normalized body is
nothing but a parenthesized Knesset repeal/deletion marker, e.g.
`(((נמחקה);))`. Confirmed concretely (poc-run.md §8 Issue 2, §12 addendum):
in the real חוק החברות corpus file, the term "בית המשפט" -- one of the most
generic phrases in Hebrew legal text -- is "defined" as
`:- "בית המשפט" – (((נמחקה);))` (verified directly against
`/Users/nerya/AI for others/israeli-laws-wiki/data/laws/חוק החברות.wiki`
line 28); this phantom Definition became the object of 98 USES_DEFINITION
assertions in the POC run (corpus-wide: 2,981 edges, ~1.4% of all
USES_DEFINITION edges, point at a נמחקה-bodied definition per the manager
addendum). The already-vendored fixture
`wiki_laws/חוק הבנקאות (שירות ללקוח)_excerpt.wiki` (line 29) has the
IDENTICAL real-corpus shape: `:- "חוק כרטיסי חיוב" - (((נמחקה);))`.

The corpus (`grep`-verified against the full 6,133-file corpus, see the
cycle-2 Planner log) uses exactly these inflections wrapped in this
parenthesized-marker convention: נמחקה / נמחק / נמחקו / בוטלה / בוטל /
בוטלו, with varying trailing punctuation (`);))`, `).))`, `)))`).

Fix (M9(b)): a candidate whose normalized body consists SOLELY of one of
these parenthesized repeal markers yields NO `DefinitionCandidate` at all
-- not a Definition row with empty/marker text, simply excluded from the
returned list. A body that merely MENTIONS one of these words as part of
genuine substantive content (e.g. an exclusion clause) must NOT be
blocked -- confirmed real corpus counter-example (must still extract):
`חוק המידע הפלילי ותקנת השבים.wiki` line 164,
`:- "מידע מהמרשם הפלילי" - למעט מידע על פרטי רישום שהתיישנו או שנמחקו.`
"""

from __future__ import annotations

import pytest


def test_extract_definitions_from_section_rejects_a_pure_נמחקה_marker_body():
    """Verbatim shape from the already-vendored fixture
    `wiki_laws/חוק הבנקאות (שירות ללקוח)_excerpt.wiki` line 29 (itself a
    verbatim excerpt of the real corpus file), which is byte-identical to
    poc-run.md §8's חוק החברות "בית המשפט" confirmed-concrete case."""
    from app.definition_links.extract import extract_definitions_from_section

    text = ':- "חוק כרטיסי חיוב" - (((נמחקה);))'
    candidates = extract_definitions_from_section(text, scope="law-wide")
    assert candidates == []


@pytest.mark.parametrize(
    "marker_text",
    [
        '(((נמחקה);))',
        '(((נמחקה).))',
        '(((נמחקה)))',
        '(((נמחק);))',
        '(((נמחק).))',
        '(((נמחק)))',
        '(((נמחקו);))',
        '(((נמחקו).))',
        '(((בוטלה);))',
        '(((בוטלה).))',
        '(((בוטלה)))',
        '(((בוטל);))',
        '(((בוטל).))',
        '(((בוטל)))',
        '(((בוטלו);))',
    ],
)
def test_extract_definitions_from_section_rejects_every_corpus_observed_repeal_marker_punctuation(
    marker_text,
):
    """Every one of these exact punctuation variants was confirmed present
    in the real 6,133-file corpus (grep -rhoE over every `.wiki` file,
    cycle-2 Planner log) -- the guard must reject all of them, not just the
    single נמחקה/`);))` shape."""
    from app.definition_links.extract import extract_definitions_from_section

    text = f':- "מונח שנמחק" - {marker_text}'
    candidates = extract_definitions_from_section(text, scope="law-wide")
    assert candidates == [], f"expected no candidates for marker {marker_text!r}, got {candidates}"


def test_extract_definitions_from_section_does_not_over_block_a_body_that_merely_mentions_repeal():
    """Real corpus counter-example (verbatim, `חוק המידע הפלילי ותקנת
    השבים.wiki` line 164): a genuinely LIVE definition whose substantive
    body happens to use the word "שנמחקו" as ordinary prose (an exclusion
    clause), not as a standalone repeal marker. Must still extract --
    the guard is scoped to bodies that are SOLELY the marker, not any body
    that merely contains one of the marker words."""
    from app.definition_links.extract import extract_definitions_from_section

    text = ':- "מידע מהמרשם הפלילי" - למעט מידע על פרטי רישום שהתיישנו או שנמחקו.'
    candidates = extract_definitions_from_section(text, scope="law-wide")
    assert len(candidates) == 1
    assert candidates[0].terms == ("מידע מהמרשם הפלילי",)
    assert "שנמחקו" in candidates[0].definition_text


def test_extract_definitions_from_section_does_not_over_block_a_body_mentioning_בוטל_as_prose():
    """Real corpus counter-example (verbatim, `חוק חדלות פירעון ושיקום
    כלכלי.wiki` line 42): "בוטל" appears as ordinary prose describing a
    conditional outcome, not as a standalone repeal marker for the term
    being defined."""
    from app.definition_links.extract import extract_definitions_from_section

    text = (
        ':- "הליכי חדלות פירעון" - הליכים לפי חוק זה החל במועד הגשת בקשה '
        "לצו לפתיחת הליכים עד למועד כמפורט להלן, ואם בוטל הצו קודם לכן - עד לביטולו;"
    )
    candidates = extract_definitions_from_section(text, scope="law-wide")
    assert len(candidates) == 1
    assert candidates[0].terms == ("הליכי חדלות פירעון",)


def test_extract_definitions_from_section_still_extracts_sibling_entries_around_a_repealed_one():
    """A הגדרות section with a live entry, a repealed entry, and another
    live entry must extract exactly the two live ones -- the guard drops
    only the offending candidate, not the whole block."""
    from app.definition_links.extract import extract_definitions_from_section

    text = (
        ':- "נכס" - מקרקעין ומיטלטלין, וכן זכויות וטובות הנאה מכל סוג שהוא;\n'
        ':- "חוק כרטיסי חיוב" - (((נמחקה);))\n'
        ':- "לקוח" - אדם המקבל שירות מתאגיד בנקאי;'
    )
    candidates = extract_definitions_from_section(text, scope="law-wide")
    terms = {c.terms for c in candidates}
    assert terms == {("נכס",), ("לקוח",)}
