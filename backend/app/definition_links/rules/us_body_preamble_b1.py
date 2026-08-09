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

_MATCHED_ENTRY = re.compile(
    r'\(\s*\d+[A-Za-z]?\s*\)[ \t]*(?:"(?P<s>[^"]{1,200})"|“(?P<c>[^”]{1,200})”)'
)
_SHARED_LIST = re.compile(
    r'(?P<entries>(?:\(\s*\d+[A-Za-z]?\s*\)[ \t]*(?:"[^"]{1,200}"|“[^”]{1,200}”)\s*;\s*(?:(?:and|or)\s*)?){2,})'
    r'(?P<relation>(?:has|have|shall\s+have)\s+the\s+(?:same\s+)?(?:meaning|definition)'
    r'(?:\s+(?:set\s+forth|provided|given|found|prescribed))?\s+(?:for\s+)?those\s+terms\b[^;\n]{0,300})',
    re.IGNORECASE,
)
_MARKER = re.compile(r'(?:\(\s*(?:\d+|[a-z]+)\s*\)|\[\s*(?:\d+|[a-z]+)\s*\]|\d+)', re.I)
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_HISTORY = re.compile(r"^\s*\[(?:L|Acts?)\s+\d{4}\b", re.I)
_POST_RELATION = re.compile(
    r'^[\s:;,.\-–—]*(?:(?:\([A-Za-z0-9]+\)|\[[A-Za-z0-9]+\]|[A-Za-z]\.)\s*)*'
    r'(?:[^;.\n]{1,160}?,\s*)?(?:means|shall\s+mean|includes|shall\s+include|'
    r'(?:has|have|shall\s+have)\s+the\s+(?:same\s+)?meaning|'
    r'the\s+meaning\s+(?:given|provided|set\s+forth|specified|prescribed))\b', re.I)
_ENUM_RELATION = re.compile(
    r'^[\s\-–—]*:\s*(?:(?:\([A-Za-z0-9]+\)|\[[A-Za-z0-9]+\])\s*)'
    r'[^;.\n]{0,160}?\b(?:means|shall\s+mean|includes|shall\s+include|'
    r'(?:has|have|shall\s+have)\s+the\s+(?:same\s+)?meaning)\b', re.I)
_ALIAS_VERB = r'(?:referred\s+to|known|designated|established|maintained)'
_ALIAS_INTRO = re.compile(
    rf'(?:(?:is|are|(?:may|shall)\s+be|in\s+[^.;:\n()]{{1,100}})\s+)?'
    rf'(?:commonly\s+)?{_ALIAS_VERB}(?:\s+in\s+[^.;:\n]{{0,100}})?\s+as(?:\s+the)?\s*$', re.I)
_ALIAS_LIST = re.compile(
    r'(?:shall|may)\s+be\s+(?:known|referred\s+to)\s+as\s+the\s*[\-–—:]\s*'
    r'(?:(?:\([A-Za-z0-9]+\)|\[[A-Za-z0-9]+\])\s*(?:"[^"]{1,200}"|“[^”]{1,200}”)\s*[;,]?\s*(?:and|or)?\s*)*'
    r'(?:\([A-Za-z0-9]+\)|\[[A-Za-z0-9]+\])?\s*$', re.I)
_RECIPROCAL = re.compile(
    rf'\b{_ALIAS_VERB}\s*,?\s*respectively\s*,?\s*as\s*'
    r'(?:(?:"[^"]{1,200}"|“[^”]{1,200}”)\s*(?:,\s*)?(?:(?:and|or)\s*)?)*$', re.I)
_FORWARDING = re.compile(
    r'(?:the\s+following\s+definitions?\s+in\s+(?:other\s+)?[^:.;\n]{0,100}\s+apply\s+to\s+this\s+[^:.;\n]{0,50}|'
    r'definitions?\s+in\s+other\s+[^:.;\n]{0,100}\s+applying\s+to\s+this\s+[^:.;\n]{0,100}\s+(?:include|are)|'
    r'the\s+following\s+terms?\s+(?:shall\s+)?have\s+the\s+(?:same\s+)?meaning\s+as\s+'
    r'(?:provided|set\s+forth|specified)\s+in\s+[^:.;\n]{0,100})\s*:', re.I)
_MAX_LOCAL = 600


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
        if _b1_colon_list_branch(after) or _b1_quote_means_branch(after):
            return "Definitions"
    return None


def is_b1_derived_body(body: str) -> bool:
    """Whether B1, rather than another body-preamble rule, recognizes body."""
    return _b1_trigger_colon_or_quote_means(body) is not None


def is_b1_rule(derive_heading) -> bool:
    """Explicit identity marker for B1's registered body-preamble callable."""
    return derive_heading is _b1_trigger_colon_or_quote_means


def _normalized_term(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().rstrip(".,;:"))


def _quote_occurrences(text: str, term: str):
    emitted = re.sub(r"\s+", " ", term.strip())
    if not emitted:
        return ()

    def matches(value: str, terminal: str):
        pattern = r"\s+".join(re.escape(part) for part in value.split())
        return tuple(re.finditer(rf'(?:(?:"\s*{pattern}{terminal}\s*")|(?:“\s*{pattern}{terminal}\s*”))', text, re.I))

    exact = matches(emitted, "")
    tolerant = matches(_normalized_term(emitted), r"[.,;:]*")
    spans = {match.span() for match in exact}

    def continuation(match) -> bool:
        if text[match.start()] != '"':
            return False
        previous = text.rfind('"', max(0, match.start() - 6000), match.start())
        return previous >= 0 and re.match(
            r'\s*\([A-Za-z0-9]+\)\s+', text[previous + 1 : match.start()]
        ) is not None

    return tuple(match for match in exact + tuple(m for m in tolerant if m.span() not in spans) if not continuation(match))


def _exact_occurrence(text: str, term: str, quote) -> bool:
    emitted = re.sub(r"\s+", " ", term.strip()).casefold()
    raw = re.sub(r"\s+", " ", text[quote.start() + 1 : quote.end() - 1].strip()).casefold()
    return emitted == raw


def _bounded_payload(text: str, quote_end: int) -> str:
    tail = text[quote_end : quote_end + _MAX_LOCAL]
    semicolon, newline = tail.find(";"), tail.find("\n")
    bounds = [semicolon] if semicolon >= 0 else []
    if newline >= 0:
        wrapped = not tail[:newline].strip() and re.match(
            r"\s*(?:means|shall\s+mean|includes|shall\s+include)\b", tail[newline:], re.I
        )
        if not wrapped:
            bounds.append(newline)
    return tail[: min(bounds)] if bounds else tail


def _substantive(payload: str) -> bool:
    if _HISTORY.match(payload):
        return False
    residual = _MARKER.sub(" ", payload)
    return any(word.casefold() not in {"and", "or"} for word in _WORD.findall(residual))


def _pre_relation(text: str, start: int) -> bool:
    lookback = text[max(0, start - _MAX_LOCAL) : start]
    sentence = re.split(r"[.;\n]", lookback)[-1]
    if _ALIAS_INTRO.search(sentence) or _ALIAS_LIST.search(lookback) or _RECIPROCAL.search(lookback):
        return True
    return _FORWARDING.search(text[max(0, start - 6000) : start]) is not None


def _groups(text: str):
    groups = []
    for trigger in _B1_TRIGGER_RE.finditer(text):
        after = text[trigger.end() : trigger.end() + _B1_LOOKAHEAD]
        colon = after.find(":")
        if colon < 0 or not _b1_colon_list_branch(after):
            continue
        start = trigger.end() + colon + 1
        for shared in _SHARED_LIST.finditer(text, start, min(len(text), start + _MAX_LOCAL)):
            terms = []
            for entry in _MATCHED_ENTRY.finditer(text, shared.start("entries"), shared.end("entries")):
                name = entry.group("s") or entry.group("c")
                span = entry.span("s") if entry.group("s") is not None else entry.span("c")
                if name.strip():
                    terms.append((name.strip(), *span))
            if len(terms) >= 2:
                relation_start = shared.start("relation")
                tail = text[relation_start : relation_start + _MAX_LOCAL]
                ends = [m.start() + 1 for m in re.finditer(r"[;\n]", tail)]
                sentence = re.search(r"(?<=[.?!])(?:\s|$)", tail)
                if sentence:
                    ends.append(sentence.start() + 1)
                relation_end = relation_start + (min(ends) if ends else len(tail))
                groups.append((tuple(terms), (relation_start, relation_end)))
    return tuple(groups)


def _owned(term: str, quote, groups) -> bool:
    normalized = _normalized_term(term).casefold()
    return any(
        normalized == _normalized_term(group_term).casefold()
        and quote.start() <= start and end <= quote.end()
        for terms, _ in groups for group_term, start, end in terms
    )


def _candidate_is_substantive(text: str, candidate, groups) -> bool:
    for term in candidate.terms:
        quotes = _quote_occurrences(text, term)
        if not quotes:
            return True
        has_exact = any(_exact_occurrence(text, term, quote) for quote in quotes)
        for quote in quotes:
            if _owned(term, quote, groups):
                continue
            tail = text[quote.end() : quote.end() + _MAX_LOCAL]
            if _POST_RELATION.match(tail) or _ENUM_RELATION.match(tail) or _pre_relation(text, quote.start()):
                return True
            if has_exact and not _exact_occurrence(text, term, quote):
                continue
            if _substantive(_bounded_payload(text, quote.end())):
                return True
    return False


def preserve_substantive_b1_candidates(candidates, raw_source: str):
    groups, kept, seen = _groups(raw_source), [], set()
    for candidate in candidates:
        key = tuple(sorted(candidate.terms))
        if key not in seen and _candidate_is_substantive(raw_source, candidate, groups):
            seen.add(key)
            kept.append(candidate)
    return kept


def plural_anaphora_repairs(raw_source: str, *, scope: str, candidate_factory):
    repairs = []
    for terms, (start, end) in _groups(raw_source):
        relation = raw_source[start:end].strip()
        repairs.extend(candidate_factory(term, relation, scope) for term, _, _ in terms)
    return repairs
