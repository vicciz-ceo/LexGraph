"""RED tests for the jurisdiction controlled vocabulary (sprint
2026-08-02-us-state-law, ruling R5, gate G5).

Director decision #3 (2026-08-02, AskUserQuestion): jurisdiction becomes a
FIXED controlled vocabulary -- `IL` plus every US state's `US-<postal>`
code, `US-DC`, `US-PR`, `US-FED` -- validated at the API and stamped by the
deterministic pipeline on every assertion it creates.

This is the SINGLE canonical definition (R5): `app.services.jurisdiction`
does not exist yet -- every test below is RED via `ImportError` until the
Developer creates it. The Planner is not permitted to write it (sprint
contract, "Forbidden").

Design calls this test pins down (so the Developer doesn't have to
re-derive them):
  - Module location: `backend/app/services/jurisdiction.py`, mirroring the
    existing `ALLOWED_ASSERTION_TYPES` / `validate_assertion_type` pattern
    in `backend/app/services/validation.py` (same package, same
    "controlled vocabulary + validate_* raises ValidationError" shape).
  - `JURISDICTION_CODES` is an ORDERED tuple (not a set/frozenset) so the
    frontend/API can offer it as a stable-ordered dropdown: `"IL"` first,
    then every `US-<postal>` state code in postal-alphabetical order, then
    `"US-DC"`, `"US-PR"`, `"US-FED"` appended last -- exactly the order
    the director's own decision text lists them in.
  - Validation is case-sensitive, exact-match only (`"us-de"` is invalid;
    only the canonical uppercase form is). No fuzzy/normalized matching --
    same "no fabricated guess" discipline `guards.resolve_law_title`
    already applies elsewhere in this codebase.
  - `validate_jurisdiction` raises `app.services.validation.ValidationError`
    (the existing exception type every other `validate_*` function in this
    codebase raises), not a new exception class.
"""

from __future__ import annotations

import pytest

# RED: this module does not exist yet.
from app.services.jurisdiction import JURISDICTION_CODES, validate_jurisdiction
from app.services.validation import ValidationError

_US_STATE_POSTAL_CODES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN "
    "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA "
    "WA WV WI WY"
).split()

EXPECTED_JURISDICTION_CODES = (
    ("IL",) + tuple(f"US-{code}" for code in _US_STATE_POSTAL_CODES) + ("US-DC", "US-PR", "US-FED")
)


def test_expected_list_is_54_codes_matching_the_directors_decision():
    """Guards the test's OWN expected list against a transcription slip --
    1 (IL) + 50 (US states) + 3 (US-DC, US-PR, US-FED)."""
    assert len(EXPECTED_JURISDICTION_CODES) == 54
    assert len(set(EXPECTED_JURISDICTION_CODES)) == 54  # no duplicates
    assert len(_US_STATE_POSTAL_CODES) == 50


def test_jurisdiction_codes_match_the_directors_controlled_vocabulary():
    assert tuple(JURISDICTION_CODES) == EXPECTED_JURISDICTION_CODES


@pytest.mark.parametrize("code", EXPECTED_JURISDICTION_CODES)
def test_validate_jurisdiction_accepts_every_canonical_code(code):
    validate_jurisdiction(code)  # must not raise


@pytest.mark.parametrize(
    "bad_code",
    [
        "EU",  # seed_demo.py's current value -- explicitly NOT in the vocabulary
        "US",  # bare federal-looking prefix, not a real code
        "IL-TX",  # malformed hybrid
        "us-de",  # lowercase -- exact-match only, no case folding
        "US-ZZ",  # not a real US state/territory postal code
        "",
        None,
    ],
)
def test_validate_jurisdiction_rejects_anything_outside_the_vocabulary(bad_code):
    with pytest.raises(ValidationError):
        validate_jurisdiction(bad_code)
