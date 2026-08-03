"""RED tests for sprint 2026-08-04-defs-us-multiterm, family 6 (dossier §2 +
§6 addendum): `("Term")` apposition abbreviations with NO means-idiom
following -- rejected even by the inline fallback's idiom-gap check
(`pipeline._MEANS_IDIOM_GAP_RE` requires literal "means"/"shall mean"/"has
the meaning"; a bare naming apposition like `(the "Act")` has none of
those).

Fixtures: REAL rows vendored verbatim at `backend/tests/fixtures/
us_statutes/inline_parenthetical_sample_rows.json` (see that directory's
`README.md` for provenance; the OK row is a documented TRIMMED excerpt of
a much larger real row -- see the fixture's own `_fixture_note` field).

This file covers ONLY the extractor-level behavior on a body in isolation
(the same functions `pipeline.py` Stage 2 calls). The OR cross-reference
row (`STATE_OR_T41_C496_S496.716`) is deliberately NOT tested here --
its root cause is a Definitions-HEADING-gate miss (family 1, owned by
sprint `2026-08-04-defs-us-scoped-inline`) COMBINED WITH core-scope's C3
gate (pipeline.py's non-Definitions-section branch is not yet profile-
dispatched), not an idiom-gap rejection -- confirmed live: the idiom-gap
regex (`_MEANS_IDIOM_GAP_RE`) already matches "has the meaning" and
correctly extracts all 5 of this row's cross-reference terms when run
directly against its body; the section is simply never reached by any
extractor in the real pipeline today. See
`backend/tests/integration/test_multiterm_f6_blocked_on_core_seam.py::
test_or_cross_reference_style_definitions_resolve` for the full-pipeline
(production entry point) proof of this row, and this sprint's log for the
`PANEL QUESTION` about whether a pointer-only definition (no substantive
text of its own) should count as "captured" once that heading gate is
fixed.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.pipeline import (
    _MEANS_IDIOM_GAP_RE,
    _QUOTE_TERM_RE,
    _determine_scope,
    _extract_inline_quoted_definitions,
)
from app.definition_links.us_profile import extract_definitions_from_section

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "inline_parenthetical_sample_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def _extract_both_ways(text: str) -> list:
    scope = _determine_scope(text)
    candidates = list(extract_definitions_from_section(text, scope=scope))
    candidates += _extract_inline_quoted_definitions(text, scope=scope)
    return candidates


# --- NH STATE_NH_TXXVII_C301-B_S1 -- genuine F6, no means-idiom at all ----
# 'This act may be cited as the "New Hampshire Decentralized Autonomous
# Organization Act" (the "Act").' -- a short-title apposition: "Act" is
# unambiguously being defined as shorthand for the long name, but there is
# no "means"/"shall mean"/"has the meaning" anywhere in the sentence for
# `_MEANS_IDIOM_GAP_RE` to anchor on.


def test_nh_s1_short_title_apposition_has_no_means_idiom_to_anchor_on():
    """Characterizes WHY this is rejected today (not just THAT it is): the
    quoted term "Act" is never followed by a recognized defining idiom
    within the bounded gap."""
    row = _load_rows()["STATE_NH_TXXVII_C301-B_S1"]
    text = row["text"]
    quote_matches = list(_QUOTE_TERM_RE.finditer(text))
    assert len(quote_matches) >= 1
    for m in quote_matches:
        gap = text[m.end() : m.end() + 200]
        assert _MEANS_IDIOM_GAP_RE.match(gap) is None, (
            f"expected NO means-idiom to follow quoted term {m.group(1)!r} in "
            f"this apposition-only sentence; regex unexpectedly matched"
        )


def test_nh_s1_act_apposition_is_extracted_as_a_definition():
    row = _load_rows()["STATE_NH_TXXVII_C301-B_S1"]
    candidates = _extract_both_ways(row["text"])
    all_terms = {t for c in candidates for t in c.terms}
    assert "Act" in all_terms, (
        f"the short-title apposition '(the \"Act\")' -- a genuine, reusable "
        f"abbreviation-definition -- produces ZERO candidates from either "
        f"extractor today (idiom-gap rejection, family 6). Got "
        f"candidates={candidates!r}"
    )


# --- OK STATE_OK_T74_S74-6106 -- FALSE-POSITIVE GUARD, not a RED test -----
# TRIMMED excerpt of the Red River Boundary Compact (see fixture's
# `_fixture_note`): '...comprised of the following repeating characters
# ("-..-") east from the body of Lake Texoma...' -- a parenthesized quoted
# string that names DASH CHARACTERS used to draw a line on a map, not a
# defined legal term. This ALREADY correctly produces zero candidates
# today (nothing in this family exists yet to over-fire) -- pinned here as
# a forward acceptance guard: whatever new apposition-detection logic gets
# built for the NH case above MUST NOT start matching this shape. Per
# U-R1-style discipline ("captured" must mean captured CLEANLY), a
# permissive rule (e.g. "any `(\"X\")` is a definition") would turn this
# into a false positive; the real rule needs a narrower trigger (a genuine
# reusable named-entity apposition, not any parenthetical quote
# whatsoever) -- see this sprint's log, `PANEL QUESTION` re: F6
# precision/recall trade-off, P-R2.


def test_ok_boundary_marker_apposition_is_not_treated_as_a_definition():
    row = _load_rows()["STATE_OK_T74_S74-6106"]
    candidates = _extract_both_ways(row["text"])
    all_terms = {t for c in candidates for t in c.terms}
    assert "-..-" not in all_terms
    assert "Reference Map" not in all_terms
