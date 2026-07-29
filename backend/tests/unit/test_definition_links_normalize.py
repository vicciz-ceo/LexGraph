"""Sprint 2026-07-29-definition-links, item DL2 — Stage 0 text normalization.

`app.definition_links.normalize` does not exist yet -- ModuleNotFoundError is
the expected RED signal for every test in this file.

Per the review doc's "Deterministic definition-linking design" (Stage 0):
runs on a PARSING-SIDE COPY only (the original text is never mutated -- that
is enforced at the call-site in `pipeline.py`, not here). Two public
functions are pinned by this file:

- `normalize_for_parsing(raw_text) -> str`: Unicode NFC normalization; strip
  Hebrew niqqud (U+0591-U+05C7) defensively; collapse dash variants (en dash
  U+2013, em dash U+2014, Hebrew maqaf U+05BE) to a canonical `-`; collapse
  quote variants (straight `"`, curly `“`/`”`, gershayim U+05F4) to
  one quote class. The single geresh `׳` (׳) is NEVER touched -- it's
  the abbreviation mark (e.g. `תשמ"א` uses gershayim, but `מס׳ 5` uses a bare
  geresh for "number").
- `strip_wikilinks(text) -> (rewritten_text, hints)`: replace every
  `[[target]]` / `[[target|display]]` span with its display text (or the
  target text when there is no `|display`), returning the rewritten plain
  text plus one `{"target": str, "display": str}` hint per link, in
  left-to-right order -- these brackets are a scrape artifact; a general
  solution must not depend on them downstream.
"""

from __future__ import annotations


def test_normalize_collapses_en_dash_and_em_dash_to_canonical_hyphen():
    from app.definition_links.normalize import normalize_for_parsing

    text = 'הגדרה – הסבר ראשון, עוד הגדרה — הסבר שני.'
    normalized = normalize_for_parsing(text)
    assert "–" not in normalized
    assert "—" not in normalized
    assert "הגדרה - הסבר ראשון" in normalized
    assert "הגדרה - הסבר שני" in normalized


def test_normalize_collapses_hebrew_maqaf_to_canonical_hyphen():
    from app.definition_links.normalize import normalize_for_parsing

    # Real corpus shape (חוק הבנקאות (שירות ללקוח).wiki line ~291):
    # curly quotes + en-dash together.
    text = '־־־'  # three maqaf characters
    normalized = normalize_for_parsing(text)
    assert normalized == "---"


def test_normalize_collapses_curly_quotes_and_gershayim_to_one_quote_class():
    from app.definition_links.normalize import normalize_for_parsing

    text = '“hello” and ״gershayim״ and "straight"'
    normalized = normalize_for_parsing(text)
    quote_chars = {ch for ch in normalized if ch in '"“”״'}
    assert len(quote_chars) == 1, f"expected exactly one collapsed quote class, got {quote_chars!r}"


def test_normalize_never_touches_bare_geresh_abbreviation_mark():
    from app.definition_links.normalize import normalize_for_parsing

    # תשמ"א uses gershayim (should collapse); מס' 5 / מס׳ 5 uses a bare
    # geresh as an abbreviation mark for "number" and must be preserved
    # untouched -- it is never a term-quote.
    text = 'תיקון מס׳ 5 (עוד מונח)'
    normalized = normalize_for_parsing(text)
    assert "׳" in normalized, "bare geresh must survive normalization untouched"


def test_normalize_strips_niqqud_defensively():
    from app.definition_links.normalize import normalize_for_parsing

    # "שָׁלוֹם" with niqqud (U+05B8, U+05B9, U+05C1 etc.) should reduce to
    # plain letters -- niqqud is in the U+0591-U+05C7 block per Stage 0.2.
    text = "שָׁלוֹם"
    normalized = normalize_for_parsing(text)
    assert normalized == "שלום"


def test_normalize_is_unicode_nfc():
    from app.definition_links.normalize import normalize_for_parsing
    import unicodedata

    text = "שלום"
    normalized = normalize_for_parsing(text)
    assert normalized == unicodedata.normalize("NFC", normalized)


def test_normalize_is_deterministic_across_repeated_calls():
    from app.definition_links.normalize import normalize_for_parsing

    text = ':- "מאגר מידע" – אוסף פרטי מידע אישי;'
    first = normalize_for_parsing(text)
    second = normalize_for_parsing(text)
    assert first == second


def test_strip_wikilinks_replaces_bracket_span_with_display_text():
    from app.definition_links.normalize import strip_wikilinks

    # Real corpus shape (חוק הגנת הפרטיות.wiki line 51).
    text = ':- "חומר מחשב", "מחשב" ו"פלט" - כהגדרתם [[בחוק המחשבים]];'
    rewritten, hints = strip_wikilinks(text)
    assert "[[" not in rewritten and "]]" not in rewritten
    assert "כהגדרתם בחוק המחשבים" in rewritten
    assert hints == [{"target": "בחוק המחשבים", "display": "בחוק המחשבים"}]


def test_strip_wikilinks_uses_display_text_when_pipe_present():
    from app.definition_links.normalize import strip_wikilinks

    # Real corpus shape (חוק להגנת רכוש מופקד.wiki line 9): target and
    # display differ.
    text = ':- "האפוטרופוס הכללי" - כמשמעותו [[חוק האפוטרופוס הכללי|בפקודת האפוטרופוס הכללי, 1944]];'
    rewritten, hints = strip_wikilinks(text)
    assert "בפקודת האפוטרופוס הכללי, 1944" in rewritten
    assert "חוק האפוטרופוס הכללי" not in rewritten  # only the DISPLAY text remains in running text
    assert hints == [
        {"target": "חוק האפוטרופוס הכללי", "display": "בפקודת האפוטרופוס הכללי, 1944"}
    ]


def test_strip_wikilinks_preserves_left_to_right_order_for_multiple_links():
    from app.definition_links.normalize import strip_wikilinks

    text = "ראו [[סעיף 2]] וגם [[סעיף 3]] בהמשך."
    _, hints = strip_wikilinks(text)
    assert [h["target"] for h in hints] == ["סעיף 2", "סעיף 3"]


def test_strip_wikilinks_is_a_noop_on_text_with_no_links():
    from app.definition_links.normalize import strip_wikilinks

    text = "לא יפגע אדם בפרטיות של זולתו ללא הסכמתו."
    rewritten, hints = strip_wikilinks(text)
    assert rewritten == text
    assert hints == []
