"""G4 RED tests -- sprint 2026-08-05-defs-core-follow-on-2, gate G4
("citation pin-cite stack corruption"). Planner: plan1 (also owns G2 in
the sibling module `test_definition_links_core_follow_on_2_g2_period_
style_markers.py` -- ONE designer for both per the sprint contract, so
the fixes compose instead of colliding).

**The defect.** `resolve_unit_path`'s "replaced" loop (us_profile.py,
approx lines 1230-1236) treats ANY token that shape-matches an already-
OPEN ancestor's kind as "the drafter returned to that level" -- it
truncates the stack to that level and overwrites the value, with NO check
of what PRECEDES the token. A citation pin-cite (`"Section 58-9-576(C)"`,
`"under subsection (1) of this section"`) is shape-indistinguishable from
a genuine marker, so it silently resets/corrupts the stack exactly like a
real structural return would.

**Four real, corpus-verified corruption shapes (independently reproduced
by this Planner against the LIVE `resolve_unit_path`, not copied from a
panel branch -- see the report for the full trace of each):**

1. **SC `Section 58-9-576(C)`** (`STATE_SC_T58_C9_A5_S58-9-576`, real
   text): a "Section N(X)" citation TO THE SAME SECTION (self-citation,
   real drafting idiom) resets the stack to `[upper_alpha:'C']`,
   discarding the genuinely-open `(C)(2)(b)` context. The genuine
   `(c)(i)` markers that follow ("(c)(i) As used in this subsection,
   "voice service" means...") are then silently I9-SKIPPED (they no
   longer match the truncated stack's one remaining ancestor). Measured:
   `resolve_unit_path` at the "voice service" quote offset returns
   `(upper_alpha:'C',)` -- ONE step -- when the document's genuine
   structure is FOUR levels deep, `(C)(2)(c)(i)`. This row ALSO contains
   a compound citation form, `"subsection (C)(2)(c)"` (structural word +
   a CHAIN of 3 parenthesized tokens joined by nothing but immediate
   adjacency), and elsewhere `"(A)(1) or (A)(2)"` (chain tokens joined by
   the connector " or " -- NOT strictly back-to-back parens). This
   Planner's prototype discriminator (structural-word-precedes-paren)
   handles the self-citation and the adjacent chain cleanly but needed a
   connector-tolerant chain-continuation rule to fully resolve the " or "
   form -- flagged explicitly below as an implementation hazard, not
   silently solved.
2. **TX `Section 37.007(a)(1)`** (`STATE_TX_Ced_C37_S37.0021`, real
   text): a citation to a DIFFERENT section entirely ("weapon" includes
   any weapon described under Section 37.007(a)(1)") relabels the TOP-
   LEVEL unit itself -- not just the depth. Before the citation, genuine
   context is subsection `(f)`; after it, the stack's top-level VALUE is
   silently overwritten to `'a'` (from the citation's own `(a)`), so the
   row's OWN subsequent genuine `(1)`/`(2)` sub-items resolve under the
   WRONG parent: `(lower_alpha:'a', digit:'2')` instead of the correct
   `(lower_alpha:'f', digit:'2')`. This is the sprint doc's "non-empty
   WRONG paths, worse than the empty-path S-R16 class" -- a subsequent
   containment/scope check against this path would silently pass or fail
   against a unit that was never actually open.
3. **ME `47 United States Code, Section 522(13)`**
   (`STATE_ME_T30-A_P2_C141_S3010`, real text): a federal citation's
   pin-cite appears BEFORE any genuine parenthesized OR period-style
   marker in the entire document. `resolve_unit_path` fabricates
   `(digit:'13',)` out of thin air and holds that WRONG non-empty value
   across the ~2,100 characters between the citation and the document's
   first genuine top-level marker ("1. Credits and refunds..."). The
   correct answer for that entire span is the EMPTY path (no genuine
   sub-article unit is open yet) -- today's actual output is a
   fabricated, plausible-looking, WRONG unit.
4. **OR "under subsection (1) of this section"**
   (`STATE_OR_T22_C238_S238.300`, real text -- the S-R14-validation-row
   latch, program-manager-relayed evidence, independently reproduced
   here): an ORDINARY IN-PROSE CROSS-REFERENCE, not a citation to a
   numbered section at all -- no "Section"/"§"/USC/CFR anywhere near it.
   Genuine context at this point is `(digit:'2', lower_alpha:'a')`; the
   bare structural word "subsection" immediately before "(1)" latches
   the top-level digit down to `'1'`, discarding the correct `'2'`. This
   is a DIFFERENT SHAPE from cases 1-3 (no citation-looking section
   number at all) -- a discriminator built only around "Section N"/"§"/
   USC/CFR patterns will NOT catch it. This row also shows the SAME
   mechanism firing on `"paragraph (b) of this subsection"` (a FORWARD
   reference to a paragraph not yet opened) earlier in the same
   sentence -- both must be ignored for the correct answer to hold.

**The fix this item specifies:** a parenthesized (or, after G2 ships,
period-style) token is treated as a GENUINE marker UNLESS it is
immediately preceded (skipping only whitespace) by CITATION/CROSS-
REFERENCE CONTEXT -- defined as a structural-unit word (section,
subsection, paragraph, subparagraph, part, subpart, chapter, article,
division, subdivision, title -- the SAME closed vocabulary this file
already uses for the unrelated D-CF guard, `_STRUCTURAL_UNIT_WORDS` in
`find_term_uses`; kept as an independent, non-coupled discriminator per
that guard's own documented "no coupling between the two features" design
note, but sharing the SAME semantic story per this sprint's requirement
for one coherent token-acceptance narrative) OR a `find_citations`-shaped
span (e.g. "Section 37.007", "47 United States Code, Section 522")
immediately before the token. Once a token is recognized as citation
context, subsequent CHAINED tokens (adjacent, or joined by a short
connector like " or "/" and "/", ") are ALSO ignored as part of the same
citation, until the chain breaks (real evidence: SC's "(A)(1) or
(A)(2)" -- flagged above as needing connector tolerance, not just
strict back-to-back adjacency).

**Validated by this Planner via a throwaway prototype** (not committed;
reuses the real `_marker_matches_kind`/ladder constants, only the
accept/reject decision is new) against all 4 real rows above: recovers the
exact correct path on 3 of 4 real cases end-to-end (TX, ME, OR exact) and
gets SC's SHAPE right (correct kinds/levels, `upper_alpha, digit,
lower_alpha, lower_roman`) but the top-level VALUE needs the connector-
chain fix above (handling `"(A)(1) or (A)(2)"`) to land exactly on 'C'
instead of drifting to 'A' -- and reproduces TODAY's values byte-for-byte
on 2 real non-corrupted paren-style rows (SC single-level, TX
single-level, both unchanged). See this Planner's report for the full
per-token trace.

**What does NOT change:** the ladder-selection mechanism (still exactly
3 named ladders, chosen from the first ACCEPTED marker's shape); the
replace-loop's fundamental "return to an open ancestor" semantics for
GENUINE markers (only the acceptance gate is new); G2's period-style
marker recognition (a separate sibling item -- see the G2 test module).

**This module carries cases 1-2 (SC, TX) plus the module docstring.**
Cases 3-4 (ME, OR) and the non-regression guard live in the sibling
module `test_definition_links_core_follow_on_2_g4_pincite_stack_cases_3_
4.py` -- split purely for this program's 300-line-per-file style gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.profiles import get_profile
from app.definition_links.sections import Article as MatcherArticle

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load_rows(filename: str) -> dict[str, dict]:
    rows = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def core_rows() -> dict[str, dict]:
    return _load_rows("core_follow_on_2_g2_g4_rows.json")


@pytest.fixture()
def us_sc():
    return get_profile("US-SC")


@pytest.fixture()
def us_tx():
    return get_profile("US-TX")


# --- Case 1: SC self-citation resets the stack, genuine (c)(i) skipped ---


def test_sc_section_self_citation_does_not_reset_the_stack(core_rows, us_sc):
    """Real `STATE_SC_T58_C9_A5_S58-9-576`. Genuine structure at the
    "voice service" defining quote is FOUR levels deep: subsection (C),
    item (2), sub-item (c), sub-sub-item (i) -- i.e. `"(c)(i) As used in
    this subsection, "voice service" means..."`. Today, the earlier
    self-citation `"Section 58-9-576(C)"` (and the compound citation
    `"subsection (C)(2)(c)"` just before it) resets the stack down to a
    single `(upper_alpha:'C',)` step, and the genuine (c)(i) markers are
    then silently I9-skipped (they no longer shape-match the truncated
    stack's one remaining ancestor). Confirmed today's actual output is
    exactly `(upper_alpha:'C',)`, not the correct 4-level path."""
    row = core_rows["STATE_SC_T58_C9_A5_S58-9-576"]
    text = row["text"]
    anchor = '"voice service" means'
    assert anchor in text, "fixture text changed -- SC voice-service anchor no longer present"
    assert "Section 58-9-576(C) prior to January 1, 2016" in text, (
        "fixture text changed -- the SC self-citation pin-cite is no longer present verbatim"
    )
    article = MatcherArticle(
        number="58-9-576", heading="Election by LEC", body=text, chapter="9"
    )

    path = us_sc.resolve_unit_path(article, char_offset=text.index(anchor))

    kinds = tuple(step.kind for step in path)
    values = tuple(step.value for step in path)
    assert kinds == ("upper_alpha", "digit", "lower_alpha", "lower_roman"), (
        f"expected the genuine 4-level (C)(2)(c)(i) path; got kinds={kinds!r} "
        f"(full path {path!r}) -- the citation pin-cite corrupted the stack"
    )
    assert values == ("C", "2", "c", "i"), values


# --- Case 2: TX external-section citation relabels the top-level unit ----


def test_tx_external_section_citation_does_not_relabel_the_open_subsection(core_rows, us_tx):
    """Real `STATE_TX_Ced_C37_S37.0021`. Genuine context is subsection
    `(f)`; the row's own text reads: `"(f) For purposes of this
    subsection, "weapon" includes any weapon described under Section
    37.007(a)(1). ... (1) the student possesses a weapon; and (2) the
    confinement..."`. "Section 37.007" cites a DIFFERENT, external
    section -- its own `(a)(1)` pin-cite must not touch this row's stack
    at all. Today, the pin-cite silently relabels the top-level VALUE
    from 'f' to 'a', so the row's own genuine "(1)"/"(2)" sub-items
    resolve under the WRONG parent. Confirmed today's actual output at
    the "(1) the student possesses" offset is
    `(lower_alpha:'a', digit:'1')`, not the correct `(lower_alpha:'f',
    digit:'1')` -- non-empty, plausible-looking, and wrong."""
    row = core_rows["STATE_TX_Ced_C37_S37.0021"]
    text = row["text"]
    assert "Section 37.007(a)(1)" in text, (
        "fixture text changed -- the TX external-section pin-cite is no longer present verbatim"
    )
    anchor = "the student possesses a weapon"
    assert anchor in text
    article = MatcherArticle(
        number="37.0021", heading="Use of confinement", body=text, chapter="37"
    )

    path = us_tx.resolve_unit_path(article, char_offset=text.index(anchor))

    assert len(path) == 2, f"expected a 2-level (f)(1) path; got {path!r}"
    assert path[0].kind == "lower_alpha"
    assert path[0].value == "f", (
        f"top-level unit was relabeled by the external citation's own (a) pin-cite; "
        f"expected 'f' (the row's genuinely open subsection), got {path[0].value!r}"
    )
    assert path[1].kind == "digit"
    assert path[1].value == "1"

