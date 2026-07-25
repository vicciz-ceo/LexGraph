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
