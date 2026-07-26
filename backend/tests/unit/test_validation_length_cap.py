"""Track A, item A8 — length cap unit tests (issue #2 sub-item, gate G4,
ruling R3: 100,000 characters).

`validate_text_length` does not exist in `app.services.validation` yet --
ImportError is the expected RED signal.
"""

from __future__ import annotations

import pytest

from app.services.validation import ValidationError, validate_text_length

MAX_LENGTH = 100_000


def test_validate_text_length_accepts_short_text():
    validate_text_length("A short proposition.", label="proposition")


def test_validate_text_length_accepts_exactly_the_boundary():
    validate_text_length("x" * MAX_LENGTH, label="proposition")


def test_validate_text_length_rejects_one_over_the_boundary():
    with pytest.raises(ValidationError):
        validate_text_length("x" * (MAX_LENGTH + 1), label="proposition")


def test_validate_text_length_error_message_is_clear_and_names_the_field():
    with pytest.raises(ValidationError) as exc_info:
        validate_text_length("x" * (MAX_LENGTH + 1), label="rationale")
    message = str(exc_info.value)
    assert "rationale" in message
    assert "100,000" in message or "100000" in message
