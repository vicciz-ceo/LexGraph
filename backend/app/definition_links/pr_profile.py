"""Puerto Rico (Spanish) jurisdiction profile (sprint 2026-08-04-defs-us-pr,
items 1/2/3-functions/4/6, gates P1 "Real PR statutes parse", P2 "Spanish
definition idioms are captured").

Design grounded in a full-corpus survey of the real 23,636-row
`us_pr_statutes.parquet` (never read by any test -- see the sprint
contract's `## Spanish idiom survey (measured)` section and
`backend/tests/fixtures/us_statutes/README.md`'s `## pr_sample_rows.json`
section for the measured counts and real examples behind every rule below).

Seam decision (Planner proposal, sprint contract `## Seam proposal`,
M-R3/M-R5): `PRProfile` is a DISTINCT profile class, the Spanish-language
sibling of `HebrewProfile` -- NOT a rule-set layered onto `USProfile`. The
reuse audit found near-zero exploitable code overlap at every layer:

  - `is_definitions_heading`: different regex vocabulary top to bottom
    (Spanish stem `[Dd]efinici[oó]n(es)?` vs. English `Definitions?`), even
    though the SHAPE (prefix-strip, first-word-or-last-word-with-
    preposition-exclusion) is a pattern worth copying from
    `USProfile.is_definitions_heading`, not code worth sharing.
  - `extract_definitions_from_section`: structurally incompatible with
    `USProfile._split_into_numbered_blocks`, which is LINE-based
    (`text.split("\\n")`). The real PR corpus has **zero newlines within any
    of the 635 canonical Definiciones section bodies measured** -- every
    entry marker sits inline in one continuous string. This module scans
    the continuous string directly via `finditer` (closer in shape to
    `pipeline.py`'s `_extract_inline_quoted_definitions`), not the line
    splitter.
  - `find_citations`: PR's dominant citation shapes (`Ley N-YYYY` dash
    form, `Ley Núm. N de <fecha>`, `Artículo N`, `L.P.R.A.`) have no
    English analog.
  - `detect_cross_law_derivations`: entirely separate Spanish idiom
    vocabulary (`según se define en`, `tiene el significado que se le
    asigna en`) vs. English's (`has the meaning specified in`, `as defined
    in`).
  - `normalize_for_parsing`: a no-op passthrough for both languages (not
    meaningful code reuse, just a shared coincidence).

Registration under `"US-PR"` in `profiles.py`'s `_REGISTRY` is OUT OF
SCOPE for this module (M-R3 -- a shared-module edit deferred to core
sprint `2026-08-04-defs-core-scope`'s published seam spec). `PRProfile` is
constructed directly in the meantime: `PRProfile(code="US-PR")`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.definition_links.derivation import LawDerivesDefinitionEdge
from app.definition_links.extract import DefinitionCandidate

# --- Item 1 (P1): Spanish Definiciones-heading detection --------------------
#
# Rule (mirrors `USProfile.is_definitions_heading`'s SHAPE, Spanish
# vocabulary -- see sprint contract "Spanish idiom survey (measured)",
# heading census: 635 genuine rows out of 652 `defini`-substring rows):
#
#   1. Strip a leading `Artículo N.`/`Sección N.` label, if present (PR
#      section numbers are dot-joined chains, e.g. "30.020", "9.04",
#      "1.090" -- same segment shape as `USProfile`'s English section
#      numbers, just introduced by a different word).
#   2. MATCH if the Spanish stem `[Dd]efinici[oó]n(es)?` is the FIRST
#      substantive token of what remains -- this also correctly recognizes
#      the real `STATE_PR_LEY_135_1979_ART1` truncated-title artifact
#      (`section_title`/`text` split mid-word at a ~200-char boundary):
#      "Definiciones" is still the first token right after "Artículo 1.",
#      even though the string runs on into body prose afterward.
#   3. OTHERWISE, MATCH if the stem is the LAST substantive token
#      (tokenizing on whitespace and separator punctuation, so
#      semicolon/comma-joined Civil-Code headings like "Bienes; definición"
#      work the same as a spaced heading) AND the token immediately before
#      it is not a Spanish preposition (de, para, a, en, según, ...) --
#      a preposition means the stem is a grammatical OBJECT, not this
#      heading's own subject.
#
# Deliberately the STEM `[Dd]efinici[oó]n(es)?`, never the bare substring
# `defin` -- real PR headings carry unrelated Spanish words sharing that
# prefix ("Aportaciones **Definidas**" -- Defined Contributions, a pension
# term of art, 12/635 real rows; "sentencia **definitiva**" -- final
# judgment, 2/635 real rows). Neither `Definidas` nor `definitiva` contains
# the literal `ci` immediately after `defini` that the stem requires, so
# both are excluded by construction, not by a separate exclusion list.
#
# This stem also naturally never matches the English word "Definitions"
# (no `ci` after `defini` in the English spelling either) -- the
# cross-language collision M-R4 exists to catch is avoided at the
# vocabulary level, not merely by a downstream guard (see
# `test_pr_profile_no_english_regression.py`).

_SEGMENT_RE = r"\d+[A-Za-z]*"
_SECTION_NUMBER_TOKEN_RE = re.compile(rf"{_SEGMENT_RE}(?:[.-]{_SEGMENT_RE})*\.?")
_SECTION_LABEL_RE = re.compile(
    rf"(?:Artículo|Sección)\s+{_SEGMENT_RE}(?:[.-]{_SEGMENT_RE})*\.?",
    re.IGNORECASE,
)

_DEFINICION_FIRST_WORD_RE = re.compile(r"[Dd]efinici[oó]n(es)?\b", re.IGNORECASE)
_DEFINICION_LAST_WORD_RE = re.compile(r"^[Dd]efinici[oó]n(es)?$", re.IGNORECASE)

# Tokenizes a heading's tail on whitespace or separator punctuation
# (hyphen, en/em dash, colon, semicolon, comma) -- mirrors
# `USProfile._TAIL_TOKEN_SPLIT_RE` exactly (same shape, language-agnostic).
_TAIL_TOKEN_SPLIT_RE = re.compile(r"[\s\-–—:;,]+")

# Spanish prepositions that, immediately before the Definici(ón|ones) stem,
# mark it as the grammatical OBJECT of the preceding word rather than this
# heading's own subject (the Spanish analog of `USProfile`'s
# `_PRECEDING_EXCLUSION_WORDS`, e.g. "Repeal **of** Definitions"). Small and
# preposition-only by design.
_SPANISH_PREPOSITIONS = frozenset(
    {
        "de",
        "del",
        "a",
        "al",
        "en",
        "para",
        "por",
        "según",
        "con",
        "sin",
        "sobre",
        "entre",
        "hasta",
        "desde",
        "ante",
        "bajo",
        "contra",
        "durante",
        "mediante",
        "salvo",
        "tras",
    }
)


def is_definitions_heading(heading: str) -> bool:
    """True when `heading`'s own operative subject is the Spanish stem
    "Definici(ón|ones)" -- see the module-level comment above for the exact
    rule."""
    rest = heading

    label_match = _SECTION_LABEL_RE.match(rest)
    if label_match:
        rest = rest[label_match.end() :]
    else:
        number_match = _SECTION_NUMBER_TOKEN_RE.match(rest)
        if number_match:
            rest = rest[number_match.end() :]
    rest = rest.lstrip()

    if _DEFINICION_FIRST_WORD_RE.match(rest):
        return True

    trimmed = rest.rstrip(" \t\r\n.")
    tokens = [t for t in _TAIL_TOKEN_SPLIT_RE.split(trimmed) if t]
    if not tokens or not _DEFINICION_LAST_WORD_RE.match(tokens[-1]):
        return False
    if len(tokens) == 1:
        return True
    preceding = tokens[-2]
    if preceding.lower() in _SPANISH_PREPOSITIONS:
        return False  # a Spanish preposition -- the stem is a
        # grammatical object here, not this heading's own subject.
    return True


# --- Item 2 (P1/P2): Spanish Definiciones-section entry extraction ----------
#
# The real PR `text` column has ZERO newlines within a Definiciones section
# body (verified: 0/635 canonical rows -- sprint contract survey), unlike
# `USProfile.extract_definitions_from_section`'s line-based
# `_split_into_numbered_blocks`. Every entry marker sits inline,
# immediately after a sentence/clause boundary (`.`/`;`/`:` -- the colon
# case covers an intro sentence like "...significado: a. ..." where the
# FIRST marker follows the section's own lead-in colon, not a period) or a
# bracketed page-break annotation (`]`, the real `[Ley N de <fecha>, según
# enmendada]` boilerplate the scrape occasionally injects mid-body -- see
# `STATE_PR_LEY_77_1957_ART30_020` entry (i), preceded by "...enmendada]
# (i) ..." not by a sentence-final period) -- or at the very start of the
# string. `_ENTRY_MARKER_RE` anchors on exactly those boundaries so it
# never mistakes an ordinary mid-sentence letter/digit for a new entry.
#
# Six measured marker shapes (see sprint contract's "Entry marker shapes"
# table) collapse into three regex alternatives here: full-paren (`(a)`,
# `(1)`), close-paren-only (`a)`, `1)` -- a distinct, newer-law convention
# with no opening paren), and period (`a.`, `1.`, the period one
# required to be followed by whitespace so it is never confused with a
# dot-continued section number like "1.090").
_ENTRY_MARKER_RE = re.compile(
    r"(?:^|(?<=[.;:\]])\s+)"
    r"(?:\((?:[a-zA-Z]|\d{1,3})\)"
    r"|(?:[a-zA-Z]|\d{1,3})\)"
    r"|(?:[a-zA-Z]|\d{1,3})\.(?=\s))"
    r"\s*"
)

# A block's term/definition separator: quoted term + colon (dominant
# canonical shape, 26+ rows -- curly `“”` in 437/635 canonical rows,
# straight `"` in 76/635, both accepted); quoted term + em/en-dash
# fallback; unquoted term + optional-period + em/en-dash (272/635 rows use
# this family, with or without a verb idiom -- `Es`/`Significará`/`Será`
# directly after the dash, or the definition starting with a bare noun
# phrase, e.g. `Secretario. – Se refiere al...`).
_QUOTED_TERM_COLON_RE = re.compile(r'^["“]([^"”]+)["”]\s*:\s*')
_QUOTED_TERM_DASH_RE = re.compile(r'^["“]([^"”]+)["”]\s*\.?\s*[–—]\s*')
_UNQUOTED_TERM_DASH_RE = re.compile(r"^(.+?)\s*\.?\s*[–—]\s*")

_TERM_SEPARATOR_PATTERNS = (
    _QUOTED_TERM_COLON_RE,
    _QUOTED_TERM_DASH_RE,
    _UNQUOTED_TERM_DASH_RE,
)


def _extract_term_and_definition(block: str) -> tuple[str, str] | None:
    """Split a single entry's raw text into (term, definition_text) using
    the first separator pattern that matches. Returns `None` for a block
    with no recognizable term/separator shape -- skipped, not fabricated
    (mirrors `USProfile.extract_definitions_from_section`'s "entries with
    no leading quoted term are skipped" discipline)."""
    for pattern in _TERM_SEPARATOR_PATTERNS:
        match = pattern.match(block)
        if match:
            term = match.group(1).strip()
            definition_text = block[match.end() :].strip()
            if term and definition_text:
                return term, definition_text
    return None


def extract_definitions_from_section(text: str, *, scope: str) -> list[DefinitionCandidate]:
    """Extract every (term, definition) pair from a located Definiciones
    section's body -- a continuous-string `finditer` scan (NOT
    line-based; see module-level comment). Handles all 6 measured
    marker shapes plus the 174/635-row no-marker single-entry shape
    (the whole body treated as one block when no marker is found at all,
    e.g. `STATE_PR_LEY_77_1957_ART1_090`'s "Secretario. — Significa el
    Secretario de Hacienda.").

    `scope` is stamped onto every candidate verbatim, exactly as supplied
    by the caller -- this function does not itself inspect the body for
    scope-setting phrases (a separate, core-seam-owned concern; see
    `test_pr_profile_scope.py`).
    """
    markers = list(_ENTRY_MARKER_RE.finditer(text))
    candidates: list[DefinitionCandidate] = []

    if not markers:
        parsed = _extract_term_and_definition(text)
        if parsed is not None:
            term, definition_text = parsed
            candidates.append(
                DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope)
            )
        return candidates

    for index, marker in enumerate(markers):
        start = marker.end()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        block = text[start:end].strip()
        parsed = _extract_term_and_definition(block)
        if parsed is None:
            continue
        term, definition_text = parsed
        candidates.append(
            DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope)
        )
    return candidates


# --- Item 3 (P2): ad-hoc/local definitions outside canonical sections -------
#
# Two mechanically distinct Spanish idioms, the analogs of Hebrew's
# `extract.extract_local_definitions`/`extract.extract_adhoc_definitions`
# respectively -- both always `scope="local"` (article-scoped, never
# broader; the sprint contract survey confirms 0/635 canonical sections
# use "A los fines/efectos de este Artículo" as their OWN scope-setter --
# article scope is exclusively this extractor's domain).

# "A los fines de este Artículo"/"Para propósitos de este Artículo",
# optionally followed by a comma, then a quoted defined term, then the
# defining clause running up to the next sentence boundary (`.`/`;`) --
# bounded so the captured definition does not run on into unrelated
# prose later in the same (non-Definiciones) article (real example:
# `STATE_PR_LEY_85_2018_ART9_04`'s "A los fines de este Artículo
# “cualquier tipo de arma” incluye..." has no comma after
# "Artículo"; the synthetic contract examples do -- both variants
# measured in the real corpus, 16 + 26 corpus-wide occurrences).
_LOCAL_TRIGGER_RE = re.compile(
    r"(?:A los fines de este Artículo|Para propósitos de este Artículo)"
    r"\s*,?\s*[\"“]([^\"”]+)[\"”]\s*(.+?[.;])(?:\s|$)",
    re.IGNORECASE,
)


def extract_local_definitions(article_body: str) -> list[DefinitionCandidate]:
    """Scan a (non-Definiciones) article body for the
    "A los fines/propósitos de este Artículo ..." family. Scope is
    always `"local"`."""
    candidates: list[DefinitionCandidate] = []
    for match in _LOCAL_TRIGGER_RE.finditer(article_body):
        term = match.group(1).strip()
        definition_text = match.group(2).strip()
        candidates.append(
            DefinitionCandidate(terms=(term,), definition_text=definition_text, scope="local")
        )
    return candidates


# "(en adelante, X)" -- an inline parenthetical apposition restating an
# immediately-preceding long noun phrase under a short name, with no idiom
# verb required and no quote marks required (49 real corpus-wide
# occurrences; a quoted variant is also accepted since the survey's
# measured shape covers both). The short name is the defined TERM; the
# noun phrase immediately preceding the parenthetical (back to the
# nearest sentence/clause boundary) is the definition.
_ADHOC_TRIGGER_RE = re.compile(r'\(en adelante,\s*["“]?([^)"”]+?)["”]?\)', re.IGNORECASE)

# A leading Spanish definite article on the captured term ("el"/"la"/
# "los"/"las") is stripped -- the short name itself is the defined term,
# not the article introducing it (real corpus phrasing sometimes includes
# the article, e.g. "(en adelante, el Departamento)").
_LEADING_SPANISH_ARTICLE_RE = re.compile(r"^(el|la|los|las)\s+", re.IGNORECASE)

_ANTECEDENT_BOUNDARY_CHARS = ".;:()"


def extract_adhoc_definitions(text: str) -> list[DefinitionCandidate]:
    """Scan `text` for `(en adelante, X)` inline appositions, outside any
    Definiciones section. Scope is always `"local"`."""
    candidates: list[DefinitionCandidate] = []
    for match in _ADHOC_TRIGGER_RE.finditer(text):
        term = match.group(1).strip()
        term = _LEADING_SPANISH_ARTICLE_RE.sub("", term).strip()
        if not term:
            continue
        prefix = text[: match.start()]
        boundary = max((prefix.rfind(char) for char in _ANTECEDENT_BOUNDARY_CHARS), default=-1)
        antecedent = prefix[boundary + 1 :].strip()
        definition_text = antecedent if antecedent else term
        candidates.append(
            DefinitionCandidate(terms=(term,), definition_text=definition_text, scope="local")
        )
    return candidates


# --- G3 analog: Spanish word-boundary term matching --------------------------


def find_term_uses(term: str, text: str) -> list[re.Match[str]]:
    """Every non-overlapping occurrence of the literal `term` in `text`,
    using ordinary `\\b`-word-boundary matching (same shape as
    `USProfile.find_term_uses` -- Python's `\\b` is Unicode-aware and
    handles accented Spanish letters as word characters natively, no
    Hebrew-style prefix-letter surface-form expansion needed)."""
    pattern = re.compile(r"\b" + re.escape(term) + r"\b")
    return list(pattern.finditer(text))


def normalize_for_parsing(text: str) -> str:
    """No normalization needed for plain Spanish statute text (no
    wikilink-bracket stripping, no RTL-bidi handling) -- passthrough,
    same as `USProfile.normalize_for_parsing`."""
    return text


# --- Item 4 (P1/P2): Spanish citation grammar --------------------------------
#
# Priority-ordered, non-overlapping (mirrors `USProfile.find_citations`'s
# claimed-span shape): most specific first, so a more specific pattern's
# match claims its span before a less specific pattern (e.g. bare `§ N`)
# can grab part of it.

# `N L.P.R.A. § N` -- PR's own citation-reporter abbreviation, PR's analog
# of `U.S.C.` (2,498 corpus-wide rows carry `L.P.R.A.`). Tried first so its
# own `§ N` portion is claimed before the bare `§ N` pattern below can.
_LPRA_CITATION_RE = re.compile(r"\d+\s+L\.P\.R\.A\.\s+§\s*\d+(?:\([^\s()]+\))*", re.IGNORECASE)

# `Ley Núm. N de <fecha>` -- the older/formal citation form (2,194
# corpus-wide rows), e.g. "Ley Núm. 4 de 23 de junio de 1971" or
# "Ley Núm. 173 de 12 agosto de 1988" (the "de" before the month is
# optional -- both real forms measured).
_LEY_NUM_DE_FECHA_RE = re.compile(
    r"Ley\s+Núm\.\s+\d+\s+de\s+\d{1,2}\s+(?:de\s+)?\w+\s+de\s+\d{4}",
    re.IGNORECASE,
)

# `Ley N-YYYY` dash form -- the single most common PR citation shape
# (7,052 corpus-wide rows, e.g. "Ley 404-2000"), no English analog.
_LEY_DASH_RE = re.compile(r"\bLey\s+\d+-\d{4}\b")

# `Artículo N` (bare, or followed by "de esta Ley" -- 1,123 corpus-wide
# rows for the full "de esta Ley" form) -- PR's analog of English
# "Section N". PR article numbers are dot-joined chains (e.g. "30.050").
_ARTICULO_RE = re.compile(r"Artículo\s+\d+(?:\.\d+)*", re.IGNORECASE)

# Bare `§ N` (2,249 corpus-wide rows) -- the symbol itself is
# language-neutral, same shape as `USProfile._SECTION_SYMBOL_RE`.
_SECTION_SYMBOL_RE = re.compile(r"§\s*\d+(?:\([^\s()]+\))*")

_CITATION_PATTERNS = (
    _LPRA_CITATION_RE,
    _LEY_NUM_DE_FECHA_RE,
    _LEY_DASH_RE,
    _ARTICULO_RE,
    _SECTION_SYMBOL_RE,
)


def find_citations(text: str) -> list[str]:
    """Every citation-shaped substring in `text`, in priority order with
    non-overlapping claimed spans (see module comment above), returned in
    the order they appear in `text`."""
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


# --- Item 6 (P5): Spanish cross-law derivation idioms ------------------------
#
# Lower priority per the sprint contract's item plan ("not gated by name in
# P1-P5, minimal test coverage only") -- Spanish idiom set entirely
# separate from `USProfile`'s English triggers (`has the meaning specified
# in`/`as defined in`), so an English trigger phrase never matches here
# (the exact collision `test_pr_profile_no_english_regression.py`'s
# `test_pr_profile_detects_no_cross_law_derivation_from_real_english_idiom_text`
# pins).
_CROSS_LAW_TRIGGER_PHRASES = (
    "tiene el significado que se le asigna en",
    "según se define en",
)
_CROSS_LAW_TRIGGER_RE = re.compile(
    "|".join(re.escape(p) for p in sorted(_CROSS_LAW_TRIGGER_PHRASES, key=len, reverse=True)),
    re.IGNORECASE,
)
_LEADING_WS_RE = re.compile(r"^\s*")


def detect_cross_law_derivations(
    text: str, *, source_term: str, known_law_titles: dict[str, str] | None = None
) -> list[LawDerivesDefinitionEdge]:
    """Scan `text` for `_CROSS_LAW_TRIGGER_PHRASES` occurrences immediately
    followed by a recognizable citation (`find_citations`'s grammar). A
    trigger followed by an anaphoric same-document reference (e.g. "este
    Código", no citation grammar) is naturally excluded -- it simply does
    not match any `_CITATION_PATTERNS` entry, so no edge is emitted for it
    (real example: `STATE_PR_LEY_77_1957_ART30_020` entry (a), "según se
    define en este Código" -- an internal reference, not a cross-law one).

    `known_law_titles` is accepted for Protocol-shape parity; unresolved
    references are still emitted with `target_law_id=None` (never a
    fabricated guess, same discipline as `USProfile.detect_cross_law_
    derivations`).
    """
    known = known_law_titles or {}
    edges: list[LawDerivesDefinitionEdge] = []

    for trigger_match in _CROSS_LAW_TRIGGER_RE.finditer(text):
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


# --- Item 6 (P5): PRProfile assembly + Protocol conformance ------------------


@dataclass(frozen=True)
class PRProfile:
    """The `"US-PR"` profile -- the Spanish-language sibling of
    `HebrewProfile`, mirroring `HebrewProfile`/`USProfile`'s exact shape
    (see module docstring for the seam decision). NOT registered in
    `profiles.py`'s `_REGISTRY` yet (M-R3, deferred to core sprint
    `2026-08-04-defs-core-scope`) -- constructed directly:
    `PRProfile(code="US-PR")`.
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
