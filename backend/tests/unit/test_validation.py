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
