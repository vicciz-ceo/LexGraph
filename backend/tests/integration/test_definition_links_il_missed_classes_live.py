"""Sprint 2026-08-04-defs-il (program 2026-08-04-definition-completeness),
Planner-authored RED tests for gate I2 -- the confirmed-missed IL definition
classes, re-confirmed LIVE against real corpus excerpts before this file was
written (see `docs/sprint/sprints/2026-08-04-defs-il-log.md` for the
re-confirmation transcripts, manager ruling M4).

Per manager ruling M2 (two-phase execution: core has published no seam spec
yet), these are BEHAVIORAL, seam-agnostic tests -- they call only the public
`ingest_wiki_law` + `run_definition_linking` pipeline entry points (never
`extract._LOCAL_TRIGGER_RE`, `extract._ADHOC_RE`, or any other frozen-module
internal) and assert on the resulting `Definition` rows the pipeline
returns. Whichever module ends up owning the Hebrew trigger CONTENT after
core's registry lands, these tests still exercise the real end-to-end path
and cannot be invalidated by an internals refactor.

Every fixture here is a REAL, verbatim excerpt copied from
`/Users/nerya/AI for others/israeli-laws-wiki` (read-only POC corpus) into
`backend/tests/fixtures/wiki_laws/` -- no fabricated text, no downloads at
test time.

All five tests below are expected RED right now: each documents the exact
live miss the Planner reproduced by calling the real `extract.py` functions
directly against the corpus before writing this file.
"""

from __future__ import annotations

import pathlib

from tests.conftest import matter_with_users  # noqa: F401  (fixture import)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_class_a_beperek_zeh_scoped_quoted_definition_is_captured(db_session, matter_with_users):
    """Class (a) -- dossier recon §3 / sprint contract item (a).

    Live re-confirmation (Planner, before writing this test): parsing
    `חוק זכות מטפחים של זני צמחים` article 15's real body --
    `(א) [[בפרק זה]], "בקשה" - כל בקשה או התנגדות לפי [[פרקים ד']]
    [[או י']].` -- through `extract.extract_local_definitions` (the
    function `pipeline.py` calls for any non-הגדרות-headed article body)
    returns `[]`. `_LOCAL_TRIGGER_RE` (extract.py:28-30) only recognizes
    the 2-word triggers `לענין זה` / `בסעיף זה`, not `בפרק זה`.
    `extract_adhoc_definitions` also returns `[]` on the same body (the
    `"term" -` shape here is quote-first, not `(TRIGGER - term)`, so it is
    not `_ADHOC_RE`'s shape either).

    Corpus frequency of this exact `TRIGGER, "term" - definition` shape
    across בפרק זה/בסימן זה/בחלק זה/לפרק זה (Planner's own broader corpus
    grep, logged in the sprint log): 154+ distinct real occurrences beyond
    this one file -- not an isolated example.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="חוק זכות מטפחים של זני צמחים, התשל״ג-1973",
        wiki_text=_read("חוק זכות מטפחים של זני צמחים_ch3_ch4_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    bakasha_defs = [d for d in result["created_definitions"] if "בקשה" in d["terms"]]
    assert len(bakasha_defs) == 1, (
        f"expected a Definition row for the בפרק זה-scoped term \"בקשה\" "
        f"(article 15); got {result['created_definitions']!r}"
    )


def test_class_b_le_inyan_seif_zeh_three_word_variant_is_captured(db_session, matter_with_users):
    """Class (b) -- dossier recon §3 / sprint contract item (b).

    Live re-confirmation: `חוק איסור הלבנת הון` article 3's real body
    contains `לענין סעיף זה, "מסירת מידע כוזב" - לרבות אי מסירת עדכון
    של פרט החייב בדיווח.` -- `extract_local_definitions` on the FULL
    article-3 body returns `[]`. `_LOCAL_TRIGGER_RE` hardcodes the 2-word
    `לענין זה`, not the 3-word `לענין סעיף זה` (nor its `לעניין` spelling
    variant). Planner's corpus grep found 255+ distinct real occurrences
    of this exact 3-word-trigger quote-dash shape corpus-wide.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק איסור הלבנת הון, התש"ס-2000',
        wiki_text=_read("חוק איסור הלבנת הון_art3_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    false_report_defs = [
        d for d in result["created_definitions"] if "מסירת מידע כוזב" in d["terms"]
    ]
    assert len(false_report_defs) == 1, (
        f'expected a Definition row for the 3-word-triggered term '
        f'"מסירת מידע כוזב" (article 3); got {result["created_definitions"]!r}'
    )


def test_class_c_adhoc_parenthetical_beperek_zeh_marker_is_captured(db_session, matter_with_users):
    """Class (c) -- dossier recon §3 / sprint contract item (c).

    Live re-confirmation with a CORRECTION to the dossier's cited example
    (manager ruling M4: "a class that reproduces DIFFERENTLY than the
    dossier says -- report the difference; the live observation wins"):
    the dossier cites `חוק רכבת תחתית (מטרו)` article 13, but that
    article's real body contains NO `(בפרק זה - X)` / `(בסימן זה - X)`
    marker anywhere (grepped the full raw file -- zero matches for that
    shape near article 13). The class itself DOES reproduce, broadly,
    elsewhere in the corpus -- 709+ distinct real
    `([[בפרק זה/בסימן זה/בחלק זה]] - X)` parenthetical markers found by
    the Planner's corpus-wide grep, e.g. `חוק החברות הממשלתיות` article
    50א's real body: `... שהוא בן העדה הדרוזית ([[בפרק זה]] - ייצוג
    הולם).` -- `extract_adhoc_definitions` on this body returns `[]`
    because `_ADHOC_RE` (extract.py:33) only recognizes the `להלן`
    trigger word, not `בפרק זה`/`בסימן זה`/`בחלק זה`.

    (Separately, `חוק רכבת תחתית (מטרו)` article 19 -- not used as this
    test's fixture, kept out for fixture-size reasons -- gives an even
    sharper live example: `extract_adhoc_definitions` on that body
    correctly captures three OTHER `(להלן - X)` markers in the same
    article while silently dropping the fourth, `([[בפרק זה]] - שומת
    ההשבחה)`, purely because of the different trigger word. See the
    sprint log for the full transcript.)
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק החברות הממשלתיות, התשל"ה-1975',
        wiki_text=_read("חוק החברות הממשלתיות_art50א_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    representation_defs = [
        d for d in result["created_definitions"] if "ייצוג הולם" in d["terms"]
    ]
    assert len(representation_defs) == 1, (
        f'expected a Definition row for the ad-hoc parenthetical term '
        f'"ייצוג הולם" (article 50א); got {result["created_definitions"]!r}'
    )


def test_class_d_prose_body_definitions_section_yields_zero_today(db_session, matter_with_users):
    """Class (d) -- dossier recon §3 / sprint contract item (d), "most
    severe, structural" case: `is_definitions_heading` correctly matches
    the section heading, but the body has no `:-` entry markers at all,
    so `extract_definitions_from_section` silently returns `[]` -- the
    section is FOUND but yields nothing.

    Live re-confirmation with the dossier's own cited example: `חוק
    החברות הממשלתיות` article 16, heading `הגדרה`
    (`is_definitions_heading("הגדרה") == True`), body `[[בפרק זה]],
    "דירקטור" - דירקטור מטעם המדינה בחברה ממשלתית.` --
    `extract_definitions_from_section(body, scope="global")` returns `[]`
    because the body has zero lines starting with `:-`.

    MAJOR SCALE CORRECTION (escalated in the sprint log, not quietly
    absorbed): the dossier characterizes this class via a single example.
    The Planner scanned the FULL 6,133-file corpus for
    `is_definitions_heading(heading) and extract_definitions_from_section
    (body, scope="global") == []` and found **592 real, non-trivial
    instances** (~9.7% of the entire corpus) -- every one inspected has
    substantive definition text, none are repealed/placeholder sections.
    This is the single largest and most severe finding of this sprint's
    recon, not an edge case.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק החברות הממשלתיות, התשל"ה-1975',
        wiki_text=_read("חוק החברות הממשלתיות_art16_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    director_defs = [d for d in result["created_definitions"] if "דירקטור" in d["terms"]]
    assert len(director_defs) == 1, (
        f'expected a Definition row for "דירקטור" from the prose-body '
        f'הגדרה section (article 16); got {result["created_definitions"]!r}'
    )


def test_class_d_variant_double_colon_entry_list_under_a_trigger_preamble_is_captured(
    db_session, matter_with_users
):
    """Class (d), second structural sub-shape found during the corpus-wide
    scan above: a recognized הגדרות-heading section whose body opens with
    a `TRIGGER -` preamble line, followed by entries marked `::-`
    (DOUBLE colon-dash) rather than the top-level `:-` the parser
    requires -- `_ENTRY_START_RE` (extract.py:19) matches `^\\s*:-`, which
    a line starting `::-` never satisfies (the second character is `:`,
    not `-`). Real fixture: `תקנות קרן גרמניה-ישראל למחקר ולפיתוח מדעי
    (פטור ממסים)` article 1 -- heading `הגדרות`, body `(א) בתקנות אלה -`
    followed by four `::-`-marked entries. Live re-confirmation:
    `extract_definitions_from_section` on this body returns `[]` (zero
    blocks -- `_split_into_blocks` never sees a line matching
    `_ENTRY_START_RE`).

    This sub-shape is distinct from the single-sentence sub-shape (the
    prior test) and from a THIRD sub-shape the Planner also found live
    (numbered `: (N) "term" -` entries under a `TRIGGER -` preamble, e.g.
    `הוראות מס הכנסה (ניהול פנקסי חשבונות)` article 27) -- flagged in the
    sprint log as a design question: any fix must be able to tell a
    numbered CONTINUATION of one definition's own text (e.g. a deduction
    formula's sub-items) apart from a numbered LIST of separate defined
    terms, or it will silently fabricate spurious extra definitions.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='תקנות קרן גרמניה-ישראל למחקר ולפיתוח מדעי (פטור ממסים), התשנ"ה-1995',
        wiki_text=_read("תקנות קרן גרמניה-ישראל_art1_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    tax_defs = [d for d in result["created_definitions"] if "מס מעסיקים" in d["terms"]]
    assert len(tax_defs) == 1, (
        f'expected a Definition row for "מס מעסיקים" from the '
        f'"::"-marked entry list under a הגדרות heading (article 1); '
        f'got {result["created_definitions"]!r}'
    )


def test_class_d_minimal_single_sentence_variant_is_captured(db_session, matter_with_users):
    """Class (d), the DOMINANT real-corpus sub-shape by instance count: a
    one-line הגדרה section with a single inline `TRIGGER, "term" -
    definition.` sentence and no list structure at all. Real fixture:
    `צו פיקוח על מחירי מצרכים ושירותים (רמת הפיקוח על חמאה)` article 1,
    heading `הגדרה`, full body `בצו זה, "חמאה" - חמאה רגילה בחבילה.`.
    Live re-confirmation: `extract_definitions_from_section` returns
    `[]` (no `:-` marker). This exact minimal shape (`TRIGGER, "term" -
    definition.`, heading correctly recognized, one sentence, zero list
    markers) recurs verbatim across dozens of the 592 corpus-wide class
    (d) hits the Planner found (see the sprint log's sample dump) --
    this fixture is representative, not cherry-picked.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='צו פיקוח על מחירי מצרכים ושירותים (רמת הפיקוח על חמאה), התשפ"ד-2024',
        wiki_text=_read("צו פיקוח על מחירי מצרכים ושירותים (חמאה)_art1_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    butter_defs = [d for d in result["created_definitions"] if "חמאה" in d["terms"]]
    assert len(butter_defs) == 1, (
        f'expected a Definition row for "חמאה" from the minimal one-'
        f'sentence הגדרה section; got {result["created_definitions"]!r}'
    )


def test_fifth_class_beparagraph_zo_paragraph_scoped_definition_is_captured(
    db_session, matter_with_users
):
    """A FIFTH missed class, not in the dossier's four -- found by the
    Planner while actively sweeping the corpus for scope-trigger phrases
    per manager instruction (M4: "actively look for a fifth class").

    `בפסקה זו, "term" - definition` -- a definition scoped to a single
    numbered PARAGRAPH (subsection) within an ordinary article, i.e. a
    granularity even NARROWER than today's `"local"` (whole-article)
    scope. Corpus frequency: 522 files contain the phrase `בפסקה זו` at
    all. Real fixture: `הוראות מס הכנסה (ניהול פנקסי חשבונות)`, appendix
    `תוספת י"א` article 3, item (8): `... :: בפסקה זו, "בעל מסעדה" -
    לרבות כל בעל עסק המעסיק מלצרים.` Live re-confirmation: both
    `extract_local_definitions` and `extract_adhoc_definitions` return
    `[]` on the real article body (heading `ספרים מיוחדים` is not a
    הגדרות heading, so this routes through the ordinary-article path).

    This class is directly on-point for the director's own mandate
    wording ("relevant only to specific articles or subsections") and is
    a strong candidate to feed core-scope's subsection-level-enforcement
    seam once it lands -- see the sprint log's design-question answers
    for why paragraph-level scope cannot be represented in today's schema
    at all (not even the partial support "chapter" scope already has).
    This test only asserts the TERM gets captured; it deliberately does
    NOT pin an expected `scope` value, since the correct scope semantics
    for this class are an open escalation, not a Planner decision.
    """
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="הוראות מס הכנסה (ניהול פנקסי חשבונות), תשל\"ג-1973",
        wiki_text=_read("הוראות מס הכנסה (ניהול פנקסי חשבונות)_besel_mesada_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    restaurant_owner_defs = [
        d for d in result["created_definitions"] if "בעל מסעדה" in d["terms"]
    ]
    assert len(restaurant_owner_defs) == 1, (
        f'expected a Definition row for the בפסקה זו-scoped term '
        f'"בעל מסעדה"; got {result["created_definitions"]!r}'
    )
