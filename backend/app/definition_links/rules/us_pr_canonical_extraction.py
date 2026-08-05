"""PR's own registered `EntrySplitterRule`/`TermClauseRule` pair (sprint
2026-08-04-defs-us-pr, cycle-9 item 33, gate P2's canonical half). Makes
`pr_profile.extract_definitions_from_section` -- and, for the first time,
its `_UNQUOTED_TERM_DASH_RE` pattern (M-R14/M-R15/M-R16) -- reachable
through `USProfile.extract_definitions_from_section`, the seam
`pipeline.py` actually calls for a canonical Definiciones section.

## Design (cycle-9 Planner, full derivation in the panel log)

`USProfile.extract_definitions_from_section` (`us_profile.py`) unions
baseline's own numbered blocks (`_split_into_numbered_blocks`, `\\n`-based
-- PR bodies have zero newlines, so this is a near-total no-op for PR, see
below) with every registered `EntrySplitterRule`'s own blocks for this
profile's code, then runs baseline's `_leading_quote_candidate` AND every
registered `TermClauseRule.parse` over EVERY block in that union (baseline
or rule-contributed alike) -- zero-miss, no rule suppresses another.

Two real corpus findings force the shape below (both verified live,
own scripts, not by inspection alone):

1. **Baseline's `_leading_quote_candidate` collision.** If this
   `EntrySplitterRule` naively returned the raw section text verbatim,
   and that text happens to start with a quote character (1/633
   canonical rows), baseline's OWN per-block parser -- which runs
   unconditionally on every block in the union, including rule-
   contributed ones -- would fabricate a candidate whose
   `definition_text` swallows the entire rest of the body. Prefixing the
   contributed block with `_SENTINEL`, a control character that is
   neither of baseline's own `_LEADING_QUOTE_RE` quote characters
   (`“`/`"`) and never appears in real scraped PR statute prose, closes
   this off by construction: `_leading_quote_candidate` never matches a
   sentinel-prefixed block.
2. **`TermClauseRule.parse(block) -> list[DefinitionCandidate]` has no
   `scope` parameter** (the frozen `rules/registry.py` shape; confirmed
   against core's own dispatch-proof test, which hardcodes
   `scope="law-wide"` literally inside its probe lambda -- the shipped
   contract, not an oversight). A canonical section's scope is a
   SECTION-level property `pipeline.py` computes once
   (`profile.determine_scope(body)`) and passes into
   `extract_definitions_from_section` as a keyword-only argument the
   registered rule never receives. So `EntrySplitterRule.split` passes
   the FULL, unmodified section body (as the un-prefixed part of its one
   block), and `_parse_canonical_block` below independently RE-DERIVES
   scope from that SAME recovered text using
   `pr_profile.detect_pr_chapter_scope` -- the identical function item
   32's `ScopeKindRule` uses (not a re-implementation) -- falling back to
   `"law-wide"` when it has no opinion, mirroring
   `USProfile.determine_scope`'s own fallback (baseline's English chapter
   check is a no-op on genuine Spanish text, so this reproduces
   `pipeline.py`'s own separately-computed value exactly, verified
   corpus-wide against all 633 canonical rows).

**`_parse_canonical_block` only acts on ITS OWN sentinel-carrying block.**
`TermClauseRule.parse` is invoked by `USProfile.extract_definitions_from_
section` on EVERY block in the union -- including baseline's own numbered
blocks, which never carry the sentinel. Guarding on the sentinel's
presence (returning `[]` for any block that lacks it) keeps this rule from
also re-parsing baseline's own blocks a second time, and is what makes the
P5 two-sided English-regression proof hold: a real English row's baseline
blocks reach this function too, and must come back empty.

## Full-corpus equivalence + live precision (own measurement, this cycle)

Registered these exact rules and ran the LIVE path against all 633
canonical rows, diffing against the already-tested DIRECT
`pr_profile.extract_definitions_from_section` call: 612/633 (96.7%) rows
produce byte-identical term sets; the remaining 21/633 (3.3%) are exactly
the baseline-collision rows named in finding 1 above (see `### ESCALATION`
below). Live canonical-path precision of `_UNQUOTED_TERM_DASH_RE`
(restricted to the 633 canonical rows, not the ~33-53% whole-corpus
projection): 91.7% (22/24 brand-new candidates hand-verified genuine).
Full derivation in the sprint contract / panel log's cycle-9 Planner entry.

## ESCALATION -- pre-existing, registration-independent defect (not fixed
here; pinned as an `xfail(strict=False)`, see
`test_pr_profile_canonical_extraction_live_cycle9.py`)

Shared, core-owned `us_profile._split_into_numbered_blocks` splits on
`text.split("\\n")` -- for a PR body (zero newlines corpus-wide) this
degenerates to ONE "line". When that one line's own START matches
baseline's `_entry_start_remainder` (a bare `(a)`/`(1)`-style marker
immediately at position 0 -- 32/633 canonical rows) AND what follows the
marker starts with a quote character (21/633), baseline's own
`_leading_quote_candidate` fabricates a candidate whose `definition_text`
is the raw remainder of the WHOLE body (up to ~32,000 chars, spanning
every other term's own definition). Reproducible TODAY with ZERO PR rules
registered anywhere -- item 31 (`HeadingRule`) alone, independent of this
module, already exposes it the moment `pipeline.py`'s `is_definitions_
heading` gate lets one of these 21 rows reach `extract_definitions_from_
section` at all. This module's sentinel design fully protects its OWN
contributed block from this collision (confirmed:
`STATE_PR_LEY_123_2020_ART2`, the one row whose raw body itself starts
with a quote character, is unaffected -- produces the correct candidates,
byte-identical to the direct call) but cannot and does not protect against
baseline's SEPARATE, unconditional call on the SAME raw text -- no
rule-level lever exists to suppress or out-prioritize baseline's own
candidate in `pipeline.py`'s first-candidate-per-key dedup. Fixing this
requires an edit to shared, core-owned `us_profile.py`/`pipeline.py`,
outside this panel's write-set -- routed to program level, tracked on the
sprint contract's Residual ledger, not worked around here.
"""

from __future__ import annotations

from app.definition_links import pr_profile
from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    EntrySplitterRule,
    TermClauseRule,
    register_entry_splitter_rule,
    register_term_clause_rule,
)

# A single control character: never one of baseline's own `_LEADING_QUOTE_RE`
# quote characters (`“`/`"`), and never appears in real scraped PR
# statute prose -- prefixed onto the whole section body so
# `_parse_canonical_block` below can recognize (and act ONLY on) the one
# block this `EntrySplitterRule` itself contributed, out of every block
# `USProfile.extract_definitions_from_section` unions together. See the
# module docstring, finding 1, for the collision this protects against.
_SENTINEL = "\x00"


def _split_full_body(text: str) -> list[str]:
    """The whole section body, unmodified, as this rule's one contributed
    block -- sentinel-prefixed so baseline's own `_leading_quote_candidate`
    (which runs on every block in the union, this one included) never
    mistakes it for a leading-quoted entry. See the module docstring for
    why the FULL body (not pre-split into per-marker blocks) is required:
    the paired `_parse_canonical_block` below needs the complete, original
    text to re-derive scope the same way `determine_scope` would."""
    return [_SENTINEL + text]


def _parse_canonical_block(block: str) -> list[DefinitionCandidate]:
    """Strip the sentinel and delegate to `pr_profile.extract_definitions_
    from_section`, independently re-deriving scope from the recovered text
    (see module docstring, finding 2). Returns `[]` for any block that
    does not carry the sentinel -- i.e. every block OTHER than the one
    `_split_full_body` above contributed (baseline's own numbered blocks
    are also passed to this function by `USProfile.extract_definitions_
    from_section`'s union loop, and must be left untouched)."""
    if not block.startswith(_SENTINEL):
        return []
    text = block[len(_SENTINEL) :]
    scope = pr_profile.detect_pr_chapter_scope(text) or "law-wide"
    return pr_profile.extract_definitions_from_section(text, scope=scope)


register_entry_splitter_rule(
    EntrySplitterRule(jurisdiction_codes=("US-PR",), split=_split_full_body)
)
register_term_clause_rule(
    TermClauseRule(jurisdiction_codes=("US-PR",), parse=_parse_canonical_block)
)
