"""Regression pins for sprint 2026-08-04-defs-us-multiterm, ruling M-R16:
the Developer's leading-quote guard in `_parse_block`
(`rules/us_inline_parenthetical.py`) -- ratified by the sprint manager as
the correct implementation of M-R12 (union semantics: a `TermClauseRule`
must stay silent on a shape baseline's own per-block pass already
handles) -- was unpinned. Pinned here in BOTH directions.

```python
_LEADING_QUOTE_TERM_RE = re.compile(r'^[“"]([^”"]+)[”"]')

def _parse_block(block: str) -> list[DefinitionCandidate]:
    candidates = _apposition_candidates(block, scope="law-wide")
    leading_term = _leading_quote_term(block)
    for candidate in _cross_reference_candidates(block, scope="law-wide"):
        if candidate.terms and candidate.terms[0] == leading_term:
            continue
        candidates.append(candidate)
    return candidates
```

Live-path discipline: both pins drive the REAL, current
`USProfile.extract_definitions_from_section` -- the dispatching profile
METHOD, reached via `get_profile(...)` -- never the bare free function and
never a private import of `_parse_block` itself (repo memory: a test
proving a rule is merely *registered*, or reaching for a private internal
instead of the public seam, proves nothing about the real dispatching
path -- rulings M-R9/M-R11).

**HONEST FINDING, not pinned as a test here (Task 1 asked specifically for
the guard's own block-level behavior; this is a DIFFERENT, newly-discovered
defect one layer up, reported to the sprint manager rather than silently
worked around or silently added as an unrequested third test):** running
the REAL, FULL, unmodified `STATE_TX_Cgv_C2009_S2009.003` row (not an
excerpt) through `get_profile("US-TX").extract_definitions_from_section(...)`
today produces TWO candidates for `"Governmental body"`, not one --
verified live, 2026-08-05. Root cause is NOT a gap in the leading-quote
guard itself (which correctly suppresses the SAME block's own duplicate,
proven by the pin below) -- it is an INTERACTION with ruling U-R10's
TX-scoped parent-redirect `EntrySplitterRule`
(`rules/us_multiterm_shared_clause.py`'s `_split_parent_redirect_whole_
text`, registered `jurisdiction_codes=("US-TX",)`): that rule re-contributes
the ENTIRE section text as one extra block (needed so its OWN parent+
children shape can be seen together), and when `_parse_block` runs on THAT
whole-text block, `_leading_quote_term(whole_text)` reads the WHOLE
TEXT's own leading token ("In this chapter:", not a quote at all -> `None`)
-- so the guard's per-block comparison (`candidate.terms[0] == leading_term`)
never catches "Governmental body" reappearing deep inside that same
whole-text block via `_cross_reference_candidates`. The guard was written
and ratified against the ORIGINAL finding-4 shape (one block, one term) and
is provably correct for that shape (the pin below); it was never evaluated
against the LATER-landed TX EntrySplitterRule's whole-text contribution,
which reintroduces exactly the double-emission M-R12 was meant to prevent,
through a different door. This is reported here for the sprint manager's
disposition (a new ruling, or folded into an existing one) -- not
unilaterally fixed, not unilaterally test-pinned as a failure, since that
is not what either of this session's two authorized tasks asked for.

Below: the guard's OWN claim, pinned precisely, using a real, verbatim,
anchor-sliced excerpt of `STATE_TX_Cgv_C2009_S2009.003`'s own text (`re.
search(r'\\(2\\) .*?552\\.003\\.', real_text, re.DOTALL)` -- the same
"never hand-retyped, always sliced from the real vendored text" discipline
`test_definition_links_e1_pointer_reference_capture.py`'s `_sentence()`
helper already established) containing ONLY the `"Governmental body"`
definition and none of the row's OTHER content (specifically, none of the
parent-redirect trigger phrase that feeds the EntrySplitterRule above) --
isolating the guard's own block-level correctness from the separate,
newly-found EntrySplitterRule interaction.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.definition_links.profiles import get_profile

_F5_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "multiterm_f5_rows.json"
)
_QA_U4_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "qa_u4_finding_rows.json"
)


def _load(path: Path) -> dict[str, dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def test_tx_governmental_body_leading_quote_block_yields_exactly_one_candidate():
    """Under-suppression pin: baseline's own `_leading_quote_candidate`
    already correctly captures `"Governmental body"` for this block (its
    OWN leading quote is immediately followed by the cross-reference
    idiom) -- the guard must stop `_parse_block`'s own `TermClauseRule`
    pass from ALSO emitting a second candidate for the exact same term
    from the exact same block. Excerpt anchor-sliced from the real,
    already-vendored `STATE_TX_Cgv_C2009_S2009.003` row (see module
    docstring for why an excerpt, not the full row, isolates the guard's
    own claim)."""
    tx_row = _load(_F5_FIXTURE_PATH)["STATE_TX_Cgv_C2009_S2009.003"]
    match = re.search(r"\(2\) .*?552\.003\.", tx_row["text"], re.DOTALL)
    assert match is not None, "anchor pattern did not match the real row text"
    excerpt = match.group(0)
    assert excerpt == '(2) "Governmental body" has the meaning assigned by Section 552.003.'

    profile = get_profile("US-TX")
    scope = profile.determine_scope(excerpt)
    candidates = profile.extract_definitions_from_section(excerpt, scope=scope)
    governmental_body = [c for c in candidates if c.terms == ("Governmental body",)]
    assert len(governmental_body) == 1, (
        f'expected EXACTLY ONE candidate for "Governmental body" -- baseline\'s own '
        f"leading-quote parse already captures it correctly for this block, and the "
        f"guard (`_leading_quote_term` comparison in `_parse_block`) must suppress "
        f"`_cross_reference_candidates`' own would-be duplicate. Got "
        f"{len(governmental_body)}: {governmental_body!r} (all candidates: "
        f"{[c.terms for c in candidates]!r})"
    )


def test_dc_parent_non_leading_quote_block_is_still_captured():
    """Over-suppression pin: DC's `"parent"` sits inside a block whose OWN
    leading content is `'(6) Parent. -- The term "parent" has the meaning
    given that term in section 8101...'` -- NOT a leading quote (baseline's
    `_LEADING_QUOTE_RE` never matches this block at all, so baseline
    produces NOTHING for it). The guard's leading-quote comparison must be
    a no-op here (`_leading_quote_term(block) is None`, never equal to any
    real term), so the cross-reference candidate must still be captured,
    not silently swallowed by an over-eager guard. Real, full, unmodified
    row `STATE_DC_T38_C18N_S38-1853.13` (already vendored, used by QA
    finding 4 -- see `test_multiterm_qa_u4_findings.py` for its own
    provenance)."""
    dc_row = _load(_QA_U4_FIXTURE_PATH)["STATE_DC_T38_C18N_S38-1853.13"]
    profile = get_profile("US-DC")
    scope = profile.determine_scope(dc_row["text"])
    candidates = profile.extract_definitions_from_section(dc_row["text"], scope=scope)
    parent = [c for c in candidates if c.terms == ("parent",)]
    assert len(parent) == 1, (
        f'expected "parent" to be captured EXACTLY ONCE (not silently swallowed by '
        f"the leading-quote guard, since this block does not start with a quote at "
        f'all -- there is no baseline candidate for the guard to avoid duplicating). '
        f"Got {len(parent)}: {parent!r} (all candidates: {[c.terms for c in candidates]!r})"
    )
