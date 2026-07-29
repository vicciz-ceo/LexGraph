"""Stage 0 -- text normalization (sprint 2026-07-29-definition-links, item DL2).

Runs on a parsing-side copy only; the original text is never mutated here
-- that discipline is enforced at the call site (`pipeline.py`), not by
this module. See the review doc's "Deterministic definition-linking
design" Stage 0 for the full spec.
"""

from __future__ import annotations

import re
import unicodedata

# Stage 0.2: Hebrew niqqud (points/cantillation marks) block, U+0591-U+05C7,
# stripped defensively -- these never carry lexical meaning for term
# matching. U+05BE (Hebrew maqaf/dash) falls numerically inside that block
# but is punctuation, not a niqqud mark, so it is carved out of this range
# (split into U+0591-U+05BD and U+05BF-U+05C7) -- Stage 0.3 collapses it to
# a canonical hyphen instead of it being silently deleted here.
_NIQQUD_RE = re.compile("[֑-ֽֿ-ׇ]")

# Stage 0.3: dash variants collapsed to a canonical ASCII hyphen -- en dash
# (U+2013), em dash (U+2014), Hebrew maqaf (U+05BE).
_DASH_VARIANTS_RE = re.compile("[–—־]")

# Stage 0.4: quote variants collapsed to one quote class (plain ASCII
# double quote) -- curly quotes (U+201C, U+201D) and gershayim (U+05F4).
# The single geresh (U+05F3) is NEVER touched here -- it is the Hebrew
# abbreviation mark (e.g. "מס' 5"), not a term-quote.
_QUOTE_VARIANTS_RE = re.compile("[“”״]")

# Stage 0.5: `[[target]]` / `[[target|display]]` wikilink spans.
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def normalize_for_parsing(raw_text: str) -> str:
    """Return a Stage-0-normalized copy of `raw_text` for parsing.

    1. Unicode NFC normalization.
    2. Strip Hebrew niqqud (U+0591-U+05C7) defensively.
    3. Collapse dash variants (en dash, em dash, Hebrew maqaf) to `-`.
    4. Collapse quote variants (curly quotes, gershayim) to one quote
       class -- the bare geresh (U+05F3) is left untouched.
    """
    text = unicodedata.normalize("NFC", raw_text)
    text = _NIQQUD_RE.sub("", text)
    text = _DASH_VARIANTS_RE.sub("-", text)
    text = _QUOTE_VARIANTS_RE.sub('"', text)
    return text


def strip_wikilinks(text: str) -> tuple[str, list[dict]]:
    """Replace every `[[target]]` / `[[target|display]]` span with its
    display text (or the target text when there is no `|display`),
    returning `(rewritten_text, hints)`.

    `hints` is a list of `{"target": str, "display": str}` dicts in
    left-to-right order -- the brackets are a scrape artifact; downstream
    stages must never depend on them.
    """
    hints: list[dict] = []

    def _replace(match: re.Match[str]) -> str:
        target = match.group(1)
        display = match.group(2) if match.group(2) is not None else target
        hints.append({"target": target, "display": display})
        return display

    rewritten = _WIKILINK_RE.sub(_replace, text)
    return rewritten, hints
