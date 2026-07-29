"""Sprint 2026-07-29-definition-links, item DL6 — Stage 4: detect cross-law
derivation and link the two laws.

`app.definition_links.derivation` does not exist yet -- ModuleNotFoundError
is the expected RED signal for every test in this file.

Input text is Stage-0-normalized, wikilink-brackets-already-stripped-to-
display-text plain text (same convention as DL4's extract.py tests).

Public API pinned:
- `TRIGGER_PHRASES`: the ten כהגדרת*/כמשמעות* trigger forms (review doc's
  corpus-wide grep table), EXCLUDING `לפי חוק`/`כאמור בחוק` (those are
  weaker/generic references, handled by `is_generic_law_reference` instead).
- `detect_cross_law_derivations(text, *, source_term, known_law_titles=None)
  -> list[LawDerivesDefinitionEdge]`: a trigger immediately followed by
  `ב<law name>` / `בפקודת <name>` / an anaphoric `בחוק האמור`/`אותו חוק`/
  `החוק האמור` is a cross-law derivation. `known_law_titles` maps a
  normalized law title -> law id; when the extracted name doesn't exact-match
  any known title, the edge is STILL emitted with `target_law_id=None` and
  the raw matched string preserved (M5) -- never a fabricated guess. A
  trigger immediately followed by `בסעיף <N>` is Stage 3 territory (same-law
  internal reference) and must NOT be emitted here.
- `is_generic_law_reference(text, trigger_pos) -> bool`: True for a bare
  `לפי חוק`/`כאמור בחוק` UNLESS it appears as a definitions-entry's entire
  body (no other text) directly after a quoted term, in which case it IS a
  derivation, not a generic cross-reference.

`LawDerivesDefinitionEdge` exposes at least `.source_term`,
`.trigger_phrase`, `.matched_text`, `.target_law_name` (str | None),
`.target_law_id` (str | None).

Sprint 2026-07-29-definition-links, cycle 2, item DL13 (G7, POC finding 3,
ruling M9(c)): `_LAW_REF_RE`'s captured law-name group EXCLUDES `(` and
`)`, so a law whose real, ingested title carries a required parenthetical
qualifier (e.g. `חוק הבנקאות (שירות ללקוח)`, `חוק מיסוי מקרקעין (שבח
ורכישה)`) can never resolve -- the regex stops at the first `(`, producing
a short name that does not exact-match `known_law_titles`. A compounding
artifact: the character class also allows `.`, so a clause ending in a
sentence-period captures that period into the "law name," blocking an
otherwise-exact match. Fix: allow ONE balanced parenthetical qualifier in
the captured name, and strip trailing sentence punctuation before
title-matching. All positive cases below are corpus-real, verbatim
(wikilink-brackets-already-stripped-to-display-text, per this file's
existing convention) -- verified directly against
`/Users/nerya/AI for others/israeli-laws-wiki/data/laws/` during Planning.
"""

from __future__ import annotations


def test_trigger_phrases_cover_the_ten_derivation_forms_and_exclude_generic_ones():
    from app.definition_links.derivation import TRIGGER_PHRASES

    expected = {
        "כהגדרתו",
        "כהגדרתה",
        "כהגדרתם",
        "כהגדרתן",
        "כהגדרת",
        "כמשמעותו",
        "כמשמעותה",
        "כמשמעותם",
        "כמשמעותן",
        "כמשמעות",
    }
    assert set(TRIGGER_PHRASES) == expected
    assert "לפי חוק" not in TRIGGER_PHRASES
    assert "כאמור בחוק" not in TRIGGER_PHRASES


def test_detect_cross_law_derivation_resolves_a_known_law_by_exact_title():
    """חוק הגנת הפרטיות §3 line 51 (wikilink already stripped to display
    text): `כהגדרתם בחוק המחשבים` -- resolved when the exact title is in
    `known_law_titles`."""
    from app.definition_links.derivation import detect_cross_law_derivations

    text = 'כהגדרתם בחוק המחשבים;'
    edges = detect_cross_law_derivations(
        text,
        source_term="חומר מחשב",
        known_law_titles={"חוק המחשבים": "law-computers-id"},
    )
    assert len(edges) == 1
    edge = edges[0]
    assert edge.source_term == "חומר מחשב"
    assert edge.trigger_phrase == "כהגדרתם"
    assert edge.target_law_id == "law-computers-id"
    assert "חוק המחשבים" in edge.target_law_name


def test_detect_cross_law_derivation_preserves_unresolved_target_with_null_id():
    """M5: an unrecognized target law is STILL emitted, target_law_id=None,
    raw matched string preserved -- never dropped, never guessed."""
    from app.definition_links.derivation import detect_cross_law_derivations

    text = "כמשמעותו בפקודת האפוטרופוס הכללי, 1944;"
    edges = detect_cross_law_derivations(
        text, source_term="האפוטרופוס הכללי", known_law_titles={}
    )
    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_law_id is None
    assert edge.target_law_name is not None
    assert "האפוטרופוס הכללי" in edge.target_law_name
    assert "האפוטרופוס הכללי" in edge.matched_text


def test_detect_cross_law_derivation_uses_construct_form_kehegderat():
    """`כהגדרת` (construct form) is always followed by an explicit term
    name -- no pronoun-gender resolution needed."""
    from app.definition_links.derivation import detect_cross_law_derivations

    text = 'כהגדרת "חייל" בחוק השיפוט הצבאי, תשט"ו-1955;'
    edges = detect_cross_law_derivations(text, source_term="עובד המדינה", known_law_titles={})
    assert len(edges) == 1
    assert edges[0].trigger_phrase == "כהגדרת"


def test_detect_cross_law_derivation_resolves_anaphoric_reference_to_prior_law_in_text():
    """`אותו חוק` (one of the anaphoric forms alongside `בחוק האמור`/`החוק
    האמור`) resolves to the most recently named law earlier in the same
    text -- loosely modeled on חוק הבנקאות (שירות ללקוח) §1's `חוק הדואר`
    passage."""
    from app.definition_links.derivation import detect_cross_law_derivations

    text = (
        'החברה כהגדרתה בחוק הדואר, התשמ"ו-1986, בנותנה את השירותים הכספיים '
        "כהגדרתם באותו חוק;"
    )
    edges = detect_cross_law_derivations(text, source_term="גוף פיננסי", known_law_titles={})
    assert len(edges) == 2
    triggers = {e.trigger_phrase for e in edges}
    assert triggers == {"כהגדרתה", "כהגדרתם"}
    assert all("חוק הדואר" in (e.target_law_name or "") for e in edges)


def test_detect_cross_law_derivation_excludes_a_besaif_follow_on_same_law_reference():
    """A trigger immediately followed by `בסעיף <N>` is a SAME-LAW internal
    reference -- Stage 3 territory, must not be emitted here."""
    from app.definition_links.derivation import detect_cross_law_derivations

    text = "מרשם מאגרי המידע כמשמעותו בסעיף 12;"
    edges = detect_cross_law_derivations(text, source_term="מרשם", known_law_titles={})
    assert edges == []


def test_is_generic_law_reference_true_for_bare_lefi_chok_in_running_text():
    from app.definition_links.derivation import is_generic_law_reference

    text = "פעולה האסורה לפי חוק אחר לגמרי, שאינו חוק זה."
    pos = text.index("לפי חוק")
    assert is_generic_law_reference(text, pos) is True


def test_is_generic_law_reference_false_when_it_is_the_entire_definition_body():
    """`לפי חוק X` is treated as a derivation, not a generic reference, only
    when the WHOLE definition body directly after the quoted term IS
    `לפי חוק X` with no other dash-definition text."""
    from app.definition_links.derivation import is_generic_law_reference

    text = ':- "ריבית" - לפי חוק פסיקת ריבית והצמדה;'
    pos = text.index("לפי חוק")
    assert is_generic_law_reference(text, pos) is False


def test_detect_cross_law_derivations_is_deterministic_across_repeated_calls():
    from app.definition_links.derivation import detect_cross_law_derivations

    text = "כהגדרתם בחוק המחשבים;"
    known = {"חוק המחשבים": "law-computers-id"}
    first = detect_cross_law_derivations(text, source_term="חומר מחשב", known_law_titles=known)
    second = detect_cross_law_derivations(text, source_term="חומר מחשב", known_law_titles=known)
    assert [(e.source_term, e.trigger_phrase, e.target_law_id) for e in first] == [
        (e.source_term, e.trigger_phrase, e.target_law_id) for e in second
    ]


# --- DL13 (cycle 2, G7, ruling M9(c)) -- parenthetical-qualifier fix -------


def test_detect_cross_law_derivation_resolves_a_law_name_with_a_parenthetical_qualifier():
    """Real corpus clause (verbatim, wikilink-stripped;
    `חוק הגנת הפרטיות.wiki:241` / `חוק הנוטריונים.wiki:121` both carry this
    exact reference): `כהגדרתו בחוק הבנקאות (שירות ללקוח), התשמ"א-1981` --
    the target law's real, ingested title genuinely carries the `(שירות
    ללקוח)` qualifier; pre-fix, `_LAW_REF_RE` stops at the `(` and produces
    the short name `"חוק הבנקאות"`, which never matches."""
    from app.definition_links.derivation import detect_cross_law_derivations

    text = 'תאגיד בנקאי כהגדרתו בחוק הבנקאות (שירות ללקוח), התשמ"א-1981;'
    edges = detect_cross_law_derivations(
        text,
        source_term="תאגיד בנקאי",
        known_law_titles={"חוק הבנקאות (שירות ללקוח)": "law-banking-consumer-id"},
    )
    assert len(edges) == 1
    assert edges[0].target_law_id == "law-banking-consumer-id"
    assert edges[0].target_law_name == "חוק הבנקאות (שירות ללקוח)"


def test_detect_cross_law_derivation_resolves_a_parenthetical_qualifier_with_no_year_clause():
    """Real corpus clause (verbatim, `חוק שירות מידע פיננסי.wiki:143`):
    `כהגדרתו [[בחוק הבנקאות (שירות ללקוח)]]` -- no trailing year clause at
    all, just the paren-qualified name directly before the semicolon."""
    from app.definition_links.derivation import detect_cross_law_derivations

    text = "תאגיד בנקאי - כהגדרתו בחוק הבנקאות (שירות ללקוח), למעט חברת שירותים משותפת;"
    edges = detect_cross_law_derivations(
        text,
        source_term="תאגיד בנקאי",
        known_law_titles={"חוק הבנקאות (שירות ללקוח)": "law-banking-consumer-id"},
    )
    assert len(edges) == 1
    assert edges[0].target_law_id == "law-banking-consumer-id"


def test_detect_cross_law_derivation_resolves_a_hyphenated_parenthetical_qualifier_with_year():
    """Real corpus clause (verbatim, `חוק הירושה.wiki:307`): `כמשמעותו
    בחוק הסעד (טיפול באנשים עם מוגבלות שכלית-התפתחותית), תשכ"ט-1969` --
    the paren qualifier itself contains a hyphen (already normalized from
    the corpus's maqaf/en-dash, per Stage 0), and a trailing Hebrew-year
    clause follows the closing paren."""
    from app.definition_links.derivation import detect_cross_law_derivations

    text = (
        'ילד עם מוגבלות שכלית-התפתחותית - כמשמעותו בחוק הסעד '
        '(טיפול באנשים עם מוגבלות שכלית-התפתחותית), התשכ"ט-1969;'
    )
    edges = detect_cross_law_derivations(
        text,
        source_term="ילד עם מוגבלות שכלית-התפתחותית",
        known_law_titles={
            "חוק הסעד (טיפול באנשים עם מוגבלות שכלית-התפתחותית)": "law-welfare-disability-id"
        },
    )
    assert len(edges) == 1
    assert edges[0].target_law_id == "law-welfare-disability-id"
    assert edges[0].target_law_name == "חוק הסעד (טיפול באנשים עם מוגבלות שכלית-התפתחותית)"


def test_detect_cross_law_derivation_resolves_a_second_parenthetical_qualifier_example_with_year():
    """Real corpus clause (verbatim, e.g. `חוק הטבות מס ליישוב אזור קו
    עימות מזרחי (הוראת שעה).wiki:10`): `כהגדרתה [[בחוק מיסוי מקרקעין (שבח
    ורכישה), התשכ"ג-1963]]` -- a second, independent corpus-real
    parenthetical-qualifier + year-clause combination."""
    from app.definition_links.derivation import detect_cross_law_derivations

    text = 'דירת מגורים - כהגדרתה בחוק מיסוי מקרקעין (שבח ורכישה), התשכ"ג-1963;'
    edges = detect_cross_law_derivations(
        text,
        source_term="דירת מגורים",
        known_law_titles={"חוק מיסוי מקרקעין (שבח ורכישה)": "law-land-taxation-id"},
    )
    assert len(edges) == 1
    assert edges[0].target_law_id == "law-land-taxation-id"
    assert edges[0].target_law_name == "חוק מיסוי מקרקעין (שבח ורכישה)"


def test_detect_cross_law_derivation_strips_a_trailing_sentence_period_before_matching():
    """Real corpus clause (verbatim, `חוק הבנקאות (רישוי).wiki:509`):
    `"אסיפה שנתית" - כהגדרתה [[בחוק החברות]].` -- the reference itself has
    NO parenthetical qualifier, but the clause ends in a sentence period
    directly after the law name (no `;`/`,` boundary); pre-fix, the
    character class (which does not exclude `.`) captures the period into
    the 'law name', producing `"חוק החברות."` which fails to exact-match
    the period-free `known_law_titles` key even though the target document
    is genuinely present."""
    from app.definition_links.derivation import detect_cross_law_derivations

    text = 'אסיפה שנתית - כהגדרתה בחוק החברות.'
    edges = detect_cross_law_derivations(
        text, source_term="אסיפה שנתית", known_law_titles={"חוק החברות": "law-companies-id"}
    )
    assert len(edges) == 1
    assert edges[0].target_law_id == "law-companies-id"
    assert edges[0].target_law_name == "חוק החברות"


def test_detect_cross_law_derivation_does_not_swallow_a_second_unrelated_parenthetical():
    """Negative case: the fix allows exactly ONE balanced parenthetical
    qualifier -- a second, immediately-following parenthetical (not
    separated by a comma/semicolon) must NOT be swallowed into the
    captured law name. Synthetic (not corpus-asserted): stress-tests the
    boundary of 'one balanced parenthetical', not a real ambiguity."""
    from app.definition_links.derivation import detect_cross_law_derivations

    text = (
        'ילד עם מוגבלות שכלית-התפתחותית - כמשמעותו בחוק הסעד '
        '(טיפול באנשים עם מוגבלות שכלית-התפתחותית) (הבהרה נוספת שאינה חלק מהשם);'
    )
    edges = detect_cross_law_derivations(
        text,
        source_term="ילד עם מוגבלות שכלית-התפתחותית",
        known_law_titles={
            "חוק הסעד (טיפול באנשים עם מוגבלות שכלית-התפתחותית)": "law-welfare-disability-id"
        },
    )
    assert len(edges) == 1
    assert edges[0].target_law_name == "חוק הסעד (טיפול באנשים עם מוגבלות שכלית-התפתחותית)"
    assert "הבהרה נוספת" not in edges[0].target_law_name
    assert "הבהרה נוספת" not in edges[0].matched_text
