"""Sprint 2026-08-04-defs-il (program 2026-08-04-definition-completeness),
Phase D, Planner D-1a (Sonnet/high) -- RED tests for QA cycle 3's three
confirmed-buildable classes (contract `## Next Steps` items D-1a / M19 /
M19-EXT; log entries `## QA cycle 3`, the manager verdict containing
**M18**, and `## 2026-08-05 -- M19-EXT`). None of these three classes had
a RED test before this file -- that is this file's entire job. Per
ruling M14, additive only: a NEW file, no existing test edited.

**Class A -- multi-term list entries dropped whole** (the largest: QA
cycle 3 measured 479/1,173 confirmed misses across 239 files). Root
cause, live-confirmed (not inferred): `rules/il_list_shape_scope.
ENTRY_TERM_DASH_RE = re.compile(r'^"([^"]+)"\\s*-\\s*(.*)$')` -- shared by
BOTH `il_colon_dash_nested_list_scope_triggers.py` (`::-`) and
`il_single_colon_list_scope_triggers.py` (`:-`) -- matches only a SINGLE
quoted term at the start of an entry line; when an entry names >=2 terms
sharing one definition (`"t1", "t2" - def` or `"t1" ו"t2" - def`),
`entry_match` succeeds (the `:-`/`::-` marker matches) but `term_match`
fails silently and the WHOLE entry is dropped -- not partially.

**Class B -- quote-first candidates with no split marker after the
quote.** Root cause, live-confirmed: `il_trigger_grammar.
extract_quote_first_candidates` calls `_find_split_marker(clause)`; when
it returns `-1` (no standalone `-`/`((-))` anywhere in the clause), the
WHOLE candidate is discarded via `continue`, even though the
trigger+quote matched correctly. Two real sub-shapes (this Planner's own
characterization, per the brief -- QA's 60-sample hand-classification was
~20%/~80% but did not fully characterize the ~80%):
  (i)  the clean cross-reference shape, `TRIGGER, "term" כהגדרתו/
       כמשמעותה [[citation]].` -- the term is defined BY REFERENCE to
       another law/section, no local defining text at all.
  (ii) a plain local-defining continuation with NO dash anywhere:
       `TRIGGER, "term" <לרבות/למעט/other predicate ... defining text>;`
       -- the definition follows the quote directly, using a Hebrew
       inclusion/exclusion verb (`לרבות` = "includes", `למעט` =
       "excludes") instead of a dash. This Planner independently
       confirmed BOTH sub-shapes live and, per ruling M4, re-derived a
       denominator SIGNAL-AGNOSTIC to this bug (P-R7): every generic
       `<<=3-word phrase><demonstrative:  זה/זו/זאת/אלה/אלו><connector>
       "term"` occurrence corpus-wide (independent of any curated trigger
       list), THEN filtered to matches of an ACTUALLY-REGISTERED
       production trigger regex (the set every rule built on
       `extract_quote_first_candidates` actually uses) and checked for a
       split marker in the remainder -- 103 production-trigger-scoped
       quote-first matches corpus-wide have no split marker, 100 of which
       are confirmed absent from live `extract_local_scope_definitions`
       output (order-of-magnitude match with QA cycle 3's own 132/6,364
       generic-population figure; this Planner's narrower, production-
       trigger-scoped re-derivation is a stricter, independently-built
       confirmation of the same class, not a copy of QA's number).

**Class C -- preambles living in the article's own HEADING.** Root
cause, live-confirmed: both list-shape rules call `PREAMBLE_RE.search
(lines[i])` only over `article_body`'s own lines; `RuleContext`/the rule
signature (`registry.py`) never receives the owning article's `.heading`
at all, and neither does `HebrewProfile.extract_local_scope_definitions`
(`profiles.py`, FROZEN) nor its caller (`pipeline.py`, FROZEN) -- so
there is genuinely no way for a `ScopeTriggerRule.extract` callable to
see heading text today. **Feasibility was independently verified live
before writing this test** (per M4/P-R10 -- the D-1a spec claims "no
frozen-file edit should be needed" and instructs treating a contrary
claim as an escalation, so this had to be checked, not assumed): a
throwaway probe registered a NEW `registry.HeadingRule` (a kind
`registry.py`, NOT frozen, already supports) whose `matches` callable
recognizes a heading ending in a bare `-` (mirroring the existing
`PREAMBLE_RE` shape) and whose `body_confirms` callable checks the body's
first line is `:-`/`::-`-marked; registering it causes `profile.
is_definitions_heading` to return `True` for the real `אכרזת גנים
לאומיים` article 8 fixture below, and `profile.extract_definitions_from_
section` (the ALREADY-CORRECT, multi-term-safe definitions-section path)
then captures all 10 real terms. This confirms the class is reachable via
a NEW rule-module-only file (zero frozen-file edits) -- exactly what the
D-1a spec asserts, now independently verified rather than trusted. (Scope
correctness for this path is a SEPARATE, open question this Planner is
NOT resolving here: `determine_scope` only reads BODY text, so a
heading-only trigger like `בתוספת זו` is invisible to it and the fix's
naive `HeadingRule`-only approach would default to `"law-wide"` --
possibly an over-claim for a schedule/appendix sub-part, mirroring M16's
own reasoning for why `בתוספת זו` is excluded from the law-wide
vocabulary. Flagged for the Developer/QA, not decided here -- this file's
tests assert CAPTURE only, never a specific `scope` value, for this
class.)

**M18 compliance (binding, program law):** every denominator cited above
is built from the ENTRY LINE / the GENERIC quote-first candidate shape,
classified AFTER matching against LIVE `extract_local_scope_definitions`
output -- never from the buggy rule's own grammar. Class A's sweep reused
`il_trigger_grammar._find_split_marker`/`_QUOTE_RE` (a DIFFERENT,
already-correct helper than the buggy `il_list_shape_scope.
ENTRY_TERM_DASH_RE` under test) purely as a measurement tool for "does
this entry line have >=2 distinct quoted terms in its header", the same
technique QA cycle 3 used. Class B's sweep used a demonstrative-anchored
generic scan (independent of any trigger list) for its outer bound, then
the real, currently-registered production trigger regexes (collected by
introspecting every `il_*_scope_triggers.py` rule module) for the
tighter, decision-relevant number. Full sweep scripts and raw output are
in this session's scratchpad (`il_d1a_classA_sweep.py`, `il_d1a_classA_
full.txt`, `il_d1a_classB_sweep.py`, `il_d1a_classB_sweep_prodtriggers.
py`) -- available on request, not reproduced in full here for length.

**P-R2/D-Q1 FP-exposure measurement (Class A widening).** Every one of
this Planner's 353-395 (methodology-dependent count; see log) live,
confirmed-missing multi-term entries was hand-read across a full,
un-truncated dump of the sweep output: every single one has genuine
defining prose after its split marker (a real `- <definition>` clause) --
zero false positives found. The multi-term grammar is a STRICT SUPERSET
of the already-shipped, already-precision-proven single-term grammar (it
additionally requires every one of N>=2 header segments to be a quoted
span separated from its neighbor by a comma and/or `ו`/`או` immediately
before the SAME already-trusted split marker) -- structurally more
constrained than the single-term case, not less, so it cannot newly admit
anything the existing single-term grammar's own precision argument
("a preamble/entry ending in `-` for an unrelated reason can never
fabricate a definition on its own") does not already cover.

**P-R2/D-Q1 FP-exposure measurement (Class B widening).** Among the 103
production-trigger-scoped no-marker matches, 2 named risk shapes were
hand-verified, both benign: (1) ~8% (5/60 hand-read, extrapolates to
~8/100) have a near-empty "rest of clause" (bare `.`/`);`/`).`) under a
naive "grab rest of clause as definition text" fix -- e.g. `חוק לימוד
חובה` art.2's "X נקרא בחוק זה 'נער בגיל לימוד חובה'." naming construct:
the TERM is genuinely real (the law does name this concept that phrase),
but its defining prose sits BEFORE the quote in this construct, not
after, so `definition_text` would degenerate to punctuation-only under
that fix strategy -- a `definition_text` QUALITY gap (term identity
unaffected), not a false CAPTURE, and the same class of pre-existing,
already-accepted imperfection as this sprint's own documented multi-line
`::`-continuation truncation residual. (2) a handful of matches (e.g.
`חוק לעידוד השקעות הון` arts.3/4, term "הפקודה") sit inside a `(TRIGGER,
"term")` PARENTHETICAL-naming construct where a stray closing `)` leads
`definition_text` -- again a formatting artifact, not a false capture (a
`(hereinafter: "the Ordinance")` alias IS a legitimate definition, the
same shape this sprint's own `(TRIGGER - term)` ad-hoc mechanism already
treats as definitional). No genuinely non-definitional term (an
established, real term wrongly captured as if newly defined) was found in
this sample. Full hand-read list in the scratchpad output.

**Live path:** every test below goes through the REAL chain --
`ingest_wiki_law` -> `run_definition_linking` (`sections.parse_articles`
-> `profile.normalize_for_parsing` -> `strip_wikilinks` -> `profile.
extract_local_scope_definitions` / `extract_definitions_from_section`
internally) -- never a rule's private `_extract` directly.

**Fixtures:** all 7 vendored below are real, unedited, programmatically-
extracted corpus excerpts, proven byte-identical substrings of their
source `.wiki` file (`fixture_bytes in corpus_source_bytes`, verified by
this Planner immediately before writing this file) and independently
live-reconfirmed through `sections.parse_articles` + `profile.
extract_local_scope_definitions` before this file was written (M4).
Offline: no test reads the corpus.
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
# Class A -- multi-term list entries dropped whole
# =====================================================================


def test_class_a_single_colon_comma_separated_multiterm_entry_is_currently_missed(
    db_session, matter_with_users
):
    """`:- "t1", "t2" - definition` (single-colon marker, PURE
    comma-separated sub-shape, TWO separate multi-term entries in one
    block).

    Fixture: `חוק הנהיגה הספורטיבית` article 4 (the schedule/`בתוספת זו`
    sub-article, real, verbatim): a `: [[בתוספת זו]] -` preamble followed
    by 5 `:-`-marked entries, two of which name TWO terms each
    (`"באגי", "מיני באגי"` and `"קרוס קארט", "רכב קארט"`), the other
    three single-term. Live-confirmed by this Planner:
    `profile.extract_local_scope_definitions` captures the three
    single-term entries (`"ענף הג'ימקאנה"`, `"רכב ספורט עממי"`,
    `"רכב שטח"`) but NOT ONE of the four multi-term terms -- proving the
    drop is per-ENTRY-LINE (whole multi-term lines vanish), not a
    corpus-wide failure of this article's list-shape detection.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='חוק הנהיגה הספורטיבית, התשע"ו-2016',
        fixture="חוק הנהיגה הספורטיבית_art4_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    assert {"ענף הג'ימקאנה", "רכב ספורט עממי", "רכב שטח"} <= captured_terms, (
        f"sanity: the three single-term sibling entries in the SAME list "
        f"should still capture today; got {captured_terms!r}"
    )
    expected_missing = {"באגי", "מיני באגי", "קרוס קארט", "רכב קארט"}
    assert expected_missing <= captured_terms, (
        f'expected all four comma-separated multi-term entry terms '
        f'{expected_missing!r} (article 4, single-colon marker) to be '
        f"captured -- they are silently dropped whole today because "
        f"`il_list_shape_scope.ENTRY_TERM_DASH_RE` only matches a SINGLE "
        f"quoted term before the dash; got {captured_terms!r}"
    )


def test_class_a_double_colon_vav_joined_multiterm_entry_is_currently_missed(
    db_session, matter_with_users
):
    """`::- "t1" ו"t2" - definition` (double-colon marker, PURE
    ו-joined sub-shape, no comma at all).

    Fixture: `חוק ביטוח בריאות ממלכתי` article 21ד (real, verbatim): a
    `בסעיף זה -` preamble followed by 3 `::-`-marked entries; the first
    names two terms via `ו` alone (`"בית מרקחת" ו"תכשיר מרשם"`), the
    third is single-term (`"רוקח אחראי"`). Live-confirmed by this
    Planner: the single-term sibling captures (`scope="local"`); the
    ו-joined pair does not.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='חוק ביטוח בריאות ממלכתי, התשנ"ד-1994',
        fixture="חוק ביטוח בריאות ממלכתי_art21ד_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    assert "רוקח אחראי" in captured_terms, (
        f"sanity: the single-term sibling entry in the SAME list should "
        f"still capture today; got {captured_terms!r}"
    )
    expected_missing = {"בית מרקחת", "תכשיר מרשם"}
    assert expected_missing <= captured_terms, (
        f'expected both ו-joined multi-term entry terms {expected_missing!r} '
        f"(article 21ד, double-colon marker) to be captured -- silently "
        f"dropped whole today; got {captured_terms!r}"
    )


def test_class_a_double_colon_mixed_comma_and_vav_multiterm_entry_is_currently_missed(
    db_session, matter_with_users
):
    """`::- "t1", "t2", ו"t3" - definition` (double-colon marker, MIXED
    comma+ו sub-shape -- the naturally-occurring Hebrew "Oxford comma
    with ו" construction, exercising both separators in one entry).

    Fixture: `חוק אזורים חופשיים לייצור בישראל` article 23א (real,
    verbatim, the SAME article QA cycle 3's log names for this exact
    example): a `בסעיף זה -` preamble (subsection (ו)) followed by 3
    `::-`-marked entries; the first names THREE terms
    (`"החזקה", "שליטה", ו"אמצעי שליטה"`), the other two are single-term
    (`"המעביר"`, `"הנעבר"`). Live-confirmed by this Planner: both
    single-term siblings capture; none of the three mixed-separator terms
    do.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='חוק אזורים חופשיים לייצור בישראל, התשנ"ד-1994',
        fixture="חוק אזורים חופשיים לייצור בישראל_art23א_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    assert {"המעביר", "הנעבר"} <= captured_terms, (
        f"sanity: the two single-term sibling entries in the SAME list "
        f"should still capture today; got {captured_terms!r}"
    )
    expected_missing = {"החזקה", "שליטה", "אמצעי שליטה"}
    assert expected_missing <= captured_terms, (
        f'expected all three mixed comma+ו multi-term entry terms '
        f'{expected_missing!r} (article 23א, double-colon marker) to be '
        f"captured -- silently dropped whole today; got {captured_terms!r}"
    )


# =====================================================================
# Class B -- quote-first candidates with no split marker after the quote
# =====================================================================


def test_class_b_reference_shape_no_dash_after_quote_is_currently_missed(
    db_session, matter_with_users
):
    """Sub-shape (i) -- the clean cross-reference shape: `TRIGGER,
    "term" כמשמעותה [[citation]].` -- no dash anywhere in the clause.

    Fixture: `חוק מס ערך מוסף` article 22 (real, verbatim, the manager's
    OWN root-case example, M18): `... לענין זה - "מסירה" כמשמעותה
    [[בסעיף 8 לחוק המכר, תשכ"ח-1968]].`. Live-confirmed by this Planner:
    `_find_split_marker` on the clause after the quote returns `(-1, 0)`
    -- genuinely no marker, not a gershayim-in-term measurement artifact
    (checked directly, per P-R10) -- so `extract_quote_first_candidates`
    discards the whole candidate via its `continue` branch.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='חוק מס ערך מוסף, התשל"ו-1975',
        fixture="חוק מס ערך מוסף_art22_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "מסירה" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for "מסירה" (article 22, no-dash '
        f"reference shape) -- discarded today because `_find_split_marker` "
        f"finds no marker in the clause; got {result['created_definitions']!r}"
    )


def test_class_b_plain_continuation_shape_no_dash_after_quote_is_currently_missed(
    db_session, matter_with_users
):
    """Sub-shape (ii) -- this Planner's own characterization of QA's
    unexplained ~80%: a plain LOCAL-defining continuation, no reference
    word, no dash -- `TRIGGER, "term" <לרבות/למעט ... defining text>;`.

    Fixture: `חוק התקנים` article 13 (real, verbatim): `... (ב) בסעיף
    זה, "מצרך" לרבות האריזה, העטיפה, הסליל או כל דבר אחר, שבהם נמכר
    המצרך, וכן כל פתק המחובר להם או למצרך.` -- the defining clause
    (`לרבות` = "includes") follows the quote directly, with NO dash
    anywhere. A second, independently live-reconfirmed real instance of
    this exact sub-shape (not vendored as a fixture, per the established
    "smallest of several instances" convention): `פקודת מס הכנסה`
    article 135, `... ולענין זה, "פקיד שומה" למעט עוזר פקיד שומה וגובה
    ראשי;` (`למעט` = "excludes") -- confirmed live: `[]` today, same root
    cause (`_find_split_marker` -> `(-1, 0)`).
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="חוק התקנים",
        fixture="חוק התקנים_art13_excerpt.wiki",
    )
    defs = [d for d in result["created_definitions"] if "מצרך" in d["terms"]]
    assert len(defs) == 1, (
        f'expected a Definition row for "מצרך" (article 13, no-dash plain-'
        f"continuation shape) -- discarded today for the same reason; got "
        f"{result['created_definitions']!r}"
    )


# =====================================================================
# Class C -- preambles living in the article's own HEADING
# =====================================================================


def test_class_c_schedule_heading_embedded_preamble_is_currently_missed(
    db_session, matter_with_users
):
    """The preamble (`... [[בתוספת זו]] -`) sits entirely in the
    article's own HEADING line; the body opens directly with `:-`-marked
    entries, no preamble line anywhere in the body.

    Fixture: `אכרזת גנים לאומיים, שמורות טבע, אתרים לאומיים ואתרי הנצחה
    (ערכי טבע מוגנים), התשס"ד-2004` article 8 (real, verbatim, a schedule
    sub-article, heading `(תיקון: תש"ף) : [[בתוספת זו]] -`): 10 `:-`-
    marked terms, ALL confirmed missing today. Live-confirmed by this
    Planner: `profile.is_definitions_heading` -> `False` for this
    heading; neither list-shape `ScopeTriggerRule` ever scans
    `article.heading`, only `article_body`'s own lines, so no rule
    reaches these entries at all. Two unrelated `(להלן - X)` ad-hoc terms
    embedded inside one entry's OWN definition text (`"פרק 92"`,
    `"צו תעריף המכס"`) DO already capture today via a different,
    unrelated mechanism -- harmless, not asserted on here.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title='אכרזת גנים לאומיים, שמורות טבע, אתרים לאומיים ואתרי הנצחה (ערכי טבע מוגנים), התשס"ד-2004',
        fixture="אכרזת גנים לאומיים_art8_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    expected_terms = {
        "תמצית",
        "כלי נגינה מוגמרים",
        "אבזרים מוגמרים לכלי נגינה",
        "חלקים מוגמרים לכלי נגינה",
        "מוצרים מוגמרים וארוזים לצורך מכירה קמעונאית",
        "אבקה",
        "משלוח",
        "עץ מעובד",
        "גידול מלאכותי",
        "שבבי עץ",
    }
    assert expected_terms <= captured_terms, (
        f"expected all 10 heading-embedded-preamble terms {expected_terms!r} "
        f"(article 8) to be captured -- no rule ever scans the article's "
        f"own heading text today; got {captured_terms!r} "
        f"(created_definitions={result['created_definitions']!r})"
    )


def test_class_c_ordinary_heading_embedded_preamble_is_currently_missed(
    db_session, matter_with_users
):
    """A SECOND, independent real instance of Class C, using a DIFFERENT
    trigger phrase (`לעניין הכרזה זו`, not the schedule-specific
    `בתוספת זו`) and a non-schedule document -- proving the class is not
    limited to `== תוספת ==`-style sub-articles.

    Fixture: `הכרזה מס' 3 על שינויים בתחולת חוק כליאתם של לוחמים בלתי
    חוקיים` article 1 (real, verbatim, heading `(תיקון: תשפ"ד) : לעניין
    הכרזה זו -`): 5 `:-`-marked terms, ALL confirmed missing today.
    """
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="הכרזה מס' 3 על שינויים בתחולת חוק כליאתם של לוחמים בלתי חוקיים",
        fixture="הכרזה מס' 3 לוחמים בלתי חוקיים_art1_excerpt.wiki",
    )
    captured_terms = {term for d in result["created_definitions"] for term in d["terms"]}
    expected_terms = {
        "הודעת ועדת השרים",
        "החוק",
        "החלטת ועדת השרים",
        "ועדת השרים",
        "תקנות מועדים לטיפול",
    }
    assert expected_terms <= captured_terms, (
        f"expected all 5 heading-embedded-preamble terms {expected_terms!r} "
        f"(article 1, non-schedule document) to be captured; got "
        f"{captured_terms!r} (created_definitions="
        f"{result['created_definitions']!r})"
    )
