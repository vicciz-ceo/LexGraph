"""Stage 4 -- detect cross-law derivation and link the two laws (sprint
2026-07-29-definition-links, item DL6).

Input text is Stage-0-normalized, wikilink-brackets-already-stripped-to-
display-text plain text (same convention as `extract.py`). See the review
doc's "Deterministic definition-linking design" Stage 4.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

TRIGGER_PHRASES = (
    "כהגדרתו",
    "כהגדרתה",
    "כהגדרתם",
    "כהגדרתן",
    "כהגדרת",
    "כמשמעותו",
    "כמשמעותה",
    "כמשמעותם",
    "כמשמעותן",
    "כמשמעות",
)

# Longest-first so e.g. "כהגדרתם" (suffixed form) is preferred over the
# bare construct form "כהגדרת" when both could match at the same position
# (the construct form is a literal prefix of every suffixed form).
_TRIGGER_RE = re.compile(
    "|".join(re.escape(t) for t in sorted(TRIGGER_PHRASES, key=len, reverse=True))
)

_QUOTE_SKIP_RE = re.compile(r'^\s*"[^"]*"\s*')
_LEADING_WS_RE = re.compile(r"^\s*")

# Stage 3 territory (same-law internal reference) -- must NOT be emitted
# as a cross-law derivation.
_BESAIF_RE = re.compile(r"^בסעיף\s+\d")

# Anaphoric forms resolving to the most recently named law earlier in the
# text (falling back to the same paragraph).
_ANAPHORIC_RE = re.compile(r"^ב?(אותו חוק|החוק האמור|חוק האמור)")

# `ב<law name>` / `בפקודת <name>`, optionally followed by ONE balanced
# parenthetical qualifier (DL13, cycle 2, G7, ruling M9(c) -- poc-run.md §8
# Issue 3: a law's real, ingested title can require a parenthetical
# qualifier, e.g. `חוק הבנקאות (שירות ללקוח)`; the base name's char class
# excludes `(`/`)` so it stops right before one -- this inserted group
# captures exactly one such qualifier before any trailing year clause), then
# optionally a trailing ", <year clause>" (Hebrew-year or plain
# Mandatory-era digit year).
_LAW_REF_RE = re.compile(
    r"^ב((?:חוק|פקודת|פקודה)\s+[^,;()]+(?:\s*\([^()]*\))?(?:,\s*[^,;()]*?\d{4})?)"
)

# A trailing ", ...<4-digit-year>" clause, stripped to get a law's
# canonical short identity (amendments keep the same short name).
_YEAR_TAIL_RE = re.compile(r",\s*[^,;()]*?\d{4}\s*$")

# DL13's compounding artifact: the base name's char class doesn't exclude
# sentence punctuation, so a law reference ending a sentence with no
# trailing comma/semicolon boundary (e.g. "...בחוק החברות.") captures the
# period into the "law name". Stripped (at minimum a trailing '.') before
# computing the `known_law_titles` lookup key -- never from `matched_text`,
# which preserves the raw captured span.
_TRAILING_SENTENCE_PUNCT_RE = re.compile(r"[.]+$")


def strip_year_suffix(name: str) -> str:
    """Return `name` with a trailing ", ...<year>" clause removed --
    the canonical short law-title identity key (year stripped since
    amendments keep the same short name)."""
    return _YEAR_TAIL_RE.sub("", name).strip()


def _strip_trailing_sentence_punctuation(name: str) -> str:
    """Strip trailing sentence punctuation (at minimum a trailing '.')
    from a captured law-reference name before computing its short-name
    identity key (DL13, ruling M9(c))."""
    return _TRAILING_SENTENCE_PUNCT_RE.sub("", name).rstrip()


@dataclass(frozen=True)
class LawDerivesDefinitionEdge:
    source_term: str
    trigger_phrase: str
    matched_text: str
    target_law_name: str | None
    target_law_id: str | None
    # NEW (sprint 2026-08-04-defs-core-scope, seam spec v2.1 §4 -- pointer
    # definitions, internal same-law targets): set ONLY when this edge is
    # a "whole-definition pointer" whose trigger+citation match consumed
    # the candidate's ENTIRE definition_text and points at a section of
    # THIS SAME document (today's `_SAME_LAW_RE`/`_BESAIF_RE` same-law
    # exclusion, redirected rather than dropped). Additive, defaulted --
    # every existing construction site (both engines' ordinary cross-law
    # edges) leaves this `None`, unaffected. `pipeline.py`'s Stage 4
    # resolves this article NUMBER (not yet an id) into the same
    # document's real Article row, the same way Stage 3 already resolves
    # same-document article numbers.
    internal_article_number: str | None = None


def detect_cross_law_derivations(
    text: str, *, source_term: str, known_law_titles: dict[str, str] | None = None
) -> list[LawDerivesDefinitionEdge]:
    """Scan `text` for `TRIGGER_PHRASES` occurrences that are immediately
    followed by an explicit law reference, an anaphoric reference to the
    most recently named law, or (excluded here) a same-law `בסעיף <N>`
    reference.

    `known_law_titles` maps a normalized (year-stripped) law title to a
    law id. When the extracted name doesn't exact-match any known title,
    the edge is STILL emitted with `target_law_id=None` and the raw
    matched string preserved (ruling M5) -- never a fabricated guess.
    """
    known = known_law_titles or {}
    edges: list[LawDerivesDefinitionEdge] = []
    last_law_name: str | None = None

    for match in _TRIGGER_RE.finditer(text):
        trigger = match.group(0)
        after = text[match.end() :]

        quote_match = _QUOTE_SKIP_RE.match(after)
        if quote_match:
            rest = after[quote_match.end() :]
        else:
            rest = after[_LEADING_WS_RE.match(after).end() :]

        if _BESAIF_RE.match(rest):
            continue  # same-law internal reference -- Stage 3 territory

        anaphoric_match = _ANAPHORIC_RE.match(rest)
        if anaphoric_match:
            if last_law_name is None:
                continue
            edges.append(
                LawDerivesDefinitionEdge(
                    source_term=source_term,
                    trigger_phrase=trigger,
                    matched_text=anaphoric_match.group(0),
                    target_law_name=last_law_name,
                    target_law_id=known.get(last_law_name),
                )
            )
            continue

        law_ref_match = _LAW_REF_RE.match(rest)
        if law_ref_match:
            full_name = law_ref_match.group(1)
            short_name = _strip_trailing_sentence_punctuation(strip_year_suffix(full_name))
            last_law_name = short_name
            edges.append(
                LawDerivesDefinitionEdge(
                    source_term=source_term,
                    trigger_phrase=trigger,
                    matched_text=full_name,
                    target_law_name=short_name,
                    target_law_id=known.get(short_name),
                )
            )
            continue
        # else: trigger not followed by a recognizable law reference --
        # not a cross-law derivation (nor a same-law one); skip.

    return edges


def is_generic_law_reference(text: str, trigger_pos: int) -> bool:
    """Stage 5.1's `לפי חוק`/`כאמור בחוק` variant: True (generic
    cross-reference, not a derivation) UNLESS this occurrence is the
    ENTIRE definition body directly after a quoted term -- i.e. the
    character immediately before `trigger_pos` (skipping whitespace) is a
    `-`/`–`, and the character before THAT (skipping whitespace) is a
    closing `"`.
    """
    i = trigger_pos - 1
    while i >= 0 and text[i].isspace():
        i -= 1
    if i >= 0 and text[i] in "-–":
        j = i - 1
        while j >= 0 and text[j].isspace():
            j -= 1
        if j >= 0 and text[j] == '"':
            return False
    return True
