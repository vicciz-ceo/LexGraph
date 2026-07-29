"""Stage 5 -- false-positive guards + ruling M7's bidi-degraded-text guard
(sprint 2026-07-29-definition-links, item DL6b).

See the review doc's "Deterministic definition-linking design" Stage 5.
"""

from __future__ import annotations


def is_plain_quotation(text: str, quote_end_pos: int) -> bool:
    """Stage 5.1: True when the quoted span ending at `quote_end_pos` is
    NOT followed by a dash within ~3 tokens (a title quote or direct
    speech, not a definition)."""
    rest = text[quote_end_pos:]
    tokens = rest.strip().split()
    window = " ".join(tokens[:3])
    return "-" not in window and "–" not in window


def is_rejectable_term(term: str) -> bool:
    """Stage 5.2: True for terms shorter than 2 characters or consisting
    only of digits (rejects quoted sub-item labels like `"א"`)."""
    stripped = term.strip()
    if len(stripped) < 2:
        return True
    if stripped.isdigit():
        return True
    return False


def resolve_law_title(candidate: str, known_titles) -> str | None:
    """Stage 5.4: EXACT match only against `known_titles` -- never a
    fuzzy fallback. Returns `None` when `candidate` doesn't exact-match
    exactly one known title (including the ambiguous case where a bare,
    unparenthesized name would otherwise collide with multiple
    parenthesized variants)."""
    matches = [title for title in known_titles if title == candidate]
    if len(matches) == 1:
        return matches[0]
    return None


def is_bidi_degraded(text: str) -> bool:
    """Stage 5.5 / ruling M7: flags text showing reversed-RTL-word-order
    artifacts characteristic of naive PDF extraction.

    No specific detection algorithm is prescribed (explicitly
    "PDF-tool-dependent" per the dossier); this checks for structural wiki
    markers (`@ N.` article markers, `:-` definition-entry markers) that
    should ONLY ever appear as line PREFIXES in correctly-ordered text --
    if `@` appears mid/end-of-line, or a line ends with `:-` instead of
    starting with it, the line's word order has been reversed.
    """
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        at_index = stripped.find("@")
        if at_index > 0:
            return True
        if stripped.endswith(":-"):
            return True
    return False
