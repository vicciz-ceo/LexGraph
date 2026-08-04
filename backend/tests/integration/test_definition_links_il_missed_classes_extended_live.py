"""Sprint 2026-08-04-defs-il (program 2026-08-04-definition-completeness),
Planner-authored RED tests, PHASE-B RESUMPTION (re-specced against the
AUTHORITATIVE seam v2.5, `docs/sprint/sprints/2026-08-04-defs-core-scope-seam.md`).

This file is ADDITIVE to (never edits) `test_definition_links_il_missed_
classes_live.py`, which the prior Planner instance authored and which is
NOT this Planner's to touch (prior ruling R2). It covers ground that file
does not:

1. Class (a)'s בסימן זה / בחלק זה sub-cases (סימן/חלק scope-trigger
   variants of the already-proven בפרק זה quote-first grammar) --
   CAPTURE only. See the sprint log for why containment (a full gate-I3
   proof, the way `test_definition_links_il_chapter_scope_live.py` proves
   it for בפرק זה) is a SEPARATE, currently-unwired architecture question
   (escalation, not a Planner decision) -- these tests deliberately do not
   assert on any `USES_DEFINITION` edge.
2. Class (c)'s בחלק זה ad-hoc-parenthetical sub-case (same trigger-word
   widening as class (a), different grammar: `(TRIGGER - term)`, no
   quotes).
3. A SIXTH class, not in the dossier's four and not in the fifth class the
   prior Planner found: `בפרט זה` ("for this item") -- ITEM-scoped
   definitions living as `::-` double-colon nested-list entries, reachable
   today only because core's bare-`@` parser fix (M8(a)) landed; CAPTURE of
   the reachable content is this sprint's own responsibility (program
   manager ruling P-E3, correcting this panel's own earlier, wrong E5
   framing -- see the log entry "UNBLOCKED: core merged; E1/E5 answered;
   my E5 framing CORRECTED").

Live re-confirmation (this Planner, before writing this file) for every
fixture below -- see the log's "v2 -> v2.5 re-spec" entry for the full
corpus-grep transcripts, including the finding that the dossier/contract's
`לפרק זה` (as a class-(a) quote-first scope trigger) does NOT reproduce
anywhere in the real corpus (103 raw occurrences checked; all are
cross-references like `סימן ג' לפרק זה` / `התוספת לפרק זה`, zero in the
"TRIGGER, \"term\" - definition" definitional grammar) -- `לפרק זה` is
therefore DROPPED from this sprint's trigger-phrase spec, not carried
forward from the original contract wording.
"""

from __future__ import annotations

import pathlib

from tests.conftest import matter_with_users  # noqa: F401  (fixture import)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_class_a_besiman_zeh_scoped_quoted_definition_is_captured(db_session, matter_with_users):
    """Class (a) sub-case -- `בסימן זה` (siman/"section-group"-scoped),
    same quote-first grammar as the already-proven `בפרק זה` trigger.

    Live re-confirmation: `חוק איסור מימון טרור` article 31's real body
    (after `normalize_for_parsing` + `strip_wikilinks`, via
    `sections.parse_articles`) contains, verbatim:
    `[[בסימן זה]], "בית המשפט" - בית המשפט שאליו הוגש כתב האישום או
    שאליו יוגש כתב האישום או בית המשפט שאליו הוגשה או שאליו תוגש הבקשה
    לחילוט בהליך אזרחי, לפי הענין.` -- `extract_local_definitions` (the
    function `pipeline.py`'s ordinary-article path reaches for a non-
    הגדרות-headed article, article 31's heading `סמכות למתן סעדים
    זמניים` is not a הגדרות heading) returns `[]` on this body; neither
    `_LOCAL_TRIGGER_RE` nor `_ADHOC_RE` recognizes `בסימן זה`. Corpus-wide
    live scan (through the real `sections.parse_articles`, not a raw-text
    grep): 63 raw `בסימן זה, "..." -` occurrences corpus-wide (this
    Planner's own re-confirmation, logged).

    CAPTURE only -- deliberately does not assert on `USES_DEFINITION`
    edges or pin a `scope` value. See the sprint log for why full
    containment enforcement for `סימן` is a separate, open architecture
    question (the registered `StructuralUnitRule`/`heading_breadcrumbs`
    machinery exists in `rules/registry.py` and is unit-tested, but has
    ZERO production callers -- `sections.py` never captures
    `heading_breadcrumbs` and `pipeline.py` never populates
    `MatcherArticle.structural_units` -- so no rule module, however
    written, can make a `סימן`-scoped definition link on the live
    pipeline path today).
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק איסור מימון טרור, התשס"ה-2005',
        wiki_text=_read("חוק איסור מימון טרור_art31_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    court_defs = [d for d in result["created_definitions"] if "בית המשפט" in d["terms"]]
    assert len(court_defs) == 1, (
        f'expected a Definition row for the בסימן זה-scoped term '
        f'"בית המשפט" (article 31); got {result["created_definitions"]!r}'
    )


def test_class_a_bechelek_zeh_scoped_quoted_definition_is_captured(db_session, matter_with_users):
    """Class (a) sub-case -- `בחלק זה` (chelek/"part"-scoped), same
    quote-first grammar.

    Live re-confirmation: `חוק השיפוט הצבאי` article 159א's real body
    (heading `חוות דעת מטעם הנאשם...` -- not a הגדרות heading) contains
    `[[בחלק זה]], "הוראת פרקליט" - הוראה של פרקליט צבאי או של הפרקליט
    הצבאי הראשי, ...`. `extract_local_definitions` returns `[]` on this
    body (same reason as the סימן case above). 29 raw `בחלק זה, "..." -`
    occurrences found corpus-wide by this Planner's live scan.

    CAPTURE only -- same containment caveat as the סימן test above.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק השיפוט הצבאי, התשט"ו-1955',
        wiki_text=_read("חוק השיפוט הצבאי_art159א_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    prosecutor_order_defs = [
        d for d in result["created_definitions"] if "הוראת פרקליט" in d["terms"]
    ]
    assert len(prosecutor_order_defs) == 1, (
        f'expected a Definition row for the בחלק זה-scoped term '
        f'"הוראת פרקליט" (article 159א); got {result["created_definitions"]!r}'
    )


def test_class_c_adhoc_parenthetical_bechelek_zeh_marker_is_captured(db_session, matter_with_users):
    """Class (c) sub-case -- ad-hoc parenthetical `(בחלק זה - X)`, the
    SAME real article as the quote-first test above (one fixture, two
    distinct grammars, both live-confirmed in the same body -- efficient
    corpus reuse, not a coincidence of authoring).

    Live re-confirmation: `חוק השיפוט הצבאי` article 159א's real body
    also contains `... לרבות חוות דעת שהוכנה בידי סניגור ([[בחלק זה]] -
    חוות דעת);` -- an unquoted apposition definition, `_ADHOC_RE`-shaped
    (`(TRIGGER - term)`) but with trigger word `בחלק זה`, which
    `_ADHOC_RE` (extract.py:33, `להלן`-only) does not recognize.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק השיפוט הצבאי, התשט"ו-1955',
        wiki_text=_read("חוק השיפוט הצבאי_art159א_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    opinion_defs = [d for d in result["created_definitions"] if "חוות דעת" in d["terms"]]
    assert len(opinion_defs) == 1, (
        f'expected a Definition row for the ad-hoc בחלק זה-scoped term '
        f'"חוות דעת" (article 159א); got {result["created_definitions"]!r}'
    )


def test_sixth_class_beprat_zeh_item_scoped_double_colon_entries_are_captured(
    db_session, matter_with_users
):
    """A SIXTH missed class (program manager ruling P-E3, correcting this
    panel's own earlier, WRONG E5 framing -- see the log's "my E5 framing
    CORRECTED" entry): `בפרט זה -` ("for this item") introduces
    ITEM-scoped definitions living as `::-` double-colon nested-list
    entries, inside an ORDINARY (non-הגדרות-headed) article body reached
    only via core's bare-`@` parser fix (M8(a)).

    Fixture: the EXACT vendored fixture already on `main`,
    `רשימת הזכויות לפי חוק לקידום התחרות ולצמצום הריכוזיות_excerpt.wiki`
    -- one bare-`@` article (synthetic number `@1`, empty heading, so
    `is_definitions_heading("") is False` -- ordinary-article path).
    Real body (verbatim, after normalize+strip-wikilinks via the real
    `sections.parse_articles` -- re-confirmed live by this Planner):
    ```
    : (3) בקשות לרישיון שניתן למבקש שאין בידיו או בידי צד הקשור לו רישיון
    נוסף בקטגוריה או בסיווג המבוקשים, ...ולא פעילות ייצור מקומית בקטגוריה
    או סיווג אלה, בפרט זה -
    ::- "סיווג" - סיווג המנוי בסעיף 271א(ד) לתקנות התעבורה;
    ::- "צד קשור" - אדם או תאגיד השולטים במבקש הבקשה, או תאגיד הנשלט על
    ידי השולט במבקש;
    ::- "קטגוריה" - קטגוריה המנויה בסעיף 271א(א) לתקנות התעבורה, לרבות
    "רכב תפעולי" כהגדרתו בסעיף 95א לתקנות התעבורה;
    ::- "שליטה" - כהגדרתה בחוק ניירות ערך, התשכ"ח-1968 (להלן - חוק ניירות
    ערך), במישרין או בעקיפין.
    ```
    `extract_local_definitions`/`extract_adhoc_definitions` both return
    `[]` on this body: neither recognizes `בפרט זה` as a trigger, and
    even if `בפרט זה` were added to `_LOCAL_TRIGGER_RE`'s alternation
    verbatim, that regex's grammar is single-line `TRIGGER, "term" -
    definition$` -- it cannot reach a PREAMBLE line (`בפרט זה -`,  no
    quoted term of its own) followed by N separate `::-`-marked entries
    on their OWN following lines; this needs its own preamble+entry-list
    grammar, not a trigger-list widening (unlike classes a/b/c).

    Live corpus scan (this Planner, before writing this test): the exact
    shape `בפרט זה -` immediately followed by a `::-`-marked line occurs
    in 7 real corpus files (a live re-measurement of the log's own
    "~8-12 files" estimate -- reported as the more precise, freshly-
    measured number, not a contradiction of it). `בפרט זה` as a bare
    phrase (any grammar, including the differently-shaped ad-hoc
    `(להלן בפרט זה - X)` apposition variant seen in `תקנות התעבורה`
    article 8א -- NOT this test's shape, left for a future item) appears
    in 68 files / 199 occurrences corpus-wide.

    CAPTURE only, all four terms in one entry list -- deliberately does
    not assert `USES_DEFINITION` edges or pin a `scope` value, same
    discipline as the fifth class's own test (containment for this
    below-article granularity has the same open architecture question --
    `resolve_unit_path`'s only recognized IL below-article marker is the
    literal phrase `סעיף קטן (X)`, which does not occur anywhere in this
    fixture's own numbered/colon-indented list convention).
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="רשימת הזכויות לפי חוק לקידום התחרות ולצמצום הריכוזיות",
        wiki_text=_read(
            "רשימת הזכויות לפי חוק לקידום התחרות ולצמצום הריכוזיות_excerpt.wiki"
        ),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    expected_terms = {"סיווג", "צד קשור", "קטגוריה", "שליטה"}
    assert expected_terms <= captured_terms, (
        f"expected all four בפרט זה-scoped terms {expected_terms!r} to be "
        f"captured; got {captured_terms!r} (created_definitions="
        f"{result['created_definitions']!r})"
    )
