"""Sprint 2026-08-04-defs-il (program 2026-08-04-definition-completeness),
Phase C -- Planner-authored RED set for the M15 bundle (see the sprint
contract's `## Next Steps` item 12 / QA cycle 2's `## QA cycle 2` log
entry / manager verdict "M15 -- Phase C scope"). Per the RED-provenance
gate, no Developer may run against these findings until every item below
has a committed, behaviorally RED test.

Four items, all BUILDABLE NOW on the already-live, already-wired
`ScopeTriggerRule` mechanism (none is E6-blocked -- QA cycle 2 measured
and live-confirmed every one of them):

  C1 -- punctuation-variant widening (comma hardcoded across every
        shipped trigger rule, incl. the FROZEN `extract._LOCAL_TRIGGER_RE`;
        the real corpus routinely uses a bare space, and occasionally a
        colon or a dash).
  C2 -- same-line-swallow bug in the FROZEN `extract._LOCAL_TRIGGER_RE`
        (greedy `(.*)$` swallows a second same-line trigger match) --
        must be worked around ADDITIVELY, never by editing the frozen
        regex.
  C3 -- inline `בפרט זה` single-line form (item 9's rule only ever built
        the `::-` LIST shape for this trigger; the plain single-line
        grammar every other trigger word already has was never built).
  C4 -- single-`:-` list generalization (the SAME preamble+list shape
        `il_colon_dash_nested_list_scope_triggers.py` already generalizes
        for the double-colon `::-` marker, reached instead via the
        single-colon `:-` marker), including the `פרשנות` heading-synonym
        sub-case.

Every fixture below was extracted PROGRAMMATICALLY (never hand-retyped)
directly from the read-only corpus via `sections.parse_articles` +
a verbatim `@ N.` marker-line regex, then proven byte-identical to the
corpus source (`fixture_bytes in corpus_source_bytes`) and behaviorally
equivalent to the original, un-trimmed article body (same LIVE captured-
terms set) before being written -- see this Planner's log entry
"Phase C -- fixture byte-verification" for the full transcript of that
proof for every fixture this file uses. Every example below was also
live re-confirmed by this Planner (ruling M4/M10) through the real chain
this file's own tests exercise -- `sections.parse_articles` ->
`profile.normalize_for_parsing` -> `strip_wikilinks` ->
`profile.extract_local_scope_definitions` -- before a single test was
written; the log has the actual output for every one of them.
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


# =====================================================================
# C1 -- punctuation-variant widening (7 families + 1 explicit colon case)
# =====================================================================
#
# Every shipped IL `ScopeTriggerRule` (and the frozen
# `extract._LOCAL_TRIGGER_RE` that `il_scope_triggers.py` wraps
# unchanged) hardcodes a LITERAL COMMA between the trigger phrase and
# the opening quote (`TRIGGER,\s*"..."`). QA cycle 2's corpus-wide
# grammar sweep (trigger phrase immediately followed by 0-3 non-quote
# characters then a quote -- independent of any of our own rules'
# regexes, per P-R7) found the real corpus routinely omits the comma
# (bare space), and occasionally uses a colon or a dash instead. This
# Planner independently re-derived the same population directly against
# this worktree's corpus (see the log) and picked one concrete,
# currently-uncaptured, live-reconfirmed real instance per family below.


def test_c1_tzere_lenyan_zeh_bare_space_variant_is_currently_missed(db_session, matter_with_users):
    """`לעניין זה "term" - definition` (TZERE spelling, NO comma) --
    `il_lenyan_zeh_tzere_scope_triggers.py` requires a literal comma
    (`לעניין זה,\\s*"..."`); the real corpus routinely omits it.

    Fixture: `תקנות הביטוח הלאומי (קביעת דרגת נכות לנפגעי עבודה)` article
    22א (real, verbatim, programmatically extracted): `... לעניין זה
    "איברים סולידיים" - איברים פנימיים, ...` -- a bare space, not a comma,
    between the trigger and the opening quote. Live-confirmed by this
    Planner: `profile.extract_local_scope_definitions` -> `set()` (the
    term is absent) on both the original corpus article body and this
    fixture's body (proven identical in the fixture-extraction log).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='תקנות הביטוח הלאומי (קביעת דרגת נכות לנפגעי עבודה), תשט"ז-1956',
        fixture="תקנות הביטוח הלאומי (קביעת דרגת נכות לנפגעי עבודה)_art22א_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "איברים סולידיים" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the bare-space לעניין זה-scoped term '
        f'"איברים סולידיים" (article 22א); got {result["created_definitions"]!r}'
    )


def test_c1_yod_lenyan_zeh_bare_space_variant_is_currently_missed(db_session, matter_with_users):
    """`לענין זה "term" - definition` (YOD spelling, NO comma) -- the
    FROZEN `extract._LOCAL_TRIGGER_RE` requires a literal comma
    (`לענין זה,\\s*"..."`); the real corpus routinely omits it. Per
    ruling M15/the log's manager note: this must be fixed as an ADDITIVE
    sibling rule, never by editing the frozen regex.

    Fixture: `חוק שירות הציבור (הגבלות לאחר פרישה)` article 7 (real,
    verbatim): `... ולענין זה "חבר הנהלה" ו"בעל מניות" בעסק - לרבות
    ...` -- bare space before the opening quote. Live-confirmed: `[]`
    today (this same body DOES already capture a different term,
    `"זכות בעסק"`, via the frozen rule's COMMA-having first clause on the
    same line -- this test targets only the still-missing bare-space
    second clause, `"חבר הנהלה"`).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="חוק שירות הציבור (הגבלות לאחר פרישה)",
        fixture="חוק שירות הציבור (הגבלות לאחר פרישה)_art7_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "חבר הנהלה" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the bare-space לענין זה-scoped term '
        f'"חבר הנהלה" (article 7); got {result["created_definitions"]!r}'
    )


def test_c1_beseif_zeh_bare_space_variant_is_currently_missed(db_session, matter_with_users):
    """`בסעיף זה "term" - definition` (NO comma) -- same hardcoded-comma
    gap in the frozen `_LOCAL_TRIGGER_RE`.

    Fixture: `חוק השיפוט הצבאי` article 415א (real, verbatim, the SAME
    law/article QA cycle 2's own log cites for this family): `... בסעיף
    זה "החלטה" - לרבות הוראה או צו.` -- bare space. Live-confirmed:
    `set()` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="חוק השיפוט הצבאי",
        fixture="חוק השיפוט הצבאי_art415א_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "החלטה" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the bare-space בסעיף זה-scoped term '
        f'"החלטה" (article 415א); got {result["created_definitions"]!r}'
    )


def test_c1_beseif_zeh_colon_variant_is_currently_missed(db_session, matter_with_users):
    """`בסעיף זה: "term" - definition` (COLON, not comma) -- the SAME
    family, a different real punctuation variant QA cycle 2 named
    explicitly.

    Fixture: `צו בדבר שטחים סגורים (אזור הגדה המערבית)` article 1ג (real,
    verbatim, the EXACT law/article/term QA cycle 2's log names): `...
    בסעיף זה: "ישראלי" - תושב ישראל, ...`. Live-confirmed: `set()` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="צו בדבר שטחים סגורים (אזור הגדה המערבית)",
        fixture="צו בדבר שטחים סגורים (אזור הגדה המערבית)_art1ג_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "ישראלי" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the colon-variant בסעיף זה-scoped '
        f'term "ישראלי" (article 1ג); got {result["created_definitions"]!r}'
    )


def test_c1_betakana_zo_dash_variant_is_currently_missed(db_session, matter_with_users):
    """`בתקנה זו - "term" - definition` (DASH, not comma) --
    `il_takana_scope_triggers.py`'s 2-word pattern requires a literal
    comma (`בתקנה זו,\\s*"..."`).

    Fixture: `תקנות הביטוח הלאומי (ביטוח מפני פגיעה בעבודה)` article 38
    (real, verbatim): `... בתקנה זו - "רופא מוסמך" - כמשמעותו ...` -- a
    " - " dash, not a comma. Live-confirmed: `set()` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות הביטוח הלאומי (ביטוח מפני פגיעה בעבודה)",
        fixture="תקנות הביטוח הלאומי (ביטוח מפני פגיעה בעבודה)_art38_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "רופא מוסמך" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the dash-variant בתקנה זו-scoped '
        f'term "רופא מוסמך" (article 38); got {result["created_definitions"]!r}'
    )


def test_c1_beseif_katan_zeh_dash_variant_is_currently_missed(db_session, matter_with_users):
    """`בסעיף קטן זה - "term" ((-)) definition` (DASH, not comma) --
    `il_subsection_scope_triggers.py` requires a literal comma
    (`בסעיף קטן זה,\\s*"..."`).

    Fixture: `צו בדבר העסקת עובדים במקומות מסוימים (יהודה והשומרון)`
    article 6 (real, verbatim): `... בסעיף קטן זה - "שוהה לא חוקי"
    ((-)) כהגדרתו ...` -- dash, not comma. Live-confirmed: `set()` today
    (the log's own named example, `פקודת מס הבולים` article 74, term
    `"ההשכרה"`, uses the bare-space form of the same family and was ALSO
    live re-confirmed by this Planner to yield `set()` -- a much larger
    fixture, not vendored here since this test already proves the same
    punctuation-variant gap for this family).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="צו בדבר העסקת עובדים במקומות מסוימים (יהודה והשומרון)",
        fixture="צו בדבר העסקת עובדים במקומות מסוימים (יהודה והשומרון)_art6_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "שוהה לא חוקי" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the dash-variant בסעיף קטן זה-scoped '
        f'term "שוהה לא חוקי" (article 6); got {result["created_definitions"]!r}'
    )


def test_c1_beparagraph_zo_dash_variant_is_currently_missed(db_session, matter_with_users):
    """`בפסקה זו - "term" ו"term2" - definition` (DASH, not comma) --
    `il_paragraph_scope_triggers.py` requires a literal comma
    (`(?:בפסקה זו|...),\\s*"..."`).

    Fixture: `תקנות תכנון משק החלב (העברת מכסות של יצרנים שיתופיים בענף
    הבקר)` article 6 (real, verbatim): `... בפסקה זו - "מועצה אזורית"
    ו"תחום מועצה אזורית" - כהגדרתם ...` -- dash, not comma. Live-
    confirmed: `set()` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות תכנון משק החלב (העברת מכסות של יצרנים שיתופיים בענף הבקר)",
        fixture="תקנות תכנון משק החלב (העברת מכסות של יצרנים שיתופיים בענף הבקר)_art6_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "מועצה אזורית" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the dash-variant בפסקה זו-scoped '
        f'term "מועצה אזורית" (article 6); got {result["created_definitions"]!r}'
    )


def test_c1_lenyan_seif_zeh_dash_variant_is_currently_missed(db_session, matter_with_users):
    """`לענין סעיף זה - "term" - definition` (DASH, not comma) -- the
    3-word variant, `il_seif_zeh_three_word_scope_triggers.py` requires a
    literal comma.

    Fixture: `צו בדבר שיקים ללא כיסוי (יהודה והשומרון)` article 17 (real,
    verbatim): `... לענין סעיף זה - "בנק הדואר" - כמשמעותו ...` -- dash,
    not comma. Live-confirmed: `set()` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="צו בדבר שיקים ללא כיסוי (יהודה והשומרון)",
        fixture="צו בדבר שיקים ללא כיסוי (יהודה והשומרון)_art17_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "בנק הדואר" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the dash-variant לענין סעיף זה-scoped '
        f'term "בנק הדואר" (article 17); got {result["created_definitions"]!r}'
    )


# =====================================================================
# C2 -- same-line-swallow bug in the FROZEN extract._LOCAL_TRIGGER_RE
# =====================================================================
#
# `_LOCAL_TRIGGER_RE` alternates `לענין זה|בסעיף זה` in ONE pattern whose
# definition-text capture group is `(.*)$` -- greedy, bounded only by
# end-of-LINE. When the SAME regex object fires twice on one physical
# source line, the first match's definition-text capture swallows the
# rest of the line, including the second trigger+quote, before
# `finditer` can reach it. Minimal synthetic repro (re-verified by this
# Planner):
#
#   >>> _LOCAL_TRIGGER_RE.finditer('foo; לענין זה, "א" - defA; לענין זה, "ב" - defB.')
#   -> ONE match only: group(1)="א", group(2)='defA; לענין זה, "ב" - defB.'
#
# Per ruling M15 (binding): this lives in the FROZEN `extract` module, so
# the fix must be an ADDITIVE sibling rule (an extra pass that re-scans
# each line for a trigger occurrence the frozen rule's own greedy match
# swallowed), never an edit to `_LOCAL_TRIGGER_RE` itself. Correctness
# note for whoever implements this (recorded here, not decided by this
# Planner): the additive rule's own capture of the FIRST trigger
# occurrence on a swallow-affected line (if its own scan is not itself
# bounded to start after the frozen rule's match) is HARMLESS even if it
# duplicates the frozen rule's own candidate for that first term --
# `pipeline.py`'s dedup key is `(owning_article.id,
# tuple(sorted(candidate.terms)))`, and BOTH the frozen rule and this
# additive sibling stamp `scope="local"` for this trigger vocabulary, so
# a same-key duplicate cannot silently swap in a different scope
# regardless of which one wins the first-candidate-wins tie-break --
# the two candidates are behaviorally identical wherever their keys
# collide.


def test_c2_second_same_line_trigger_match_is_currently_swallowed(db_session, matter_with_users):
    """When `בסעיף זה,`/`לענין זה,` fires TWICE on one physical source
    line, only the FIRST quoted term is captured -- the frozen greedy
    `(.*)$` capture swallows the rest of the line, including the second
    trigger+quote, before `finditer` can reach it.

    Fixture: `חוק הסדרת מקומות רחצה` article 5א (real, verbatim, one of
    the three real corpus instances QA cycle 2's log names): `... בסעיף
    זה, "מקום מרפא" - בריכות שחיה, ... הכריז עליהם בהודעה ברשומות כי הם
    מקום מרפא; לענין זה, "בית מלון" - כהגדרתו ...` -- TWO triggers
    (`בסעיף זה,` then `לענין זה,`) on the SAME physical line. Live-
    confirmed by this Planner: `profile.extract_local_scope_definitions`
    -> captures `{'מקום מרפא'}` only; `"בית מלון"` is silently dropped
    despite sitting in the exact same, already-fully-supported
    `TRIGGER, "term" - definition` grammar. (The other two real corpus
    instances QA's log names -- `היתר לעשיית עסקה בניירות ערך (עובדי
    הרשות)` article 1 (`"תאגיד מפוקח"` captured / `"חברה מוחזקת"`
    swallowed) and `חוק מס ערך מוסף` article 106ב (`"בעל תפקיד"`
    captured / `"בעל שליטה"` swallowed) -- were independently
    live-reconfirmed by this Planner too; see the log for the transcript.
    This test vendors only the smallest of the three as its fixture.)
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='חוק הסדרת מקומות רחצה',
        fixture="חוק הסדרת מקומות רחצה_art5א_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    assert "מקום מרפא" in captured_terms, (
        f"sanity: the FIRST same-line trigger's term should still capture "
        f"today; got {captured_terms!r}"
    )
    assert "בית מלון" in captured_terms, (
        f'expected the SECOND same-line trigger\'s term "בית מלון" (article '
        f'5א) to ALSO be captured -- it is silently swallowed by the frozen '
        f'greedy `(.*)$` capture today; got {captured_terms!r}'
    )


# =====================================================================
# C3 -- inline בפרט זה single-line form
# =====================================================================
#
# `il_prat_zeh_item_scope_triggers.py` (item 9) only ever built the
# `::-` LIST shape for this trigger (`בפרט זה -` preamble line followed
# by separate `::-`-marked entry lines); the plain single-line `בפרט זה,
# "term" - definition.` grammar -- the SAME shape every OTHER trigger
# word this sprint already has -- has no rule at all. Confirmed by this
# Planner's own full-corpus grammar sweep (independent of any shipped
# rule's regex, per P-R7): 19/19 real ordinary-article occurrences
# across 6 files corpus-wide, ZERO captured today, ZERO overlap with the
# already-shipped `::-` list-shape rule (structurally disjoint grammars
# -- the list rule's preamble line ends in a bare `-` with nothing after
# it; this shape's line has the quoted term and its definition on the
# SAME line as the trigger).


def test_c3_inline_beprat_zeh_single_line_form_is_currently_missed(db_session, matter_with_users):
    """`בפרט זה, "term" - definition` (single-line, NOT the `::-` list
    shape item 9's rule already handles) -- no rule reaches this grammar
    at all today.

    Fixture: `חוק בתי משפט לענינים מינהליים` article 40 (real, verbatim,
    the EXACT law/article/term named in the log): `... בפרט זה, "גוף
    אחר" - כהגדרתו בהוראות החשב הכללי ...`. Live-confirmed by this
    Planner: `profile.extract_local_scope_definitions` -> `set()` today
    (item 9's `il_prat_zeh_item_scope_triggers.py` only looks for a
    `בפרט זה -` preamble line followed by `::-` entries, which this
    single-line form is not).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="חוק בתי משפט לענינים מינהליים",
        fixture="חוק בתי משפט לענינים מינהליים_art40_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "גוף אחר" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for the inline single-line בפרט זה-scoped '
        f'term "גוף אחר" (article 40); got {result["created_definitions"]!r}'
    )


# =====================================================================
# C4 -- single-`:-` list generalization, incl. the פרשנות heading synonym
# =====================================================================
#
# `il_colon_dash_nested_list_scope_triggers.py` already generalizes the
# preamble+list shape for the DOUBLE-colon `::-` marker (100% capture,
# QA cycle 2). The SAME grammar with the SINGLE-colon `:-` marker (the
# definitions-SECTION entry marker, `extract._ENTRY_START_RE`) is reached
# by NO rule today, in articles that are NOT dispatched as definitions
# sections. Two sub-shapes, both live-confirmed by this Planner:
#   (i)  `פרשנות` ("Interpretation") heading synonym --
#        `sections._DEFINITIONS_HEADING_RE` does not recognize it, so
#        every real article headed exactly `פרשנות` (optionally with a
#        `(תיקון: ...)` suffix) is dispatched as an ORDINARY article --
#        `is_definitions_heading` confirmed `False` for it by this
#        Planner -- and its genuine `:-`-marked definitions list yields
#        `set()` for every term.
#   (ii) genuine embedded `:-`-marked definitions lists sitting inside
#        substantive, topically-unrelated articles (heading recognized
#        fine, article legitimately about something else), usually (not
#        always) introduced by a recognizable trigger phrase.
# Both sub-shapes reach the ordinary-article `extract_local_scope_
# definitions` dispatch path TODAY (no frozen-file change needed) --
# this Planner's own full-corpus structural sweep (denominator: a bare
# `-`-ending preamble line immediately followed by one-or-more
# `:-`-marked `"term" - definition` entry lines, independent of any
# trigger word -- P-R7) found 1,107 such terms / 189 files corpus-wide
# reachable this way (a superset of QA cycle 2's own "800/130" estimate;
# see the log for the reconciliation of the two counts -- this Planner's
# sweep additionally catches several near-miss headings QA's own count
# did not separately break out, e.g. numbered-prefixed "N. הגדרות"
# headings in `קובץ החלטות מועצת מקרקעי ישראל`, which fall through
# `is_definitions_heading` for the same "not exactly at the start of the
# heading text" reason `פרשנות` does, and are reached by the identical
# fix). Hand-verified (this Planner, two independent random samples,
# mirroring QA cycle 2's own methodology): zero false positives -- every
# candidate obeys the SAME strict `"term" - definition` entry grammar
# the already-shipped `::-` rule relies on for its own precision, so a
# preamble ending in `-` for an unrelated reason can never fabricate a
# candidate on its own.


def test_c4_entry_start_re_cannot_match_double_colon_marker():
    """Non-overlap proof (manager-verified technical fact #1, explicit
    assertion per the brief): `extract._ENTRY_START_RE` is
    `^\\s*:-\\s?`, which structurally CANNOT match a `::-` line -- the
    leading `\\s*` cannot consume the first `:` of `::-`, so the pattern
    always needs the VERY NEXT character after any leading whitespace to
    be `:` followed immediately by `-`; a `::-` line's second character
    is `:`, not `-`, so the match fails at that position. This is the
    load-bearing non-overlap claim for C4: a NEW single-`:-` rule
    anchored the same way as `_ENTRY_START_RE` structurally cannot
    double-fire alongside `il_colon_dash_nested_list_scope_triggers.py`
    (whose own entry regex, `^\\s*::-\\s*`, requires the DOUBLE colon) on
    the same line -- the two markers are mutually exclusive by
    construction, not merely by convention.
    """
    from app.definition_links.extract import _ENTRY_START_RE

    assert _ENTRY_START_RE.match(':- "term" - definition') is not None
    assert _ENTRY_START_RE.match('::- "term" - definition') is None
    assert _ENTRY_START_RE.match('::-"term" - definition') is None


def test_c4_parshanut_heading_synonym_single_colon_list_is_currently_missed(
    db_session, matter_with_users
):
    """`פרשנות` heading synonym (sub-shape i) -- `is_definitions_heading`
    returns `False` for it (not in `_DEFINITIONS_HEADING_RE`'s
    alternation), so the article dispatches as ORDINARY and its genuine
    `:-`-marked definitions list is scanned by NO rule today.

    Fixture: `כללי אתיקה לדיינים` article 1 (real, verbatim, heading
    EXACTLY `פרשנות`): a `: לעניין כללים אלה -` preamble followed by 6
    `:-`-marked entries. Live-confirmed by this Planner:
    `profile.is_definitions_heading("פרשנות")` -> `False`;
    `profile.extract_local_scope_definitions` -> `set()` for this body
    (all 6 terms absent) today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="כללי אתיקה לדיינים",
        fixture="כללי אתיקה לדיינים_art1_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    expected_terms = {
        "בן משפחה",
        "דיין",
        "דיין בדימוס",
        "נושא משרה",
        "נשיא בית הדין הרבני הגדול",
        "עד מרכזי",
    }
    assert expected_terms <= captured_terms, (
        f"expected all 6 פרשנות-heading single-:- -listed terms {expected_terms!r} "
        f"to be captured (article 1); got {captured_terms!r} (created_definitions="
        f"{result['created_definitions']!r})"
    )


def test_c4_embedded_single_colon_list_with_trigger_is_currently_missed(
    db_session, matter_with_users
):
    """Genuine embedded definitions list (sub-shape ii) inside a
    substantive, topically-unrelated article -- heading recognized fine
    (not a definitions heading, correctly so: this article is about
    theft of vessels/aircraft, not definitions), introduced by the
    already-known trigger `בסעיף זה -`.

    Fixture: `חוק העונשין` article 401 (heading `גניבת כלי שיט או כלי
    טיס...`, real, verbatim): `: בסעיף זה -` preamble followed by 2
    `:-`-marked entries (`"כלי שיט"`, `"כלי טיס"`). Live-confirmed by
    this Planner: `profile.extract_local_scope_definitions` -> `set()`
    today (the shipped `il_colon_dash_nested_list_scope_triggers.py`
    only matches `::-`; this article's entries use the single `:-`
    marker).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="חוק העונשין",
        fixture="חוק העונשין_art401_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    expected_terms = {"כלי שיט", "כלי טיס"}
    assert expected_terms <= captured_terms, (
        f"expected both single-:- -listed, בסעיף זה-scoped terms {expected_terms!r} "
        f"to be captured (article 401); got {captured_terms!r} (created_definitions="
        f"{result['created_definitions']!r})"
    )


def test_c4_embedded_single_colon_list_second_trigger_word_is_currently_missed(
    db_session, matter_with_users
):
    """A SECOND genuine embedded-list example, using a different trigger
    word (`לעניין זה -`) than the previous test, to show the shape
    recurs across distinct trigger vocabularies, not just one.

    Fixture: `חוק הדיור המוגן` article 55 (heading `תחולה על בתים
    משותפים`, real, verbatim): `... לעניין זה -` preamble followed by 2
    `:-`-marked entries (`"בית משותף"`, `"חוק המקרקעין"`). Live-
    confirmed by this Planner: `set()` today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="חוק הדיור המוגן",
        fixture="חוק הדיור המוגן_art55_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    expected_terms = {"בית משותף", "חוק המקרקעין"}
    assert expected_terms <= captured_terms, (
        f"expected both single-:- -listed, לעניין זה-scoped terms {expected_terms!r} "
        f"to be captured (article 55); got {captured_terms!r} (created_definitions="
        f"{result['created_definitions']!r})"
    )


# =====================================================================
# M16 (round 2, manager ruling) -- law-wide scope under-claim
# =====================================================================
#
# `_infer_scope`-style default-to-"local" is correct for a genuinely
# UNKNOWN preamble (narrowest, safest, never over-claims) but WRONG for
# a preamble that explicitly names the WHOLE instrument (`בחוק זה -`,
# `בתקנות אלה -`, `בהסכם זה -`, `בכללים אלה -`, `בפקודה זו -`, `בצו זה
# -`, `באכרזה זו -`, `בנוהל זה -`, `בחוק יסוד זה -`, each also with the
# `לענין/לעניין` preposition variant) -- a `Definition` stamped `"local"`
# under such a preamble is captured but its `USES_DEFINITION` assertions
# everywhere else in the SAME instrument are never created (`matcher.
# _in_scope`'s `"local"` branch requires `article.number ==
# definition.source_article_number`; `"law-wide"` returns unconditional
# `True`). This Planner's OWN `HebrewProfile.determine_scope` reads
# confirm the parity argument: a RECOGNIZED הגדרות section already
# defaults to `"law-wide"` (unless a chapter trigger is present) via
# EXACTLY this same "preamble names the whole document" reasoning --
# `il_colon_dash_nested_list_scope_triggers.py`'s own `_infer_scope`
# (and the not-yet-shipped single-`:-` sibling C4 needs) should be
# brought to the same behavior for consistency, not a new precision
# risk.
#
# **Vocabulary -- measured, not trusted.** Re-derived the full
# preamble-phrase population independently (own script, corpus-wide,
# both `:-` and `::-`, ordinary articles only) and reproduced the
# manager-relayed headline number exactly: 1,107 single-`:-` terms. Full
# per-phrase breakdown (term counts) logged separately; every candidate
# phrase below was hand-verified against >=2 real corpus instances
# (fetched live this session) before inclusion:
#
#   INCLUDED (law-wide, whole-instrument reference confirmed):
#     בחוק זה, בחוק יסוד זה, בתקנות אלה, בתקנות אלו, בהסכם זה, בכללים
#     אלה, בפקודה זו, בצו זה, באכרזה זו, בנוהל זה, and the לענין/לעניין
#     preposition variant of each (e.g. לענין חוק זה / לעניין חוק זה).
#
#   EXCLUDED (deliberately, with the reason verified live):
#     - בתוספת זו ("in this schedule") -- the manager's own named
#       boundary case, confirmed: a schedule is a sub-part, never the
#       whole instrument.
#     - בפוליסה זו ("in this policy") -- this Planner's OWN additional
#       catch, NOT named by the manager: every real instance found
#       (`הוראות הפיקוח על שירותים פיננסיים (ביטוח) (תנאי חוזה לביטוח
#       חובה של רכב מנועי)`) sits inside an article headed `<עוגן * פרט
#       N לטופס זה>` -- the "policy" is itself an embedded FORM
#       (a schedule-equivalent sub-document), not the regulation it is
#       prescribed by. Same risk shape as בתוספת זו; would have been a
#       genuine over-claim if included.
#     - בפרק משנה זה ("in this sub-chapter") -- narrower than the
#       instrument (a structural sub-unit, same open-containment
#       category as סימן/חלק already left capture-only this sprint).
#     - בנספח זה ("in this appendix"), בטבלה זו ("in this table"),
#       בנוסחה זו ("in this formula") -- all sub-parts, same reasoning
#       as בתוספת זו.
#     - בתקנה זאת (an alternate spelling of בתקנה זו, i.e. LOCAL/
#       article-level per D-Q1, not law-wide -- a real, additional
#       missing-spelling finding, but a SEPARATE, smaller issue than
#       M16's law-wide defect; not folded in here, flagged in the log).
#     - בתקנת שעת חירום זו ("in this emergency regulation") -- same
#       article/regulation-level granularity as בתקנה זו, not the whole
#       instrument.
#     - לעניין כלל זה ("regarding this RULE", singular) -- one specific
#       rule within a כללים instrument, narrower than the whole
#       document; NOT the same phrase as בכללים אלה (plural).
#     - לעניין פרט חימוש זה ("regarding this ammunition item"), באמת
#       מידה זו ("in this standard/metric") -- both far narrower than
#       even a single article.
#     - לענין הסעיפים X-Y / לעניין סעיפים N ו-M (enumerated multi-
#       article ranges) -- narrower than the whole law; a separate,
#       smaller potential under-scope this bundle does NOT address
#       (flagged, not silently folded in).
#     - לענין/לעניין סעיף (קטן) זה (the existing 3-word local/subsection
#       triggers) -- already correctly narrow via other mechanisms.
#
# **Zero collision with existing tests (verified, not assumed).** Every
# fixture already in `backend/tests/fixtures/wiki_laws/` containing any
# INCLUDED law-wide phrase was checked: all 8 hits (`חוק להגנת רכוש
# מופקד`, `חוק המחשבים_stub`, `חוק הבנקאות (רישוי)_stub`, `תקנות קרן
# גרמניה-ישראל_art1`, `צו איסור הלבנת הון (מפעיל מערכת
# לתיווך)_excerpt`, plus 3 more that turned out to be the UNRELATED
# ad-hoc-parenthetical grammar, not this preamble+list shape) sit inside
# an article whose heading IS a recognized `הגדרות` heading --
# `is_definitions_heading` returns `True`, so these are dispatched via
# `extract_definitions_from_section` (which ALREADY defaults to
# `"law-wide"` via `determine_scope`), never via the `ScopeTriggerRule`
# path this change touches. **None of the 12 `test_definition_links_il_
# qa_cycle1_fixups_live.py` tests (nor any other existing test) assert
# on a `d["scope"]` value from a real IL fixture that this change would
# alter** -- grepped every test file for `["scope"]`/`.scope` assertions;
# the only 3 hits are in `test_definition_links_pipeline_scope_seam.py`,
# a core-owned seam test using synthetic `"Term"`/`"Widget"` fixtures,
# unrelated to any real IL corpus content. Nothing to escalate.
#
# **Containment machinery re-verified directly (static, not a shipped
# pytest test -- see the log for the transcript):** `matcher._in_scope`
# called with synthetic `Definition`/`Article` stand-ins confirms (1) a
# `scope="law-wide"` definition covers a DIFFERENT article of the same
# document (`True`), (2) the CURRENT naive `scope="local"` classification
# of the exact same preamble does NOT (`False` -- the precise under-
# claim M16 names), and (3) a genuinely `scope="local"` definition
# (e.g. `בסעיף זה -`) correctly does NOT leak to a different article
# (`False`) -- the negative/non-leakage direction is ALREADY proven by
# this unchanged, already-battle-tested branch (every other local-scoped
# rule this sprint ships relies on it); a repo-committed pytest RED test
# for that direction would be vacuously green today (nothing captured
# yet for the not-yet-shipped C4 rule, so "no assertion" trivially holds)
# and would therefore violate the RED-provenance gate -- not written for
# that reason, not an oversight. Recommended as a QA cycle 3 live
# verification once the Developer's real implementation lands.


def test_m16_lawwide_preamble_definition_links_a_mention_in_a_different_article(
    db_session, matter_with_users
):
    """The assertion-level under-reach proof: a term defined in article 1
    under a law-wide preamble (`לעניין כללים אלה -`) must get a
    `USES_DEFINITION` assertion for a genuine mention in a DIFFERENT
    article of the SAME instrument -- today (before C4 ships at all)
    there is no capture and therefore no assertion; once C4 ships with
    the CORRECT law-wide classification this test goes green, but a C4
    implementation that (per this Planner's own original round-1 design)
    defaults this preamble to `scope="local"` would leave this test RED
    forever -- exactly the discriminating power M16 asks for.

    Fixture: `כללי אתיקה לדיינים` articles 1+2 (real, verbatim, TWO
    independently byte-verified spans concatenated -- see the log's
    fixture-verification transcript). Article 1's preamble is `לעניין
    כללים אלה -` (heading `פרשנות`, NOT a recognized definitions
    heading); one of its 6 `:-`-marked terms is `"דיין"`. Article 2
    (heading `מקור הכללים ותכליתם`) genuinely mentions `דיין` in
    substantive prose (`"...ולדרכי התנהגותו ואורחותיו של הדיין; ...דיין
    ינהג דרכו..."`).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="כללי אתיקה לדיינים",
        fixture="כללי אתיקה לדיינים_art1_art2_excerpt.wiki",
    )
    uses_definition = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    art2_dayan = [
        a for a in uses_definition if a["proposition"] == 'Article 2 uses the definition of "דיין".'
    ]
    assert art2_dayan, (
        f'expected article 2 to get a USES_DEFINITION assertion for the '
        f'law-wide-scoped term "דיין" defined in article 1 (לעניין כללים '
        f'אלה -); got USES_DEFINITION assertions: {uses_definition!r} '
        f"(created_definitions={result['created_definitions']!r})"
    )


def test_m16_already_shipped_double_colon_rule_under_scopes_a_lawwide_list(
    db_session, matter_with_users
):
    """The SAME defect, already live in production TODAY via the
    ALREADY-SHIPPED `il_colon_dash_nested_list_scope_triggers.py` --
    this file (`il_colon_dash_nested_list_scope_triggers.py`) is NOT
    frozen, so per the manager's instruction the Developer may edit it,
    but the RED-provenance gate still requires this committed RED first.

    Fixture: `חוק הרשות לחקירה בטיחותית בתעופה` articles 1+2 (real,
    verbatim, two independently byte-verified spans concatenated).
    Article 2 (heading `פרשנות`, NOT a recognized definitions heading)
    has a `::-`-marked list under the preamble `בחוק זה -`; one entry is
    `"חוק הטיס" - [[חוק הטיס, התשע"א-2011]]`. Article 1 (heading `מטרה`)
    genuinely mentions `[[חוק הטיס]]` in its own body. Live-confirmed by
    this Planner: the term "חוק הטיס" IS captured TODAY (the `::-` rule
    already runs, `"בחוק זה"` just isn't in its trigger table so it
    defaults to `scope="local"`) -- this is the cleaner of the two M16
    REDs: capture already exists, only the SCOPE (and therefore the
    cross-article assertion) is wrong.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="חוק הרשות לחקירה בטיחותית בתעופה",
        fixture="חוק הרשות לחקירה בטיחותית בתעופה_art1_art2_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "חוק הטיס" in d["terms"]]
    assert defs, (
        f'sanity: expected "חוק הטיס" to already be captured today '
        f"(scope may be wrong, but capture itself is not this test's "
        f"point); got {result['created_definitions']!r}"
    )
    uses_definition = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    art1_tisa = [
        a
        for a in uses_definition
        if a["proposition"] == 'Article 1 uses the definition of "חוק הטיס".'
    ]
    assert art1_tisa, (
        f'expected article 1 to get a USES_DEFINITION assertion for the '
        f'law-wide-scoped term "חוק הטיס" defined in article 2 (בחוק זה '
        f"-); got USES_DEFINITION assertions: {uses_definition!r} "
        f"(created_definitions={result['created_definitions']!r})"
    )


# =====================================================================
# M17 (round 3, manager ruling, LAST increment before Developer) --
# systematic spelling-variant audit
# =====================================================================
#
# **Enumeration method (corpus-derived, not invented from grammar
# rules alone).** Two full-corpus sweeps, ordinary (non-הגדרות-heading)
# articles only: (1) every `<word(s)> <demonstrative><punct>"` occurrence
# (quote-first grammar) and (2) every `<word(s)> <demonstrative> -` at a
# preamble-line tail (list grammar), for `<demonstrative>` in `{זה, זו,
# זאת, אלה, אלו}` -- the closed set of Hebrew "this/these" forms. This
# produced 54 distinct quote-first phrases (4,421 occurrences) and 52
# distinct list-shape phrases (901 occurrences) -- the FULL universe of
# "concept-noun + demonstrative" constructions the corpus actually
# contains, not a guessed list. Every phrase not already a known/planned
# trigger (every shipped `rules/il_*.py` module's trigger table, the
# FROZEN `extract._LOCAL_TRIGGER_RE`/`_ADHOC_RE`, and the M16 law-wide
# table) was individually classified: (a) an orthographic/phrasing
# variant of an EXISTING trigger -- measured precisely (via the REAL
# downstream grammar, not the loose enumeration scan) and, if nonzero,
# fixed here; (b) a genuinely different concept -- logged as a residual,
# per the "no new classes" boundary, and NOT built.
#
# **Completeness argument (the sentence this Planner expects QA cycle 3
# to read hardest).** The enumeration is complete FOR THE DEMONSTRATIVE-
# ADJACENT SHAPE this sprint's own trigger grammar universally uses --
# every one of the ~30 trigger phrases across every shipped/planned rule
# module has the form `<noun phrase> <demonstrative>`, so scanning for
# THAT exact shape corpus-wide, unfiltered by any assumption about which
# nouns or demonstratives are "expected," cannot miss a variant that
# shares the shape (a variant using a DIFFERENT demonstrative than the
# 5 canonical Hebrew "this/these" forms does not exist in the language).
# What this enumeration CANNOT catch, stated honestly: (1) a variant
# that drops the demonstrative entirely (e.g. a bare noun used
# elliptically) -- no evidence any shipped trigger works this way, so
# this is not a live risk, but it is not provably absent either; (2) a
# variant using a preposition OTHER than `ב`/`ל` (the sweep's own regex
# only captures those two prefixes plus "no prefix") -- the sweep DID
# surface `לצורך X זה` ("for the purpose of this X") 5 times using a
# THIRD preposition; logged as a residual below rather than silently
# folded in, since `לצורך` is a different word, not an orthographic
# variant of `ל`/`לענין`; (3) a genuine spelling variant of a
# CONCEPT-NOUN this Planner did not think to include in the ~30-trigger
# base set at all (as opposed to a variant of a demonstrative/
# preposition attached to an ALREADY-known noun) -- mitigated, not
# eliminated, by the fact the enumeration scan itself is noun-agnostic
# (it does not presuppose which nouns matter), so an unknown noun's
# EXISTING spelling would still surface in the frequency table and be
# manually reviewed; a variant of a noun that appears ZERO times under
# any demonstrative in the whole corpus is, by construction, undetectable
# by any corpus-derived method and is not claimed to be covered.
#
# **Verified findings, per variant (real corpus occurrence count, both
# grammars, through the live chain):**
#
# BUILT (nonzero, genuinely uncaptured today -- one RED test each below):
#   בתקנה זאת (quote-first, 6); בפסקה זאת (quote-first, 1); לענין/
#   לעניין פסקה זאת (quote-first, 1); בתקנת משנה זאת (quote-first, 4);
#   בפסקה משנה זו -- ה-spelling of the known construct-state בפסקת
#   משנה זו (quote-first, 4); לענין/לעניין פרט זה -- the missing 3-word
#   sibling of the already-known 2-word בפרט זה, matching the SAME
#   2-word-to-3-word pattern every OTHER trigger in this sprint already
#   has (quote-first, 15); בחוק זה (quote-first, 45 -- the M16 word was
#   only added to the list-shape/law-wide table, never to the
#   quote-first grammar); לענין/לעניין חוק זה (quote-first, 8); בתקנות
#   אלה (quote-first, 23); בתקנות אלו (quote-first, 1; ALSO a genuine
#   single-`:-` list-shape miss, 1 -- see below); לענין/לעניין תקנות
#   אלה (quote-first, 2); בכללים אלה (quote-first, 1); בפקודה זו
#   (quote-first, 1); בצו זה (quote-first, 2); לענין/לעניין צו זה
#   (quote-first, 1).
#
# MEASURED ZERO (verified, not merely unsampled -- reported per the
# binding instruction that a measured zero is itself a finding):
#   לענין/לעניין תקנה זאת (3-word, both grammars: 0); לענין/לעניין
#   פסקה זאת (list-shape: 0, quote-first already listed above as
#   nonzero); בפסקה משנה זאת (both grammars: 0); בחוק יסוד זה
#   (quote-first: 0 -- already correctly captured via M16's list-shape
#   vocabulary, list-shape: 3); לענין/לעניין הסכם זה (both: 0); בכללים
#   אלו (both: 0); לענין/לעניין כללים אלה (quote-first: 0 -- list-shape
#   already M16-covered, 13); לענין/לעניין פקודה זו (both: 0); באכרזה
#   זו (quote-first: 0 -- list-shape already M16-covered, 2); לענין/
#   לעניין אכרזה זו (both: 0); בנוהל זה (quote-first: 0 -- list-shape
#   already M16-covered, 20); לענין/לעניין נוהל זה (both: 0).
#
# CORRECTED FINDING, not a gap (initial scan false-positive, caught
# before writing a test): `בתקנה זאת` list-shape showed as a
# 15-occurrence miss under a naive "trigger phrase anywhere in the
# preamble line" scan -- re-verified with a TAIL-anchored check (the
# phrase must be the line's own GOVERNING preamble, immediately before
# the trailing dash, not merely present earlier in a long sentence, e.g.
# inside an unrelated ad-hoc parenthetical `(בתקנה זאת - X)` mid-line)
# and found: all 15 are `::-`-marked, ALREADY captured today (the
# shipped `::-` rule's detection is trigger-word-independent), and
# ALREADY correctly scoped `"local"` (a `תקנה`-family word is
# article-level per D-Q1, so the existing unrecognized-trigger default
# happens to be correct here -- unlike the M16 law-wide words, where the
# SAME default was wrong). Zero genuine single-`:-` misses (0/0). No
# test needed; recorded here so the false lead is not silently dropped.
#
# RESIDUALS (genuinely NOT a spelling variant of an existing trigger --
# per the "no new classes" boundary, logged with counts, not built):
#   לענין הגדרה זו / לעניין הגדרה זו ("regarding this DEFINITION", 11+13
#   quote-first/list-shape) -- a NESTED-definition cross-reference,
#   matching the FROZEN `extract._NESTED_MARKER_RE` concept
#   (`לעניין הגדרה זו,`), structurally different from a scope-container
#   trigger; not reachable by the ordinary-article path at all today.
#   לענין קו זה (6, "regarding this bus/train LINE") -- unrelated
#   transportation concept. פרט משנה זה (4, "sub-item") -- a genuinely
#   NEW granularity word (not a spelling variant of בפרט זה), following
#   the "X משנה" sub-unit PATTERN but with a different base noun.
#   לצורך X זה (~5, "for the purpose of this X") -- a THIRD preposition
#   family (`לצורך`), not an orthographic variant of `ל`/`לענין`.
#   בכלל זה (2, idiom "including this") -- a false friend, NOT a
#   respelling of `בכללים אלה`; excluded explicitly, same caution as
#   round 2's own false-friend catch. במנשר זה (2, "in this manifesto")
#   -- a rare, distinct historical-instrument word, thematically
#   parallel to the M16 law-wide family but not a respelling of any word
#   already in it. ביום זה (6, temporal, unrelated). Already-excluded
#   sub-part family restated (unchanged from round 2, re-confirmed
#   present in this sweep too, not a new finding): באמת מידה זו (~146
#   combined), בתוספת זו, בנספח זה, בטבלה זו, בפוליסה זו, בנוסחה(ות)
#   זו/אלה, בפרק משנה זה.


def test_m17_takana_zot_quote_first_is_currently_missed(db_session, matter_with_users):
    """`בתקנה זאת, "term" - definition` -- זאת (archaic register) variant
    of the already-known `בתקנה זו`. Fixture: `תקנות הגנת הצומח (מניעת
    חדירה של נגעים לאזור הערבה)` art.2א, term `"אזור הערבה"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות הגנת הצומח (מניעת חדירה של נגעים לאזור הערבה)",
        fixture="תקנות הגנת הצומח (מניעת חדירה של נגעים לאזור הערבה)_art2א_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "אזור הערבה" in d["terms"]]
    assert defs, f'expected "אזור הערבה" captured (art.2א); got {result["created_definitions"]!r}'


def test_m17_peska_zot_quote_first_is_currently_missed(db_session, matter_with_users):
    """`בפסקה זאת, "term" - definition` -- זאת variant of `בפסקה זו`.
    Fixture: `תקנות הנזיקים האזרחיים (אחריות המדינה)` art.3, term
    `"תאגיד"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות הנזיקים האזרחיים (אחריות המדינה)",
        fixture="תקנות הנזיקים האזרחיים (אחריות המדינה)_art3_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "תאגיד" in d["terms"]]
    assert defs, f'expected "תאגיד" captured (art.3); got {result["created_definitions"]!r}'


def test_m17_lenyan_peska_zot_quote_first_is_currently_missed(db_session, matter_with_users):
    """`לעניין פסקה זאת, "term" - definition` -- the 3-word זאת sibling
    of `לעניין פסקה זו`. Fixture: `תקנות סמכויות מיוחדות להתמודדות עם
    נגיף הקורונה החדש` art.5ב, term `"קשיים מיוחדים"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות סמכויות מיוחדות להתמודדות עם נגיף הקורונה החדש",
        fixture="תקנות סמכויות מיוחדות להתמודדות עם נגיף הקורונה החדש_art5ב_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "קשיים מיוחדים" in d["terms"]]
    assert defs, f'expected "קשיים מיוחדים" captured (art.5ב); got {result["created_definitions"]!r}'


def test_m17_takanat_mishne_zot_quote_first_is_currently_missed(db_session, matter_with_users):
    """`בתקנת משנה זאת, "term" - definition` -- זאת variant of `בתקנת
    משנה זו`. Fixture: `תקנות לימוד חובה (ייעוד כספי תשלומים)` art.7,
    term `"סכום חריג"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות לימוד חובה (ייעוד כספי תשלומים)",
        fixture="תקנות לימוד חובה (ייעוד כספי תשלומים)_art7_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "סכום חריג" in d["terms"]]
    assert defs, f'expected "סכום חריג" captured (art.7); got {result["created_definitions"]!r}'


def test_m17_peska_mishne_zo_he_spelling_quote_first_is_currently_missed(
    db_session, matter_with_users
):
    """`בפסקה משנה זו, "term" - definition` -- the ה-spelling variant of
    the known construct-state `בפסקת משנה זו` (Hebrew smichut normally
    drops the ה for ת before a following noun; this corpus instance
    keeps it). Fixture: `צו לימוד חובה (שיעור ההשתתפות)` art.2, term
    `"הוצאות תפעוליות שאינן שכר"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="צו לימוד חובה (שיעור ההשתתפות)",
        fixture="צו לימוד חובה (שיעור ההשתתפות)_art2_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "הוצאות תפעוליות שאינן שכר" in d["terms"]]
    assert defs, (
        f'expected "הוצאות תפעוליות שאינן שכר" captured (art.2); '
        f'got {result["created_definitions"]!r}'
    )


def test_m17_lenyan_prat_zeh_three_word_quote_first_is_currently_missed(
    db_session, matter_with_users
):
    """`לעניין פרט זה, "term" - definition` -- the missing 3-word
    sibling of the already-known 2-word `בפרט זה`, matching the SAME
    2-word-to-3-word `לענין/לעניין` extension pattern every OTHER
    trigger in this sprint already has (`סעיף זה`, `תקנה זו`, `פסקה
    זו`, `תקנת משנה זו` all do). 15 real occurrences corpus-wide.
    Fixture: `תקנות הביטוח הלאומי (קביעת דרגת נכות לנפגעי עבודה)`
    art.92, term `"פגימות נלוות לתסמונת"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='תקנות הביטוח הלאומי (קביעת דרגת נכות לנפגעי עבודה), תשט"ז-1956',
        fixture="תקנות הביטוח הלאומי (קביעת דרגת נכות לנפגעי עבודה)_art92_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "פגימות נלוות לתסמונת" in d["terms"]]
    assert defs, (
        f'expected "פגימות נלוות לתסמונת" captured (art.92); '
        f'got {result["created_definitions"]!r}'
    )


def test_m17_bachok_zeh_quote_first_is_currently_missed(db_session, matter_with_users):
    """`בחוק זה, "term" - definition` -- the M16 law-wide word `חוק` was
    only added to the list-shape/preamble+list vocabulary; the
    QUOTE-FIRST grammar (`TRIGGER, "term" - definition` on one line) was
    never extended to include it at all. 45 real corpus occurrences.
    Fixture: `חוק-יסוד: השפיטה` art.1, term `"שופט"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="חוק-יסוד: השפיטה",
        fixture="חוק-יסוד_ השפיטה_art1_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "שופט" in d["terms"]]
    assert defs, f'expected "שופט" captured (art.1); got {result["created_definitions"]!r}'


def test_m17_lenyan_chok_zeh_quote_first_is_currently_missed(db_session, matter_with_users):
    """`לעניין חוק זה, "term" - definition` -- the 3-word sibling of the
    above, same missing-quote-first-grammar gap. Fixture: `חוק משק הדלק
    (איסור מכירת דלק לתחנות תדלוק מסוימות)` art.6, term `"נושא משרה
    בתאגיד"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="חוק משק הדלק (איסור מכירת דלק לתחנות תדלוק מסוימות)",
        fixture="חוק משק הדלק (איסור מכירת דלק לתחנות תדלוק מסוימות)_art6_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "נושא משרה בתאגיד" in d["terms"]]
    assert defs, (
        f'expected "נושא משרה בתאגיד" captured (art.6); got {result["created_definitions"]!r}'
    )


def test_m17_takanot_ele_quote_first_is_currently_missed(db_session, matter_with_users):
    """`בתקנות אלה, "term" - definition` -- same M16-word/quote-first-
    grammar gap as `בחוק זה` above. 23 real corpus occurrences. Fixture:
    `תקנות סדר הדין הפלילי (היוועדות חזותית)` art.7, term `"ועדת
    שחרורים"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות סדר הדין הפלילי (היוועדות חזותית)",
        fixture="תקנות סדר הדין הפלילי (היוועדות חזותית)_art7_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "ועדת שחרורים" in d["terms"]]
    assert defs, f'expected "ועדת שחרורים" captured (art.7); got {result["created_definitions"]!r}'


def test_m17_takanot_elu_quote_first_is_currently_missed(db_session, matter_with_users):
    """`בתקנות אלו, "term" - definition` -- אלו/אלה plural-"these"
    register variant of `בתקנות אלה`. Fixture: `תקנות בתי הדין הדתיים
    הדרוזיים (אגרות)` art.2א, term `"מדד"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות בתי הדין הדתיים הדרוזיים (אגרות)",
        fixture="תקנות בתי הדין הדתיים הדרוזיים (אגרות)_art2א_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "מדד" in d["terms"]]
    assert defs, f'expected "מדד" captured (art.2א); got {result["created_definitions"]!r}'


def test_m17_takanot_elu_single_colon_list_shape_is_currently_missed(
    db_session, matter_with_users
):
    """`בתקנות אלו -` followed by a SINGLE-`:-` list -- the SAME אלו/אלה
    register variant, but this time the list-shape gap (not yet reached
    by ANY rule, single-`:-` marker, same as C4's own core finding).
    Confirmed via marker-split re-measurement: 0 `::-` occurrences, 1
    genuine `:-` occurrence -- not the false-positive shape `בתקנה זאת`
    (list-shape) turned out to be (see the module-level note above).
    Fixture: `תקנות בדבר סמכויות הקונסולים בישראל` art.2, term
    `"קונסול"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות בדבר סמכויות הקונסולים בישראל",
        fixture="תקנות בדבר סמכויות הקונסולים בישראל_art2_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "קונסול" in d["terms"]]
    assert defs, f'expected "קונסול" captured (art.2); got {result["created_definitions"]!r}'


def test_m17_lenyan_takanot_ele_quote_first_is_currently_missed(db_session, matter_with_users):
    """`לעניין תקנות אלה, "term" - definition` -- the 3-word sibling,
    same quote-first-grammar gap. Fixture: `תקנות איסור הלבנת הון
    (דרכים ומועדים)` art.5, term `"מען"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="תקנות איסור הלבנת הון (דרכים ומועדים)",
        fixture="תקנות איסור הלבנת הון (דרכים ומועדים)_art5_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "מען" in d["terms"]]
    assert defs, f'expected "מען" captured (art.5); got {result["created_definitions"]!r}'


def test_m17_klalim_ele_quote_first_is_currently_missed(db_session, matter_with_users):
    """`בכללים אלה, "term" - definition` -- same M16-word/quote-first
    gap. Fixture: `כללי מס הכנסה (השוואת הון על פי דוח שהגיש יהלומן)`
    art.1, term `"הצהרת הון"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="כללי מס הכנסה (השוואת הון על פי דוח שהגיש יהלומן)",
        fixture="כללי מס הכנסה (השוואת הון על פי דוח שהגיש יהלומן)_art1_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "הצהרת הון" in d["terms"]]
    assert defs, f'expected "הצהרת הון" captured (art.1); got {result["created_definitions"]!r}'


def test_m17_bapkuda_zo_quote_first_is_currently_missed(db_session, matter_with_users):
    """`בפקודה זו, "term" - definition` -- same M16-word/quote-first
    gap. Fixture: `פקודת המועצות המקומיות` art.21א, term `"ערבות
    בנקאית"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="פקודת המועצות המקומיות",
        fixture="פקודת המועצות המקומיות_art21א_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "ערבות בנקאית" in d["terms"]]
    assert defs, f'expected "ערבות בנקאית" captured (art.21א); got {result["created_definitions"]!r}'


def test_m17_batzav_zeh_quote_first_is_currently_missed(db_session, matter_with_users):
    """`בצו זה, "term" - definition` -- same M16-word/quote-first gap.
    Fixture: `צו נכי רדיפות הנאצים (הגבלת שכר טרחה)` art.1, term
    `"תביעה"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="צו נכי רדיפות הנאצים (הגבלת שכר טרחה)",
        fixture="צו נכי רדיפות הנאצים (הגבלת שכר טרחה)_art1_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "תביעה" in d["terms"]]
    assert defs, f'expected "תביעה" captured (art.1); got {result["created_definitions"]!r}'


def test_m17_lenyan_tzav_zeh_quote_first_is_currently_missed(db_session, matter_with_users):
    """`לעניין צו זה, "term" - definition` -- the 3-word sibling, same
    quote-first-grammar gap. Fixture: `צו הכניסה לישראל (פטור תושבי
    רצועת עזה)` art.1, term `"תושב רצועת עזה"`.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="צו הכניסה לישראל (פטור תושבי רצועת עזה)",
        fixture="צו הכניסה לישראל (פטור תושבי רצועת עזה)_art1_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "תושב רצועת עזה" in d["terms"]]
    assert defs, (
        f'expected "תושב רצועת עזה" captured (art.1); got {result["created_definitions"]!r}'
    )
