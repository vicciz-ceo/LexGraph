"""R-VERB-extended: `defined` immediately followed by punctuation, a dash,
or a whitelisted connector word/phrase -- cycles 2-5's connector-whitelist
extensions all live here. See the package `__init__.py` module docstring
for the full per-cycle history (BUG1-5, H-R7, H-R9, D-DF) and the cycle-5
RED test module docstrings for items 10/11/15's evidence.

Word/phrase connector whitelist, CLOSED (never "any word"):
  - `for`             -- D-DF (cycle 4) gates this alternation separately,
                          body-confirmed (`matches_defined_for_heading`
                          below); excluded from the *_UNCONDITIONAL_RE.
  - `as`, `term`       -- cycle 3, H-R9.
  - `and`              -- cycle 5, item 10 (same H-R7/H-R9-class connector
                          gap; UNCONDITIONAL -- not flagged as a precision
                          risk by QA cycle 3 or the manager's remeasurement).
  - `further`, `when`  -- cycle 5, item 15, mechanism 1 (manager class-5
                          evidence: ID "DEFINED FURTHER", MA "defined when").
  - `in case of`       -- cycle 5, item 15, mechanism 1, a 3-word phrase
                          (SC "defined in case of burglary...") -- DISTINCT
                          from the already-excluded bare `defined in`
                          cross-reference shape (FL "defined in s. 800.04"),
                          which stays unmatched because it lacks the
                          literal words "case of".

Trailing numeric/bracket scrape artifact (item 15, mechanism 2): a
footnote marker glued onto the heading by the scrape -- `defined 1`/
`defined 1]` -- matched only at the END of the heading. The LEFT WORD
BOUNDARY before `defined` is load-bearing: an earlier, unanchored probe
matched real Nevada `"...boundaries redefined 1969"` rows before this was
added (see the class-5 RED test's own regression guard,
`test_class5_trailing_artifact_strip_does_not_match_redefined`).

Mojibake dash tolerance (item 11): `normalize_mojibake` (own module,
`_shared.py`) runs before every regex below, so RI's `\\x80\\x94` byte
sequence is treated identically to a real em-dash.
"""

from __future__ import annotations

import re

from app.definition_links.rules.us_heading_variants._shared import normalize_mojibake

_NEGATION_GUARD = r"(?<!not )(?<!never )(?<!longer )"
_PUNCT_DASH_BRANCHES = (
    r"\s*[;:,.]"
    r"|\s*(?:[–—]|-{2,})"
    r"|\s+-(?!-)"
)
_IN_CASE_OF_BRANCH = r"\s+in\s+case\s+of\b"
_TRAILING_ARTIFACT_BRANCH = r"\s+\d+\]?\.?\s*$"

_CONNECTOR_WORDS_FULL = r"for|as|term|and|further|when"
_CONNECTOR_WORDS_UNCONDITIONAL = r"as|term|and|further|when"

# R-VERB-extended: the historical, UNCHANGED-meaning union (still includes
# the `for` connector) -- what `matches_heading_variant` composes with.
_VERB_EXTENDED_RE = re.compile(
    rf"{_NEGATION_GUARD}\bdefined\b(?:"
    rf"{_PUNCT_DASH_BRANCHES}"
    rf"|\s+(?:{_CONNECTOR_WORDS_FULL})\b"
    rf"|{_IN_CASE_OF_BRANCH}"
    rf"|{_TRAILING_ARTIFACT_BRANCH}"
    rf")",
    re.IGNORECASE,
)

# Cycle 4, D-DF: the SAME alternation with the `for` branch removed -- what
# `matches_heading_variant_unconditional` composes with (registered with
# `body_confirms=None`).
_VERB_EXTENDED_UNCONDITIONAL_RE = re.compile(
    rf"{_NEGATION_GUARD}\bdefined\b(?:"
    rf"{_PUNCT_DASH_BRANCHES}"
    rf"|\s+(?:{_CONNECTOR_WORDS_UNCONDITIONAL})\b"
    rf"|{_IN_CASE_OF_BRANCH}"
    rf"|{_TRAILING_ARTIFACT_BRANCH}"
    rf")",
    re.IGNORECASE,
)

# Cycle 4, D-DF: exactly the alternation split OUT of R-VERB-extended above
# -- `defined` immediately followed by the literal connector word `for`.
# Registered separately with `body_confirms=defines_in_body`.
_VERB_FOR_RE = re.compile(rf"{_NEGATION_GUARD}\bdefined\b\s+for\b", re.IGNORECASE)


def rule_verb_extended(heading: str) -> bool:
    """R-VERB-extended: `defined` immediately followed by punctuation, a
    dash, or a whitelisted connector word/phrase -- see `_VERB_EXTENDED_RE`."""
    return bool(_VERB_EXTENDED_RE.search(normalize_mojibake(heading)))


def rule_verb_extended_unconditional(heading: str) -> bool:
    """Cycle 4, D-DF: same as `rule_verb_extended` but via
    `_VERB_EXTENDED_UNCONDITIONAL_RE` -- every R-VERB-extended shape except
    the `for` connector, which is gated separately (`matches_defined_for_
    heading` below)."""
    return bool(_VERB_EXTENDED_UNCONDITIONAL_RE.search(normalize_mojibake(heading)))


def matches_defined_for_heading(heading: str) -> bool:
    """Cycle 4, D-DF: NARROW predicate, true iff `defined` is immediately
    followed by the literal connector word `for`. Registered with
    `body_confirms=defines_in_body`, so a match here only counts once the
    body also carries a self-definition marker."""
    return bool(_VERB_FOR_RE.search(normalize_mojibake(heading)))
