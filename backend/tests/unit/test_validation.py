"""B5 — pure validation/sanitization unit tests (spec §2, §7, gate G10).

Exercises `app.services.validation` directly. Bodies are
`raise NotImplementedError` pending the B5 Developer track.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.services.validation import (
    ValidationError,
    sanitize_for_storage,
    validate_effective_dates,
    validate_proposition_not_empty,
)


def test_sanitize_strips_script_tags_but_preserves_text():
    result = sanitize_for_storage("<script>alert(1)</script>Clause 8.4 controls.")
    assert "<script>" not in result
    assert "Clause 8.4 controls." in result


def test_sanitize_is_a_no_op_on_plain_text():
    plain = "Clause 8.4 creates a limited exception."
    assert sanitize_for_storage(plain) == plain


def test_sanitize_neutralizes_event_handler_attributes():
    result = sanitize_for_storage("<img src=x onerror=alert(1)>")
    assert "onerror" not in result


# --- QA regression (2026-07-26): unclosed-tag bypass ------------------------
#
# `sanitize_for_storage`'s tag stripper is `<[^>]+>`, which requires a
# closing `>` inside the SAME string to recognize and remove a tag. A tag
# with no closing `>` (a well-known regex-sanitizer bypass class — QA
# brief item (b)) survives untouched, including any event-handler
# attribute it carries. Gate G10 requires hostile input be "stored/
# rendered as inert data" regardless of whether the attacker bothers to
# close their tag. These are RED against the current implementation and
# pin the REQUIRED behavior, not the bug.


def test_sanitize_neutralizes_unclosed_tag_with_event_handler():
    result = sanitize_for_storage("<img src=x onerror=alert(1) trailing text with no closing bracket")
    assert "<img" not in result
    assert "onerror" not in result


def test_sanitize_neutralizes_unclosed_tag_even_when_followed_by_more_markup():
    # Realistic shape: the sanitized value is later concatenated into a
    # larger HTML document, so a `>` appearing later in the *page* (not in
    # the user's input) must not "complete" the attacker's tag. The
    # sanitizer must neutralize the open tag using only the text it was
    # given -- it must not rely on a `>` that never arrives.
    result = sanitize_for_storage("<svg onload=alert(document.cookie) foo=bar")
    assert "<svg" not in result
    assert "onload" not in result


def test_sanitize_neutralizes_unclosed_tag_with_single_quoted_attribute():
    # QA cycle-2 regression pin: this quoted-attribute shape already
    # passes against the cycle-1 fix (`_UNCLOSED_TAG_RE`'s
    # `[^\s>]*` attribute-value class happily matches quote characters
    # too) but had no dedicated test of its own -- pinning it so a future
    # change can't silently regress it.
    result = sanitize_for_storage("<img src='x' onerror='alert(1)' trailing prose stays")
    assert "<img" not in result
    assert "onerror" not in result
    assert "trailing prose stays" in result


# --- QA regression (2026-07-26, cycle 2): no-space-before-attribute bypass --
#
# `_UNCLOSED_TAG_RE` requires `\s+` immediately before every `key=value`
# attribute token, so it only recognizes attributes separated from the tag
# name (or from each other) by whitespace. A `/` immediately after the tag
# name with NO whitespace -- e.g. `<img/onerror=alert(1)` -- is a
# well-documented real-world sanitizer-evasion shape (OWASP XSS cheat
# sheet): per the HTML5 tokenizer, a `/` right after the tag name enters
# "self-closing start tag state", and the very next non-`>` character
# (here `o` of `onerror`) is reconsumed in "before attribute name state" --
# so `onerror` IS parsed as a live attribute by real browsers even though
# no whitespace precedes it. The current regex's `\s+` requirement means
# this whole class survives `sanitize_for_storage` untouched. Confirmed
# live via the real API (create/PATCH/revisions/comments/rating-rationale
# all reproduce this -- same shared function). RED against the current
# implementation; pins the REQUIRED behavior, not the bug.


def test_sanitize_neutralizes_unclosed_tag_with_no_space_before_attribute():
    result = sanitize_for_storage("<img/onerror=alert(1) Clause 8.4 still creates the exception.")
    assert "<img" not in result
    assert "onerror" not in result


def test_sanitize_neutralizes_unclosed_svg_with_no_space_before_attribute():
    result = sanitize_for_storage("<svg/onload=alert(document.cookie) Good point.")
    assert "<svg" not in result
    assert "onload" not in result


# --- QA regression (2026-07-26, cycle 2): benign-prose corruption -----------
#
# `_TAG_RE = r"<[^>]+>"` has no concept of "this `<` and that `>` are
# unrelated" -- it strips everything between the FIRST `<` and the very
# next `>` anywhere later in the string, even when both characters are
# ordinary comparison operators in unrelated clauses. Legal/financial
# prose routinely uses both in one sentence (amount thresholds, term
# lengths, date ranges), so this silently deletes legitimate authored
# content -- violating spec §2 ("propositions are stored exactly as
# authored") and the QA brief's explicit benign-preservation requirement.
# Pre-existing in `_TAG_RE` (unchanged by the cycle-1 fix), first caught by
# this adversarial probe. RED against the current implementation; pins the
# REQUIRED behavior (byte-for-byte preservation of benign text), not the
# bug.


def test_sanitize_preserves_prose_with_less_than_and_later_unrelated_greater_than():
    benign = "The threshold is met if the amount is < $500 and the term is > 10 years."
    assert sanitize_for_storage(benign) == benign


def test_sanitize_preserves_prose_with_multiple_unrelated_comparisons():
    benign = "if x < y and y > z then the exception in Clause 3 < Clause 8 applies"
    assert sanitize_for_storage(benign) == benign


# --- QA regression (2026-07-26, cycle 3): CDATA/RCDATA-adjacent-element bypass
#
# `_SanitizingParser._CDATA_CONTENT_TAGS` only suppresses `handle_data` for
# `script`/`style`. But the stdlib `html.parser.HTMLParser` this class is
# built on treats a WIDER set of elements as raw-text containers
# internally: `HTMLParser.CDATA_CONTENT_ELEMENTS` also includes `iframe`,
# `xmp`, `noembed`, `noframes` (their content is tokenized as one opaque
# blob, never sub-parsed for nested tags -- exactly matching how real
# browsers treat these elements), and `HTMLParser.RCDATA_CONTENT_ELEMENTS`
# covers `textarea`/`title` the same way. Because our suppression list
# doesn't match the parser's own raw-text list, a `<script>` payload
# nested inside any of these wrapper elements is delivered to
# `handle_data` as literal, unparsed text -- and since `_cdata_skip_depth`
# never got incremented for the wrapper tag, that text is NOT suppressed:
# it survives `sanitize_for_storage` byte-for-byte, e.g.
# `<iframe><script>alert(1)</script></iframe>` -> `<script>alert(1)</script>`
# stored verbatim. A downstream render of the "sanitized" value would
# execute this. Confirmed live via the real API on all five write paths
# (create, PATCH, revisions, comments, rating-rationale -- all call this
# same shared function). RED against the current implementation; pins the
# REQUIRED behavior (no live-looking markup survives), not the bug.


def test_sanitize_neutralizes_script_nested_inside_iframe():
    result = sanitize_for_storage("<iframe><script>alert(1)</script></iframe>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_textarea():
    result = sanitize_for_storage("<textarea><script>alert(1)</script></textarea>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_title():
    result = sanitize_for_storage("<title><script>alert(1)</script></title>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_noembed():
    result = sanitize_for_storage("<noembed><script>alert(1)</script></noembed>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_noframes():
    result = sanitize_for_storage("<noframes><script>alert(1)</script></noframes>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_script_nested_inside_xmp():
    result = sanitize_for_storage("<xmp><script>alert(1)</script></xmp>Clause stays.")
    assert "<script" not in result
    assert "Clause stays." in result


def test_sanitize_neutralizes_dangerous_tag_nested_inside_iframe_without_script():
    # Not every payload needs an inner <script> -- any tag-shaped content
    # inside the raw-text wrapper survives the same way.
    result = sanitize_for_storage('<iframe><img src=x onerror=alert(1)></iframe>Clause stays.')
    assert "<img" not in result
    assert "onerror" not in result
    assert "Clause stays." in result


# --- QA regression (2026-07-26, cycle 3): second abandoned tag leaks --------
#
# `_salvage_trailing_prose` walks the leftover, unresolved tail from ONE
# abandoned (never-closed) start tag: it strips the tag name plus a run of
# `name=value` attribute tokens, then returns whatever follows untouched.
# When the untouched remainder itself contains a SECOND, independent
# abandoned tag (e.g. two unclosed elements chained back-to-back with no
# `>` anywhere in the whole input), the attribute-token walk correctly
# stops at the second tag's `<` (since `<svg` isn't `key=value`-shaped),
# but the returned "prose tail" then contains that second tag's raw
# opening markup AND its own live-looking attribute verbatim --
# `<img src=x onerror=alert(1) <svg onload=alert(2) trailing` sanitizes to
# ` <svg onload=alert(2) trailing`, i.e. the second tag's `<svg
# onload=alert(2)` survives untouched. Confirmed live via the real API.
# RED against the current implementation; pins the REQUIRED behavior (no
# live-looking tag/attribute text survives), not the bug.


def test_sanitize_neutralizes_second_of_two_chained_abandoned_tags():
    result = sanitize_for_storage(
        "<img src=x onerror=alert(1) <svg onload=alert(2) trailing"
    )
    assert "<img" not in result
    assert "<svg" not in result
    assert "onerror" not in result
    assert "onload" not in result


def test_sanitize_neutralizes_second_of_two_chained_abandoned_tags_same_tag_name():
    result = sanitize_for_storage(
        "<img src=x onerror=alert(1) <img src=y onerror=alert(2) more text"
    )
    assert result.count("<img") == 0
    assert "onerror" not in result


# --- QA regression pins (2026-07-26, cycle 3): confirmed-correct shapes -----
#
# These attack/edge-case shapes were adversarially probed in cycle 3 and
# found already handled correctly by the `html.parser`-based tokenizer.
# Pinned here so a future change to `_SanitizingParser` or
# `_salvage_trailing_prose` can't silently regress them.


def test_sanitize_neutralizes_unclosed_tag_with_quoted_attribute_containing_greater_than():
    # A literal `>` INSIDE a quoted attribute value must not be mistaken
    # for the tag's closing bracket -- the tag stays open past it, exactly
    # as a real browser's tokenizer would treat it.
    result = sanitize_for_storage('<img src="x" onerror="alert(1)>" trailing prose stays')
    assert "<img" not in result
    assert "onerror" not in result
    assert "trailing prose stays" in result


def test_sanitize_neutralizes_closed_tag_with_literal_greater_than_in_attribute_value():
    result = sanitize_for_storage('<img alt="a>b" onerror=alert(1)>Clause stays.')
    assert "<img" not in result
    assert "onerror" not in result
    assert result == "Clause stays."


def test_sanitize_neutralizes_script_with_space_before_closing_bracket():
    # `</script >` (whitespace before `>`) is still a valid closing tag
    # per the HTML5 spec's tag-name-state grammar.
    result = sanitize_for_storage("<script>alert(1)</script >Clause stays.")
    assert "<script" not in result
    assert "alert(1)" not in result
    assert result == "Clause stays."


def test_sanitize_neutralizes_script_with_tab_before_closing_bracket():
    result = sanitize_for_storage("<script>alert(1)</script\t>Clause stays.")
    assert "<script" not in result
    assert "alert(1)" not in result
    assert result == "Clause stays."


def test_sanitize_preserves_section_symbol_and_ampersand():
    benign = "§8.2 & 8.4"
    assert sanitize_for_storage(benign) == benign


def test_sanitize_preserves_curly_quotes_and_em_dash():
    benign = "“The party shall” — as defined herein — comply with §8.2 & 8.4."
    assert sanitize_for_storage(benign) == benign


def test_sanitize_preserves_literal_entity_text_written_by_author():
    benign = "The literal text &amp; appears here, written by the author, not as markup."
    assert sanitize_for_storage(benign) == benign


def test_sanitize_preserves_multi_paragraph_text_with_newlines():
    benign = (
        "Paragraph one, discussing Clause 8.4.\n\n"
        "Paragraph two, discussing Clause 9.1 < Clause 12.\n\n"
        "Paragraph three."
    )
    assert sanitize_for_storage(benign) == benign


def test_validate_proposition_not_empty_rejects_blank():
    with pytest.raises(ValidationError):
        validate_proposition_not_empty("   ")


def test_validate_proposition_not_empty_accepts_text():
    validate_proposition_not_empty("A non-empty proposition.")


def test_validate_effective_dates_rejects_end_before_start():
    with pytest.raises(ValidationError):
        validate_effective_dates(date(2026, 1, 1), date(2020, 1, 1))


def test_validate_effective_dates_accepts_open_ended_range():
    validate_effective_dates(date(2020, 1, 1), None)


def test_validate_effective_dates_accepts_none_none():
    validate_effective_dates(None, None)
