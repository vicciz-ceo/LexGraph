"""B1 recognizer for US body-preamble definitions.

Kept separate from ``us_body_preamble`` so its registration order stays in
that module while this narrowly-scoped recognition logic remains readable.
"""

from __future__ import annotations

import re

# B1 is registered by ``us_body_preamble`` only after the California,
# Nebraska, Named-Act, and B2 rules. Registration order is precedence, so this
# broad US-* recognizer must retain that position rather than self-register.
#
# The normal trigger is tried at every occurrence. It recognizes "As used in",
# "For (the) purpose(s) of", and "In this <unit>" introductions. Singular
# ``purpose`` and the statutory ``divisions (C) and (D) of this section``
# qualifier are bounded real intro forms; neither changes shared extraction.
_B1_TRIGGER_RE = re.compile(
    r"(?:As used in(?:\s+divisions?\s+\([A-Z]\)\s+and\s+\([A-Z]\)\s+of)?|"
    r"For (?:the )?purposes? of|In) this\s+[A-Za-z][A-Za-z0-9 .\-]{0,30}",
    re.IGNORECASE,
)
_B1_LOOKAHEAD = 250
_B1_COLON_WINDOW = 160
# Colon-list recognition permits a colon within this measured 160-character
# window after the trigger. Its filler can be "the term", a short qualifier,
# or a longer "following terms ... meanings" clause, but must not be a
# forwarding/exclusion pointer. The window keeps the SD administrative
# citation-note colon (231 characters away) outside the branch.
_B1_FORWARDING_PHRASES = (
    "shall be as defined in",
    "shall have the same meaning as",
    "has the same meaning as",
    "has the meaning provided in",
    "has the meaning found in",
    "has the meaning stated in",
    "shall not include",
    "does not impair",
)
# Shapes 2 and 6 share this quote branch: a quoted term can follow the trigger
# directly (KS), after a bare comma, after "the term" (SD), or after one short
# comma-bounded qualifier (TN). The gap excludes quotes/commas and is capped
# at 60 characters, so it cannot swallow a real term while seeking another.
# D-INCLUDES applies here: a quote-following ``includes``/``shall include`` is
# a B1 recognition verb, while the PA direct branch below remains means-only.
_B1_QUOTE_MEANS_RE = re.compile(
    r'^(?P<gap>(?:,\s*(?:[^"“”,\n]{1,60},\s*)?)?(?:the term\s+)?)'
    r'["“](?P<term>[^"”]{1,150})["”]\s*(?:means|shall mean|includes|shall include)\b',
    re.IGNORECASE,
)
_B1_DIRECT_QUOTE_MEANS_RE = re.compile(
    r'\bthe\s+(?:word|term)\s+["“][^"”]{1,150}["”]\s+in\s+this\s+'
    r'[A-Za-z][A-Za-z0-9 .\-]{0,30}?\s+(?:means|shall mean)\b',
    re.IGNORECASE,
)

# "In this" is a statutory introduction only when its object is a legal
# unit.  Ordinary prose such as "in this manner" and "in this disclosure
# statement" may still contain quoted notices, but is not a definitions
# preamble.  Keep this vocabulary deliberately closed: it describes the
# grammatical role of the words following ``this``, not a jurisdiction or
# corpus-specific spelling.
_B1_LEGAL_UNIT_RE = re.compile(
    r"^(?:section|chapter|article|act|title|part|subsection|statute|code)\b",
    re.IGNORECASE,
)
_B1_SUBSTANTIVE_QUOTE_RE = re.compile(
    r'["“][^"”]{1,150}["”]\s*(?:means|shall mean|includes|shall include|denotes)\b',
    re.IGNORECASE,
)
_B1_PLURAL_LIST_RE = re.compile(
    r'(?P<list>(?:\(\d+\)\s*)?["“][^"”]{1,150}["”]\s*;\s*'
    r'(?:(?:and|or)\s+)?(?:\(\d+\)\s*)?["“][^"”]{1,150}["”]\s*;\s*)'
    r'(?P<relation>have\s+the\s+meaning\s+(?:set\s+forth|provided|specified)'
    r'[^\n]{0,180}?\bthose\s+terms\b[^\n]{0,180})',
    re.IGNORECASE | re.DOTALL,
)
_B1_VALID_QUOTED_TERM_RE = re.compile(r'(["“])(?P<term>[^"”]{1,150})(["”])')
_B1_COORDINATION_ONLY_RE = re.compile(
    r"^[\s;,:()\[\]{}\d]*(?:\([A-Za-z0-9]+\)[\s;,:()\[\]{}\d]*)?"
    r"(?:(?:and|or)\b[\s;,:()\[\]{}\d]*)?$",
    re.IGNORECASE,
)


def _b1_colon_list_branch(after: str) -> bool:
    window = after[:_B1_COLON_WINDOW]
    # The em-dash branch is not corpus-unique: M-R53 reconciled 1,788
    # whole-body occurrences and 984 rows operationally captured by this
    # rule. It is retained here as a behavior-preserving, zero-filler intro.
    if window[:1] == "—":
        return True
    colon_index = window.find(":")
    if colon_index == -1:
        return False
    filler = window[:colon_index].lower()
    return not any(phrase in filler for phrase in _B1_FORWARDING_PHRASES)


def _b1_quote_means_branch(after: str) -> bool:
    # Quote-gap filtering uses the same forwarding vocabulary as colon-list
    # filtering. This is deliberately retained because widened quote shapes
    # otherwise admit forwarding pointers rather than local definitions.
    match = _B1_QUOTE_MEANS_RE.match(after)
    if match is None:
        return False
    gap = match.group("gap").lower()
    return not any(phrase in gap for phrase in _B1_FORWARDING_PHRASES)


def _b1_trigger_colon_or_quote_means(body: str) -> str | None:
    # PA's "the word \"association\" in this chapter means" needs a direct,
    # non-greedy means path: the general trigger's historical greedy unit tail
    # can consume its defining verb. This direct path is intentionally not a
    # D-INCLUDES path; includes belongs to the quote branch above.
    if _B1_DIRECT_QUOTE_MEANS_RE.search(body):
        return "Definitions"
    for trigger_match in _B1_TRIGGER_RE.finditer(body):
        after = body[trigger_match.end() : trigger_match.end() + _B1_LOOKAHEAD]
        trigger = trigger_match.group(0)
        if trigger.lower().startswith("in this") and not _B1_LEGAL_UNIT_RE.match(
            trigger[7:].lstrip()
        ):
            continue
        if _b1_quote_means_branch(after):
            return "Definitions"
        if _b1_colon_list_branch(after):
            if trigger.lower().startswith("as used in") and not (
                _B1_SUBSTANTIVE_QUOTE_RE.search(after) or _B1_PLURAL_LIST_RE.search(after)
            ):
                continue
            if '"' in after or '“' in after:
                return "Definitions"
    return None


def is_b1_derived_body(body: str) -> bool:
    """Whether B1, rather than another body-preamble rule, recognizes body."""
    return _b1_trigger_colon_or_quote_means(body) is not None


def _raw_payloads_for_term(raw_source: str, term: str) -> list[str]:
    """Return payloads immediately following exact, valid raw quoted terms.

    A normalized quote can help discover a candidate, but only matching raw
    delimiters count as evidence for removing it.  The next quoted term (or
    end of source) bounds the payload, preventing a later real definition
    from being attributed to an earlier list entry.
    """
    payloads: list[str] = []
    matches = list(_B1_VALID_QUOTED_TERM_RE.finditer(raw_source))
    for index, match in enumerate(matches):
        if match.group("term").strip() != term or match.group(1) != match.group(3):
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_source)
        payloads.append(raw_source[match.end() : end])
    return payloads


def preserve_substantive_b1_candidates(candidates, raw_source: str):
    """Default-preserve B1 candidates unless raw evidence proves a pseudo-entry."""
    kept = []
    for candidate in candidates:
        payloads = [payload for term in candidate.terms for payload in _raw_payloads_for_term(raw_source, term)]
        if not payloads or any(not _B1_COORDINATION_ONLY_RE.fullmatch(payload) for payload in payloads):
            kept.append(candidate)
    return kept


def plural_anaphora_repairs(raw_source: str, *, scope: str, candidate_factory):
    """Repair only a fully matched quoted list with its explicit plural relation."""
    repairs = []
    for match in _B1_PLURAL_LIST_RE.finditer(raw_source):
        terms = [quote.group("term").strip() for quote in _B1_VALID_QUOTED_TERM_RE.finditer(match.group("list"))]
        relation = match.group("relation").strip()
        repairs.extend(candidate_factory(term, relation, scope) for term in terms if term)
    return repairs
