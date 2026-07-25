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
