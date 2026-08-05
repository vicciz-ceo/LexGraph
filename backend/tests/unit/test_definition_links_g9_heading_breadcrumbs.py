"""Sprint 2026-08-05-defs-core-follow-on-2, gate G9 (breadcrumbs data
source). Planner (plan6). RE-AUTHORED (not cherry-picked) equivalent of the
`heading_breadcrumbs`-shaped finding first surfaced by `claude/defs-il`'s
D-1b Planner (commit bc54e1a, `test_definition_links_il_siman_chelek_
containment_live.py`'s module docstring) and accepted into this sprint as
gate G9 (manager ruling, `docs/sprint/sprints/2026-08-05-defs-core-follow-on-2-log.md`,
"Phase 1b -- TWO NEW GATES"). New fixtures, new law, new articles -- built
independently from this Planner's own corpus read, per program convention
that authorship of vendored REDs stays clean across panels/sprints.

## The defect (`sections.py:138`)

`sections.parse_articles`'s `_HEADING_BREAK_RE` matches ANY `={2,}` heading
break (chapter `==`, siman `===`, and deeper `====` addenda/chelek
headings alike) and always ENDS the current article's body scope -- but
only a LITERAL 2-equals break updates the tracked `current_chapter`:

    if len(break_match.group(1)) == 2:
        current_chapter = break_match.group(2)

A 3-or-more-equals break's own heading TEXT (`break_match.group(2)`) is
read by the regex match, then simply discarded -- no `Article` field ever
receives it. This RED file pins the FIX contract: a new, additive
`Article.heading_breadcrumbs: tuple[tuple[int, str], ...]` field (default
`()`, mirrors `Article.structural_units`'s own additive-default
convention already in this module) that accumulates EVERY open heading
depth as an ordered `(depth, heading_text)` stack -- a heading at depth
`d` supersedes (pops) any currently-open entry at depth `>= d`, then
pushes itself. `.chapter`'s own existing len==2-gated computation is left
COMPLETELY UNTOUCHED -- this is a parallel, additive accumulation, not a
rewrite of the existing gate (see `test_the_existing_len_two_chapter_gate_
stays_byte_identical_alongside_the_new_field` below for the regression
proof this sprint's quality bar demands).

## Fixtures (byte-verified, read-only corpus, real rows)

Both new fixtures under `backend/tests/fixtures/wiki_laws/` are literal,
unedited excerpts (verified this session via direct Python substring
checks against the read-only corpus at
`/Users/nerya/AI for others/israeli-laws-wiki/data/laws/`, corpus never
touched by any test):

- `חוק תכנון משק החלב_g9_breadcrumbs_excerpt.wiki` -- from
  `חוק תכנון משק החלב, התשע"א-2011` (Milk Economy Planning Law):
  article 1 (`פרק א': מטרות החוק`, no סימן -- chapter-only case), and a
  non-adjacent assembly (no heading line altered or inserted between
  excerpted spans -- matches the established
  `il_phaseC_plan_m16_multi_fixture_builder.py` method) of `פרק ג':
  תכנון משק החלב` > `סימן א': הסדרת הייצור והשיווק` (articles 3, 12) and
  `סימן ב': קביעת מחירים` (articles 13, 15) -- the SAME chapter, two
  DIFFERENT simanim, proving reset-not-leak.
- `תקנות מחלות בעלי חיים (שחיטת בהמות)_g9_nonmonotonic_depth_excerpt.wiki`
  -- from `תקנות מחלות בעלי חיים (שחיטת בהמות)`: a REAL corpus case where
  a depth-4 heading (`==== ((([[תקנה 49]]))) ====`) appears BEFORE the
  depth-3 heading it is nested under (`=== הוראות בדבר בדיקה לאחר
  השחיטה ===`), which is itself followed by a second depth-4 heading
  (`==== הוראות כלליות ====`). This is the exact "nesting depth is NOT
  uniform corpus-wide" complication the D-1b Planner flagged (their own
  `תקנות המשקלות והמידות` finding) -- reproduced here independently
  against a DIFFERENT real file, proving the pop-on-shallower-heading
  design handles a genuine non-monotonic real sequence, not just a
  hand-picked monotonic one.

## Why these are live-path-adjacent but NOT the P-R8 consumption proof

This file exercises `sections.parse_articles` directly (a pure function,
no jurisdiction dispatch, no registry) -- it pins the CAPTURE half of the
defect only. The CONSUMPTION half (`StructuralUnitRule.derive` actually
RECEIVING these breadcrumbs through the real `pipeline.py` construction
site and changing an observable `USES_DEFINITION` answer) is proven
end-to-end in
`backend/tests/integration/test_definition_links_g9_heading_breadcrumbs_live.py`
instead -- P-R8 requires both, and conflating them into one file would
hide which half a failure belongs to.
"""

from __future__ import annotations

import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_articles_captures_chapter_and_siman_breadcrumbs_for_a_nested_article():
    """Article 3 sits under `פרק ג': תכנון משק החלב` (depth 2) AND
    `סימן א': הסדרת הייצור והשיווק` (depth 3) -- today, RED:
    `Article` has no `heading_breadcrumbs` attribute at all (only
    `.chapter`, which alone cannot express the siman level)."""
    from app.definition_links.sections import parse_articles

    text = _read("חוק תכנון משק החלב_g9_breadcrumbs_excerpt.wiki")
    articles = {a.number: a for a in parse_articles(text)}

    assert articles["3"].heading_breadcrumbs == (
        (2, "פרק ג': תכנון משק החלב"),
        (3, "סימן א': הסדרת הייצור והשיווק"),
    ), articles["3"]


def test_parse_articles_captures_chapter_only_breadcrumbs_when_no_siman_is_open():
    """Article 1 sits directly under `פרק א': מטרות החוק` with no siman
    nested underneath it -- breadcrumbs must be exactly the one depth-2
    entry, not padded or duplicated."""
    from app.definition_links.sections import parse_articles

    text = _read("חוק תכנון משק החלב_g9_breadcrumbs_excerpt.wiki")
    articles = {a.number: a for a in parse_articles(text)}

    assert articles["1"].heading_breadcrumbs == ((2, "פרק א': מטרות החוק"),), articles["1"]


def test_parse_articles_resets_the_siman_breadcrumb_and_does_not_leak_the_prior_simans_text():
    """Article 12 is the LAST article of סימן א'; article 13/15 come
    AFTER `=== סימן ב': קביעת מחירים ===`, the same chapter but a
    genuinely DIFFERENT siman. Both must carry the SAME chapter entry
    (depth 2, unchanged) but a DIFFERENT depth-3 entry -- proving a new
    depth-3 heading REPLACES (does not append alongside) the prior one."""
    from app.definition_links.sections import parse_articles

    text = _read("חוק תכנון משק החלב_g9_breadcrumbs_excerpt.wiki")
    articles = {a.number: a for a in parse_articles(text)}

    assert articles["12"].heading_breadcrumbs == (
        (2, "פרק ג': תכנון משק החלב"),
        (3, "סימן א': הסדרת הייצור והשיווק"),
    ), articles["12"]
    assert articles["15"].heading_breadcrumbs == (
        (2, "פרק ג': תכנון משק החלב"),
        (3, "סימן ב': קביעת מחירים"),
    ), articles["15"]
    # The stale סימן א' entry must be GONE, not merely superseded at the
    # front -- a naive "append, never pop" implementation would leave both
    # depth-3 texts stacked.
    assert (3, "סימן א': הסדרת הייצור והשיווק") not in articles["15"].heading_breadcrumbs


def test_parse_articles_handles_a_real_non_monotonic_depth_sequence():
    """Real corpus quirk (`תקנות מחלות בעלי חיים (שחיטת בהמות)`): a
    depth-4 heading (`(((תקנה 49)))`) appears BEFORE the depth-3 heading
    it nests under, itself followed by a second depth-4 heading
    (`הוראות כלליות`). The first depth-4 entry must be POPPED when the
    depth-3 heading arrives (a heading at depth `d` supersedes any
    currently-open entry at depth `>= d`) -- it must not survive
    alongside the second depth-4 entry, and it must not appear at all in
    the final breadcrumbs of either article that follows."""
    from app.definition_links.sections import parse_articles

    text = _read("תקנות מחלות בעלי חיים (שחיטת בהמות)_g9_nonmonotonic_depth_excerpt.wiki")
    articles = {a.number: a for a in parse_articles(text)}

    expected = (
        (2, "תוספת שביעית"),
        (3, "הוראות בדבר בדיקה לאחר השחיטה"),
        (4, "הוראות כלליות"),
    )
    assert articles["1"].heading_breadcrumbs == expected, articles["1"]
    assert articles["2"].heading_breadcrumbs == expected, articles["2"]
    assert "(((תקנה 49)))" not in [text for _, text in articles["1"].heading_breadcrumbs]


def test_the_existing_len_two_chapter_gate_stays_byte_identical_alongside_the_new_field():
    """The regression proof this sprint's quality bar demands: `.chapter`
    (the existing, len==2-gated field every other IL test depends on) must
    be EXACTLY what it is today for every article touched by this file's
    fixtures -- siman/chelek-depth headings must never leak into it, and
    adding `heading_breadcrumbs` must not perturb it in any way. These
    exact `.chapter` values were confirmed by running today's UNMODIFIED
    `parse_articles` against these fixtures before this field existed."""
    from app.definition_links.sections import parse_articles

    text1 = _read("חוק תכנון משק החלב_g9_breadcrumbs_excerpt.wiki")
    articles1 = {a.number: a for a in parse_articles(text1)}
    assert articles1["1"].chapter == "פרק א': מטרות החוק"
    assert articles1["3"].chapter == "פרק ג': תכנון משק החלב"
    assert articles1["12"].chapter == "פרק ג': תכנון משק החלב"
    assert articles1["13"].chapter == "פרק ג': תכנון משק החלב"
    assert articles1["15"].chapter == "פרק ג': תכנון משק החלב"

    text2 = _read("תקנות מחלות בעלי חיים (שחיטת בהמות)_g9_nonmonotonic_depth_excerpt.wiki")
    articles2 = {a.number: a for a in parse_articles(text2)}
    # The depth-3/depth-4 headings nested under "תוספת שביעית" must NEVER
    # overwrite `.chapter` -- only a literal 2-equals break may.
    assert articles2["1"].chapter == "תוספת שביעית"
    assert articles2["2"].chapter == "תוספת שביעית"
