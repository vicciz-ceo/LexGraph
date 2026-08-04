"""Rule: M17 spelling-variant audit -- quote-first orthographic/register
variants of already-known trigger phrases the corpus genuinely uses,
never captured because the quote-first grammar was only ever built for
one spelling (sprint 2026-08-04-defs-il, Phase C, ruling M17).

A corpus-derived, shape-based sweep (every `<noun phrase> <demonstrative>`
occurrence immediately before a quote, for `<demonstrative>` in the
closed set `{זה, זו, זאת, אלה, אלו}` -- see the sprint log's Phase C
round 3 entry for the full methodology and per-phrase corpus counts)
found real, nonzero, currently-uncaptured quote-first occurrences for
every trigger below. Two groups:

**Group 1 -- article/subsection/paragraph/item-level spelling variants,
not law-wide** (each disjoint in TEXT from every existing trigger this
sprint ships -- e.g. `בתקנה זאת` ends `זאת`, the existing `בתקנה זו`
ends `זו`; `לענין פרט זה` inserts `פרט` between `לענין` and `זה`, so it
is never a substring of the existing 2-word `לענין זה` -- a given real
occurrence can therefore only ever match ONE trigger, never two with
possibly-different scopes):
  - `בתקנה זאת` (זאת register of `בתקנה זו`) -> `"local"` (D-Q1:
    תקנה-family is article-level).
  - `בפסקה זאת` / `לענין פסקה זאת` / `לעניין פסקה זאת` (זאת register of
    `בפסקה זו`) -> `"paragraph"`.
  - `בתקנת משנה זאת` (זאת register of `בתקנת משנה זו`) -> `"subsection"`.
  - `בפסקה משנה זו` (ה-spelling of the construct-state `בפסקת משנה זו`
    -- Hebrew smichut normally drops the ה for ת before a following
    noun; this corpus instance keeps it) -> `"subsection"`.
  - `לענין פרט זה` / `לעניין פרט זה` (the missing 3-word sibling of the
    already-known 2-word `בפרט זה`, the SAME 2-word-to-3-word pattern
    every other trigger in this sprint already has) -> `"item"`.

**Group 2 -- law-wide instrument words, quote-first grammar.** M16 (round
2) added these words to the LIST-shape scope-inference vocabulary only;
the quote-first grammar was never extended to include them at all (e.g.
`בחוק זה` has 45 real quote-first occurrences, `בתקנות אלה` has 23).
Reuses `il_trigger_grammar.law_wide_preamble_phrases()` verbatim -- the
SAME measured vocabulary the list-shape rules use (program efficiency
directive: one vocabulary, two grammars, not two separately-maintained
lists) -- so every `<ב-word>`/`לענין <word>`/`לעניין <word>` law-wide
phrase is covered here too, stamping `scope="law-wide"`.

Per ruling M17, residuals that are genuinely NOT a spelling variant of an
existing trigger (e.g. `לענין הגדרה זו` -- a nested-definition
cross-reference, not a scope-container trigger; `בכלל זה` -- a false
friend meaning "including this"; the `לצורך`-prefixed third-preposition
family) are deliberately NOT built here -- see the sprint log's Phase C
round 3 entry for the full residual list with counts.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.il_trigger_grammar import (
    extract_quote_first_candidates,
    law_wide_preamble_phrases,
    quote_first_re,
)
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

# Group 1: (trigger alternation, scope) pairs, each disjoint in text from
# every other trigger this sprint registers (see module docstring).
_GROUP_1_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"בתקנה זאת", "local"),
    (r"(?:בפסקה זאת|לענין פסקה זאת|לעניין פסקה זאת)", "paragraph"),
    (r"בתקנת משנה זאת", "subsection"),
    (r"בפסקה משנה זו", "subsection"),
    (r"(?:לענין|לעניין) פרט זה", "item"),
)

_GROUP_1_RULES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (quote_first_re(alt), scope) for alt, scope in _GROUP_1_PATTERNS
)

# Group 2: the SAME measured law-wide vocabulary the list-shape rules use
# (`il_list_shape_scope.py`), applied to the quote-first grammar M16
# never touched.
_LAW_WIDE_TRIGGER_RE = quote_first_re(
    "(?:" + "|".join(law_wide_preamble_phrases()) + ")"
)


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    results: list[DefinitionCandidate] = []
    for pattern, scope in _GROUP_1_RULES:
        candidates = extract_quote_first_candidates(article_body, pattern, scope=scope)
        if scope == "subsection":
            for candidate in candidates:
                candidate.scope_value = None
        results.extend(candidates)
    results.extend(
        extract_quote_first_candidates(article_body, _LAW_WIDE_TRIGGER_RE, scope="law-wide")
    )
    return results


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
