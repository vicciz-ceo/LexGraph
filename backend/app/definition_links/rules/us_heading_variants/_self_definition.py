"""D-DF's self-definition-marker predicate (`defines_in_body`, cycle 4) --
the BODY-side gate for `matches_defined_for_heading`. UNTOUCHED by cycle 5:
60 D-DF-confirmed rows are already pinned against this exact regex by
`test_definition_links_us_heading_variants_d_df.py`; item 13's
`defines_qualifier_in_body` (`_qualifier.py`, a DELIBERATE SUPERSET reusing
these same quote/gap primitives) is a NEW, separate predicate, not a
widening of this one -- widening this whitelist directly would risk
silently changing the already-shipped, already-QA'd 60-row population.

A quoted TERM -- straight or curly DOUBLE quotes, or curly single quotes --
directly followed, or after a short intervening gap and/or a whitelisted
"as used in .../for (the) purpose(s) of ..." lead-in clause BEFORE the
quote, by the defining verb `means`/`mean`/`shall mean` or the phrase `is
defined as`. A straight apostrophe (') is deliberately EXCLUDED from the
quote-char classes: it is indistinguishable from a contraction/possessive
in running prose ("individual's", "owner's").

Deliberately conservative, known limits (not pinned either direction):
misses defining verbs other than `means`/`mean`/`shall mean`/`is defined
as` (`includes`, `refers to`, `is a`, ...) by design. A cross-reference verb
("has the meaning ascribed to...", "is defined IN ...") never itself
contains `means`/`shall mean`/`is defined as` as a whole word, so it never
matches -- `has the meaning` is deliberately NOT in the verb whitelist, it
is precisely the cross-reference shape D-DF exists to exclude.
"""

from __future__ import annotations

import re

_QUOTE_OPEN_CHARS = "\"‘“"
_QUOTE_CLOSE_CHARS = "\"’”"
_LEAD_IN_CLAUSE_RE = (
    rf"(?:as used in|for (?:the )?purposes? of)\b[^{_QUOTE_OPEN_CHARS}{_QUOTE_CLOSE_CHARS},]{{0,60}}"
)
_DEFINING_VERB_RE = r"(?:means?|shall\s+mean|is\s+defined\s+as)\b"

# The AFTER-quote gap between the term's closing quote and the defining
# verb: a bounded, NON-GREEDY run of any characters EXCEPT quote
# characters (forbidding intervening quotes stops a later, unrelated
# entry's own quoted term from ever bridging a match across it). Bound is
# 80 (not e.g. 200): measured over the real 110-row `defined for`
# population as the smallest bound that clears genuine intervening-
# qualifier gaps while excluding one real false-positive bridge a wider
# bound let through.
_AFTER_QUOTE_GAP_RE = rf"[^{_QUOTE_OPEN_CHARS}{_QUOTE_CLOSE_CHARS}]{{0,80}}?"

_SELF_DEFINITION_RE = re.compile(
    rf"(?:{_LEAD_IN_CLAUSE_RE}\s*,?\s*)?"
    rf"[{_QUOTE_OPEN_CHARS}][^{_QUOTE_OPEN_CHARS}{_QUOTE_CLOSE_CHARS}]{{1,80}}[{_QUOTE_CLOSE_CHARS}]"
    rf"{_AFTER_QUOTE_GAP_RE}"
    rf"{_DEFINING_VERB_RE}",
    re.IGNORECASE,
)


def defines_in_body(body: str) -> bool:
    """Scans the FULL body via `re.search` (not anchored or prefix-
    limited): a real pinned marker can sit ~1500 chars in."""
    return bool(_SELF_DEFINITION_RE.search(body))
