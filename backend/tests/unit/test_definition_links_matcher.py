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
    # `str | tuple[str, ...] | None`: sprint 2026-08-04-defs-core-scope
    # (seam v2.1, M9) widens these two legacy fields to also accept an
    # enumerated/ranged tuple of values, not just one scalar -- existing
    # callers passing a bare string are completely unaffected.
    source_article_number: str | tuple[str, ...] | None = None
    source_chapter: str | tuple[str, ...] | None = None
    # NEW (seam v2, M4): the generic value field every kind OTHER than
    # the two legacy ones above (chapter/local) uses -- e.g. "subsection"
    # (v1), or any new kind a family panel registers (part/siman/...).
    scope_value: str | tuple[str, ...] | None = None


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


# --- QA cycle-3 manager-flagged probe (same G5 family as DL11, distinct
# mechanism): `claimed_spans` is still keyed by `article.number`, not
# `article_index` ---


def test_link_articles_to_definitions_does_not_cross_suppress_duplicate_numbered_articles_with_overlapping_offsets():
    """DL11 fixed WHICH article an edge is attributed to (`.article_index`
    instead of a `{number: article}` dict), but `link_articles_to_definitions`
    still builds `claimed_spans` keyed by `article.number`
    (`claimed_spans.setdefault(article.number, [])`). When TWO articles
    share a number and BOTH have their own, independent, genuine use of the
    same defined term at the SAME character offset within their own body
    (a realistic coincidence -- e.g. near-identical boilerplate opening
    clauses in a schedule that reuses a marker number), the shared registry
    treats the second article's match as if it were an overlapping span in
    the FIRST article's body and silently drops it.

    Per the review doc's Stage 3 spec ("Longest-match-wins": overlap
    claiming is per-article-body -- a span can only be "claimed" against
    other spans within the SAME body), longest-match-wins must never
    reach across two different articles' bodies just because they happen
    to share a `.number`. Each duplicate-numbered article's body is its
    own independent offset space; BOTH articles must get their own
    USES_DEFINITION edge (`article_index` 0 AND 1), not just the first.

    Pre-fix (RED): `claimed_spans["17"]` records article 0's match first;
    when article 1 (a DIFFERENT body, unrelated to article 0's text) is
    processed, its identical-offset match is wrongly treated as
    overlapping article 0's already-claimed span and is suppressed --
    only 1 edge is produced instead of 2.
    """
    from app.definition_links.matcher import link_articles_to_definitions

    term = "פעולה"
    # Deliberately identical prefix length in both bodies so the term
    # lands at the SAME char_offset in each article's own body -- this is
    # what a number-keyed (rather than article-keyed) claimed_spans
    # registry confuses for a same-body overlap.
    prefix = "לעניין סעיף זה, "
    body_a = prefix + term + " ראשונה שבוצעה על ידי המבקש."
    body_b = prefix + term + " שניה ונפרדת שבוצעה על ידי הנתבע."
    assert body_a.find(term) == body_b.find(term)  # sanity: same offset

    article_a = _Article(number="17", heading="סעיף א", body=body_a)
    article_b = _Article(number="17", heading="סעיף ב", body=body_b)
    definition = _DefinitionCandidate(terms=(term,), definition_text="...", scope="law-wide")

    edges = link_articles_to_definitions([definition], [article_a, article_b])

    # Both duplicate-numbered articles have their OWN genuine, non-
    # overlapping-within-their-own-body use of the term -- both must be
    # linked, independently, via their own article_index.
    assert {e.article_index for e in edges} == {0, 1}
    assert len(edges) == 2


# --- Sprint 2026-08-04-defs-core-scope (gate C1, seam spec, current as of
# --- v2.3) -- subsection granularity + generic scope units (M4/M9) ------
#
# Behavioral-contract tests, matcher-internal-wiring level (this file's
# own long-standing isolation convention: local stand-in dataclasses, not
# the real modules -- see the file's header docstring). The PUBLIC
# family-panel-facing seam is `profile.resolve_unit_path` (v2.2's unified
# `UnitPath` retrieval seam, pinned separately in
# `test_definition_links_profiles.py`); how `link_articles_to_definitions`
# internally receives per-position structural info from whatever
# pipeline.py precomputes (below, via `.subsections`/`.structural_units`
# stub fields) is implementation wiring this file exercises at the
# BEHAVIOR level, not a second copy of the public `UnitPath` vocabulary.
# `_DefinitionCandidate.scope_value` is the generic value field (v2 M4);
# `source_article_number`/`source_chapter` may now ALSO be assigned a
# tuple of strings for an enumerated/ranged unit (v2.1/v2.2 M9) -- both
# are exercised below.


@dataclass(frozen=True)
class _Subsection:
    label: str
    start: int
    end: int


@dataclass(frozen=True)
class _ScopeUnit:
    kind: str
    value: str


def _article_with_subsections(**kwargs):
    """`_Article` doesn't declare `.subsections`/`.structural_units` in its
    header dataclass (kept minimal for the pre-existing tests above) --
    build an equivalent lightweight namespace object with those extra
    attributes for the new tests below, so `_in_scope`'s generic/subsection
    branches (reached only via `link_articles_to_definitions`) have
    something real to read."""
    from types import SimpleNamespace

    base = dict(chapter=None, subsections=(), structural_units=())
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_link_articles_to_definitions_respects_subsection_scope_isolation():
    """A `scope="subsection"` definition must only link a mention whose
    CHAR OFFSET falls inside the matching labeled `Subsection` of its OWN
    article -- a mention of the same term elsewhere in the SAME article
    but a DIFFERENT subsection must not link, even though both subsections
    belong to the same `.number` (the case v1's plain `"local"` scope
    cannot express -- C1's genuinely-new-below-article-level granularity)."""
    from app.definition_links.matcher import link_articles_to_definitions

    term = "מונח מקומי"
    body = f'סעיף קטן (א): {term} ראשון. סעיף קטן (ב): {term} שני.'
    subsection_a_end = body.index("סעיף קטן (ב):")
    article = _article_with_subsections(
        number="12",
        heading="נושא",
        body=body,
        subsections=(
            _Subsection(label="a", start=0, end=subsection_a_end),
            _Subsection(label="b", start=subsection_a_end, end=len(body)),
        ),
    )
    definition = _DefinitionCandidate(
        terms=(term,),
        definition_text="...",
        scope="subsection",
        source_article_number="12",
        scope_value="a",
    )

    edges = link_articles_to_definitions([definition], [article])
    # Only the occurrence physically inside subsection (a)'s char range may
    # link -- the occurrence inside subsection (b) must not.
    assert len(edges) == 1
    assert edges[0].char_offset < subsection_a_end


def test_link_articles_to_definitions_respects_generic_scope_unit_containment():
    """A registered NON-legacy kind (e.g. `"part"`, M4) is enforced by
    matching `definition.scope_value` against the owning article's
    `.structural_units` -- the same mechanism `"chapter"`/`"local"` use
    via their own dedicated fields, generalized rather than duplicated
    per kind."""
    from app.definition_links.matcher import link_articles_to_definitions

    term = "מונח חלקי"
    in_part_article = _article_with_subsections(
        number="40",
        heading="נושא",
        body=f"{term} מוזכר כאן.",
        structural_units=(_ScopeUnit(kind="part", value="II"),),
    )
    other_part_article = _article_with_subsections(
        number="41",
        heading="נושא אחר",
        body=f"{term} מוזכר גם כאן.",
        structural_units=(_ScopeUnit(kind="part", value="III"),),
    )
    definition = _DefinitionCandidate(
        terms=(term,), definition_text="...", scope="part", scope_value="II"
    )

    edges = link_articles_to_definitions([definition], [in_part_article, other_part_article])
    linked = {e.article_number for e in edges}
    assert "40" in linked
    assert "41" not in linked


def test_link_articles_to_definitions_respects_enumerated_local_scope():
    """M9 -- SD 3-14-5-shaped scope: `source_article_number` may be a
    TUPLE of article numbers (an enumeration, not a single scalar). A
    mention in ANY enumerated member article links; a mention in a
    non-member article, even one that shares the same body text, does
    not."""
    from app.definition_links.matcher import link_articles_to_definitions

    term = "מונח משותף"
    member_one = _article_with_subsections(number="3-14-3", heading="א", body=f"{term} כאן.")
    member_two = _article_with_subsections(number="3-14-4", heading="ב", body=f"{term} גם כאן.")
    non_member = _article_with_subsections(number="3-14-9", heading="ג", body=f"{term} ושם.")
    definition = _DefinitionCandidate(
        terms=(term,),
        definition_text="...",
        scope="local",
        source_article_number=("3-14-3", "3-14-4"),
    )

    edges = link_articles_to_definitions(
        [definition], [member_one, member_two, non_member]
    )
    linked = {e.article_number for e in edges}
    assert linked == {"3-14-3", "3-14-4"}
