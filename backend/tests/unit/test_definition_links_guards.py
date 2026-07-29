"""Sprint 2026-07-29-definition-links, item DL6b — Stage 5 false-positive
guards + ruling M7's bidi-degraded-text guard.

`app.definition_links.guards` does not exist yet -- ModuleNotFoundError is
the expected RED signal for every test in this file.

Public API pinned:
- `is_plain_quotation(text, quote_end_pos) -> bool` (Stage 5.1): True when a
  quoted span is NOT followed by a dash within ~3 tokens -- a title quote or
  direct speech, not a definition.
- `is_rejectable_term(term) -> bool` (Stage 5.2): True for terms shorter than
  2 characters or consisting only of digits/Hebrew numeral letters (rejects
  quoted sub-item labels like `"א"`).
- `resolve_law_title(candidate, known_titles) -> str | None` (Stage 5.4):
  EXACT match only against `known_titles` -- never a fuzzy fallback. When
  `candidate` matches more than one or zero known titles, returns `None`
  rather than silently picking one (the `חוק הבנקאות` ambiguity case: both
  `חוק הבנקאות (רישוי)` and `חוק הבנקאות (שירות ללקוח)` are known, so the
  bare, unparenthesized name must NOT resolve).
- `is_bidi_degraded(text) -> bool` (Stage 5.5 / M7): flags text showing
  reversed-RTL-word-order artifacts characteristic of naive PDF extraction.
  No specific detection algorithm is prescribed by the dossier (explicitly
  "PDF-tool-dependent") -- this test only pins the OBSERVABLE outcome: a
  normal, correctly-ordered Hebrew article body is NOT degraded, and the
  vendored synthetic fixture (`degraded_bidi_sample.wiki`, hand-derived by
  reversing each line's word order from the already-vendored clean fixture
  `חוק להגנת רכוש מופקד.wiki` -- NOT sourced from the out-of-scope BOI
  corpus) IS degraded.
"""

from __future__ import annotations

import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def test_is_plain_quotation_true_when_no_dash_follows_within_a_few_tokens():
    from app.definition_links.guards import is_plain_quotation

    text = 'החוק ידוע בכינויו "חוק ההגנה על הפרטיות" בקרב הציבור הרחב.'
    quote_end = text.index('"חוק ההגנה על הפרטיות"') + len('"חוק ההגנה על הפרטיות"')
    assert is_plain_quotation(text, quote_end) is True


def test_is_plain_quotation_false_when_dash_follows_shortly_after():
    from app.definition_links.guards import is_plain_quotation

    text = ':- "נכס" - מקרקעין ומיטלטלין, וכן זכויות.'
    quote_end = text.index('"נכס"') + len('"נכס"')
    assert is_plain_quotation(text, quote_end) is False


def test_is_rejectable_term_true_for_single_character():
    from app.definition_links.guards import is_rejectable_term

    assert is_rejectable_term("א") is True


def test_is_rejectable_term_true_for_digits_only():
    from app.definition_links.guards import is_rejectable_term

    assert is_rejectable_term("123") is True


def test_is_rejectable_term_false_for_a_genuine_short_legal_term():
    from app.definition_links.guards import is_rejectable_term

    assert is_rejectable_term("נכס") is False


def test_resolve_law_title_exact_match_succeeds():
    from app.definition_links.guards import resolve_law_title

    known = ["חוק הבנקאות (רישוי)", "חוק הבנקאות (שירות ללקוח)", "חוק המחשבים"]
    assert resolve_law_title("חוק המחשבים", known) == "חוק המחשבים"


def test_resolve_law_title_ambiguous_bare_name_returns_none_never_a_fuzzy_guess():
    """The exact edge case named in the review doc's Stage 5.4: a bare,
    unparenthesized `חוק הבנקאות` must not resolve when BOTH parenthesized
    variants are known -- no fuzzy fallback allowed."""
    from app.definition_links.guards import resolve_law_title

    known = ["חוק הבנקאות (רישוי)", "חוק הבנקאות (שירות ללקוח)"]
    assert resolve_law_title("חוק הבנקאות", known) is None


def test_resolve_law_title_unknown_name_returns_none():
    from app.definition_links.guards import resolve_law_title

    known = ["חוק המחשבים"]
    assert resolve_law_title("חוק שלא קיים בכלל", known) is None


def test_is_bidi_degraded_false_for_normal_article_text():
    from app.definition_links.guards import is_bidi_degraded

    text = (FIXTURES / "חוק להגנת רכוש מופקד.wiki").read_text(encoding="utf-8")
    assert is_bidi_degraded(text) is False


def test_is_bidi_degraded_true_for_the_synthetic_scrambled_fixture():
    from app.definition_links.guards import is_bidi_degraded

    text = (FIXTURES / "degraded_bidi_sample.wiki").read_text(encoding="utf-8")
    assert is_bidi_degraded(text) is True


def test_is_bidi_degraded_is_deterministic_across_repeated_calls():
    from app.definition_links.guards import is_bidi_degraded

    text = (FIXTURES / "degraded_bidi_sample.wiki").read_text(encoding="utf-8")
    assert is_bidi_degraded(text) == is_bidi_degraded(text)
