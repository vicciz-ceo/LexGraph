"""US jurisdiction profile (sprint 2026-08-02-us-state-law, item 3, gates
G2 "a real US statute parses", G3 "English term linking works", G4 "US
citations are recognised").

Design decision (documented per the item brief): **ONE `"US"`-family profile
class (`USProfile`) serves every `US-*`/`US-FED` jurisdiction code**, not a
per-state profile. Evidence: the RED unit test (`test_definition_links_us_
profile.py`) instantiates the profile via `get_profile("US-DE")` and every
assertion in it exercises pure English statutory-drafting conventions
(`"Definitions"` headings, `has the meaning specified in` / `as defined in`
idioms, `Section N` / `§ N` / `N U.S.C. § N` citation grammar) that are not
Delaware-specific -- nothing in the fixture data or the gate text (G2-G4)
calls for state-specific parsing rules. `profiles.py` registers the SAME
`USProfile()` instance under every one of the 53 non-`"IL"` codes in
`app.services.jurisdiction.JURISDICTION_CODES` (`US-<postal>`, `US-DC`,
`US-PR`, `US-FED`). A later sprint can split this into per-state profiles
if state-specific drafting conventions are ever found to diverge; nothing
in this module's public surface assumes a single profile instance, so that
split is additive whenever it is needed.

Inputs to every function/method here are plain, NOT Stage-0-normalized in
the Hebrew-engine sense (`normalize_for_parsing` is a passthrough -- see its
docstring) -- English statute text needs no wikilink-bracket stripping or
bidi handling. `is_definitions_heading` in particular is deliberately a
CONTAINS/substring check, not an anchored-at-start check like Hebrew's
`sections._DEFINITIONS_HEADING_RE`: real Delaware `section_title` values
carry scrape-noise (mojibake `Â`, a raw CRLF, leading whitespace) BEFORE the
actual heading text (see `backend/tests/fixtures/us_statutes/README.md`),
so anchoring at the start of the raw string would fail on 100% of that real
dataset.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.definition_links.derivation import LawDerivesDefinitionEdge
from app.definition_links.extract import DefinitionCandidate

# --- G2: Definitions-heading detection --------------------------------------

# The real Delaware `section_title` shape is scrape-noise-prefixed non-letter
# junk (mojibake `Â`, a raw CRLF, leading whitespace, the `§` symbol, a bare
# section number, a trailing period) followed by the section's own title
# (see module docstring / `backend/tests/fixtures/us_statutes/README.md`).
# A "clean" synthetic heading can instead carry that same section-number
# prefix spelled out as the word "Section" (e.g. "Section 101. Definitions.").
# This is deliberately NOT a start-of-raw-string anchor (that fails on 100%
# of the real dataset, which always carries the scrape-noise prefix) and NOT
# an unanchored substring search either (that over-matches real non-
# definitions headings where "Definitions" is merely mentioned elsewhere in
# a longer phrase, e.g. "Application of Definitions to Prior Acts", "Repeal
# of Definitions") -- it skips over any leading run of non-letter characters
# (scrape noise, digits, punctuation, whitespace) and/or a "Section <N>."
# label, then requires "Definition(s)" to be the FIRST WORD of whatever
# remains -- i.e. the heading's own operative subject, not a word embedded
# later in an unrelated title.
_DEFINITIONS_HEADING_RE = re.compile(r"^(?:[^A-Za-z]+|Section\s+\d+\.?)*Definitions?\b")


def is_definitions_heading(heading: str) -> bool:
    """True when, after any leading scrape-noise and/or spelled-out
    "Section <N>." prefix is skipped, `heading`'s first word is
    "Definition"/"Definitions" -- i.e. that word is the heading's own
    operative subject, not merely present somewhere inside a longer,
    unrelated heading (see module-level regex comment).
    """
    return bool(_DEFINITIONS_HEADING_RE.match(heading))


# --- G2 (continued): extracting defined terms out of a Definitions section --

# A numbered-paragraph entry marker, e.g. "(1)", "(2)" -- the real DE
# fixture's Definitions-section body shape. Matched at the start of a line
# (mirrors extract.py's `_ENTRY_START_RE` block-splitting approach for
# Hebrew's `:-`-marked entries, adapted to this structurally different
# marker).
_ENTRY_START_RE = re.compile(r"^\s*\(\d+\)\s*")

# The real fixture uses CURLY quotes (“/”) around each defined
# term, not straight ASCII quotes -- both accepted here since a clean/
# synthetic input might reasonably use either.
_LEADING_QUOTE_RE = re.compile(r'^[“"]([^”"]+)[”"]')


def _split_into_numbered_blocks(text: str) -> list[str]:
    lines = text.split("\n")
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if _ENTRY_START_RE.match(line):
            if current is not None:
                blocks.append(current)
            current = [_ENTRY_START_RE.sub("", line, count=1)]
        elif current is not None:
            current.append(line)
    if current is not None:
        blocks.append(current)
    return ["\n".join(b).strip() for b in blocks]


def extract_definitions_from_section(text: str, *, scope: str) -> list[DefinitionCandidate]:
    """Extract every (term, definition) pair from a located Definitions
    section's body composed of `(N) "Term" ...` numbered entries (the real
    DE fixture's shape).

    Each entry's leading quoted span is the defined term; the remainder of
    the entry (after the closing quote) is the definition text. Entries
    with no leading quoted term are skipped (not a recognizable defined-
    term entry).
    """
    candidates: list[DefinitionCandidate] = []
    for block in _split_into_numbered_blocks(text):
        term_match = _LEADING_QUOTE_RE.match(block)
        if not term_match:
            continue
        term = term_match.group(1)
        definition_text = block[term_match.end() :].strip()
        candidates.append(
            DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope)
        )
    return candidates


# --- G3: English word-boundary term matching --------------------------------


def find_term_uses(term: str, text: str) -> list[re.Match[str]]:
    """Every non-overlapping occurrence of the literal `term` in `text`,
    using ordinary `\\b`-word-boundary matching -- NO Hebrew-style prefix-
    letter surface-form expansion. A defined term never false-matches as a
    substring of a longer word (`\\b` handles this natively: e.g. `term=
    "Affiliate"` will not match inside `"Affiliates"` or `"disaffiliated"`,
    since there is no word-boundary at that position).
    """
    pattern = re.compile(r"\b" + re.escape(term) + r"\b")
    return list(pattern.finditer(text))


def normalize_for_parsing(text: str) -> str:
    """No normalization needed for plain English statute text (no
    wikilink-bracket stripping, no RTL-bidi handling) -- passthrough."""
    return text


# --- G4: US citation grammar -------------------------------------------------

# Most specific first: a full `N U.S.C. § N(...)` federal citation, so its
# "§ N" portion is claimed before the bare `§ N` pattern below can grab it.
_USC_CITATION_RE = re.compile(r"\d+\s+U\.S\.C\.\s+§\s*\d+(?:\([^\s()]+\))*")

# `Section N` (spelled out).
_SECTION_WORD_RE = re.compile(r"\bSection\s+\d+\b")

# Bare `§ N` (optionally followed by parenthetical subdivisions).
_SECTION_SYMBOL_RE = re.compile(r"§\s*\d+(?:\([^\s()]+\))*")

# Tried in priority order; a later pattern's match is discarded if it
# overlaps a span already claimed by an earlier (more specific) pattern.
_CITATION_PATTERNS = (_USC_CITATION_RE, _SECTION_WORD_RE, _SECTION_SYMBOL_RE)


def find_citations(text: str) -> list[str]:
    """Every citation-shaped substring in `text`: `Section N`, `§ N`, and
    `N U.S.C. § N` federal citations. Returned in the order they appear in
    `text`.
    """
    claimed: list[tuple[int, int]] = []
    found: list[tuple[int, str]] = []
    for pattern in _CITATION_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()
            if any(not (end <= s or e <= start) for s, e in claimed):
                continue
            claimed.append((start, end))
            found.append((start, match.group(0)))
    found.sort(key=lambda item: item[0])
    return [text for _, text in found]


# English defining idioms that introduce a cross-law derivation (the real
# fixture text uses the first form, not "means"). Longest-first so a
# suffixed/longer idiom is preferred if both could match at a position.
_TRIGGER_PHRASES = ("has the meaning specified in", "as defined in")
_TRIGGER_RE = re.compile(
    "|".join(re.escape(p) for p in sorted(_TRIGGER_PHRASES, key=len, reverse=True)),
    re.IGNORECASE,
)

# A same-document/same-chapter internal reference immediately following the
# matched citation (mirrors Hebrew derivation.py's `_BESAIF_RE` same-law
# exclusion philosophy) -- excluded from cross-law derivations.
_SAME_LAW_RE = re.compile(
    r"^\s*of this (chapter|title|subchapter|part|section|act)\b", re.IGNORECASE
)

_LEADING_WS_RE = re.compile(r"^\s*")


def detect_cross_law_derivations(
    text: str, *, source_term: str, known_law_titles: dict[str, str] | None = None
) -> list[LawDerivesDefinitionEdge]:
    """Scan `text` for `_TRIGGER_PHRASES` occurrences immediately followed
    by a recognizable citation (`find_citations`' grammar). A same-
    document/same-chapter reference (`"...of this chapter"` etc.
    immediately after the citation) is EXCLUDED -- Stage-3 territory, not a
    cross-law derivation.

    `known_law_titles` is accepted for Protocol-shape parity with the
    Hebrew engine; US citations resolve to a `target_law_id` only via an
    exact key match, same "never a fabricated guess" discipline as
    `derivation.py` (ruling M5, ported): an unresolved reference is still
    emitted, with `target_law_id=None`.
    """
    known = known_law_titles or {}
    edges: list[LawDerivesDefinitionEdge] = []

    for trigger_match in _TRIGGER_RE.finditer(text):
        trigger = trigger_match.group(0)
        rest = text[trigger_match.end() :]
        ws_end = _LEADING_WS_RE.match(rest).end()
        rest = rest[ws_end:]

        citation_match = None
        for pattern in _CITATION_PATTERNS:
            citation_match = pattern.match(rest)
            if citation_match:
                break
        if citation_match is None:
            continue  # trigger not followed by a recognizable citation

        after_citation = rest[citation_match.end() :]
        if _SAME_LAW_RE.match(after_citation):
            continue  # same-document/same-chapter reference -- not cross-law

        matched_text = citation_match.group(0)
        edges.append(
            LawDerivesDefinitionEdge(
                source_term=source_term,
                trigger_phrase=trigger,
                matched_text=matched_text,
                target_law_name=None,
                target_law_id=known.get(matched_text),
            )
        )

    return edges


@dataclass(frozen=True)
class USProfile:
    """The `"US-*"`/`"US-FED"` profile family -- ONE instance serves every
    US jurisdiction code (see module docstring for the per-state-vs-single
    decision). `.code` is set per-registration in `profiles.py`, not fixed
    here, since the same behavior applies under every US code.
    """

    code: str

    def is_definitions_heading(self, heading: str) -> bool:
        return is_definitions_heading(heading)

    def normalize_for_parsing(self, text: str) -> str:
        return normalize_for_parsing(text)

    def find_term_uses(self, term: str, text: str) -> list[re.Match[str]]:
        return find_term_uses(term, text)

    def find_citations(self, text: str) -> list[str]:
        return find_citations(text)

    def extract_definitions_from_section(
        self, text: str, *, scope: str
    ) -> list[DefinitionCandidate]:
        return extract_definitions_from_section(text, scope=scope)

    def detect_cross_law_derivations(
        self,
        text: str,
        *,
        source_term: str,
        known_law_titles: dict[str, str] | None = None,
    ) -> list[LawDerivesDefinitionEdge]:
        return detect_cross_law_derivations(
            text, source_term=source_term, known_law_titles=known_law_titles
        )
