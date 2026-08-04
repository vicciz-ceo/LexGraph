"""A corpus-shaped regression floor, CYCLE 3 -- sprint 2026-08-04-defs-us-pr.

Same discipline as `test_pr_profile_corpus_floor_cycle2.py` (see that
file's own module docstring for the full "why a floor, not just
family-specific tests" rationale -- not repeated here). This file adds
cycle 3's new families to the SAME kind of aggregate floor: every row
independently known (by direct human reading of the real text, not by
re-deriving from the extractor) to be genuinely capturable yields >=1
candidate; every row known to be a correct rejection (heading-anchor
residue, or a correct-zero cross-law/title deferral) yields NONE.

A SIBLING file, not a merge into cycle 2's -- cycle 2's file and its
already-committed 33 rows are untouched.

Constraint from the sprint contract: "Extend the corpus-floor test... so
the new families are covered by the aggregate floor too, not only by
individual tests." This file is that extension for cycle 3's two new
capabilities: the heading-anchored bucket-D rule
(`extract_heading_anchored_definition`) and the widened/lead-in-fixed
`extract_definitions_from_section` ordinary-workload families.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load(*filenames: str) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for filename in filenames:
        rows = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
        for row in rows:
            merged[row["act_id"]] = row
    return merged


ALL_ROWS = _load("pr_sample_rows.json", "pr_sample_rows_cycle2.json", "pr_sample_rows_cycle3.json")

# Heading-anchored bucket-D rows: known, by direct human reading, to name
# their own defined term in the heading AND corroborate it verbatim in the
# body -- must yield exactly one candidate via
# `extract_heading_anchored_definition`.
MUST_BE_HEADING_ANCHORED = [
    "STATE_PR_CIVIL_ART236",
    "STATE_PR_LEY_77_1957_ART5_020",
    "STATE_PR_CIVIL_ART1264",
    "STATE_PR_CIVIL_ART1508",
    "STATE_PR_CIVIL_ART326",
    "STATE_PR_RENTAS_SEC2030_03",
    "STATE_PR_LEY_77_1957_ART36_020",
    "STATE_PR_CIVIL_ART1139",
    "STATE_PR_CIVIL_ART263",
]

# The FINAL documented bucket-D residue (director-reviewable gap) -- known
# to have NO safe heading anchor. Must continue to yield NOTHING via
# `extract_heading_anchored_definition` -- the floor's own guard against
# the rule being over-widened into a general prose matcher.
MUST_STAY_HEADING_ANCHOR_RESIDUE = [
    "STATE_PR_CIVIL_ART1526",
    "STATE_PR_LEY_77_1957_ART35_020",
    "STATE_PR_LEY_77_1957_ART42_010",
    "STATE_PR_CIVIL_ART1293",
    "STATE_PR_LEY_77_1957_ART4_010",
    "STATE_PR_PENAL_ART15",
    "STATE_PR_LEY_77_1957_ART5_030",
]

# Ordinary-workload rows: known to define a real term, currently zero-yield
# via `extract_definitions_from_section`, must yield >=1 candidate once the
# lead-in-strip / idiom-widening fixes land.
MUST_CAPTURE_AT_LEAST_ONE_TERM = [
    "STATE_PR_LEY_66_2011_ART3",
    "STATE_PR_LEY_133_1979_ART1",
    "STATE_PR_LEY_141_2002_ART6",
    "STATE_PR_LEY_155_1937_SEC1",
    "STATE_PR_LEY_9_2020_ART2",
    "STATE_PR_LEY_26_1941_ART57",
    "STATE_PR_RENTAS_SEC1010_01",
]

# Correct-zero guards: known, by direct human reading, to be a wholesale
# cross-law/title deferral with zero local terms of its own -- must
# continue to yield NOTHING via `extract_definitions_from_section`, and
# the precision regression guard for the idiom-widening fix (below).
MUST_CAPTURE_NOTHING = [
    "STATE_PR_LEY_48_2018_ART3",
]

# The idiom-widening precision regression guard: a real marked list of
# >=20 distinct terms whose LEAD-IN happens to satisfy a widened bare-idiom
# shape -- must never collapse to a single fabricated "term".
MUST_NOT_COLLAPSE_TO_ONE_FABRICATED_TERM = [
    ("STATE_PR_LEY_214_2004_ART2", 20),
]


@pytest.mark.parametrize("act_id", MUST_BE_HEADING_ANCHORED)
def test_known_heading_anchored_row_yields_exactly_one_candidate(act_id):
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = ALL_ROWS[act_id]
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert len(candidates) == 1, f"{act_id}: expected exactly 1 candidate, got {len(candidates)}"


@pytest.mark.parametrize("act_id", MUST_STAY_HEADING_ANCHOR_RESIDUE)
def test_known_residue_row_stays_at_zero_heading_anchored_candidates(act_id):
    from app.definition_links.pr_profile import extract_heading_anchored_definition

    row = ALL_ROWS[act_id]
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert candidates == [], f"{act_id}: expected 0 candidates (documented gap), got {candidates!r}"


@pytest.mark.parametrize("act_id", MUST_CAPTURE_AT_LEAST_ONE_TERM)
def test_known_ordinary_workload_row_yields_at_least_one_candidate(act_id):
    from app.definition_links.pr_profile import extract_definitions_from_section

    row = ALL_ROWS[act_id]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert len(candidates) >= 1, f"{act_id}: expected >=1 candidate, got 0"


@pytest.mark.parametrize("act_id", MUST_CAPTURE_NOTHING)
def test_known_correct_zero_row_stays_at_zero(act_id):
    from app.definition_links.pr_profile import extract_definitions_from_section

    row = ALL_ROWS[act_id]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert candidates == [], f"{act_id}: expected 0 candidates, got {len(candidates)}"


@pytest.mark.parametrize("act_id,min_terms", MUST_NOT_COLLAPSE_TO_ONE_FABRICATED_TERM)
def test_known_marked_list_does_not_collapse_under_idiom_widening(act_id, min_terms):
    from app.definition_links.pr_profile import extract_definitions_from_section

    row = ALL_ROWS[act_id]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert len(candidates) >= min_terms, (
        f"{act_id}: idiom-widening regression -- expected >={min_terms} candidates, "
        f"got {len(candidates)}"
    )


def test_floor_lists_are_disjoint_and_non_trivial():
    """Sanity check on this floor's own bookkeeping."""
    assert len(MUST_BE_HEADING_ANCHORED) >= 8
    assert len(MUST_STAY_HEADING_ANCHOR_RESIDUE) >= 5
    assert len(MUST_CAPTURE_AT_LEAST_ONE_TERM) >= 5
    assert set(MUST_BE_HEADING_ANCHORED).isdisjoint(MUST_STAY_HEADING_ANCHOR_RESIDUE)
    assert set(MUST_CAPTURE_AT_LEAST_ONE_TERM).isdisjoint(MUST_CAPTURE_NOTHING)
    all_ids = (
        MUST_BE_HEADING_ANCHORED
        + MUST_STAY_HEADING_ANCHOR_RESIDUE
        + MUST_CAPTURE_AT_LEAST_ONE_TERM
        + MUST_CAPTURE_NOTHING
        + [a for a, _ in MUST_NOT_COLLAPSE_TO_ONE_FABRICATED_TERM]
    )
    for act_id in all_ids:
        assert act_id in ALL_ROWS, f"{act_id} referenced but not vendored in any fixture file"
