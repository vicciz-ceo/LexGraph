"""Sprint 2026-08-04-defs-il (program 2026-08-04-definition-completeness),
Planner-authored RED set for QA cycle 1's confirmed I4 FAIL (see the log's
`## QA cycle 1` entry, the manager's ACCEPTED verdict, and the D-Q1
regulation-scope closure -- all read in full before this file was written).
Per program rule (the RED-provenance gate), a Developer may not run on QA's
findings until each bounced item has a committed RED test here.

Live re-confirmed (this Planner, before writing a single test, per ruling
M4/M10 -- never trusting a prior role's report, always calling the real
`sections.parse_articles` -> `normalize_for_parsing` -> `strip_wikilinks` ->
`profile.extract_local_scope_definitions` chain directly first): every
fixture below reproduces exactly as QA's log entry describes.

Three groups, matching the manager's classification of what is BUILDABLE
NOW (this whole file -- everything here uses the already-live, already-
wired `ScopeTriggerRule` mechanism; nothing here is E6/E7-blocked):

1. **Group A -- 8 new/unimplemented single-line quote-first trigger
   families** (below), one test each, capture-only (this sprint's
   established discipline throughout -- scope kind is specified in the
   contract's item text, not asserted here).
2. **Group B -- ONE mechanism-level test** generalizing the `::-`
   nested-list-under-preamble shape item 9's rule already proves reachable
   for `בפרט זה`, to ANY preceding trigger text (program efficiency
   directive: one item serving ~2,288 occurrences, not per-trigger tests).
3. **Three precision RED tests** for the confirmed false positives in the
   LIVE `il_adhoc_scope_triggers` rule -- citation-shorthand labels
   (`סעיף 149א`/`סעיף 51טו`/`סעיף 9`) captured as if they were substantive
   defined terms. Each asserts the citation term is NOT captured -- FAILS
   today because it IS captured (manager's own framing: "a test that FAILS
   while the citation is captured").

Yod/tzere audit (manager-requested, "assume the bug is everywhere until
proven otherwise"): read all six of this sprint's shipped IL rule modules
plus the original `il_scope_triggers.py`. Only `extract._LOCAL_TRIGGER_RE`
(the frozen 2-word `לענין זה`/`בסעיף זה` trigger, wrapped unchanged by
`il_scope_triggers.py`) has the yod-only hole -- covered by Group A test 1
below. `il_seif_zeh_three_word_scope_triggers.py` (item 3) ALREADY covers
both spellings correctly (`(?:לענין|לעניין) סעיף זה`) -- no gap. The other
four shipped rules' trigger words (`בפרק זה`/`בסימן זה`/`בחלק זה`/`בפסקה
זו`/`בפרט זה`) do not use the `לענין`/`לעניין` word at all, so the
yod/tzere spelling pair does not apply to them -- confirmed by direct
source read, not assumed.
"""

from __future__ import annotations

import pathlib

from tests.conftest import matter_with_users  # noqa: F401  (fixture import)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _ingest_and_link(db_session, matter_with_users, *, title: str, fixture: str) -> dict:
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=title,
        wiki_text=_read(fixture),
    )
    return run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )


# --- Group A -- 8 new/unimplemented single-line quote-first trigger families ---


def test_lenyan_zeh_tzere_spelling_two_word_trigger_is_captured(db_session, matter_with_users):
    """QA cycle 1's headline finding, the canonical P-R7 lesson: `לעניין
    זה` (TZERE spelling) is a completely different string from `לענין זה`
    (YOD spelling) to a regex -- `extract._LOCAL_TRIGGER_RE` has covered
    only the yod spelling since before this whole sprint. Live-verified:
    1,563 ordinary-article occurrences / 714 files corpus-wide (QA's
    trigger-independent sweep); this Planner's own audit of all six
    shipped IL rule modules confirms the hole exists ONLY here -- no other
    rule's trigger words use the לענין/לעניין word at all.

    Fixture: real excerpt, `הוראות הפיקוח על שירותים פיננסיים (ביטוח)
    (ביטוח אובדן כושר עבודה קבוצתי)` article 3 -- `... לעניין זה, "ביטוח
    מועדף" - כהגדרתו בסעיף 32(14) לפקודת מס הכנסה.` (QA's own cited
    example). `extract_local_definitions`/`extract._LOCAL_TRIGGER_RE`
    yields `[]` for this body; this Planner's live probe confirms it
    (`profile.extract_local_scope_definitions` -> `[]`).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='הוראות הפיקוח על שירותים פיננסיים (ביטוח) (ביטוח אובדן כושר עבודה קבוצתי), תשפ"ב',
        fixture="הוראות הפיקוח על שירותים פיננסיים (ביטוח) (ביטוח אובדן כושר עבודה קבוצתי)_art3_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "ביטוח מועדף" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the tzere-spelled לעניין זה-scoped '
        f'term "ביטוח מועדף" (article 3); got {result["created_definitions"]!r}'
    )


def test_betakana_zo_regulation_local_trigger_is_captured(db_session, matter_with_users):
    """`בתקנה זו, "term" - definition` -- a completely NEW regulation-
    level trigger, entirely unimplemented before this cycle. D-Q1 closed
    the scope question by evidence: `sections.parse_articles` over real
    regulation files gives `תקנה` units as `Article` rows, so this is
    `scope="local"`, enforceable by existing machinery -- no modelling
    gap, ship now. 427 real ordinary-article occurrences / 289 files
    corpus-wide (QA's sweep).

    Fixture: `צו הבטיחות בעבודה (אגרות בדיקה)` article 6 (real, verbatim):
    `בתקנה זו, "מדד" - מדד המחירים לצרכן שמפרסמת הלשכה המרכזית
    לסטטיסטיקה.` -- `extract_local_definitions` yields `[]` (no trigger
    in `_LOCAL_TRIGGER_RE`'s alternation recognizes `בתקנה זו`).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="צו הבטיחות בעבודה (אגרות בדיקה)",
        fixture="צו הבטיחות בעבודה (אגרות בדיקה)_art6_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "מדד" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the בתקנה זו-scoped term "מדד" '
        f"(article 6); got {result['created_definitions']!r}"
    )


def test_beseif_katan_zeh_subsection_trigger_is_captured(db_session, matter_with_users):
    """`בסעיף קטן זה, "term" - definition` -- a NEW subsection-scoped
    trigger. D-Q1: subsection-level, which the seam's `UnitPath`/
    `resolve_unit_path` already models (this test asserts CAPTURE only,
    per this sprint's established discipline -- containment is a separate
    concern the contract item addresses, not this RED test's job). 313
    real ordinary-article occurrences / 213 files (QA's sweep).

    Fixture: `החלטת הרשויות המקומיות (גמלאות לראש רשות וסגניו)` article
    29ב (real, verbatim): `... בסעיף קטן זה, "המדד" - מדד המחירים לצרכן
    שמפרסמת הלשכה המרכזית לסטטיסטיקה.` -- note this SAME article already
    captures a DIFFERENT term ("יום העדכון") via the already-shipped
    `בפסקה זו` ad-hoc rule (item 10); this test targets the STILL-missing
    `"המדד"` capture specifically, live-confirmed by this Planner
    (`extract_local_scope_definitions` -> `[('יום העדכון',)]`, i.e.
    `"המדד"` absent).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='החלטת הרשויות המקומיות (גמלאות לראש רשות וסגניו)',
        fixture="החלטת הרשויות המקומיות (גמלאות לראש רשות וסגניו)_art29ב_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "המדד" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the בסעיף קטן זה-scoped term '
        f'"המדד" (article 29ב); got {result["created_definitions"]!r}'
    )


def test_lenyan_takana_zo_three_word_regulation_trigger_is_captured(db_session, matter_with_users):
    """`לעניין תקנה זו, "term" - definition` -- the 3-word regulation-
    local variant (mirrors item 3's 2-word-vs-3-word relationship for
    `לענין זה`/`לענין סעיף זה`). D-Q1: `scope="local"` (same regulation-
    as-Article evidence as `בתקנה זו`). 104 real ordinary-article
    occurrences / 90 files (QA's sweep, both spellings combined). This
    test uses the TZERE spelling (`לעניין`) -- the rule's own trigger
    alternation must cover BOTH spellings (per the canonical lesson
    above), same precedent as item 3's already-correct
    `(?:לענין|לעניין) סעיף זה`.

    Fixture: `תקנות בריאות העם (דיגום וביצוע בדיקות קורונה)` article 14
    (real, verbatim): `... לעניין תקנה זו, "ציוד רפואי" - כהגדרתו בחוק
    ציוד רפואי, התשע"ב-2012` -- live-confirmed `[]` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='תקנות בריאות העם (דיגום וביצוע בדיקות קורונה), תשפ"ב',
        fixture="תקנות בריאות העם (דיגום וביצוע בדיקות קורונה)_art14_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "ציוד רפואי" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the לעניין תקנה זו-scoped term '
        f'"ציוד רפואי" (article 14); got {result["created_definitions"]!r}'
    )


def test_betakanat_mishne_zo_sub_regulation_trigger_is_captured(db_session, matter_with_users):
    """`בתקנת משנה זו, "term" - definition` -- a NEW sub-regulation-scoped
    trigger. D-Q1: subsection-level (`UnitPath`-modeled), ship now,
    capture-only per this sprint's discipline. 83 real ordinary-article
    occurrences / 68 files (QA's sweep).

    Fixture: `תקנות שירות הביטחון הכללי (סייגים בקרבת משפחה)` article 4
    (real, verbatim): `... בתקנת משנה זו, "קרוב משפחה" - אב, אם, בן, בת,
    אח או אחות.` -- live-confirmed `[]` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות שירות הביטחון הכללי (סייגים בקרבת משפחה)",
        fixture="תקנות שירות הביטחון הכללי (סייגים בקרבת משפחה)_art4_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "קרוב משפחה" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the בתקנת משנה זו-scoped term '
        f'"קרוב משפחה" (article 4); got {result["created_definitions"]!r}'
    )


def test_takanat_mishne_zo_bare_sub_regulation_trigger_is_captured(db_session, matter_with_users):
    """`תקנת משנה זו` (BARE, no leading `ב`) -- QA's sweep found this as
    its own distinct family from `בתקנת משנה זו` (both real, both
    unimplemented): `לעניין תקנת משנה זו, "term" - definition`. Same
    D-Q1 subsection-level classification, capture-only. 42 real
    ordinary-article occurrences / 39 files.

    Fixture: `תקנות צער בעלי חיים (הגנה על בעלי חיים) (החזקה שלא לצרכים
    חקלאיים)` article 26 (real, verbatim): `... לעניין תקנת משנה זו,
    "משקל כולל" - המשקל העצמי של הכרכרה או העגלה בתוספת משקל המטען
    והנוסעים שעליה.` -- live-confirmed `[]` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות צער בעלי חיים (הגנה על בעלי חיים) (החזקה שלא לצרכים חקלאיים)",
        fixture="תקנות צער בעלי חיים (הגנה על בעלי חיים) (החזקה שלא לצרכים חקלאיים)_art26_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "משקל כולל" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the bare תקנת משנה זו-scoped term '
        f'"משקל כולל" (article 26); got {result["created_definitions"]!r}'
    )


def test_lenyan_paragraph_zo_alt_phrasing_trigger_is_captured(db_session, matter_with_users):
    """`לעניין פסקה זו, "term" - definition` -- an alternate phrasing of
    the already-shipped `בפסקה זו` trigger (item 7), not covered by that
    rule's exact-phrase regex. Semantically the same "narrower than local"
    granularity item 7 already registers (`scope="paragraph"`) -- this
    Planner's own inference (D-Q1's explicit ruling covers the tekana/
    subsection families but does not separately re-state this one;
    flagged in the log as an inference, not guessed at silently). 121
    real ordinary-article occurrences / 98 files (QA's sweep, both
    spellings combined) -- 11 more sit inside a הגדרות-heading section,
    E6-blocked, not this test's concern.

    Fixture: `הוראות הבחירות לכנסת (סדרי הצבעה...)` article 5 (real,
    verbatim): `... לעניין פסקה זו, "מזוודת החומר הרגיש" - מזוודה הכוללת
    את הציוד המנוי בפסקאות (5), (10) ו-(13) עד (20) של תקנה 33(ב)
    לתקנות הבחירות לכנסת.` -- live-confirmed `[]` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="הוראות הבחירות לכנסת (סדרי הצבעה והוראות בדבר הצבעה בקלפיות לחייבים בבידוד בבחירות לכנסת ה-25)",
        fixture="הוראות הבחירות לכנסת (סדרי הצבעה והוראות בדבר הצבעה בקלפיות לחייבים בבידוד בבחירות לכנסת ה-25)_art5_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "מזוודת החומר הרגיש" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the לעניין פסקה זו-scoped term '
        f'"מזוודת החומר הרגיש" (article 5); got {result["created_definitions"]!r}'
    )


def test_beparagraph_mishne_zo_sub_paragraph_trigger_is_captured(db_session, matter_with_users):
    """`בפסקת משנה זו, "term" - definition` -- a NEW sub-paragraph-scoped
    trigger. D-Q1: subsection-level (`UnitPath`-modeled), capture-only.
    59 real ordinary-article occurrences / 46 files (QA's sweep).

    Fixture: `פקודת מס הכנסה` article 87ה (real, verbatim): `... מקרובו;
    בפסקת משנה זו, "קרוב" - כהגדרתו בסעיף 88;` -- live-confirmed `[]`
    today (`extract_local_definitions`/`extract_adhoc_definitions` both
    miss this quote-first grammar inside a numbered sub-list item).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="פקודת מס הכנסה",
        fixture="פקודת מס הכנסה_art87ה_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "קרוב" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the בפסקת משנה זו-scoped term '
        f'"קרוב" (article 87ה); got {result["created_definitions"]!r}'
    )


# --- Group B -- ONE mechanism-level test for the ::- nested-list generalization ---


def test_colon_dash_nested_list_shape_is_captured_for_an_already_implemented_trigger_word(
    db_session, matter_with_users
):
    """QA cycle 1's Group B, program efficiency directive (binding): ONE
    well-tested MECHANISM item, not per-trigger items. 2,300 occurrences
    corpus-wide of a bare preamble line ending `-` immediately followed by
    `::-`-marked entry lines; only 12 (0.5%) captured today -- item 9's
    rule already proves this SHAPE is reachable via `ScopeTriggerRule`,
    but it is hardcoded to the single trigger word `בפרט זה`. This test
    uses `בסעיף זה` -- an ALREADY-implemented trigger word for the
    single-line quote-first grammar -- specifically to prove the miss is
    about the LIST SHAPE, not about trigger-word coverage: even a trigger
    this sprint has fully implemented for one grammar still misses the
    SAME term when its quote sits on a separate `::-` line instead of
    inline.

    Fixture: `החלטת מימון מפלגות (יחידות מימון ומועדי תשלום)` article 2
    (real, verbatim, the EXACT law/article QA's own log cites):
    ```
    : (א) בסעיף זה -
    ::- "מדד" - מדד המחירים לצרכן המתפרסם מדי פעם מטעם הלשכה המרכזית לסטטיסטיקה;
    ::- "מדד יסודי" - המדד לחודש מאי 1991.
    ```
    Live-confirmed by this Planner: `profile.extract_local_scope_
    definitions` on this real, normalized, wikilink-stripped body -> `[]`
    -- both `"מדד"` and `"מדד יסודי"` genuinely dropped, despite `בסעיף
    זה` being a trigger word THIS SPRINT ALREADY IMPLEMENTS for the
    inline quote-first and ad-hoc-parenthetical grammars.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='החלטת מימון מפלגות (יחידות מימון ומועדי תשלום)',
        fixture="החלטת מימון מפלגות (יחידות מימון ומועדי תשלום)_art2_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    expected_terms = {"מדד", "מדד יסודי"}
    assert expected_terms <= captured_terms, (
        f"expected both ::- -listed, בסעיף זה-scoped terms {expected_terms!r} "
        f"to be captured; got {captured_terms!r} (created_definitions="
        f"{result['created_definitions']!r})"
    )


# --- Precision REDs -- 3 confirmed false positives in the LIVE ad-hoc rule ---


def test_adhoc_rule_does_not_capture_citation_shorthand_seif_9(db_session, matter_with_users):
    """QA cycle 1's confirmed false positive #1 (0.08% of 3,605 live
    candidates from the already-shipped `il_adhoc_scope_triggers` rule):
    `(בסעיף זה - סעיף 9)` is a citation-shorthand-naming convention
    ("hereinafter in this section: 'section 9'"), not a substantive term
    definition -- the SAME apposition grammar the rule trusts, aimed at a
    cross-reference instead of a concept. Precision RED (manager's own
    framing): this test FAILS while the citation is captured.

    Fixture: `חוק התוכנית הכלכלית (תיקוני חקיקה ליישום המדיניות הכלכלית
    לשנות התקציב 2023 ו-2024)` article 33 (real, verbatim): `... כאמור
    בפרק זה (בסעיף זה - סעיף 9), ...`. Live-confirmed by this Planner:
    the LIVE registered rule captures `terms=("סעיף 9",)` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='חוק התוכנית הכלכלית (תיקוני חקיקה ליישום המדיניות הכלכלית לשנות התקציב 2023 ו-2024), תשפ"ד',
        fixture="חוק התוכנית הכלכלית (תיקוני חקיקה ליישום המדיניות הכלכלית לשנות התקציב 2023 ו-2024)_art33_excerpt.wiki",
    )
    citation_defs = [d for d in result["created_definitions"] if "סעיף 9" in d["terms"]]
    assert not citation_defs, (
        f'the citation-shorthand label "סעיף 9" (article 33) must NOT be '
        f'captured as a substantive defined term -- it is a cross-reference '
        f'naming convention, not a definition; got {citation_defs!r}'
    )


def test_adhoc_rule_does_not_capture_citation_shorthand_seif_149a(db_session, matter_with_users):
    """QA cycle 1's confirmed false positive #2: `(בסעיף זה – סעיף 149א)`
    -- same citation-shorthand shape as above, different law. Precision
    RED: FAILS while the citation is captured.

    Fixture: `חוק ההתייעלות הכלכלית (תיקוני חקיקה להשגת יעדי התקציב לשנת
    התקציב 2019)` article 34 (real, verbatim): `... כנוסחו בחוק זה
    (בסעיף זה – סעיף 149א);`. Live-confirmed: the LIVE registered rule
    captures `terms=("סעיף 149א",)` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="חוק ההתייעלות הכלכלית (תיקוני חקיקה להשגת יעדי התקציב לשנת התקציב 2019)",
        fixture="חוק ההתייעלות הכלכלית (תיקוני חקיקה להשגת יעדי התקציב לשנת התקציב 2019)_art34_excerpt.wiki",
    )
    citation_defs = [d for d in result["created_definitions"] if "סעיף 149א" in d["terms"]]
    assert not citation_defs, (
        f'the citation-shorthand label "סעיף 149א" (article 34) must NOT be '
        f'captured as a substantive defined term; got {citation_defs!r}'
    )


def test_adhoc_rule_does_not_capture_citation_shorthand_seif_51tet_vav(
    db_session, matter_with_users
):
    """QA cycle 1's confirmed false positive #3: `(בסעיף זה - סעיף
    51טו)`. Precision RED: FAILS while the citation is captured.

    Fixture: `חוק המדיניות הכלכלית לשנים 2011 ו-2012 (תיקוני חקיקה)`
    article 39 (real, verbatim): `... כנוסחו בסעיף 37(32) לחוק זה (בסעיף
    זה - סעיף 51טו), יחולו -`. Live-confirmed: the LIVE registered rule
    captures `terms=("סעיף 51טו",)` today (alongside the genuine, correct
    `"יום התחילה"` capture earlier in the same article -- this test does
    NOT object to that one, only to the citation-shaped capture).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="חוק המדיניות הכלכלית לשנים 2011 ו-2012 (תיקוני חקיקה)",
        fixture="חוק המדיניות הכלכלית לשנים 2011 ו-2012 (תיקוני חקיקה)_art39_excerpt.wiki",
    )
    citation_defs = [d for d in result["created_definitions"] if "סעיף 51טו" in d["terms"]]
    assert not citation_defs, (
        f'the citation-shorthand label "סעיף 51טו" (article 39) must NOT be '
        f'captured as a substantive defined term; got {citation_defs!r}'
    )
