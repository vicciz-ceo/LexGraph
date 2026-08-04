"""Shared quote-first grammar helpers for IL `ScopeTriggerRule` modules
(sprint 2026-08-04-defs-il, Phase C, rulings C1/C2/M16 -- program
efficiency directive: ONE shared punctuation-connector pattern + parsing
algorithm, reused across rule files, instead of near-identical clones).

## C1 -- the widened trigger-to-quote connector

Every shipped IL quote-first trigger rule (and the FROZEN
`extract._LOCAL_TRIGGER_RE`) hardcoded a literal comma between the
trigger phrase and the opening quote (`TRIGGER,\\s*"..."`). The real
corpus also uses a bare space, a colon, and a dash -- each with optional
surrounding whitespace -- but never a zero-length gap (excluding the
pathological case of a trigger phrase sitting immediately adjacent to an
unrelated quote elsewhere, e.g. a gershayim year abbreviation
`תשע"א`): every live-reconfirmed real occurrence requires >=1 separator
character (either the punctuation mark itself, or >=1 whitespace char).
Whitespace here is deliberately `[ \\t]` only (never `\\n`) -- every real
occurrence this sprint measured has its trigger and opening quote on the
SAME physical line, so restricting to intra-line whitespace is a
precision safeguard, not a completeness gap.

## The quote-first parsing algorithm (`extract_quote_first_candidates`)

A single `"([^"]+)"\\s*-\\s*(.*)$` capturing group (every rule module's
pre-Phase-C shape) cannot parse a real, common corpus shape: MULTIPLE
quoted terms before the split marker (`"term1" ו"term2" qualifier -
definition`, e.g. `חוק שירות הציבור...` art.7's `"חבר הנהלה" ו"בעל
מניות"`). `_find_split_marker`/`_parse_terms_and_qualifier` below mirror
(a local copy, not an import -- `extract.py` is FROZEN and this sprint's
change set is rule-modules-only) the SAME proven algorithm the list-shape
entry grammar already uses for this exact shape.

`_find_split_marker` additionally recognizes the corpus's own `((-))`
double-paren-escaped-dash idiom (the SAME escaping family visible in this
corpus's repeal markers, e.g. `(((נמחקה);))`) as a valid split marker
alongside a plain standalone `-` -- evidence-grounded, not invented:
required by the real `צו בדבר העסקת עובדים...` art.6 fixture (`"שוהה לא
חוקי" ((-)) כהגדרתו ...`), where the definition begins right after a
`((-))` marker rather than a bare dash.

Finding every trigger occurrence via a SHORT match (trigger text +
connector only, never a greedy to-end-of-line capture) also happens to
fix C2's same-line-swallow bug for free, for every rule built on this
helper: `finditer`'s scan position after a short match is unaffected by
how far the WRAPPER function reads ahead for its own clause/definition
text, so a second same-line trigger occurrence is always found
independently by `finditer` itself, regardless of what the first
occurrence's own (best-effort, truncated-at-the-next-trigger) definition
text captured.

## M16/M17 -- shared law-wide instrument vocabulary

`LAW_WIDE_WORDS`/`law_wide_preamble_phrases` -- measured, hand-verified
per phrase (sprint log's Phase C round 2 entry has the full per-phrase
verification transcript) -- instrument words whose preamble genuinely
names the WHOLE law/instrument (`scope="law-wide"`), each with its
`לענין`/`לעניין` preposition variant. Shared between the list-shape
scope-inference table (`il_list_shape_scope.py`) and the quote-first
law-wide rule (`il_m17_spelling_variant_scope_triggers.py`) so the
vocabulary is defined and measured ONCE, not duplicated per grammar
shape. Deliberately EXCLUDES (each verified against real corpus
instances -- see the log): `בתוספת זו` (schedule), `בפוליסה זו` (an
embedded form), `בפרק משנה זה` (sub-chapter), `בנספח זה` (appendix),
`בטבלה זו` (table), `בנוסחה זו` (formula), `בתקנה זאת`/`בתקנת שעת חירום
זו` (article-level, not law-wide), `לעניין כלל זה` (one rule, singular
-- NOT the same as plural `בכללים אלה`), `לעניין פרט חימוש זה`, `באמת
מידה זו`, enumerated multi-article ranges, and `בכלל זה` (a false
friend meaning "including this").
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate

# --- C1: the widened trigger-to-quote connector ----------------------------

_WS = r"[ \t]"
CONNECTOR = rf"(?:{_WS}*[,:\-]{_WS}*|{_WS}+)"


def quote_first_re(trigger_alternation: str) -> re.Pattern[str]:
    """Compile a `TRIGGER<CONNECTOR>` matcher -- matches ONLY the trigger
    phrase + connector, stopping right before the opening quote, never a
    greedy to-end-of-line capture (see module docstring: this is what
    lets C2's same-line-swallow bug never happen for a rule built on
    this helper)."""
    return re.compile(rf"{trigger_alternation}{CONNECTOR}", re.MULTILINE)


# --- The quote-first parsing algorithm --------------------------------------

_QUOTE_RE = re.compile(r'"([^"]+)"')
_ESCAPED_DASH_MARKER = "((-))"


def _find_split_marker(text: str) -> tuple[int, int]:
    """First term/definition split marker OUTSIDE any quoted span in
    `text`: a standalone `-` (preceded/followed by whitespace or
    start/end) or the corpus's own `((-))` escaped-dash idiom (see module
    docstring), whichever comes first. Returns `(-1, 0)` if neither is
    found."""
    in_quote = False
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if ch == '"':
            in_quote = not in_quote
            i += 1
            continue
        if not in_quote:
            if text.startswith(_ESCAPED_DASH_MARKER, i):
                return i, len(_ESCAPED_DASH_MARKER)
            if ch == "-":
                before_ok = i == 0 or text[i - 1].isspace()
                after_ok = i == n - 1 or text[i + 1].isspace()
                if before_ok and after_ok:
                    return i, 1
        i += 1
    return -1, 0


def _parse_terms_and_qualifier(header: str) -> tuple[list[str], str | None]:
    """Mirrors `extract._parse_terms_and_qualifier`'s proven algorithm (a
    local copy, not an import -- see module docstring): every quoted term
    in `header`, plus any trailing non-quote qualifier text (e.g. the
    `בעסק` in `"חבר הנהלה" ו"בעל מניות" בעסק`)."""
    matches = list(_QUOTE_RE.finditer(header))
    if not matches:
        return [], None
    terms = [m.group(1).strip() for m in matches]
    leftover = header[matches[-1].end() :]
    cleaned = re.sub(r"^[\s,]+", "", leftover).strip()
    qualifier = cleaned if cleaned and cleaned != "ו" else None
    return terms, qualifier


def extract_quote_first_candidates(
    article_body: str, trigger_re: re.Pattern[str], *, scope: str
) -> list[DefinitionCandidate]:
    """Every `TRIGGER<connector>"term"(ו"term2")*[qualifier]<split>
    definition` occurrence in `article_body`, up to end-of-physical-line
    (or up to the NEXT trigger occurrence on the same line, whichever is
    first -- C2's fix: a second same-line trigger's own clause is never
    swallowed into the first's definition text). `scope` is stamped as
    given; every other `DefinitionCandidate` field is left at its default
    for the caller to override if needed (e.g. `source_chapter` for a
    chapter-scoped rule)."""
    results: list[DefinitionCandidate] = []
    for match in trigger_re.finditer(article_body):
        start = match.end()
        if start >= len(article_body) or article_body[start] != '"':
            continue
        line_end = article_body.find("\n", start)
        if line_end == -1:
            line_end = len(article_body)
        next_match = trigger_re.search(article_body, start)
        clause_end = line_end
        if next_match is not None and next_match.start() < clause_end:
            clause_end = next_match.start()
        clause = article_body[start:clause_end]

        marker_idx, marker_len = _find_split_marker(clause)
        if marker_idx == -1:
            continue
        header = clause[:marker_idx].rstrip()
        terms, qualifier = _parse_terms_and_qualifier(header)
        if not terms:
            continue
        definition_text = clause[marker_idx + marker_len :].strip()
        results.append(
            DefinitionCandidate(
                terms=tuple(terms),
                definition_text=definition_text,
                scope=scope,
                qualifier=qualifier,
            )
        )
    return results


# --- M16/M17: shared law-wide instrument vocabulary -------------------------

LAW_WIDE_WORDS: tuple[str, ...] = (
    "חוק זה",
    "חוק יסוד זה",
    "תקנות אלה",
    "תקנות אלו",
    "הסכם זה",
    "כללים אלה",
    "פקודה זו",
    "צו זה",
    "אכרזה זו",
    "נוהל זה",
)


def law_wide_preamble_phrases() -> tuple[str, ...]:
    """Every `<ב-word>` / `לענין <word>` / `לעניין <word>` law-wide
    phrase built from `LAW_WIDE_WORDS`, longest-first (defensive against
    substring-shadowing in a linear scope-inference scan, even though no
    actual collision exists among these phrases -- see
    `il_list_shape_scope.py`)."""
    phrases: list[str] = []
    for word in LAW_WIDE_WORDS:
        phrases.append("ב" + word)
        phrases.append("לענין " + word)
        phrases.append("לעניין " + word)
    return tuple(sorted(phrases, key=len, reverse=True))
