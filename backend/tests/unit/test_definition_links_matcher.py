"""Sprint 2026-07-29-definition-links, item DL5 — Stage 3: build the
article -> definition link index (inflection-tolerant matching, longest-
match-wins, scope-aware).

`app.definition_links.matcher` does not exist yet -- ModuleNotFoundError is
the expected RED signal for every test in this file.

Public API pinned:
- `find_term_uses(term, text) -> list[re.Match[str]]`: every non-overlapping
  occurrence of `term`'s closed-candidate-set surface-form alternation in
  `text`, using a manual boundary check (not `\\b`, unreliable across Hebrew
  bidi/punctuation): character before must be start-of-string/whitespace/
  `(`/`"`/maqaf; character after must be whitespace/`,`/`.`/`;`/`)`/`"`/
  end-of-string. A leading Hebrew prefix letter (Stage 3.1) is part of the
  MATCHED SPAN itself (the boundary check anchors before the prefix, not
  after it) -- `match.group(0)` for a prefixed occurrence like `במאגר המידע`
  is the full prefixed string, not just the bare term.
- `link_articles_to_definitions(definitions, articles) -> list[ArticleUsesTermEdge]`
  runs each definition's matcher over every article body within its scope,
  applies longest-match-wins across overlapping candidate terms, and
  excludes matches inside the term's own defining entry.

`ArticleUsesTermEdge` exposes at least `.article_number`, `.term`,
`.matched_surface_form`, `.char_offset`.

Sprint 2026-07-29-definition-links, cycle 2, item DL11 (G5, ruling M9(a)):
`ArticleUsesTermEdge` additionally carries `.article_index` (int) -- the
POSITION of the article within the `articles` list passed into
`link_articles_to_definitions`, NOT a lookup by `.article_number`. This is
the fix for poc-run.md §8 Issue 1: a document whose wiki source contains
more than one `@ N.` marker with the same `N` (schedules/appendices reusing
the marker syntax) previously collapsed via a plain `{number: article}`
dict in `pipeline.py`, silently misattributing a match found in one
duplicate-numbered article to a DIFFERENT article sharing the same number.
`.article_number` is kept as a PROVENANCE field only -- identity/attribution
must go through `.article_index`.

`DefinitionCandidate` additionally carries two PROVENANCE fields that
`extract_definitions_from_section`/`extract_local_definitions` themselves
leave as `None` (they only see one article body's text, not which article or
chapter it came from) -- the caller (`pipeline.py`) fills these in right
after extraction, before handing candidates to `link_articles_to_definitions`:
`.source_article_number` (str | None, the article housing a `scope="local"`
definition) and `.source_chapter` (str | None, the chapter housing a
`scope="chapter"` definition). `link_articles_to_definitions` uses these to
enforce scope isolation (Stage 3.5/3.8): a chapter-scoped definition may only
link articles sharing its `.source_chapter`; a local-scoped one may only link
its own `.source_article_number`.

`app.definition_links.sections.Article` and `app.definition_links.extract
.DefinitionCandidate` are the input shapes -- both already pinned by their
own test files (DL3/DL4); this file constructs lightweight stand-ins with
the same field names rather than importing across not-yet-existing modules,
so this file's RED signal is scoped to `matcher` alone.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _Article:
    number: str
    heading: str
    body: str
    chapter: str | None = None


@dataclass(frozen=True)
class _DefinitionCandidate:
    terms: tuple[str, ...]
    definition_text: str
    scope: str
    qualifier: str | None = None
    parent_term: str | None = None
    source_article_number: str | None = None
    source_chapter: str | None = None


def test_find_term_uses_matches_the_bare_defined_form():
    from app.definition_links.matcher import find_term_uses

    text = "לא יעבד אדם מידע אישי במסגרת מאגר מידע."
    matches = find_term_uses("מאגר מידע", text)
    assert len(matches) == 1
    assert matches[0].group(0) == "מאגר מידע"


def test_find_term_uses_matches_construct_state_definite_article_insertion():
    """`"מאגר מידע"` (as defined) appears in running text as `מאגר המידע`
    -- the definite article ה is inserted before the LAST word of a
    multi-word term (Stage 3.2). Unprefixed here, isolating this phenomenon
    from prefix-letter attachment (tested separately below)."""
    from app.definition_links.matcher import find_term_uses

    text = "מאגר המידע נוצר בהתאם לחוק זה. מאגר המידע נבדק מדי שנה."
    matches = find_term_uses("מאגר מידע", text)
    assert len(matches) == 2
    assert all(m.group(0) == "מאגר המידע" for m in matches)


def test_find_term_uses_matches_construct_plural_of_first_word():
    """`מאגר` -> `מאגרי` construct-plural of the first word (Stage 3.3):
    a closed candidate-set alternation, not a general suffix rule.
    Unprefixed here, isolating this phenomenon from prefix-letter
    attachment (tested separately below)."""
    from app.definition_links.matcher import find_term_uses

    text = "מאגרי מידע רבים קיימים במדינה לפי הוראות חוק זה."
    matches = find_term_uses("מאגר מידע", text)
    assert len(matches) == 1
    assert matches[0].group(0) == "מאגרי מידע"


def test_find_term_uses_matches_prefixed_forms_with_hebrew_letter_prefixes():
    """Hebrew prefix letters (ובלכמשה, 1-2 stacked before the root) attach
    directly to the surface form with no intervening space -- e.g. `ב` +
    `מאגר המידע` = `במאגר המידע` (Stage 3.1)."""
    from app.definition_links.matcher import find_term_uses

    text = "לא יעבד אדם מידע אישי ממאגר מידע ללא הרשאה מאת בעל השליטה במאגר המידע."
    matches = find_term_uses("מאגר מידע", text)
    surfaces = {m.group(0) for m in matches}
    assert "ממאגר מידע" in surfaces
    assert "במאגר המידע" in surfaces


def test_find_term_uses_respects_manual_boundary_check_not_a_substring_match():
    """`find_term_uses("מידע", ...)` must not match inside the middle of a
    longer word (Hebrew has no `\\b`-safe boundary for this) -- e.g. must
    not spuriously fire inside `מידעני` (a hypothetical longer word sharing
    the substring)."""
    from app.definition_links.matcher import find_term_uses

    text = "מידעני אינו מונח מוכר בחוק זה."
    matches = find_term_uses("מידע", text)
    assert matches == []


def test_link_articles_to_definitions_longest_match_wins_over_a_shorter_term():
    """Stage 3.6: once a span is claimed by a longer term, a shorter term
    may not claim OVERLAPPING offsets. `מאגר מידע` (2 tokens) must win over
    a hypothetical shorter competing term `מידע` (1 token) for the same
    text span -- but a genuinely separate, non-overlapping standalone
    occurrence of the shorter term elsewhere in the same body is still its
    own valid edge (Stage 3.6 only forbids a shorter term claiming an
    ALREADY-claimed span, not every occurrence of it everywhere)."""
    from app.definition_links.matcher import link_articles_to_definitions

    article = _Article(
        number="8",
        heading="שימוש במאגר",
        body="עיבוד מידע נדרש. בתוך מאגר מידע נשמרים הנתונים.",
    )
    long_term = _DefinitionCandidate(terms=("מאגר מידע",), definition_text="...", scope="law-wide")
    short_term = _DefinitionCandidate(terms=("מידע",), definition_text="...", scope="law-wide")

    edges = link_articles_to_definitions([long_term, short_term], [article])

    long_hits = [e for e in edges if e.term == "מאגר מידע"]
    assert len(long_hits) == 1
    long_start = long_hits[0].char_offset
    long_end = long_start + len(long_hits[0].matched_surface_form)

    short_hits = [e for e in edges if e.term == "מידע"]
    # The standalone "עיבוד מידע" occurrence (before the long match) is a
    # separate, non-overlapping use and remains its own edge.
    assert any(e.char_offset < long_start for e in short_hits)
    # No short-term edge may start inside the long match's claimed span.
    assert all(not (long_start <= e.char_offset < long_end) for e in short_hits)


def test_link_articles_to_definitions_excludes_the_terms_own_defining_entry():
    """Stage 3.7: a match inside the term's own `@ N.` definitions-section
    heading/entry is the definition itself, not a "use" -- it must be
    excluded from the edges."""
    from app.definition_links.matcher import link_articles_to_definitions

    definitions_article = _Article(
        number="3",
        heading="הגדרת מונחים",
        body=':- "נכס" - מקרקעין ומיטלטלין, וכן זכויות וטובות הנאה מכל סוג שהוא.',
    )
    using_article = _Article(number="6", heading="פסילת מינוי", body="לא תירשם פעולה בנכס.")
    definition = _DefinitionCandidate(terms=("נכס",), definition_text="...", scope="law-wide")

    edges = link_articles_to_definitions([definition], [definitions_article, using_article])
    assert all(e.article_number != "3" for e in edges)
    assert any(e.article_number == "6" for e in edges)


def test_link_articles_to_definitions_respects_chapter_scope_isolation():
    """A chapter-scoped definition must not link an article in a DIFFERENT
    chapter that happens to contain the same surface form."""
    from app.definition_links.matcher import link_articles_to_definitions

    same_chapter_article = _Article(
        number="35", heading="ענשים", body="חבלה חמורה גוררת עונש כבד.", chapter="פרק ו"
    )
    other_chapter_article = _Article(
        number="99", heading="נושא אחר", body="חבלה חמורה מוזכרת כאן בלבד לצורך ההשוואה.",
        chapter="פרק אחר לגמרי",
    )
    definition = _DefinitionCandidate(
        terms=("חבלה חמורה",),
        definition_text="...",
        scope="chapter",
        source_chapter="פרק ו",
    )

    edges = link_articles_to_definitions(
        [definition], [same_chapter_article, other_chapter_article]
    )
    linked_articles = {e.article_number for e in edges}
    assert "35" in linked_articles
    assert "99" not in linked_articles


def test_link_articles_to_definitions_respects_local_scope_isolation():
    """A `scope="local"` definition (triggered by `לענין זה,`/`בסעיף זה,`
    inside one specific article) must only link uses within that SAME
    article, never a different article containing the same surface form."""
    from app.definition_links.matcher import link_articles_to_definitions

    owning_article = _Article(
        number="35", heading="הענשים", body="שיעור מעודכן חל על התיק שיעור מעודכן פעם נוספת.",
    )
    other_article = _Article(
        number="40", heading="נושא אחר", body="שיעור מעודכן מוזכר כאן גם כן.",
    )
    definition = _DefinitionCandidate(
        terms=("שיעור מעודכן",),
        definition_text="...",
        scope="local",
        source_article_number="35",
    )

    edges = link_articles_to_definitions([definition], [owning_article, other_article])
    linked_articles = {e.article_number for e in edges}
    assert "35" in linked_articles
    assert "40" not in linked_articles


def test_find_term_uses_is_deterministic_across_repeated_calls():
    from app.definition_links.matcher import find_term_uses

    text = "במאגר המידע ובמאגרי מידע רבים."
    first = [(m.group(0), m.start()) for m in find_term_uses("מאגר מידע", text)]
    second = [(m.group(0), m.start()) for m in find_term_uses("מאגר מידע", text)]
    assert first == second


# --- DL11 (cycle 2, G5, ruling M9(a)) -- attribution by article IDENTITY ---


def test_article_uses_term_edge_carries_an_article_index_field():
    """Additive field: `.article_index` is the POSITION of the matched
    article within the `articles` list, independent of `.article_number`."""
    from app.definition_links.matcher import link_articles_to_definitions

    article = _Article(number="8", heading="שימוש", body="נעשה שימוש במונח נכס כאן.")
    definition = _DefinitionCandidate(terms=("נכס",), definition_text="...", scope="law-wide")

    edges = link_articles_to_definitions([definition], [article])
    assert len(edges) == 1
    assert edges[0].article_index == 0
    assert edges[0].article_number == "8"  # provenance -- still present, unchanged


def test_link_articles_to_definitions_attributes_duplicate_numbered_articles_by_position_not_number():
    """poc-run.md §8 Issue 1's exact reproduction shape: a document whose
    wiki source has TWO `@ 17.` markers (e.g. the real article, then a
    later schedule/appendix list reusing the same number). Both articles
    passed to `link_articles_to_definitions` share `article_number == "17"`
    -- only the FIRST (index 0 here) actually contains the matched text; the
    SECOND (index 1) is an unrelated body that must get its own, distinct
    `.article_index`, never collapse onto the first via a number-keyed
    lookup."""
    from app.definition_links.matcher import link_articles_to_definitions

    real_article = _Article(
        number="17", heading="ניהול רישומים ושמירתם",
        body="פרטי כל פעולה כספית שבוצעה יישמרו, לרבות תאריך ביצוע הפעולה.",
    )
    duplicate_article = _Article(
        number="17", heading=": פעולה של ארגון שאינו למטרת רווח", body="",
    )
    definition = _DefinitionCandidate(terms=("פעולה",), definition_text="...", scope="law-wide")

    edges = link_articles_to_definitions([definition], [real_article, duplicate_article])

    assert len(edges) >= 1
    assert all(e.article_number == "17" for e in edges)
    # Every edge must resolve to index 0 (the article whose body genuinely
    # contains the match) -- never index 1 (the empty duplicate), even
    # though both share the same `.article_number`.
    assert {e.article_index for e in edges} == {0}
