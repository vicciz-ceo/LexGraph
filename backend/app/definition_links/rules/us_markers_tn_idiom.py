"""Rule: TN's `"Term": (1) Has the same meaning as interpreted by ...`
colon-then-list shape (family 3). Confirmed live (sprint 2026-08-04-defs-
us-markers, planner passes 1-2), `STATE_TN_T50_C2_S50-2-115`: the real
idiom is "Has the same meaning AS INTERPRETED BY the United States supreme
court ..." -- `us_profile._MEANS_IDIOM_GAP_RE`'s literal `has the meaning`
never matches, because the interposed "same ... as interpreted by" breaks
the bounded gap; this sprint's own tight-idiom engine
(`us_markers_boundary.extract_quote_anchored_entries`) has the identical
gap problem for the same reason, so TN needs its own narrow rule rather
than a further-loosened shared idiom pattern (which would risk matching
unrelated "has the same X as Y" phrasing corpus-wide).

TN's own real row's `text` field independently repeats its own content
twice (a real, non-injected vaquill data-quality quirk -- once flowing,
once line-broken, each copy followed by its own "Added by 2024 Tenn.
Acts, ..." amendment-history tail) -- taking only the FIRST `"Term":`
occurrence and truncating at the FIRST trailing "Added by <year>" annotation
keeps the captured definition to the clean first copy, matching ruling
U-R1's clean-boundary bar without depending on the duplication being
resolved elsewhere.

**Corpus self-verification caught a real precision defect in an earlier
draft of this rule, fixed here:** a bare `"Term":` search (no idiom check
at all) matches ANY quoted-term-then-colon shape anywhere in a TN
Definitions section -- including huge PART-level sections that bundle
dozens of unrelated entries (e.g. `STATE_TN_T36_C1_S36-1-102`, a
165,438-char "Part definitions" section). Without an idiom check, the
first `"Term":` found (there, `"Adoption facilitator":`, entry 6 of many)
swallowed everything to the end of the section -- 153,837 chars, the
single worst false-positive this sprint's corpus sweep found. The fix:
require the match to be immediately followed by TN's OWN confirmed idiom
opening, `(1) Has the same meaning` (case-insensitive, parens optional) --
this is what genuinely distinguishes the colon-then-list shape from an
ordinary `"Term": (A) Means ...` entry inside a ordinary large section."""

from __future__ import annotations

import re

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule
from app.definition_links.rules.us_markers_boundary import MAX_CLEAN_DEFINITION_LENGTH

_TN_TERM_RE = re.compile(
    r'"([^"]{1,60})":\s*(?=\(?1\)?\.?\s*Has the same meaning\b)', re.IGNORECASE
)
_ADDED_BY_RE = re.compile(r"\bAdded by \d{4}\b")


def _split(text: str) -> list[str]:
    m = _TN_TERM_RE.search(text)
    if m is None:
        return []
    stop = _ADDED_BY_RE.search(text, m.end())
    end = stop.start() if stop else len(text)
    definition_text = text[m.end() : end].strip()
    if not definition_text or len(definition_text) > MAX_CLEAN_DEFINITION_LENGTH:
        return []
    return [f'"{m.group(1).strip()}" {definition_text}']


register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-TN",), split=_split))
