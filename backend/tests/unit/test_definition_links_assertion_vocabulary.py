"""Sprint 2026-07-29-definition-links, item DL1 — assertion-type vocabulary
extension (ruling M2).

`app.services.validation.ALLOWED_ASSERTION_TYPES` already exists (sprint
2026-07-25-collaborative-assertions) -- this file's RED signal is a genuine
assertion FAILURE (the two new type names are simply absent yet), not an
import error.

Ruling M2: the LINKS this sprint produces are Assertions with two NEW
vocabulary entries (exact names Planner's call, consistent with the existing
ALLOWED_ASSERTION_TYPES naming style -- all-caps verb phrases):
- `USES_DEFINITION`: an article uses a term whose definition lives
  elsewhere (Stage 3's `article_uses_term` edge).
- `DERIVES_FROM_LAW`: a definition explicitly derives from another law
  (Stage 4's `law_derives_definition` edge), including the M5 case where
  the target law is unresolved (target_law_id=null) but the assertion is
  still created.

Both must validate WITHOUT `is_proposed_new=True` once added -- they are
part of the controlled vocabulary from this sprint on, not one-off
submitter-flagged exceptions.
"""

from __future__ import annotations

import pytest


def test_uses_definition_is_in_the_controlled_vocabulary():
    from app.services.validation import ALLOWED_ASSERTION_TYPES

    assert "USES_DEFINITION" in ALLOWED_ASSERTION_TYPES


def test_derives_from_law_is_in_the_controlled_vocabulary():
    from app.services.validation import ALLOWED_ASSERTION_TYPES

    assert "DERIVES_FROM_LAW" in ALLOWED_ASSERTION_TYPES


@pytest.mark.parametrize("assertion_type", ["USES_DEFINITION", "DERIVES_FROM_LAW"])
def test_new_definition_link_types_validate_without_the_proposed_new_flag(assertion_type):
    from app.services.validation import validate_assertion_type

    # Must not raise -- these are controlled-vocabulary members, not
    # submitter-flagged proposed-new types.
    validate_assertion_type(assertion_type, is_proposed_new=False)
