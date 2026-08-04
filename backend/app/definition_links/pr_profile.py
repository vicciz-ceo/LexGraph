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
import unicodedata
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


# --- Cycle-2 heading fixes (P1 generalization gap) ---------------------------
#
# Live-corpus sweep found 13/635 real heading misses, collapsing into TWO
# independent gaps (see sprint contract's `### Cycle-2 corrections` and this
# module's sibling test file `test_pr_profile_headings_cycle2.py` for the
# full diagnosis):
#
#   Gap 1 (11/13 misses) -- CLAUSE-SCOPED first-word position. Real PR
#   headings frequently place the stem as the first (or trailing-
#   preposition-suffixed) word of an INNER semicolon-, comma-, or em-dash-
#   delimited CLAUSE ("Parentesco; definición y alcance",
#   "Microseguros, definición y clases autorizadas"), not necessarily of
#   the WHOLE tail. Fix: split the tail into clauses on `;`, `,`, `–`/`—`
#   and apply the EXISTING first-word-or-last-word-with-preposition-
#   exclusion rule to EACH clause independently -- a flat split (not a
#   hierarchical one) already handles the one row needing two delimiter
#   levels ("Agregado, Definición de; Limitado...") because comma and
#   semicolon are both clause delimiters at the same flat level, so
#   "Definición de" surfaces as its own clause regardless of which
#   delimiter type bounds it on either side.
#   Both real TOC rejections stay rejected under this widening: neither
#   has a semicolon/comma/em-dash immediately adjacent to "Definiciones"
#   in its OWN heading tail (it's buried in a whitespace-joined run-on),
#   so clause-splitting never isolates it as its own clause there.
#
#   Gap 2 (2/13 misses) -- fully-parenthesized whole heading
#   ("(Definiciones)"). Orthogonal to gap 1: parentheses aren't in
#   `_TAIL_TOKEN_SPLIT_RE`'s split class, so the whole parenthesized
#   string tokenizes as one un-matchable token. Fix: strip a single
#   enclosing `(...)` wrapper (only when it spans the ENTIRE remaining
#   tail, with no internal unmatched parens) before the existing rule
#   (now including gap 1's clause-splitting) runs.

_CLAUSE_DELIM_RE = re.compile(r"[;,–—]")


def _matches_definicion_stem(text: str) -> bool:
    """True when the Spanish stem is the first substantive token of `text`,
    or its last substantive token without an immediately preceding Spanish
    preposition -- the original single-clause rule, now applied per-clause
    by `is_definitions_heading` (see the module comment above)."""
    text = text.strip()
    if _DEFINICION_FIRST_WORD_RE.match(text):
        return True

    trimmed = text.rstrip(" \t\r\n.")
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


def _heading_tail(heading: str) -> str:
    """Strip a leading `Artículo N.`/`Sección N.` label and, if present, a
    single fully-enclosing paren wrapper -- the shared tail-extraction logic
    behind BOTH `is_definitions_heading` (cycle 2) and
    `extract_heading_anchored_definition` (cycle 3, item 13). Pure
    extraction of the existing cycle-2 gap-1/gap-2 preprocessing, factored
    out so both consumers reuse the SAME code instead of a second copy."""
    rest = heading

    label_match = _SECTION_LABEL_RE.match(rest)
    if label_match:
        rest = rest[label_match.end() :]
    else:
        number_match = _SECTION_NUMBER_TOKEN_RE.match(rest)
        if number_match:
            rest = rest[number_match.end() :]
    rest = rest.lstrip()

    # Gap 2: a fully-parenthesized whole tail -- strip the enclosing parens
    # (only when they wrap the ENTIRE remaining tail with nothing left
    # outside them, and there is no internal unmatched paren) before the
    # clause-scoped rule below runs.
    paren_candidate = rest.rstrip(" \t\r\n.")
    if (
        paren_candidate.startswith("(")
        and paren_candidate.endswith(")")
        and "(" not in paren_candidate[1:-1]
        and ")" not in paren_candidate[1:-1]
    ):
        inner = paren_candidate[1:-1].strip()
        if inner:
            rest = inner
    return rest


def is_definitions_heading(heading: str) -> bool:
    """True when `heading`'s own operative subject is the Spanish stem
    "Definici(ón|ones)" -- see the module-level comments above for the
    exact rule (base single-clause rule plus the two cycle-2 gap fixes).

    Gap 1: check the stem against the WHOLE tail as well as every inner
    semicolon/comma/em-dash-delimited clause (a flat split of `rest`
    returns `[rest]` unchanged when no delimiter is present, so this is a
    strict generalization of the original whole-tail-only rule, not a
    replacement for it)."""
    rest = _heading_tail(heading)
    return any(_matches_definicion_stem(clause) for clause in _CLAUSE_DELIM_RE.split(rest))


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
#
# `_MARKER_UNIT_RE` adds "ch" as its own two-character letter alternative
# (tried before the single-character class) -- traditional Spanish
# alphabetical enumeration treats "ch" as its own letter, producing a real
# marker `ch)` (`STATE_PR_LEY_46_2008_ART3`) that a single-character
# `[a-zA-Z]` class can never match (cycle-2 marker-inventory gap).
#
# The boundary prefix carries a SECOND lookbehind, `(?<!\b[A-Za-z]\.)`,
# excluding a candidate whose qualifying period is itself the trailing
# period of an isolated single-letter token (e.g. the "U." in a spaced
# abbreviation like "U. S. Geological Survey") -- without it, that lone
# "U." satisfies the ordinary `(?<=[.;:\]])\s+` boundary and the following
# "S." misfires as a spurious entry marker, fragmenting the real entry's
# `definition_text` mid-sentence (cycle-2 precision defect, found in
# `STATE_PR_LEY_51_2003_ART2`). A genuine entry always ends its previous
# block with an ordinary multi-letter Spanish word, which never matches
# this exclusion (no word boundary sits directly before its last letter).
_MARKER_UNIT_RE = r"(?:ch|[a-zA-Z]|\d{1,3})"
_ENTRY_MARKER_RE = re.compile(
    r"(?:^|(?<=[.;:\]])(?<!\b[A-Za-z]\.)\s+)"
    rf"(?:\({_MARKER_UNIT_RE}\)"
    rf"|{_MARKER_UNIT_RE}\)"
    rf"|{_MARKER_UNIT_RE}\.(?=\s))"
    r"\s*"
)

# A block's term/definition separator. Cycle 1 shipped 3 patterns (quoted+
# colon, quoted+typographic-dash, unquoted+typographic-dash) but the real
# corpus needs 6 more -- live-diagnosed against 153 real zero-yield rows,
# see sprint contract's `### Cycle-2 corrections` and this module's sibling
# test file `test_pr_profile_extraction_cycle2.py`'s module docstring for
# the full per-shape table with real examples. Tried in this order (most
# specific separator character first, so a more permissive pattern never
# preempts a more specific one that should win):
#
#   1. quoted term + colon (dominant canonical shape, unchanged from cycle
#      1) -- curly `“”` in 437/635 canonical rows, straight `"` in 76/635,
#      both accepted.
#   2. quoted term + comma + a defining-verb idiom immediately after the
#      comma (`"Análisis Clínico", significará...`) -- the idiom lookahead
#      keeps an ordinary comma after a quoted phrase from misfiring as a
#      definition separator. An OPTIONAL `" o "` + a second quoted phrase
#      is allowed between the first quote and the comma (`"Barbero" o
#      "Estilista en Barbería", significará...`, `STATE_PR_LEY_60_1988_
#      ART1`) -- the FIRST quoted phrase is still what gets captured as
#      the term; the entry is not silently dropped just because it names
#      an alternate term via "o".
#   3. quoted term + em/en-dash OR a plain ASCII hyphen-minus (`"Activo" -
#      significa...` -- cycle 1 only accepted the typographic dash). The
#      same optional `" o "` + second-quoted-phrase allowance as pattern 2
#      applies here too (`"Gobierno de Puerto Rico" o "Gobierno"
#      -significará...`, same real row).
#   4/5. quoted term, NO separator character at all, just whitespace then
#      the rest of the block -- the single largest real shape (~133/153 of
#      bucket A). Split into TWO patterns, NOT unified into one permissive
#      "whitespace then anything" rule, because a fully unconstrained
#      version of this shape is language-BLIND and regresses gate P5 (M-
#      R4): a real English `"Affiliate" has the meaning specified in
#      ...` (`STATE_DE_T5_C7_SVIII_S796`) has the IDENTICAL quote-then-
#      whitespace-then-prose structure and would be wrongly captured too
#      if the pattern did not also require a Spanish-specific signal
#      immediately after the whitespace:
#        4. a directly-following Spanish defining-verb idiom
#           (`"Cuenta" significa...`) -- English's "has"/"means"/"shall"
#           never match this alternation.
#        5. NO idiom verb, but the definition starts with a CAPITALIZED
#           word (`"Activos líquidos" Aquellos activos que...`) -- English
#           "has the meaning..." starts lower-case ("has"), so this
#           pattern does not match it either; both together still cover
#           every real A1/A3 row measured.
#      Tried LAST among the quoted patterns (least specific), though in
#      practice they never wrongly preempt 1-3: none of those require
#      whitespace as the character immediately after the closing quote,
#      so these patterns' own `\s+` requirement already excludes those
#      shapes.
#   5. unquoted term + colon (`Certificación: documento oficial...` -- no
#      `_UNQUOTED_TERM_COLON_RE` existed at all before cycle 2). The
#      excluded-char class keeps the non-greedy term search from crossing
#      a sentence boundary to reach a colon that belongs to unrelated,
#      later prose (real example: `STATE_PR_LEY_52_2019_ART3`'s cross-law
#      deferral sentence has a `Núm.`-abbreviation period long before its
#      only colon -- excluding periods from the term class correctly
#      blocks this pattern from firing there at all). Also length-bounded
#      to <=100 chars (same reasoning as patterns 6/7 below): a colon can
#      legitimately sit deep INSIDE a correctly-dash-separated
#      definition's own prose (`STATE_PR_LEY_3_2022_ART4`: "Comandante de
#      Operaciones Regionales – Significa el(la) oficial de rango
#      designado a comandar alguna de las cuatro regiones policíacas, a
#      saber: Región 1...") -- without the bound, this pattern (tried
#      before the dash pattern) reaches straight past the real, near
#      dash separator to that unrelated, much later colon instead.
#   6. unquoted term + optional-period + em/en-dash (unchanged from cycle
#      1, 272/635 rows use this family, with or without a verb idiom --
#      `Es`/`Significará`/`Será` directly after the dash, or the
#      definition starting with a bare noun phrase, e.g. `Secretario. –
#      Se refiere al...`).
#   7. unquoted term + its OWN trailing period (not colon, not dash) then
#      a bare, capitalized definition (`Agencia. Cualquier
#      departamento...`). THREE guards keep this from misfiring: the
#      trailing `(?=[A-ZÁÉÍÓÚÑÜ])` lookahead requires the next real
#      sentence to start with a capital letter (so an abbreviation like
#      `Núm. 228` -- digit, not a capital letter, after the period -- is
#      never mistaken for a split point); the `(?<!\.[A-Z])` lookbehind
#      excludes a period that is itself the second half of a chained
#      single-letter abbreviation (`U.S.` in `U.S. Geological Survey` --
#      the period right after the "S" is preceded by "." + "S", so this
#      pattern correctly keeps expanding past it to the REAL term-ending
#      period after "Survey", real example `STATE_PR_LEY_51_2003_ART2`
#      entry 4, `"U.S. Geological Survey. Servicio Geológico Federal..."`);
#      and the group itself is built from `(?:[^.]|\.(?!-))+?` instead of
#      a plain `.+?` -- a period immediately followed by an ASCII hyphen
#      (no space) can NEVER be absorbed into the term, so the match fails
#      CLOSED (returns no match at all, rather than skipping past it to
#      hunt for some other, unrelated period later in the block) whenever
#      the block opens with a subsection-label shape like `"(a) En
#      General.- El caudal relicto bruto..."`. Confirmed live corpus-wide
#      against `STATE_PR_RENTAS_SEC2022_01`/`_SEC2042_01` (M-R7's correct-
#      zero rows): an earlier version of this pattern used unrestricted
#      `.+?`, which happily skipped the unmatchable "En General.-" and
#      kept expanding across the ENTIRE first block hunting for the next
#      period+capital-letter anywhere in the paragraph, fabricating a huge
#      bogus "term" out of the whole thing. This exclusion targets the
#      exact structural shape at fault instead of an arbitrary length cap
#      (which was tried first and cost real corpus-wide recall on
#      genuinely long-but-valid terms elsewhere).
_QUOTED_TERM_COLON_RE = re.compile(r'^["“]([^"”]+)["”]\s*:\s*')

# A canonical Spanish defining-verb idiom, shared by the comma-idiom
# pattern below and the dispatch-fallback bare-idiom pattern further down.
_DEFINING_IDIOM_ALTERNATION = r"(?:significará|significa|será|es)\b"

# Cycle-3 (item 15): `se refiere a`/`se referirá a` are real, safe defining
# idioms -- but ONLY for the per-BLOCK quoted patterns below, which fire
# exclusively on a block that already/now starts with a quote character
# (see `_extract_term_and_definition` and `_extract_lead_in_then_quoted_
# term`). Deliberately a SEPARATE, wider alternation from
# `_DEFINING_IDIOM_ALTERNATION` above -- the DISPATCH-FALLBACK check
# (`_UNQUOTED_BARE_IDIOM_TERM_RE` further below) keeps using the narrow
# one. Live-verified: widening the SAME alternation the dispatch fallback
# uses wrongly treats `STATE_PR_LEY_214_2004_ART2`'s gender-neutrality
# preamble ("...se refiere a ambos géneros...") as a single fabricated
# bare-copulative definition, collapsing 26 real marked terms into 1 --
# pinned as a permanent regression guard in
# `test_pr_profile_idiom_widening_cycle3.py`.
_QUOTED_DEFINING_IDIOM_ALTERNATION = (
    r"(?:significará|significa|será|es|se\s+refiere\s+a|se\s+referirá\s+a)\b"
)

_QUOTED_TERM_COMMA_IDIOM_RE = re.compile(
    r'^["“]([^"”]+)["”](?:\s+o\s+["“][^"”]+["”])?\s*,\s*(?='
    + _QUOTED_DEFINING_IDIOM_ALTERNATION
    + r")",
    re.IGNORECASE,
)
_QUOTED_TERM_DASH_RE = re.compile(
    r'^["“]([^"”]+)["”](?:\s+o\s+["“][^"”]+["”])?\s*\.?\s*[–—-]\s*'
)
_QUOTED_TERM_BARE_IDIOM_RE = re.compile(
    r'^["“]([^"”]+)["”]\s+(?=' + _QUOTED_DEFINING_IDIOM_ALTERNATION + r")",
    re.IGNORECASE,
)
_QUOTED_TERM_BARE_CAPITALIZED_RE = re.compile(r'^["“]([^"”]+)["”]\s+(?=[A-ZÁÉÍÓÚÑÜ])')
_UNQUOTED_TERM_COLON_RE = re.compile(r"^([^.:;\n]{1,100}?):\s*")
# Both unquoted patterns below bound their term group to <=100 chars.
# Real unquoted terms are short noun phrases (the longest measured across
# every fixture, `"Programa de educación agrícola o programas
# especializados en agricultura"`, is 72 chars) -- an UNBOUNDED non-greedy
# group, with no quote character to anchor its own far end the way the
# quoted patterns have, will happily walk straight through an entire
# multi-sentence block hunting for its first reachable dash or period
# anywhere at all, fabricating a huge, wrong "term" out of most of the
# block whenever no separator sits near the real start (confirmed live
# corpus-wide, e.g. `STATE_PR_CIVIL_ART326`'s `"Poder es la facultad por
# la que..."` -- no colon or dash anywhere near the front -- previously
# matched a full paragraph as one "term" via a dash many sentences later).
_UNQUOTED_TERM_DASH_RE = re.compile(r"^(.{1,100}?)\s*\.?\s*[–—]\s*")
_UNQUOTED_TERM_PERIOD_RE = re.compile(
    r"^((?:[^.]|\.(?!-)){1,100}?)(?<!\.[A-Z])\.\s+(?=[A-ZÁÉÍÓÚÑÜ])"
)

# Cycle-3 (item 16, shape 4): an unquoted term with a Spanish SCOPE clause
# ("a los fines de esta Ley", "para los efectos de este Capítulo", "para
# propósitos de...") INTERJECTED by commas between the term and its own
# idiom verb (`STATE_PR_LEY_9_2020_ART2`: `"Mujer trabajadora, a los fines
# de esta Ley, significará..."`) -- none of `_UNQUOTED_TERM_SEPARATOR_
# PATTERNS` above expect a second clause between the term and its
# separator. Term group excludes `.,:;` (mirrors every other unquoted
# pattern's discipline) so a block opening with a label-period-hyphen
# shape (the M-R7 "(a) En General.-" family) can never match here either --
# the period is never reachable by the term group, so the match fails
# closed at position 0, same protection as the other unquoted patterns.
_SCOPE_PHRASE_LEAD_ALTERNATION = (
    r"(?:a|para)\s+los\s+(?:fines|efectos)\s+de|para\s+prop[oó]sitos\s+de"
)
_UNQUOTED_TERM_INTERJECTED_SCOPE_IDIOM_RE = re.compile(
    r"^([^.,:;\n]{1,80}?),\s*(?:" + _SCOPE_PHRASE_LEAD_ALTERNATION + r")[^,]{0,60},\s*"
    r"(?=" + _DEFINING_IDIOM_ALTERNATION + r")",
    re.IGNORECASE,
)

# Split into a QUOTED group and an UNQUOTED group, tried separately (see
# `_extract_term_and_definition` below) rather than as one flat, ordered
# list -- a block that visibly STARTS with a quote character but matches
# none of the quoted patterns (an unrecognized idiom like "se refiere a",
# not one of `_DEFINING_IDIOM_ALTERNATION`'s 4 words) must be skipped
# entirely, not handed to the unquoted patterns. The unquoted patterns'
# char classes do not exclude quote characters, so without this split they
# would happily treat the leading quote mark as an ordinary character and
# keep searching -- often for a very long distance -- for their own
# separator (a colon, dash, or period) somewhere deep in the DEFINITION
# text instead, fabricating a huge, wrong "term" out of most of the block.
# Confirmed live corpus-wide: `STATE_PR_LEY_4_2022_ART1_03` entry (e),
# `"Cuenta Dotal de Equiparación" se refiere a la cuenta restricta,
# creada...` -- "se refiere a" is not a recognized idiom, so no quoted
# pattern matches, but `_UNQUOTED_TERM_PERIOD_RE` used to keep expanding
# straight through the quote marks and the entire definition sentence to
# the FIRST unrelated period+capital-letter it could find, three sentences
# later.
_QUOTED_TERM_SEPARATOR_PATTERNS = (
    _QUOTED_TERM_COLON_RE,
    _QUOTED_TERM_COMMA_IDIOM_RE,
    _QUOTED_TERM_DASH_RE,
    _QUOTED_TERM_BARE_IDIOM_RE,
    _QUOTED_TERM_BARE_CAPITALIZED_RE,
)
_UNQUOTED_TERM_SEPARATOR_PATTERNS = (
    _UNQUOTED_TERM_INTERJECTED_SCOPE_IDIOM_RE,
    _UNQUOTED_TERM_COLON_RE,
    _UNQUOTED_TERM_DASH_RE,
    _UNQUOTED_TERM_PERIOD_RE,
)
_QUOTE_CHARS = '"“'

# A5 -- a marker can be followed by a DECORATIVE em/en-dash before the
# actual term (`a. — "Nueva programación" significa...`,
# `STATE_PR_LEY_190_1995_ART2`) -- a block-PREFIX gap, not a new
# term/separator shape: stripped before the patterns above ever run, so
# what remains (`"Nueva programación" significa...`) is the ordinary A1
# bare-quoted shape.
_LEADING_DECORATIVE_DASH_RE = re.compile(r"^[–—]\s*")


# Cycle-3 (item 16, shapes 1/2/3/5): a block that does NOT start with a
# quote character can still contain one a short distance in, preceded by an
# unquoted lead-in ("El término "X" <idiom>", a scope-phrase lead-in before
# a comma-idiom quoted term, or a lead-in IDIOM CUE like "se considera
# como" with no separator at all after the quote). Bounded and disciplined,
# same "no unbounded forward search" precision philosophy as every other
# pattern in this module:
#   - the lead-in must be SHORT (<=60 chars) -- long enough for every real
#     shape measured this cycle (11-44 chars), short enough to reject the
#     one real correct-zero guard this bound was checked against,
#     `STATE_PR_LEY_48_2018_ART3`'s 85-char "conocida como" lead-in (a
#     cross-law/title deferral, NOT a term definition -- see
#     `test_pr_profile_extraction_cycle3.py`);
#   - AND the lead-in must cross no REAL sentence boundary of its own (a
#     semicolon, or a period NOT immediately followed by a hyphen -- the
#     same `\.(?!-)` exclusion `_UNQUOTED_TERM_PERIOD_RE` already uses to
#     protect the M-R7 "(a) En General.-" subsection-label shape, reused
#     here so a genuine "Label.-El término..." prefix does not itself
#     disqualify a lead-in the way an ordinary sentence-ending period
#     should -- this is what makes `STATE_PR_RENTAS_SEC1010_01`'s "(2)
#     Corporación.-El término "corporación" ..." block reachable);
#   - AND (belt-and-suspenders on top of the length bound) the lead-in must
#     not contain the `conocido/a como`/`denominado/a` law-title-naming
#     idiom the cycle-1 survey already flagged as unsafe to treat as a
#     term-defining trigger -- confirmed live against
#     `STATE_PR_LEY_48_2018_ART3`/`STATE_PR_LEY_52_2019_ART3`.
# Two independent techniques are tried, in order:
#   (a) re-try the ordinary QUOTED separator patterns starting AT the
#       quote (handles "El término "X" significa..." and a scope-phrase
#       lead-in before a comma-idiom quoted term -- both already-existing
#       patterns, no new vocabulary needed);
#   (b) if (a) finds nothing, check whether the lead-in itself ENDS with a
#       recognized cue idiom ("el término", "se considera(rá)(n) como") --
#       if so, the quoted term is definitional regardless of what
#       (if anything) follows the closing quote (`STATE_PR_LEY_155_1937_
#       SEC1`'s "se considera como "amplificador o altoparlante" todo
#       artefacto..." -- "todo" is not a recognized idiom word, so (a)
#       alone cannot capture this row). `definition_text` is bounded to the
#       SENTENCE immediately following the quoted term (not "everything
#       after") -- guards against a block whose entry-marker split left
#       more than one entry's worth of prose in it from fabricating one
#       bloated "definition" out of several distinct entries.
_MAX_LEAD_IN_LEN = 60
_LEAD_IN_REAL_SENTENCE_BREAK_RE = re.compile(r";|\.(?!-)")
_LAW_TITLE_NAMING_CUE_RE = re.compile(r"conocid[oa]s?\s+como|denominad[oa]s?\b", re.IGNORECASE)
_PRE_QUOTE_IDIOM_CUE_RE = re.compile(
    r"(?:el\s+t[eé]rmino|se\s+considera(?:r[aá]n?)?\s+como)\s*$", re.IGNORECASE
)
_BARE_QUOTED_TERM_HEAD_RE = re.compile(r'^["“]([^"”]+)["”]\s*')
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")


def _sentence_containing(body: str, pos: int) -> str:
    """The sentence in `body` containing character index `pos` -- split on
    `.`/`!`/`?` followed by whitespace. Falls back to the whole body when
    no such boundary is found (a genuinely single-sentence body, or a match
    in the LAST sentence with no trailing punctuation+whitespace after
    it). Shared by the lead-in fallback below and
    `extract_heading_anchored_definition` (item 13)."""
    start = 0
    for boundary in _SENTENCE_END_RE.finditer(body):
        if boundary.start() >= pos:
            return body[start : boundary.start()].strip()
        start = boundary.end()
    return body[start:].strip()


def _extract_lead_in_then_quoted_term(block: str) -> tuple[str, str] | None:
    """See the module comment block above -- a bounded, disciplined
    fallback for a block that does not start with a quote character but
    contains one a short, sentence-boundary-free distance in."""
    quote_pos = next((i for i, ch in enumerate(block) if ch in _QUOTE_CHARS), -1)
    if quote_pos <= 0 or quote_pos > _MAX_LEAD_IN_LEN:
        return None
    lead_in = block[:quote_pos]
    if _LEAD_IN_REAL_SENTENCE_BREAK_RE.search(lead_in):
        return None
    if _LAW_TITLE_NAMING_CUE_RE.search(lead_in):
        return None
    rest = block[quote_pos:]

    for pattern in _QUOTED_TERM_SEPARATOR_PATTERNS:
        match = pattern.match(rest)
        if match:
            term = match.group(1).strip()
            definition_text = rest[match.end() :].strip()
            if term and definition_text:
                return term, definition_text

    if _PRE_QUOTE_IDIOM_CUE_RE.search(lead_in):
        head_match = _BARE_QUOTED_TERM_HEAD_RE.match(rest)
        if head_match:
            term = head_match.group(1).strip()
            after = rest[head_match.end() :]
            definition_text = _sentence_containing(after, 0) if after else ""
            if term and definition_text:
                return term, definition_text
    return None


def _extract_term_and_definition(block: str) -> tuple[str, str] | None:
    """Split a single entry's raw text into (term, definition_text) using
    the first separator pattern that matches. Returns `None` for a block
    with no recognizable term/separator shape -- skipped, not fabricated
    (mirrors `USProfile.extract_definitions_from_section`'s "entries with
    no leading quoted term are skipped" discipline).

    A block that STARTS with a quote character only ever tries the QUOTED
    patterns, never the unquoted ones -- see the comment above
    `_QUOTED_TERM_SEPARATOR_PATTERNS` for why falling through to an
    unquoted pattern on quoted content is unsafe. A block that does NOT
    start with a quote character tries the UNQUOTED patterns first
    (unchanged cycle-1/2 behavior, tried first so nothing already working
    can regress), and only falls back to `_extract_lead_in_then_quoted_
    term` (cycle 3, item 16) when every unquoted pattern fails."""
    block = _LEADING_DECORATIVE_DASH_RE.sub("", block, count=1)
    if block[:1] in _QUOTE_CHARS:
        for pattern in _QUOTED_TERM_SEPARATOR_PATTERNS:
            match = pattern.match(block)
            if match:
                term = match.group(1).strip()
                definition_text = block[match.end() :].strip()
                if term and definition_text:
                    return term, definition_text
        return None

    for pattern in _UNQUOTED_TERM_SEPARATOR_PATTERNS:
        match = pattern.match(block)
        if match:
            term = match.group(1).strip()
            definition_text = block[match.end() :].strip()
            if term and definition_text:
                return term, definition_text
    return _extract_lead_in_then_quoted_term(block)


# A no-marker, single-entry article whose body ALSO contains an incidental
# enumerated sub-list of that SAME term's own duties/clauses (e.g.
# `(1)`..`(11)`) needs a bare-copulative-idiom shape with NO punctuation
# separator at all (`Agente General es la persona nombrada...`,
# `STATE_PR_LEY_77_1957_ART9_040`) -- see `extract_definitions_from_section`
# below for why this is a DISPATCH fix (checked against the LEAD-IN before
# the first marker, not a 4th quoted/unquoted pattern added to the general
# per-block list above). Deliberately narrow (capital-letter-anchored,
# length-bounded, no punctuation allowed in the term) precisely so it
# cannot collide with English text the way a broader colon/dash-based
# check would (see the dispatch docstring for the real regression this
# avoids).
_UNQUOTED_BARE_IDIOM_TERM_RE = re.compile(
    r"^([A-ZÁÉÍÓÚÑ][^.:;\n]{0,80}?)\s+" + _DEFINING_IDIOM_ALTERNATION
)


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

    Dispatch (cycle-2 fix): a body with NO markers always takes the
    single-entry path, unchanged from cycle 1. A body WITH markers used to
    be all-or-nothing -- ANY marker anywhere sent the whole body down the
    markers path, which has no "entry -1" for text before the first
    marker. That silently dropped the term and lead-in of a genuinely
    single-entry, no-top-level-marker article whose body happens to
    contain an INCIDENTAL enumerated sub-list of that one term's own
    duties/clauses (`STATE_PR_LEY_77_1957_ART9_040`: `"Agente General es
    la persona nombrada..."`, followed by a `(1)`..`(11)` duties list),
    producing 11 bogus fragment "entries" instead of the one real
    candidate.

    Fix: check whether the LEAD-IN text (everything before the FIRST
    marker) itself matches the narrow bare-copulative-idiom shape
    (`_UNQUOTED_BARE_IDIOM_TERM_RE` -- capital-letter-anchored term,
    directly followed by a Spanish idiom word). If it does, the whole body
    is a single entry; treat the enumerated markers found after it as
    incidental sub-clauses of that ONE definition, not a top-level entries
    list. This check is deliberately NARROWER than "does the first
    marker's own block fail to parse" (an earlier version of this fix used
    that broader check and it regressed gate P5/M-R4: a genuine English
    multi-entry preamble like `"As used in this subchapter:"` also fails
    to parse its own first entry -- `"Affiliate" has the meaning
    specified in...` never matches a Spanish idiom -- but its PREAMBLE
    also happens to satisfy the general unquoted-colon pattern, wrongly
    treating the preamble itself as a fabricated "term". Anchoring
    specifically on the bare-idiom shape, which requires an explicit
    Spanish idiom WORD immediately after the term with nothing but
    whitespace between them, has no English collision: no English word
    matches `significa`/`significará`/`será`/`es` as a whole word).
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

    lead_in = text[: markers[0].start()]
    lead_in_match = _UNQUOTED_BARE_IDIOM_TERM_RE.match(lead_in)
    if lead_in_match:
        term = lead_in_match.group(1).strip()
        definition_text = text[lead_in_match.end() :].strip()
        if term and definition_text:
            candidate = DefinitionCandidate(
                terms=(term,), definition_text=definition_text, scope=scope
            )
            return [candidate]

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


# --- Item 13 (P1/P4, director-ordered): heading-anchored bucket-D rule ------
#
# Director ruling (cycle 3): capture the subset of copulative/prose
# Definiciones-section bodies (bucket D -- no entry marker, no canonical
# defining idiom) whose HEADING NAMES THE DEFINED TERM, using the heading
# as the anchor -- e.g. `"Artículo 236. Bienes; definición"` -> body `"Son
# bienes las cosas o derechos..."`. NO general Spanish prose matcher: this
# function never inspects body prose for copulative SHAPE on its own. It
# only fires when TWO independent conditions both hold:
#
#   1. `heading` is already a genuine Definiciones heading (reuses
#      `is_definitions_heading` itself as the FIRST gate -- a heading not
#      recognized as Definiciones at all names no term to anchor from), and
#      its own non-"definición(es)" clause names a specific term -- either
#      a clause that does NOT itself match the stem (the semicolon/comma/
#      em-dash-compound-heading shape, `_candidate_terms_from_heading`
#      below), or a single clause shaped "Definici(ón|ones) de X" (the term
#      is the prepositional object of "de" within the SAME clause that also
#      satisfies the stem match).
#   2. That EXACT term (word-boundary, accent-folded, case-insensitive,
#      leading-Spanish-article-stripped) is independently corroborated by
#      appearing, VERBATIM and CONTIGUOUSLY, somewhere in the section's own
#      body -- a literal presence check, not a fuzzy/grammatical one. A
#      nominalization ("se enriquece" for a heading naming "Enriquecimiento
#      sin causa"), a non-contiguous paraphrase ("un activo es uno no
#      admitido" for "Activo no Admitido"), or a genuine heading/body term
#      mismatch (heading names "las normas de la compraventa", body defines
#      "permuta") all correctly yield NOTHING -- see
#      `test_pr_profile_bucket_d_heading_anchored.py`'s residue tests.
#
# Searches the FULL body (never window-truncated -- one real anchor,
# `STATE_PR_LEY_77_1957_ART36_020`'s "Sistema de logias", sits at the very
# END of its body), but EXCLUDES a real, previously-uncatalogued page-break
# scrape-footer artifact (`"Rev. <date> www.ogp.pr.gov Página N de M
# "<Law Title>"[ de <year>] [Ley N-YYYY, según enmendada]"`, 370
# corpus-wide rows, quote style and trailing "de <year>" both optional --
# confirmed via 3 real corpus shapes) that can inject its OWN, UNRELATED
# quoted law title anywhere mid-body and would otherwise be indistinguishable
# from a real corroborating quote.

_PAGE_BREAK_FOOTER_RE = re.compile(
    r"Rev\.\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\s+www\.ogp\.pr\.gov\s+"
    r"Página\s+\d+\s+de\s+\d+\s+.*?\[Ley[^\]]*\]\s*",
    re.IGNORECASE,
)

# "Definici(ón|ones) de X" -- a SINGLE clause (no `;`/`,`/em-dash) where the
# whole clause satisfies the stem match AND the anchor term is the
# prepositional object of "de" within that SAME clause (cycle 2's crude
# split only extracted a term from a clause that does NOT itself match the
# stem -- this is the genuinely new shape cycle 3 found).
_DEFINICION_DE_X_RE = re.compile(r"^[Dd]efinici[oó]n(?:es)?\s+de\s+(.+)$", re.IGNORECASE)


def _candidate_terms_from_heading(heading: str) -> list[str]:
    """Every candidate defined term named by `heading`'s own clauses. A
    clause that does NOT itself match the Definici(ón|ones) stem is a
    candidate verbatim (leading Spanish article stripped); a clause that
    DOES match the stem, shaped "Definici(ón|ones) de X", also yields X
    (leading article stripped) as an ADDITIONAL candidate. Reuses
    `_heading_tail`/`_CLAUSE_DELIM_RE`/`_matches_definicion_stem` -- the
    SAME clause-splitting/stem-matching machinery `is_definitions_heading`
    itself uses, not a duplicate."""
    rest = _heading_tail(heading)
    candidates: list[str] = []
    for raw_clause in _CLAUSE_DELIM_RE.split(rest):
        clause = raw_clause.strip().rstrip(" \t\r\n.")
        if not clause:
            continue
        if not _matches_definicion_stem(clause):
            term = _LEADING_SPANISH_ARTICLE_RE.sub("", clause).strip()
            if term:
                candidates.append(term)
            continue
        de_x_match = _DEFINICION_DE_X_RE.match(clause)
        if de_x_match:
            term = de_x_match.group(1).strip().rstrip(" \t\r\n.")
            term = _LEADING_SPANISH_ARTICLE_RE.sub("", term).strip()
            if term:
                candidates.append(term)
    return candidates


def _fold_char(ch: str) -> str:
    """Strip a single character down to its base Latin letter (accent
    removed) via NFD decomposition -- always returns exactly ONE character
    (falls back to `ch` unchanged if decomposition yields anything other
    than a single base character), so folding a whole string char-by-char
    preserves its length and every original character INDEX -- letting a
    match found in the folded copy be sliced directly out of the ORIGINAL
    string with no separate offset-mapping step."""
    decomposed = unicodedata.normalize("NFD", ch)
    base = "".join(c for c in decomposed if not unicodedata.combining(c))
    return base if len(base) == 1 else ch


def _fold(text: str) -> str:
    return "".join(_fold_char(ch) for ch in text)


def _find_corroborated_term(candidate_terms: list[str], body: str) -> tuple[str, int, int] | None:
    """The first candidate term (longest first, in case more than one
    heading clause names a candidate) that is independently corroborated --
    appears, verbatim, word-boundary, accent-folded, case-insensitive --
    somewhere in `body`. Returns `(term, match_start, match_end)` in
    `body`'s OWN index space (via `_fold`'s length-preserving property) so
    the caller can locate the real surrounding prose; `None` if no
    candidate corroborates."""
    folded_body = _fold(body)
    for term in sorted(set(candidate_terms), key=len, reverse=True):
        folded_term = _fold(term).strip()
        if not folded_term:
            continue
        pattern = re.compile(r"\b" + re.escape(folded_term) + r"\b", re.IGNORECASE)
        match = pattern.search(folded_body)
        if match:
            return term, match.start(), match.end()
    return None


def extract_heading_anchored_definition(
    heading: str, body: str, *, scope: str
) -> list[DefinitionCandidate]:
    """The director-ordered, narrow bucket-D capture (cycle 3, item 13) --
    see the module comment block above for the full two-condition rule.
    Returns exactly one candidate when both conditions hold, else `[]`.

    A THIRD, precondition gate, found via this cycle's own corpus
    self-check (not named by any test, but required by the sprint
    contract's own bucket-D definition): bucket D is, BY DEFINITION, "no
    entry marker and no canonical defining idiom" -- a body that DOES have
    `_ENTRY_MARKER_RE` marker structure is not bucket D at all, it is
    `extract_definitions_from_section`'s domain (markers path or the
    M-R7-protected subsection-label shape), and this rule must defer to
    that verdict rather than layering a second, competing capture on top.
    Confirmed live: WITHOUT this guard, the heading-anchor rule also fires
    on ruling M-R7's three correct-zero rows (`STATE_PR_LEY_77_1957_
    ART36_030`, `STATE_PR_RENTAS_SEC2022_01`, `STATE_PR_RENTAS_SEC2042_
    01`) -- each has a heading that genuinely names a term AND that term
    genuinely appears verbatim in the body, so the two-condition rule alone
    is not sufficient; each body ALSO has multiple `(a)`/`(b)`/`(1)`...
    markers (unlike every one of the 70 real anchored rows and 7 residue
    rows, independently confirmed to have ZERO markers). This guard keeps
    those two populations disjoint by the same signal the corpus itself
    uses to distinguish them."""
    if not is_definitions_heading(heading):
        return []
    if _ENTRY_MARKER_RE.search(body):
        return []

    candidate_terms = _candidate_terms_from_heading(heading)
    if not candidate_terms:
        return []

    footer_stripped_body = _PAGE_BREAK_FOOTER_RE.sub(" ", body)
    corroboration = _find_corroborated_term(candidate_terms, footer_stripped_body)
    if corroboration is None:
        return []

    term, match_start, _match_end = corroboration
    definition_text = _sentence_containing(footer_stripped_body, match_start)
    if not definition_text:
        return []
    return [DefinitionCandidate(terms=(term,), definition_text=definition_text, scope=scope)]


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
