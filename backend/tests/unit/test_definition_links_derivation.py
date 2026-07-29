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
