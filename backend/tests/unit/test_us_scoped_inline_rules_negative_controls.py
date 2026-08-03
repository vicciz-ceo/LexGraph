"""Sprint 2026-08-04-defs-us-scoped-inline (Planner, D5, target 1: pure rule
module). RED today with `ModuleNotFoundError` -- see
`test_us_scoped_inline_rules_trigger_axis.py`'s module docstring for the
full public-API contract this sprint pins.

This file: the ZERO-FALSE-POSITIVE half of the U4/U5 zero-miss-vs-precision
tension (P-R2). The director's absolute zero-miss bar creates real
precision pressure -- these tests are the counterweight, pinning that the
new rule module stays quiet on real corpus text that merely LOOKS like
family 1 but is not:

1. A scope-trigger phrase followed by an UNQUOTED cross-reference
   ("...is the same as defined in Section N") -- no quoted term, no
   recognized defining idiom.
2. Bare "in this <unit>" used as ordinary prose, nowhere near a definition
   (measured: 72.7% of all bare-`in`-trigger hits across the 12 lead
   states are exactly this shape -- see the sprint log's D1/D2 sections).
3. Real baseline-state (U5 regression set) rows with NO family-1 trigger
   at all -- the new rule module must never manufacture a candidate out of
   ordinary substantive statute text just because SOME word combination
   resembles a trigger.
4. The genuinely ambiguous PA "References to X shall include Y" shape,
   which the Planner excludes from this sprint's positive scope by
   design (a construction/interpretation clause about how OTHER text
   should be read, not a `"X" means Y`-shaped definition) -- escalated to
   the manager in the sprint log's D2 section, not silently decided.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_scoped_inline_rows.json"
)


def _rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))}


# --- unquoted cross-reference bait ------------------------------------------


def test_unquoted_cross_reference_yields_nothing():
    """`STATE_UT_T10_S10_21_302`: `"For purposes of this section, a
    manufactured home is the same as defined in Section 15A-1-302..."`
    -- the term is never quoted and the idiom is "is the same as defined
    in", not one of the recognized defining idioms (`means`/`shall
    mean`/`is defined as`/`has the meaning`/`includes`)."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_UT_T10_S10_21_302"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert candidates == []


# --- bare "in this <unit>" as ordinary prose --------------------------------


def test_bare_in_this_section_mid_sentence_prose_yields_nothing():
    """`STATE_UT_T11_S11_59_603`: `"Nothing in this section may be
    construed to relieve a purchaser..."` -- "in this section" here is
    ordinary cross-referencing prose, not a definitions trigger: there is
    no quote and no defining idiom anywhere nearby. This is the exact
    shape the trigger-axis file's module docstring measured as 72.7% of
    all bare-`in`-trigger hits across the 12 lead states."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_UT_T11_S11_59_603"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert candidates == []


# --- baseline-state (U5 regression set) rows with zero trigger -------------


def test_baseline_montana_row_with_no_trigger_yields_nothing():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_MT_T76_C13_P1_S76-13-107"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert candidates == []


def test_baseline_indiana_row_with_no_trigger_yields_nothing():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_IN_T13_A23_C12_S13-23-12-3"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert candidates == []


def test_baseline_new_york_row_with_no_trigger_yields_nothing():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_NY_ATAX_A9_S197-D"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert candidates == []


# --- escalation-flagged boundary case: excluded from v1 by design ----------


def test_references_to_term_shall_include_is_excluded_by_design():
    """`STATE_PA_T15_C57_S5749`: `"For the purposes of this
    subchapter: (1) References to \\"other enterprises\\" shall
    include employee benefit plans..."` -- grammatically this is a
    RULE about how the phrase "other enterprises" should be READ
    elsewhere in the subchapter (a construction/interpretation clause),
    not a definition that introduces "other enterprises" as a term with a
    meaning ("X" means Y). The Planner's lean is to exclude this shape
    from v1 (real ambiguity, escalated to the manager rather than silently
    decided either way -- see the sprint log's D2 section). This test pins
    that lean as the CURRENT design decision; if the manager overrules it,
    this is the one test to update."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_PA_T15_C57_S5749"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "other enterprises" not in terms
    assert "serving at the request of the corporation" not in terms
