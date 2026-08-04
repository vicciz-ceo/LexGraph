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
