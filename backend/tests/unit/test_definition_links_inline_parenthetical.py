"""RED tests for sprint 2026-08-04-defs-us-multiterm, family 6 (dossier §2 +
§6 addendum): `("Term")` apposition abbreviations with NO means-idiom
following -- rejected even by the inline fallback's idiom-gap check
(`us_profile._MEANS_IDIOM_GAP_RE`, moved out of `pipeline.py` and made
PRIVATE to `us_profile.py` by core's C3 gate -- reached here only through
the public `extract_definitions_from_section(..., heading_was_derived=
True)` seam, per sprint `2026-08-04-defs-us-multiterm` ruling M-R9, never
by importing the relocated private symbol -- requires literal
"means"/"shall mean"/"has the meaning"; a bare naming apposition like
`(the "Act")` has none of those).

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
regex (`us_profile._MEANS_IDIOM_GAP_RE`) already matches "has the meaning" and
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

from app.definition_links.profiles import get_profile
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


def _profile_for(row: dict):
    # Sprint 2026-08-04-defs-us-multiterm, ruling M-R9: repoint to the
    # PUBLIC seam (`get_profile(...).determine_scope(...)`), the same
    # call shape `pipeline.py` itself now uses -- not a new private
    # import of whatever internal free function replaced
    # `pipeline._determine_scope`. `USProfile.determine_scope` ignores
    # `self.code` entirely, so this cannot change the returned value; the
    # row's own state code is used anyway for documentation fidelity.
    return get_profile("US-" + row["act_id"].split("_")[1])


def _extract_both_ways(row: dict) -> list:
    text = row["text"]
    profile = _profile_for(row)
    scope = profile.determine_scope(text)
    # Sprint 2026-08-04-defs-us-multiterm, ruling M-R9: the old code called
    # `pipeline._extract_inline_quoted_definitions` directly (now private
    # to `us_profile.py`, moved there by core's C3 gate). Repointed to the
    # PUBLIC `extract_definitions_from_section(..., heading_was_derived=
    # True)` seam instead of importing the relocated private symbol --
    # `heading_was_derived=True` is the documented, public way to force
    # the exact same inline-quoted fallback path (verified live for both
    # fixture rows this sprint: neither has any "(N)"-block marker, so the
    # block splitter always yields nothing and the fallback always fires;
    # `extract_definitions_from_section(text, scope=scope,
    # heading_was_derived=True)` therefore returns THE SAME candidate list
    # the old two-call union produced -- no expected value changed, only
    # the access path).
    return list(extract_definitions_from_section(text, scope=scope, heading_was_derived=True))


# --- NH STATE_NH_TXXVII_C301-B_S1 -- genuine F6, no means-idiom at all ----
# 'This act may be cited as the "New Hampshire Decentralized Autonomous
# Organization Act" (the "Act").' -- a short-title apposition: "Act" is
# unambiguously being defined as shorthand for the long name, but there is
# no "means"/"shall mean"/"has the meaning" anywhere in the sentence for
# `us_profile._MEANS_IDIOM_GAP_RE` to anchor on.
#
# Sprint 2026-08-04-defs-us-multiterm, ruling M-R10 (deletion, not a
# reformulation): this section used to also carry
# `test_nh_s1_short_title_apposition_has_no_means_idiom_to_anchor_on`, a
# white-box characterization asserting the two idiom-gap regexes above
# don't match. When M-R9 repointed it off the (now-private) regexes onto
# the public `extract_definitions_from_section(...)` OUTPUT, its assertion
# silently became "this row yields no definitions" -- the exact claim this
# sprint exists to falsify, and the literal negation of the RED test right
# below it. That test is DELETED, not reformulated: a "why it's broken
# today" characterization pinned at the regex level would have stayed true
# forever (a new F6 rule module is not those two regexes), but no
# equivalent formulation exists at the public-output level that both (a)
# avoids importing the now-private regexes and (b) stays true once the F6
# rule ships and "Act" is correctly extracted -- any such formulation would
# have to assert emptiness, which is precisely what must stop being true.
# The RED test below already pins the real requirement; a defect-
# characterization test that is a straight negation of it has no value
# once the row is fixed and the Developer cannot touch tests to remove it.


def test_nh_s1_act_apposition_is_extracted_as_a_definition():
    row = _load_rows()["STATE_NH_TXXVII_C301-B_S1"]
    candidates = _extract_both_ways(row)
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
    candidates = _extract_both_ways(row)
    all_terms = {t for c in candidates for t in c.terms}
    assert "-..-" not in all_terms
    assert "Reference Map" not in all_terms
