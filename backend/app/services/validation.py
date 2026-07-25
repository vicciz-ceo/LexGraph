"""User-submitted assertion validation (shape only — Developer track B5).

Spec §7 / gate G10: propositions/rationales/comments must be sanitized so
raw HTML/scripts are stored/rendered as inert data, and submitted text
must never be treated as system/model instructions. The proposition must
be stored EXACTLY as authored (spec §2) — sanitization must not rewrite
legitimate text, only neutralize active markup.
"""

from __future__ import annotations

from datetime import date


class ValidationError(ValueError):
    """Raised when a user-submitted assertion payload fails validation."""


def sanitize_for_storage(raw_text: str) -> str:
    """Return `raw_text` with any active HTML/script content neutralized."""
    raise NotImplementedError("developer: implement HTML/script sanitization (B5)")


def validate_proposition_not_empty(proposition: str) -> None:
    raise NotImplementedError("developer: implement proposition presence check (B5)")


def validate_effective_dates(
    effective_from: date | None, effective_to: date | None
) -> None:
    """Raise ValidationError if the date range is not logically consistent."""
    raise NotImplementedError("developer: implement effective-date validation (B5)")
