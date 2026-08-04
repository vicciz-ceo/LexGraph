"""Sprint 2026-07-29-definition-links, item DL3 — Stage 1: locate articles
and definitions sections (scope, not yet terms).

`app.definition_links.sections` does not exist yet -- ModuleNotFoundError is
the expected RED signal for every test in this file.

Per the review doc's Stage 1: `@ N. <heading>` lines mark article/section
starts. A definitions section is identified by heading form (`הגדרות`,
`הגדרת מונחים`, `הגדרה`, `הגדרות ופירוש`) -- NOT assumed to be section 1
only (`חוק העונשין` alone has 15 scattered `הגדרות` sections, each scoped to
its own chapter). An article's body runs from its `@ N.` line to the next
`@ N.` line at the same/shallower level, or to a `==` chapter break --
whichever comes first.

Two public names are pinned:
- `parse_articles(text) -> list[Article]`, where `Article` exposes at least
  `.number` (str, e.g. "34כד"), `.heading` (str), `.body` (str, the article's
  own text only), and `.chapter` (str | None, nearest preceding `==` chapter
  heading text).
- `locate_definitions_sections(articles) -> list[Article]`, returning only
  the articles whose heading matches a known definitions-heading form.
"""

from __future__ import annotations

import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_articles_splits_on_at_n_markers():
    from app.definition_links.sections import parse_articles

    text = _read("חוק להגנת רכוש מופקד.wiki")
    articles = parse_articles(text)
    numbers = [a.number for a in articles]
    assert numbers == ["1", "2", "3", "4", "5", "6", "7", "8"]


def test_article_body_excludes_the_next_articles_heading_and_text():
    from app.definition_links.sections import parse_articles

    text = _read("חוק להגנת רכוש מופקד.wiki")
    articles = {a.number: a for a in parse_articles(text)}
    article_1 = articles["1"]
    assert "האפוטרופוס הכללי" in article_1.body
    assert "הודעה על טיפול בנכס" not in article_1.body  # that's article 2's heading


def test_locate_definitions_sections_finds_the_single_section_1_case():
    from app.definition_links.sections import locate_definitions_sections, parse_articles

    text = _read("חוק להגנת רכוש מופקד.wiki")
    articles = parse_articles(text)
    definitions_sections = locate_definitions_sections(articles)
    assert [a.number for a in definitions_sections] == ["1"]


def test_locate_definitions_sections_does_not_assume_section_1_only():
    """חוק העונשין's definitions sections are scattered (e.g. §34כד, §51א),
    never at §1 in our excerpt -- locate_definitions_sections must find both
    without special-casing "section 1"."""
    from app.definition_links.sections import locate_definitions_sections, parse_articles

    text = _read("חוק העונשין_excerpt.wiki")
    articles = parse_articles(text)
    definitions_sections = locate_definitions_sections(articles)
    numbers = {a.number for a in definitions_sections}
    assert "34כד" in numbers
    assert "51א" in numbers
    assert "1" not in numbers  # this excerpt has no section 1 at all


def test_definitions_heading_recognizes_all_named_forms():
    from app.definition_links.sections import is_definitions_heading

    assert is_definitions_heading("הגדרות")
    assert is_definitions_heading("הגדרת מונחים (תיקון: תשמ\"א)")
    assert is_definitions_heading("הגדרה")
    assert is_definitions_heading("הגדרות ופירוש")
    assert not is_definitions_heading("איסור הפגיעה בפרטיות")


def test_article_scope_ends_at_a_double_equals_chapter_break():
    """Article body must not swallow content past a `==` chapter break even
    when the source excerpt jumps straight from one article to a chapter
    heading (חוק הגנת הפרטיות_excerpt.wiki: article 3's definitions section
    is directly followed by `== פרק ב' ==`)."""
    from app.definition_links.sections import parse_articles

    text = _read("חוק הגנת הפרטיות_excerpt.wiki")
    articles = {a.number: a for a in parse_articles(text)}
    article_3 = articles["3"]
    assert "מאגר מידע" in article_3.body  # the definitions text itself
    assert "ניהול מאגר מידע" not in article_3.body  # that's article 8's heading


# --- Sprint 2026-08-04-defs-core-scope (manager ruling M8(a)) -----------
#
# `_ARTICLE_MARKER_RE` requires the literal `@ <digits><Hebrew letters>.`
# shape -- a BARE `@` (no number, no trailing period) silently fails to
# match, and `parse_articles` has no fallback: every line before the
# first successful match is dropped (never appended to any article, since
# `current_number` stays `None`). Measured by the IL panel: 124/6,133 real
# israeli-laws-wiki documents use a bare `@` for at least one section; 12
# of those 124 contain unambiguous definitions that are therefore never
# captured. This fixture reproduces the SHAPE (a bare `@` line, same wiki
# markup conventions as every other vendored fixture in this directory,
# prior R6 -- no corpus download) rather than a specific named real file
# this Planner does not have local access to.


def test_parse_articles_does_not_silently_merge_a_bare_at_marker_section_into_its_neighbor():
    """RED today: `@` (bare, no number/period) does not match
    `_ARTICLE_MARKER_RE`, so it is treated as ordinary body text and
    silently MERGED into whichever article is currently open --
    `current_number` never resets for it, so its own content (here, a
    second definitions entry that belongs to its OWN section) is
    misattributed to the PRECEDING article rather than parsed as its own
    section. Today: `len(articles) == 2` (only "1" and "2"), with the
    bare-`@` section's text folded into article "1"'s body -- confirmed
    by running this exact fixture, not merely asserted."""
    from app.definition_links.sections import parse_articles

    text = (
        "@ 1. פרשנות\n"
        ':- "מונח" - הגדרה רגילה.\n'
        "@\n"
        ':- "מונח נוסף" - הגדרה שאבדה.\n'
        "@ 2. הוראה נוספת\n"
        "תוכן רגיל.\n"
    )
    articles = parse_articles(text)
    # A bare `@` line must start its OWN section, not fall through into
    # whichever article happened to be open -- 3 sections in this
    # fixture, not 2.
    assert len(articles) == 3


def test_parse_articles_does_not_return_zero_articles_for_a_document_using_only_bare_at_markers():
    """The literal M8(a) measurement: 124/6,133 real israeli-laws-wiki
    documents use a bare `@` for EVERY section marker (no `@ N.` form
    anywhere in the document at all) -- `current_number` never becomes
    non-`None`, so `parse_articles` returns an EMPTY list and every line,
    including a genuine definitions entry, is silently dropped. Fixture
    reproduces the SHAPE (prior R6: no corpus download; this Planner
    verified no local corpus copy exists in this worktree -- see the
    panel log)."""
    from app.definition_links.sections import parse_articles

    text = (
        "@\n"
        "פרשנות\n"
        ':- "מונח יסודי" - הגדרה שאף פעם לא נקלטת.\n'
        "@\n"
        "הוראה נוספת\n"
        "תוכן רגיל.\n"
    )
    articles = parse_articles(text)
    assert len(articles) > 0
    assert "מונח יסודי" in "".join(a.body for a in articles)


def test_article_records_its_nearest_preceding_chapter_heading():
    from app.definition_links.sections import parse_articles

    text = _read("חוק הגנת הפרטיות_excerpt.wiki")
    articles = {a.number: a for a in parse_articles(text)}
    assert "פרק א" in (articles["1"].chapter or "")
    assert "פרק ב" in (articles["8"].chapter or "")


def test_parse_articles_is_deterministic_across_repeated_calls():
    from app.definition_links.sections import parse_articles

    text = _read("חוק העונשין_excerpt.wiki")
    first = [(a.number, a.body) for a in parse_articles(text)]
    second = [(a.number, a.body) for a in parse_articles(text)]
    assert first == second
