"""Stage 3 -- build the article -> definition link index (sprint
2026-07-29-definition-links, item DL5).

See the review doc's "Deterministic definition-linking design" Stage 3.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Hebrew prefix letters (the "ובלכמשה" mnemonic set), 1-2 stacked directly
# before the root with no intervening space (Stage 3.1).
_PREFIX_LETTERS = "ובלכמשה"

# Manual boundary check (Stage 3.4) -- not `\b`, unreliable across Hebrew
# bidi/punctuation.
_BEFORE_OK = set(" \t\n(\"־")
_AFTER_OK = set(" \t\n,.;)\"")


def _surface_variants(term: str) -> set[str]:
    """Build the closed candidate-set of surface forms for `term`
    (Stage 3.1-3.3): the bare term, construct-state definite-article
    insertion before the last word of a multi-word term, and a
    construct-plural of the first word -- each optionally preceded by 1-2
    stacked Hebrew prefix letters attached directly to the surface form.
    """
    words = term.split()
    base_forms = {term}

    if len(words) >= 2:
        head, last = words[:-1], words[-1]
        ha_inserted = " ".join([*head, "ה" + last])
        base_forms.add(ha_inserted)

        first_plural = words[0] + "י"
        plural_form = " ".join([first_plural, *words[1:]])
        base_forms.add(plural_form)

        plural_ha_form = " ".join([first_plural, *head[1:], "ה" + last])
        base_forms.add(plural_ha_form)
    else:
        base_forms.add(term + "י")

    variants: set[str] = set(base_forms)
    for form in base_forms:
        for p1 in _PREFIX_LETTERS:
            variants.add(p1 + form)
            for p2 in _PREFIX_LETTERS:
                variants.add(p1 + p2 + form)
    return variants


def find_term_uses(term: str, text: str) -> list[re.Match[str]]:
    """Every non-overlapping occurrence of `term`'s closed surface-form
    alternation in `text`, using a manual boundary check. A leading Hebrew
    prefix letter is part of the matched span itself.
    """
    variants = sorted(_surface_variants(term), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(v) for v in variants))

    matches: list[re.Match[str]] = []
    n = len(text)
    pos = 0
    while pos <= n:
        m = pattern.search(text, pos)
        if not m:
            break
        start, end = m.start(), m.end()
        before_ok = start == 0 or text[start - 1] in _BEFORE_OK
        after_ok = end == n or text[end] in _AFTER_OK
        if before_ok and after_ok:
            matches.append(m)
            pos = end
        else:
            pos = start + 1
    return matches


@dataclass(frozen=True)
class ArticleUsesTermEdge:
    article_number: str
    term: str
    matched_surface_form: str
    char_offset: int
    # DL11 (cycle 2, G5, ruling M9(a)): the POSITION of the matched article
    # within the `articles` list passed to `link_articles_to_definitions`.
    # `.article_number` is kept as a provenance field only -- attribution
    # back to a real article must go through `.article_index`, since a
    # document's wiki source can contain more than one `@ N.` marker sharing
    # the same `N` (poc-run.md §8 Issue 1).
    article_index: int


def _is_own_defining_entry(text: str, start: int, end: int) -> bool:
    """Stage 3.7: a match immediately bounded by quote characters on both
    sides (`"term"`) is the term's own defining entry, not a use."""
    before_is_quote = start > 0 and text[start - 1] == '"'
    after_is_quote = end < len(text) and text[end] == '"'
    return before_is_quote and after_is_quote


# Sprint 2026-08-04-defs-core-scope (gate C1, seam spec v2/v2.1/v2.2):
# `source_chapter`/`source_article_number`/`scope_value` may each be a
# single scalar OR (M9, enumerated/ranged scopes) a tuple of allowed
# values -- "expected in (actual if isinstance(actual, tuple) else
# (actual,))" collapses to today's plain `==` check for the ordinary
# scalar case, so this is purely additive.
_LEGACY_KIND_RANK = {"subsection": 0, "local": 1, "chapter": 2, "law-wide": 1000}
# A registered kind this module has never heard of (e.g. a family panel's
# "part") is treated as the same narrowness tier as "local" -- a safe,
# conservative default absent a real UnitPath-depth signal on this
# legacy-field containment path (v2.2's "rank = path length" governs the
# PUBLIC `profile.resolve_unit_path` seam; this is matcher.py's own
# internal approximation for the SAME "narrowest governs" precedence,
# expressed over the legacy per-kind fields these tests pin).
_DEFAULT_KIND_RANK = _LEGACY_KIND_RANK["local"]


def scope_rank(scope: str) -> int:
    """How narrow `scope` is, lower is narrower/more specific -- used by
    `pipeline.py`'s Stage-3 attribution rewrite to implement "narrowest
    governs" precedence (director ruling, seam spec v2.2 §3) across every
    candidate definition sharing one mention's term, not just a single
    in/out-of-scope boolean."""
    return _LEGACY_KIND_RANK.get(scope, _DEFAULT_KIND_RANK)


def _value_matches(actual, expected) -> bool:
    if isinstance(expected, tuple):
        return actual in expected
    return actual == expected


def _in_scope(definition, article) -> bool:
    """Coarse, article-level (position-independent) containment check --
    the ONLY check for "chapter"/"local"/"law-wide"; a necessary (but for
    "subsection", not sufficient -- see `_subsection_contains_offset`)
    check for every other kind."""
    scope = definition.scope
    if scope == "chapter":
        return _value_matches(article.chapter, definition.source_chapter)
    if scope == "local":
        return _value_matches(article.number, definition.source_article_number)
    if scope == "subsection":
        # A subsection always belongs to exactly one owning article --
        # narrower than "local", never broader.
        return _value_matches(article.number, definition.source_article_number)
    if scope == "law-wide":
        return True
    # Any OTHER (generic, e.g. "part") registered kind: matched against
    # the owning article's `.structural_units` tuple -- the SAME
    # mechanism "chapter"/"local" use via their own dedicated fields,
    # generalized rather than duplicated per kind (v2 M4). A real
    # production `MatcherArticle` has no `.structural_units` attribute at
    # all today (no rule in this sprint stamps a generic kind), so this
    # defaults to "not contained" rather than raising.
    units = getattr(article, "structural_units", ())
    return any(
        unit.kind == scope and _value_matches(unit.value, definition.scope_value)
        for unit in units
    )


def _subsection_contains_offset(definition, article, char_offset: int) -> bool:
    """Fine, position-dependent check: for a `scope="subsection"`
    definition, does `char_offset` fall inside the matching labeled
    `Subsection` of `article`? A no-op (always True) for every other
    scope -- `_in_scope` above is already sufficient for those."""
    if definition.scope != "subsection":
        return True
    subsections = getattr(article, "subsections", ())
    expected = definition.scope_value
    allowed = expected if isinstance(expected, tuple) else (expected,)
    return any(
        sub.label in allowed and sub.start <= char_offset < sub.end for sub in subsections
    )


def definition_covers_mention(definition, article, char_offset: int) -> bool:
    """Whether `definition`'s scope governs a mention at `char_offset`
    within `article` -- the SAME containment `link_articles_to_
    definitions` applies internally, exposed for `pipeline.py`'s Stage 3
    re-resolution (each edge re-checked against every candidate
    definition sharing its term, not a flat last-write-wins dict)."""
    return _in_scope(definition, article) and _subsection_contains_offset(
        definition, article, char_offset
    )


def link_articles_to_definitions(
    definitions, articles, *, profile=None
) -> list[ArticleUsesTermEdge]:
    """Run each definition's term matcher over every article body within
    its scope, applying longest-match-wins (Stage 3.6) and excluding a
    term's own defining entry (Stage 3.7).

    `profile` (sprint 2026-08-02-us-state-law, item 2, gate G1) is an
    optional keyword-only `JurisdictionProfile`-shaped object. When given,
    term matching delegates to `profile.find_term_uses` instead of this
    module's Hebrew-specific `find_term_uses`; when omitted (the default),
    behavior is byte-identical to before this parameter existed -- every
    existing call site (this module's own tests, `pipeline.py`) passes no
    such kwarg and is unaffected.
    """
    term_uses = profile.find_term_uses if profile is not None else find_term_uses
    # (definition, term) pairs, longest term first (token count, then
    # character length) so a longer term claims its span before a shorter,
    # overlapping term is considered.
    pairs: list[tuple[object, str]] = [
        (definition, term) for definition in definitions for term in definition.terms
    ]
    pairs.sort(key=lambda dt: (len(dt[1].split()), len(dt[1])), reverse=True)

    claimed_spans: dict[int, list[tuple[int, int]]] = {}
    edges: list[ArticleUsesTermEdge] = []

    for definition, term in pairs:
        for article_index, article in enumerate(articles):
            if not _in_scope(definition, article):
                continue
            spans = claimed_spans.setdefault(article_index, [])
            for match in term_uses(term, article.body):
                start, end = match.start(), match.end()
                if _is_own_defining_entry(article.body, start, end):
                    continue
                if not _subsection_contains_offset(definition, article, start):
                    continue
                if any(not (end <= s or e <= start) for s, e in spans):
                    continue
                spans.append((start, end))
                edges.append(
                    ArticleUsesTermEdge(
                        article_number=article.number,
                        article_index=article_index,
                        term=term,
                        matched_surface_form=match.group(0),
                        char_offset=start,
                    )
                )
    return edges
