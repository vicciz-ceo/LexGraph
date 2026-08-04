"""Sprint 2026-08-04-defs-us-scoped-inline, Planner pass 6. Pins the 3 of
QA cycle 1's 8 confirmed root causes (`docs/sprint/sprints/
2026-08-04-defs-us-scoped-inline-log.md`'s `## 2026-08-04 -- QA (cycle 1...)`
section, root causes #2/#5/#6) that got documented but NOT independently
committed as RED tests in `test_us_scoped_inline_qa_cycle1_missed_
conventions.py` (that file kept itself under the style gate by pinning only
6 of the 8 distinct causes). Gate U4 is the director's absolute zero-miss
bar -- an unpinned root cause is a real hole: a fix with no committed pin
can regress silently. `us_scoped_inline.py` is UNMODIFIED in this worktree
(a Developer is fixing it concurrently in a different worktree); these
tests are RED today and are expected to go GREEN once that fix lands.

Every row below is real, unmodified, vendored corpus text
(`planner_pass6_missed_conventions_rows.json`), independently fetched
directly from the live HF parquet snapshot and byte-verified (`section_
title` + `text`) against a second, separate fetch -- no invented text, no
synthetic reproduction standing in for a real miss.

Root-cause coverage in this file:

1. Period-style list markers (`1.` `2.` instead of `(1)` `(2)`) --
   `STATE_FL_TXVIII_C253_S253.04`.
2. `the term:` with no space before the colon -- `STATE_DC_T47_C20_
   S47-2002.01`.
3. `shall have (the following) meaning(s)` / `shall have meanings as
   follows` connector vocabulary gap -- `STATE_MS_T27_C29_S51-5`
   (the primary pin QA's manager-relayed brief prefers over
   `STATE_NY_ARPP_A8_S280-D`: the NY row's 3 "definitions" are entirely
   UNQUOTED labeled paragraphs -- `(a) Reverse mortgage loan. A reverse
   mortgage loan as defined in...` -- with zero quote characters anywhere
   in its body (independently verified: `re.findall(r'["“”]',
   text) == []`). Even a fully corrected connector could never surface a
   candidate from that row, because `_QUOTE_TERM_RE` requires a quoted
   term and this row's convention is the SEPARATE, deliberately-excluded
   unquoted-labeled-paragraph precision tradeoff (QA cycle 1's own note:
   NY "ALSO independently exhibits" that convention "as a second,
   compounding issue on the same row"). A NY-based test would therefore
   stay RED forever, even post-fix -- not a valid pin of THIS root cause.
   MS's row, by contrast, uses quoted terms throughout
   (`“ Motor vehicle ” means...`) gated behind the exact same
   unrecognized connector phrase (`shall have meanings as follows:`), so
   it isolates the connector-vocabulary gap cleanly and will go GREEN once
   (and only once) that gap is closed.
4. A SECOND, independent confirmation of the already-pinned "intervening
   secondary citation clause" root cause (QA's own DE-row pin,
   `test_intervening_secondary_citation_clause_breaks_recognition_
   delaware`) -- `STATE_OR_T62_C835_S835.200`. Judgement call (per the
   brief): added because this row's citation shape is structurally
   DIFFERENT from DE's (`"and in Section 15-105 of this title"`, plain
   prose) and from OH's (`"and section 1707.471 of the Revised Code"`,
   same plain-prose shape as DE) -- OR's citation is `"and ORS 835.210
   (Application by political subdivision for special regulation)"`: a
   NESTED parenthetical embedded inside the intervening citation itself,
   followed by an unusual space-before-comma (`") , "`) directly before
   the quoted term. A connector-tolerance fix implemented as "skip past
   an `and <citation>` clause" could plausibly mishandle the nested `)`
   (treating it as the end of tolerance) or the non-adjacent comma in a
   way a DE/OH-shaped row would never expose -- real incremental
   regression value, not redundant bulk. (OH's row was deliberately NOT
   also added: its citation shape is a plain "and section N of the
   Revised Code", already fully covered by DE's pin.)
"""

from __future__ import annotations

import json
import pathlib

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "planner_pass6_missed_conventions_rows.json"
)


def _rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))}


def test_period_style_list_markers_not_recognized_florida():
    """`STATE_FL_TXVIII_C253_S253.04`: `"As used in this subsection, the
    term: 1. "Seagrass" means Cuban shoal grass... 2. "Seagrass scarring"
    means destruction of seagrass roots..."` -- a clean STRONG trigger
    ("as used in this subsection") + colon + two quoted terms each
    followed by a recognized idiom ("means"). ROOT CAUSE: `_MARKER_RE`
    (`r"\\((?:[0-9]{1,3}|[A-Za-z]{1,3})\\)"`) requires a LITERAL
    parenthesized marker; this row numbers its list entries with a bare
    period (`1.` `2.`), a real, unremarkable Florida convention. Because
    the connector's colon IS detected here, `_leading_events` correctly
    routes to `_multi_entries` -- but `_multi_entries` finds ZERO
    `_MARKER_QUOTE_RE` matches (no `(...)` immediately precedes either
    quote), so it returns `[]` and `_single_entry` is never tried as a
    fallback: the entire two-term block is lost, exactly the same failure
    shape as QA's unmarked-colon-list root cause, but triggered by a
    non-parenthesized marker instead of no marker at all."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_FL_TXVIII_C253_S253.04"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert {"Seagrass", "Seagrass scarring"} <= terms, (
        "the rule captured nothing from a clean 'As used in this subsection, the "
        'term: 1. "Seagrass" means... 2. "Seagrass scarring" means...\' colon-list '
        f"-- period-style (non-parenthesized) markers broke recognition -- got {candidates!r}"
    )


def test_the_term_colon_no_space_breaks_colon_detection_dc():
    """`STATE_DC_T47_C20_S47-2002.01`: `"(a) For the purposes of this
    section, the term:\\n  (1) "Business Beneficial License Holder"
    means..."` -- a clean STRONG trigger ("for the purposes of this
    section") immediately followed by "the term:" with NO whitespace
    between "term" and the colon, then 4 marker-prefixed quoted entries.
    ROOT CAUSE: `_STRONG_CONNECTOR_RE`'s `(?:the term\\s+|an?\\s+)?`
    alternative requires ONE OR MORE trailing whitespace characters after
    "term" before it can even attempt to match -- "term:" has none, so
    that whole optional group matches zero-width, leaving "the term:"
    itself completely unconsumed at the position where the trailing
    `(?P<colon>:)?` group is then tried; that group's next character is
    "t" (of "the"), not ":", so it ALSO matches empty. `conn.group(
    "colon")` is therefore `None` -- `saw_colon` is `False` -- so
    `_leading_events` routes this event to `_single_entry` (not
    `_multi_entries`), with `region_start` pointing at the still-unconsumed
    "the term:\\n  (1) ..." text. `_single_entry` immediately fails: the
    text right there is "t" (of "the"), not a quote character, so
    `_QUOTE_TERM_RE.match` fails and `[]` is returned -- all 4 entries
    lost, not just under-split."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_DC_T47_C20_S47-2002.01"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert {"Business Beneficial License Holder", "Street vendor"} <= terms, (
        "the rule captured nothing from 'for the purposes of this section, the "
        'term:\\n  (1) "Business Beneficial License Holder" means...\' -- the '
        "space-less \"the term:\" broke colon detection entirely -- "
        f"got {candidates!r}"
    )


def test_shall_have_meanings_as_follows_connector_not_recognized_mississippi():
    """`STATE_MS_T27_C29_S51-5`: `"The subject words and terms of this
    section, for the purpose of this chapter, shall have meanings as
    follows:\\n\\n(a) "Motor vehicle" means any device..."` -- a clean
    STRONG trigger ("for the purpose of this chapter") followed by "shall
    have meanings as follows:", then lettered, quoted entries each with a
    recognized idiom ("means"). ROOT CAUSE: `_STRONG_CONNECTOR_RE`'s
    fixed connector vocabulary recognizes ONLY `(the following terms?)
    mean(s)` or `the term`/`a`/`an`, immediately followed (after an
    optional leading comma) by an optional colon -- "shall have meanings
    as follows:" matches none of those alternatives, so every connector
    sub-group matches zero-width and the trailing `(?P<colon>:)?` group
    is tried at "shall have...", not at the colon many characters later;
    it fails to match, `saw_colon` is `False`, and `_single_entry` is
    tried starting at "shall" -- which is not a quote character, so `[]`
    is returned. The colon EXISTS in this row's text; the connector
    regex's lack of tolerance for arbitrary filler text before it is what
    breaks recognition, not colon-detection itself. Preferred over
    `STATE_NY_ARPP_A8_S280-D` (this cycle's other row that also fails on
    this exact connector phrase, "shall have the following meanings:") --
    see this file's module docstring for why NY is not a valid pin of
    THIS root cause (its terms are entirely unquoted, a separate,
    deliberately-excluded convention)."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_MS_T27_C29_S51-5"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert {"Motor vehicle", "Public highway"} <= terms, (
        "the rule captured nothing from 'for the purpose of this chapter, shall "
        'have meanings as follows:\\n\\n(a) "Motor vehicle" means...\' -- the '
        "\"shall have meanings as follows\" connector phrase is not in the "
        f"recognized connector vocabulary -- got {candidates!r}"
    )


def test_intervening_citation_with_nested_parenthetical_breaks_recognition_oregon():
    """`STATE_OR_T62_C835_S835.200`: `"(4) As used in this section and ORS
    835.210 (Application by political subdivision for special
    regulation) , "seaplane" means an aircraft equipped to land on
    water."` -- SAME root cause as QA's already-pinned DE row
    (`test_intervening_secondary_citation_clause_breaks_recognition_
    delaware`): `_STRONG_CONNECTOR_RE` has zero tolerance for text
    between the unit word and the connector/colon, so an "and
    <citation>" clause inserted before the quoted term breaks recognition
    the same way. Added as a SECOND, independent confirmation (a
    Planner judgement call, not required by the QA brief) because this
    row's citation shape genuinely differs from DE's/OH's plain-prose
    citations: OR nests a nested parenthetical INSIDE the citation itself
    (`"(Application by political subdivision for special regulation)"`)
    and places an unusual space before the following comma (`") , "`)
    directly ahead of the quote -- a shape that could stress a
    citation-tolerance fix differently than DE's/OH's simpler `"and
    [citation] of this/the title/Code, "` pattern (e.g. a fix that skips
    past "and <citation>" up to the next comma could mishandle the
    embedded `)` or the non-adjacent comma in a way the DE/OH shape never
    exposes)."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_OR_T62_C835_S835.200"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "seaplane" in terms, (
        "the rule captured nothing from 'As used in this section and ORS 835.210 "
        '(Application by political subdivision for special regulation) , '
        '"seaplane" means...\' -- the intervening citation clause (with a nested '
        f"parenthetical) broke recognition -- got {candidates!r}"
    )
