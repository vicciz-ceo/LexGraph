"""Cycle 5, item 13: `defined (qualifier)` / `defined to [verb]` -- ships as
a GATED third `HeadingRule`, mirroring D-DF's exact two-field pattern (see
`_self_definition.py` / `matches_defined_for_heading` in `_verb_extended.py`
for that precedent). See the cycle-5 RED test module docstring ("Item 13")
for the full rationale, including the VA judgment-call negative guard
(`STATE_VA_T8.01_C14_A4_S8.01-397.1`, an "is a" copula body deliberately
left unrecognized).

`matches_defined_qualifier_heading` is deliberately LOOSE (it also matches
the VA row, on purpose) -- precision is `defines_qualifier_in_body`'s job,
the same split D-DF uses. `defines_qualifier_in_body` is a DELIBERATE
SUPERSET of `_self_definition.defines_in_body`: same quoted-term +
lead-in-clause + bounded-gap mechanics, with the defining-verb whitelist
WIDENED to also accept `include(s)`/`shall (not )?include(s)` -- MO's own
drafting idiom (`the word "county" includes...`, `"employee" shall not
include...`). This is a NEW predicate; `defines_in_body` itself stays
untouched (see that module's docstring).
"""

from __future__ import annotations

import re

from app.definition_links.rules.us_heading_variants._self_definition import (
    _AFTER_QUOTE_GAP_RE,
    _LEAD_IN_CLAUSE_RE,
    _QUOTE_CLOSE_CHARS,
    _QUOTE_OPEN_CHARS,
)

_NEGATION_GUARD = r"(?<!not )(?<!never )(?<!longer )"

# Heading-shape predicate: a parenthetical, or the connector word `to`
# immediately followed by a verb, right after `defined`.
_DEFINED_QUALIFIER_RE = re.compile(
    rf"{_NEGATION_GUARD}\bdefined\b(?:\s*\(|\s+to\s+\w+)",
    re.IGNORECASE,
)

_QUALIFIER_DEFINING_VERB_RE = (
    r"(?:means?|shall\s+mean|is\s+defined\s+as|(?:shall\s+(?:not\s+)?)?includes?)\b"
)
_SELF_DEFINITION_QUALIFIER_RE = re.compile(
    rf"(?:{_LEAD_IN_CLAUSE_RE}\s*,?\s*)?"
    rf"[{_QUOTE_OPEN_CHARS}][^{_QUOTE_OPEN_CHARS}{_QUOTE_CLOSE_CHARS}]{{1,80}}[{_QUOTE_CLOSE_CHARS}]"
    rf"{_AFTER_QUOTE_GAP_RE}"
    rf"{_QUALIFIER_DEFINING_VERB_RE}",
    re.IGNORECASE,
)


def matches_defined_qualifier_heading(heading: str) -> bool:
    return bool(_DEFINED_QUALIFIER_RE.search(heading))


def defines_qualifier_in_body(body: str) -> bool:
    return bool(_SELF_DEFINITION_QUALIFIER_RE.search(body))
