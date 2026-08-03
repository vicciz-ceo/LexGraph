"""Jurisdiction controlled vocabulary (sprint 2026-08-02-us-state-law,
ruling R5, gate G5).

Director decision #3 (2026-08-02, AskUserQuestion): jurisdiction is a FIXED
controlled vocabulary -- `IL` plus every US state's `US-<postal>` code,
`US-DC`, `US-PR`, `US-FED` -- validated at the API and stamped by the
deterministic pipeline on every assertion it creates.

Mirrors the existing `ALLOWED_ASSERTION_TYPES` / `validate_assertion_type`
pattern in `app.services.validation`: a controlled-vocabulary constant plus
a `validate_*` function that raises the SAME `ValidationError` class every
other validator in this codebase raises (not a new exception type).

`JURISDICTION_CODES` is an ORDERED tuple (not a set/frozenset) so the
frontend/API can offer it as a stable-ordered dropdown: `"IL"` first, then
every `US-<postal>` state code in postal-alphabetical order, then
`"US-DC"`, `"US-PR"`, `"US-FED"` appended last -- exactly the order the
director's own decision text lists them in.

Validation is case-sensitive, exact-match only (`"us-de"` is invalid; only
the canonical uppercase form is). No fuzzy/normalized matching -- same
"no fabricated guess" discipline `guards.resolve_law_title` already
applies elsewhere in this codebase.
"""

from __future__ import annotations

from app.services.validation import ValidationError

_US_STATE_POSTAL_CODES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN "
    "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA "
    "WA WV WI WY"
).split()

JURISDICTION_CODES: tuple[str, ...] = (
    ("IL",)
    + tuple(f"US-{code}" for code in _US_STATE_POSTAL_CODES)
    + ("US-DC", "US-PR", "US-FED")
)

_JURISDICTION_CODE_SET = frozenset(JURISDICTION_CODES)


def validate_jurisdiction(jurisdiction: str | None) -> None:
    """Raise `ValidationError` unless `jurisdiction` is exactly one of the
    canonical `JURISDICTION_CODES`.

    Case-sensitive, exact-match only. Callers that treat jurisdiction as an
    optional field should skip calling this for `None` (see
    `app.routers.assertions`) -- this function itself always rejects `None`
    since the RED unit tests exercise it as a bad-code case directly.
    """
    if jurisdiction in _JURISDICTION_CODE_SET:
        return
    raise ValidationError(
        f"jurisdiction '{jurisdiction}' is not in the controlled vocabulary"
    )
