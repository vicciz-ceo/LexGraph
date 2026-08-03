"""A CORPUS-SHAPED regression floor for the PR Spanish profile (sprint
2026-08-04-defs-us-pr, cycle 2, deliverable 4).

## Why this file exists (the cycle-1 lesson, stated as a test design rule)

Cycle 1 authored 5 hand-picked, individually-perfect fixture tests. All 5
passed; the suite was green; and the real capture rate over the full
23,636-row corpus was 56.4%. A test suite built ONLY from N hand-picked rows
cannot prove a zero-miss gate, no matter how real or well-chosen those rows
are -- passing N bespoke tests says nothing about row N+1.

This file is deliberately shaped differently: it is not "does row X extract
term Y" (that's what `test_pr_profile_extraction_cycle2.py` and
`test_pr_profile_headings_cycle2.py` already prove, family by family). It
is an AGGREGATE FLOOR over a modest, broad, real sample (33 rows -- the 10
cycle-1 rows + 23 of cycle 2's 24, one per independently-diagnosed family,
drawn from the manager's own measured miss workload, not re-derived) that
asserts: every row known to be a genuine, capturable Definiciones section
yields AT LEAST ONE candidate, and every row known to be a correct
rejection (a non-heading, or a heading with zero local terms) yields NONE.

A future regression of this same CLASS -- e.g. a well-intentioned separator-
pattern tweak that accidentally narrows one of the 6 patterns back down, or
a heading-widening change that only special-cases the exact 13 rows
cycle 2 named instead of fixing the underlying clause-scoping gap -- will
show up here as a floor violation even if every family-specific unit test
still passes, because this file does not re-derive its expectations from
`pr_profile.py`'s own internals; it derives them from what the manager and
Planner independently determined, by reading the real text, that a human
would extract.

## What this file deliberately does NOT do

It does not read the parquet (no test in this sprint does -- every row
below is already vendored, byte-compared, in `pr_sample_rows.json` /
`pr_sample_rows_cycle2.json`). It does not assert exact term sets or exact
candidate counts per row (that precision belongs in the family-specific
files) -- only the coarser "captured something" / "captured nothing"
floor, which is exactly the granularity that would have caught cycle 1's
56.4% gap without over-fitting to any one row's exact shape. It does not
touch bucket D or any row whose correct extraction is still an open
question (P-R2/Q-1) -- the "must capture" list below is restricted to
rows this cycle's diagnosis positively resolved.

## If this file ever needs a new row added

That is a feature, not a maintenance burden: every time a future cycle
diagnoses a new family and vendors a new fixture row, add it to the
relevant list below. The floor's value is proportional to how many
independently-sourced rows back it, not how cleverly any single row is
picked.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.pr_profile import extract_definitions_from_section, is_definitions_heading

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load(*filenames: str) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for filename in filenames:
        rows = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
        for row in rows:
            merged[row["act_id"]] = row
    return merged


ALL_ROWS = _load("pr_sample_rows.json", "pr_sample_rows_cycle2.json")

# Real canonical Definiciones rows (heading already known-True, or fixed by
# this cycle's heading tests) whose body is known -- by direct human reading
# of the real text, not by re-deriving from the extractor -- to define at
# least one real term. Every row here is drawn from the manager's own
# bucket A/B/C miss workload or from cycle 1's already-passing set.
MUST_CAPTURE_AT_LEAST_ONE_TERM = [
    # cycle 1 (already green; re-asserted here as part of the broader floor)
    "STATE_PR_LEY_249_2003_ART3",
    "STATE_PR_LEY_63_2023_ART3",
    "STATE_PR_LEY_77_1957_ART30_020",
    "STATE_PR_LEY_77_1957_ART1_090",
    "STATE_PR_LEY_15_2024_ART3",
    "STATE_PR_LEY_135_1979_ART1",
    # cycle 2 -- bucket A (extractor separator-pattern gaps)
    "STATE_PR_LEY_77_1957_ART39_050",
    "STATE_PR_LEY_73_2003_ART2",
    "STATE_PR_LEY_189_1996_ART2",
    "STATE_PR_LEY_214_1995_ART2",
    "STATE_PR_LEY_33_2017_ART3",
    "STATE_PR_LEY_39_1988_ART2",
    "STATE_PR_LEY_493_1952_ART1",
    "STATE_PR_LEY_318_1999_ART2",
    "STATE_PR_LEY_167_1988_ART2",
    "STATE_PR_LEY_60_1988_ART1",
    "STATE_PR_LEY_66_1975_ART3",
    "STATE_PR_AMBIENTAL_ART51",
    # cycle 2 -- bucket C re-diagnosis
    "STATE_PR_LEY_190_1995_ART2",
    # cycle 2 -- bucket B (settled)
    "STATE_PR_LEY_199_2015_ART2",
    "STATE_PR_LEY_46_2008_ART3",
    "STATE_PR_LEY_51_2003_ART2",
    "STATE_PR_LEY_77_1957_ART9_040",
]

# Real rows whose heading must be recognized as a genuine Definiciones
# heading (positive P1 target) -- the 13 real misses this cycle diagnosed,
# plus the cycle-1 rows already green.
MUST_RECOGNIZE_AS_DEFINITIONS_HEADING = [
    "STATE_PR_LEY_249_2003_ART3",
    "STATE_PR_LEY_63_2023_ART3",
    "STATE_PR_LEY_77_1957_ART30_020",
    "STATE_PR_LEY_77_1957_ART1_090",
    "STATE_PR_LEY_15_2024_ART3",
    "STATE_PR_LEY_135_1979_ART1",
    "STATE_PR_CIVIL_ART365",
    "STATE_PR_LEY_77_1964_ART1",
    "STATE_PR_LEY_15_1931_SEC22",
    "STATE_PR_MUNICIPAL_ART7_212",
    "STATE_PR_LEY_77_1957_ART15_020",
]

# Real rows whose heading must be REJECTED (false-positive guards) --
# unchanged by this cycle, re-asserted as part of the same floor so a
# precision regression shows up in the same place as a recall regression.
MUST_REJECT_AS_DEFINITIONS_HEADING = [
    "STATE_PR_LEY_160_2013_ART5_4",  # "Aportaciones Definidas" pension term
    "STATE_PR_LEY_165_2020_ART1_2",  # TOC listing (cycle 1)
    "STATE_PR_LEY_85_2018_ART9_04",  # ordinary substantive article
    "STATE_PR_LEY_70_1997_ART1",  # ordinary substantive article
    "STATE_PR_LEY_51_2020_ART1_2",  # TOC listing (cycle 2, 2nd real row)
]

# A row whose body is a genuine Definiciones section but correctly yields
# ZERO local candidates (wholesale cross-law deferral) -- the floor's own
# guard against the fix being over-widened to fabricate terms.
MUST_CAPTURE_NOTHING = [
    "STATE_PR_LEY_52_2019_ART3",
]


@pytest.mark.parametrize("act_id", MUST_CAPTURE_AT_LEAST_ONE_TERM)
def test_known_capturable_row_yields_at_least_one_candidate(act_id):
    """The floor cycle 1 lacked: every row independently diagnosed (by a
    human reading the real text, not by the extractor's own behavior) as a
    genuine, capturable Definiciones entry must yield >=1 candidate. A
    change that fixes the exact rows named in a family-specific test file
    but leaves this broader, independently-sourced list short is a real
    regression this floor catches and the narrower files would not."""
    row = ALL_ROWS[act_id]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert len(candidates) >= 1, f"{act_id}: expected >=1 candidate, got 0"


@pytest.mark.parametrize("act_id", MUST_RECOGNIZE_AS_DEFINITIONS_HEADING)
def test_known_definitions_heading_is_recognized(act_id):
    row = ALL_ROWS[act_id]
    assert is_definitions_heading(row["section_title"]) is True, (
        f"{act_id}: expected heading match, section_title={row['section_title']!r}"
    )


@pytest.mark.parametrize("act_id", MUST_REJECT_AS_DEFINITIONS_HEADING)
def test_known_non_definitions_heading_stays_rejected(act_id):
    row = ALL_ROWS[act_id]
    assert is_definitions_heading(row["section_title"]) is False, (
        f"{act_id}: expected heading rejection (false-positive guard), "
        f"section_title={row['section_title']!r}"
    )


@pytest.mark.parametrize("act_id", MUST_CAPTURE_NOTHING)
def test_known_correct_zero_row_stays_at_zero(act_id):
    """The floor's own over-widening guard: a row correctly yields zero
    candidates (a wholesale cross-law deferral, not a miss) and must
    continue to. If a future extraction change starts fabricating terms
    out of a cross-reference sentence just to chase this floor's own
    "at least one" assertions elsewhere, this test catches it."""
    row = ALL_ROWS[act_id]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert candidates == [], f"{act_id}: expected 0 candidates, got {len(candidates)}"


def test_floor_lists_are_disjoint_and_non_trivial():
    """Sanity check on the floor's own bookkeeping -- not a corpus
    assertion, a guard against this file silently degrading into a no-op
    (e.g. an empty parametrize list "passing" vacuously)."""
    assert len(MUST_CAPTURE_AT_LEAST_ONE_TERM) >= 20
    assert len(MUST_RECOGNIZE_AS_DEFINITIONS_HEADING) >= 10
    assert len(MUST_REJECT_AS_DEFINITIONS_HEADING) >= 4
    assert set(MUST_REJECT_AS_DEFINITIONS_HEADING).isdisjoint(MUST_RECOGNIZE_AS_DEFINITIONS_HEADING)
    all_ids = (
        MUST_CAPTURE_AT_LEAST_ONE_TERM
        + MUST_RECOGNIZE_AS_DEFINITIONS_HEADING
        + MUST_REJECT_AS_DEFINITIONS_HEADING
        + MUST_CAPTURE_NOTHING
    )
    for act_id in all_ids:
        assert act_id in ALL_ROWS, f"{act_id} referenced but not vendored in either fixture file"
