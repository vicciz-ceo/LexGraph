"""Sprint 2026-07-29-definition-links, item DL4 — Stage 2: extract
(term, definition) pairs from a located definitions section / article body.

`app.definition_links.extract` does not exist yet -- ModuleNotFoundError is
the expected RED signal for every test in this file.

Inputs to every function here are ALREADY the Stage 0/1 output (normalized,
wikilink-brackets-already-stripped-to-display-text plain text for one
section/article body) -- Stage 2 itself does no normalization or wikilink
handling; that is `app.definition_links.normalize`'s job, composed upstream
in `pipeline.py`. Test text below is real corpus prose (from the vendored
fixtures) with wikilink brackets manually pre-stripped to their display text,
exactly as Stage 0.5 would leave it.

Three public functions are pinned:
- `extract_definitions_from_section(text, *, scope) -> list[DefinitionCandidate]`
  over a located הגדרות section's body (multi-term entries, qualifier-before-
  dash, list-form blocks, and recursive nested sub-definitions).
- `extract_local_definitions(article_body) -> list[DefinitionCandidate]`
  scans a non-הגדרות article body for `לענין זה,` / `בסעיף זה,` immediately
  preceding a quoted-term-dash-definition (scope="local").
- `extract_adhoc_definitions(text) -> list[DefinitionCandidate]` for unquoted
  `(להלן - X)` apposition definitions outside any הגדרות section, requiring
  the captured span to be <=4 tokens (scope="local").

`DefinitionCandidate` exposes at least `.terms` (tuple[str, ...]),
`.definition_text` (str), `.scope` (str), `.qualifier` (str | None), and
`.parent_term` (str | None, set only for nested sub-definitions). It also
carries `.source_article_number` and `.source_chapter` (both str | None) as
provenance fields -- these functions leave them `None` since a single
section/article body has no way to know its own article number or chapter;
`pipeline.py` fills them in right after calling these functions, before
handing candidates to `app.definition_links.matcher.link_articles_to_
definitions` (which enforces chapter/local scope isolation using them; see
`tests/unit/test_definition_links_matcher.py`).
"""

from __future__ import annotations


def test_extract_single_term_definition():
    from app.definition_links.extract import extract_definitions_from_section

    text = ':- "נכס" - מקרקעין ומיטלטלין, וכן זכויות וטובות הנאה מכל סוג שהוא.'
    candidates = extract_definitions_from_section(text, scope="law-wide")
    assert len(candidates) == 1
    assert candidates[0].terms == ("נכס",)
    assert "מקרקעין ומיטלטלין" in candidates[0].definition_text
    assert candidates[0].scope == "law-wide"


def test_extract_multi_term_single_definition_emits_one_candidate_with_all_terms():
    """חוק הגנת הפרטיות.wiki line 51 (wikilink already stripped to display
    text by Stage 0): one dash, three terms sharing one derivation-clause
    body -- must emit ONE definition node with all three terms, not three
    separate candidates."""
    from app.definition_links.extract import extract_definitions_from_section

    text = ':- "חומר מחשב", "מחשב" ו"פלט" - כהגדרתם בחוק המחשבים;'
    candidates = extract_definitions_from_section(text, scope="law-wide")
    assert len(candidates) == 1
    assert set(candidates[0].terms) == {"חומר מחשב", "מחשב", "פלט"}
    assert "כהגדרתם" in candidates[0].definition_text


def test_extract_qualifier_before_dash_is_captured_separately_from_the_term():
    """חוק העונשין §34כד: `"ניפוק", של דבר -` -- the qualifier clause is
    captured but excluded from the term string itself."""
    from app.definition_links.extract import extract_definitions_from_section

    text = (
        ':- "ניפוק", של דבר - לרבות שימוש או עשיה בו, נסיון של שימוש או עשיה בו, '
        "או נסיון להניע אדם להשתמש או לעשות בו או לפעול על פיו;"
    )
    candidates = extract_definitions_from_section(text, scope="chapter")
    assert len(candidates) == 1
    assert candidates[0].terms == ("ניפוק",)
    assert candidates[0].qualifier is not None
    assert "של דבר" in candidates[0].qualifier
    assert candidates[0].definition_text.startswith("לרבות שימוש")


def test_extract_list_form_definition_spans_to_the_next_top_level_entry():
    """חוק העונשין §34כד: `"עובד הציבור" -` is followed by an indented
    `:: (1) ... (11) ...` block where EVERY numbered item already ends with
    its own `;` -- the naive "stop at the first semicolon" reading would
    wrongly truncate at item (1). The correct definition body runs through
    item (11) up to (but not including) the next top-level `:-` entry
    ("פומבי")."""
    from app.definition_links.extract import extract_definitions_from_section

    text = (
        ':- "עובד הציבור" -\n'
        ":: (1) עובד המדינה, לרבות חייל כמשמעותו בחוק השיפוט הצבאי, תשט\"ו-1955;\n"
        ":: (2) עובד רשות מקומית או רשות חינוך מקומית;\n"
        ':: (11) דירקטור מטעם המדינה בחברה ממשלתית, כמשמעותן בחוק החברות הממשלתיות, תשל"ה-1975;\n'
        ':- "פומבי", לענין מעשה -\n'
        ":: (1) מקום ציבורי, כשאדם יכול לראות את המעשה מכל מקום שהוא;\n"
    )
    candidates = extract_definitions_from_section(text, scope="chapter")
    by_term = {c.terms: c for c in candidates}
    public_worker = by_term[("עובד הציבור",)]
    assert "עובד המדינה" in public_worker.definition_text
    assert "דירקטור מטעם המדינה" in public_worker.definition_text  # item (11), not truncated at item (1)
    assert "פומבי" not in public_worker.definition_text  # must not swallow the NEXT entry

    public = by_term[("פומבי",)]
    assert "מקום ציבורי" in public.definition_text


def test_extract_recurses_into_nested_sub_definitions_scoped_to_the_outer_term():
    """חוק הגנת הפרטיות §3 line 62: `"מידע אישי" - ...; לעניין הגדרה זו,
    "אדם הניתן לזיהוי" - ...;` -- recurse Stage 2 on the outer definition's
    body; the inner term is scoped only to the outer term's own occurrences,
    not law-wide."""
    from app.definition_links.extract import extract_definitions_from_section

    text = (
        ':- "מידע אישי" - נתון הנוגע לאדם מזוהה או לאדם הניתן לזיהוי; לעניין הגדרה זו, '
        '"אדם הניתן לזיהוי" - מי שניתן לזהותו במאמץ סביר, במישרין או בעקיפין;'
    )
    candidates = extract_definitions_from_section(text, scope="law-wide")
    assert len(candidates) == 2

    outer = next(c for c in candidates if c.terms == ("מידע אישי",))
    assert outer.parent_term is None
    assert "נתון הנוגע לאדם מזוהה" in outer.definition_text

    inner = next(c for c in candidates if c.terms == ("אדם הניתן לזיהוי",))
    assert inner.parent_term == "מידע אישי"
    assert "מי שניתן לזהותו" in inner.definition_text


def test_extract_local_definitions_finds_leanyan_zeh_trigger():
    """חוק העונשין §35(ב)/(ג): `לענין זה,`/`בסעיף זה,` immediately before a
    quoted-term-dash-definition, ending with `.` (last entry in the
    paragraph), not `;`."""
    from app.definition_links.extract import extract_local_definitions

    article_body = (
        ': (ב) היה העונש קנס... לענין זה, "שיעור מעודכן" - שיעור הקנס שהיה קבוע בחוק לעבירה.\n'
        ': (ג) שונה שיעור הקנס... בסעיף זה, "מדד" - מדד המחירים לצרכן שמפרסמת הלשכה המרכזית לסטטיסטיקה.\n'
    )
    candidates = extract_local_definitions(article_body)
    terms = {c.terms[0] for c in candidates}
    assert terms == {"שיעור מעודכן", "מדד"}
    assert all(c.scope == "local" for c in candidates)


def test_extract_local_definitions_finds_besaif_zeh_trigger_in_subsection():
    """חוק הגנת הפרטיות §8(א): `בסעיף זה, "עיבוד" - למעט אחסון באקראי
    ובתום לב.`"""
    from app.definition_links.extract import extract_local_definitions

    article_body = ': (א) בסעיף זה, "עיבוד" - למעט אחסון באקראי ובתום לב.\n'
    candidates = extract_local_definitions(article_body)
    assert len(candidates) == 1
    assert candidates[0].terms == ("עיבוד",)
    assert candidates[0].scope == "local"


def test_extract_adhoc_unquoted_definition_requires_short_captured_span():
    """חוק להגנת רכוש מופקד §2: `(להלן - בעל זכות)` -- ad-hoc unquoted
    inline definition by apposition, outside any הגדרות section."""
    from app.definition_links.extract import extract_adhoc_definitions

    text = (
        "מי שנמסר נכס להנהלתו או לשליטתו לטובתו של אחר (להלן - בעל זכות) על פי "
        "הרשאה או מינוי או בחזקת נאמן, ימסור לאפוטרופוס הכללי הודעה על כך בכתב."
    )
    candidates = extract_adhoc_definitions(text)
    assert len(candidates) == 1
    assert candidates[0].terms == ("בעל זכות",)
    assert candidates[0].scope == "local"


def test_extract_adhoc_unquoted_definition_single_token_case():
    """חוק הבנקאות (שירות ללקוח) §3: `(להלן - הטעיה)`."""
    from app.definition_links.extract import extract_adhoc_definitions

    text = (
        "דבר העלול להטעות לקוח בכל ענין מהותי למתן שירות ללקוח (להלן - הטעיה); "
        "בלי לגרוע מכלליות האמור יראו ענינים אלה כמהותיים:"
    )
    candidates = extract_adhoc_definitions(text)
    assert len(candidates) == 1
    assert candidates[0].terms == ("הטעיה",)


def test_extract_definitions_from_section_is_deterministic_across_repeated_calls():
    from app.definition_links.extract import extract_definitions_from_section

    text = ':- "נכס" - מקרקעין ומיטלטלין, וכן זכויות וטובות הנאה מכל סוג שהוא.'
    first = extract_definitions_from_section(text, scope="law-wide")
    second = extract_definitions_from_section(text, scope="law-wide")
    assert [(c.terms, c.definition_text) for c in first] == [
        (c.terms, c.definition_text) for c in second
    ]
