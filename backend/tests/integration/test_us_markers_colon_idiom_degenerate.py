"""RED test -- sprint 2026-08-04-defs-us-markers, phase-3 Planner (QA cycle
2 queue item 3, sprint log `## M22`/`## M23`, Developer B's honest gap):
`extract_quote_anchored_entries` (the shared family-3 engine,
`us_markers_boundary.py`) has a PRE-EXISTING defect, unrelated to Developer
B's own MN/ME/OH registration work -- a colon-introduced sub-list
(`"Term" means:` / `"Term" shall mean:` followed by a lettered/numbered
enumeration that is itself the definition's real content, not a sibling
top-level entry) collapses to a near-empty `definition_text`, silently
losing the entire enumeration. Reproduces with Developer B's own MN/ME
registration modules (`us_markers_mn_subd_marker.py`,
`us_markers_me_pl_citation.py`) removed entirely -- confirmed directly
against the unmodified, shared `extract_quote_anchored_entries`, so this
is not Developer B's defect. No fix exists yet; red-before-green, per
program law. This file's own job is to PIN it, not fix it.

**Root cause, diagnosed this pass** (M22 named the defect but not its
mechanism): the list-introducer exclusion
(`us_markers_boundary._LIST_INTRODUCER_BEFORE_RE`, `[:—]\\s*$`) is what is
SUPPOSED to stop a colon-introduced sub-list's own first marker from being
misread as a sibling top-level entry boundary -- the same guard that
correctly protects e.g. `STATE_AZ_T28_C16_A4_S5857`'s `"agricultural
products" means either:\\n\\n1. Crops, ...` (see `us_markers_boundary.py`'s
own module docstring). It works by checking whether the text immediately
before the candidate marker, skipping only real whitespace (`\\s*`), ends
in a literal `:`. Real `us_ny_statutes.parquet` rows store every line
break as the LITERAL two-character sequence `\\` + `n` (backslash-n),
never a real newline byte -- a separate, already-documented NY corpus
defect (`ny_m14_newline_defect_row.json`'s own README section, 40,102/
40,102 real NY rows). `\\s` does not match a literal backslash character or
a literal `n` character -- they are ordinary non-whitespace text to the
regex engine. So on a real NY row, `_LIST_INTRODUCER_BEFORE_RE`'s `\\s*$`
cannot bridge the literal `\\n` sitting between the colon and the marker,
the exclusion never fires, and the sub-list's own first marker (its first
word capitalized, as real statutory drafting almost always is) is instead
treated as an ordinary hard-stop by `_DIGIT_MARKER_RE`'s
`_AFTER_MARKER_UPPER_OR_QUOTE_RE` check -- closing the candidate just a
few (non-whitespace-per-`.strip()`) characters after the idiom itself,
before any real content is captured.

**Confirmed, this pass, on two independent real NY rows** (see fixture
docstring below) -- `entries["Hospital"]` and
`entries["chief fiscal officer"]` are BOTH the literal 2-character string
`"\\n"` (backslash + n, survives `.strip()` because neither character is
real whitespace) despite each term's real definition being a substantial,
multi-item enumeration (~1,200 and ~870+ chars respectively, verified
directly against the row's own `text`).

**Honest gap, reported per this pass's brief** (do not carry M22's MN/ME
counts forward as verified): M22 states this defect affects "~16/12,575
MN, 3/9,588 ME, 13 NY" rows, describing the shape uniformly as "collapse
to degenerate definitions (`means:`, `:`)". Re-measured this pass, in
full, against the entire real corpus (27,747 MN rows, 25,316 ME rows,
`extract_quote_anchored_entries` called directly, zero exceptions): **MN
and ME produce ZERO near-total-collapse (<=5 stripped chars) results --
none.** MN/ME both store REAL newline bytes (verified directly), so the
literal-`\\n` mechanism above cannot reproduce there; the closest MN/ME
analogues found this pass are a DIFFERENT, milder shape -- partial
truncation at a colon-list's SECOND item onward (its first item is
protected by the SAME list-introducer check, still directly adjacent to
the real colon; subsequent items are not, the identical adjacency gap,
just without NY's literal-`\\n` trigger) -- e.g. real ME row
`STATE_ME_T39-A_P1_C1_S105-A`'s "Person" -> `"(1) An individual;"` (loses
"(2)"/"(3)" onward). That is plausibly a RELATED defect in the same
adjacency-only list-introducer check, but it is NOT the same near-empty
"means:"/":" shape M22 named, and this pass does not have verified
evidence it affects 16 MN / 3 ME rows specifically. Only the NY shape
pinned below is independently re-verified end to end this pass. Flagged
for the manager rather than silently amended into M22's number."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_ny_colon_idiom_degenerate_rows.json"
)

# Matches wave1's own fixture-file convention (see
# `test_us_markers_wave1_auto_rescue_subcases.py`): a definition this short
# is degenerate on its face, real US statutory definitions are essentially
# never this terse.
DEGENERATE_THRESHOLD = 10  # chars


def _load_rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def test_fixture_rows_are_the_expected_real_ny_rows():
    rows = _load_rows()
    assert set(rows) == {"STATE_NY_AISC_A55_S5501", "STATE_NY_ALFN_A1_S2.00"}
    assert rows["STATE_NY_AISC_A55_S5501"]["section_title"] == "Definitions"
    assert rows["STATE_NY_ALFN_A1_S2.00"]["section_title"] == "Definitions"


def test_ny_hospital_colon_list_definition_is_not_swallowed_to_near_empty():
    """`STATE_NY_AISC_A55_S5501` (NY Insurance Law § 5501, real
    Definitions section) -- entry `(c) "Hospital" means:` is followed by a
    real, substantial 4-item enumeration ((1) a licensed hospital/nursing
    home facility, (2) a registered ambulance service, (3) a community
    mental health center, (4) a certified home care agency -- ~1,200 real
    chars). `extract_quote_anchored_entries`, called directly on this
    row's real, unmodified `text`, must not collapse this to a near-empty
    capture. RED today: currently returns the literal 2-character string
    `"\\n"` (backslash-n survives `.strip()` -- neither character is real
    whitespace), losing the entire enumeration. No fix exists yet -- see
    this file's module docstring for the diagnosed root cause (NY's own
    literal-`\\n` line-break encoding defeating the list-introducer
    exclusion)."""
    rows = _load_rows()
    row = rows["STATE_NY_AISC_A55_S5501"]
    entries = dict(extract_quote_anchored_entries(row["text"]))
    assert "Hospital" in entries, f"'Hospital' missing entirely -- got {sorted(entries)!r}"
    definition_text = entries["Hospital"]
    assert len(definition_text.strip()) >= DEGENERATE_THRESHOLD, (
        f"'Hospital' definition_text is degenerate ({len(definition_text.strip())} chars "
        f"after stripping): {definition_text!r} -- the real definition is a ~1,200-char "
        f"4-item enumeration (hospital facility / ambulance service / community mental "
        f"health center / home care agency); this defect silently drops all of it"
    )
    assert "ambulance service" in definition_text, (
        f"'Hospital' definition_text is missing real enumerated content ('ambulance "
        f"service', item (2) of 4): {definition_text!r}"
    )


def test_ny_chief_fiscal_officer_colon_list_definition_is_not_swallowed_to_near_empty():
    """`STATE_NY_ALFN_A1_S2.00` (NY Local Finance Law § 2.00, real
    Definitions section) -- entry `5. The term "chief fiscal officer"
    shall mean:` is followed by real, substantial lettered/nested-numbered
    content (multiple paragraphs covering counties, cities, towns, and
    villages). Same defect, an independent second real row -- proves this
    is not a single-row fluke. RED today, same literal `"\\n"` collapse."""
    rows = _load_rows()
    row = rows["STATE_NY_ALFN_A1_S2.00"]
    entries = dict(extract_quote_anchored_entries(row["text"]))
    assert "chief fiscal officer" in entries, (
        f"'chief fiscal officer' missing entirely -- got {sorted(entries)!r}"
    )
    definition_text = entries["chief fiscal officer"]
    assert len(definition_text.strip()) >= DEGENERATE_THRESHOLD, (
        f"'chief fiscal officer' definition_text is degenerate "
        f"({len(definition_text.strip())} chars after stripping): {definition_text!r} -- "
        f"the real definition is a substantial multi-paragraph provision covering "
        f"counties, cities, towns and villages; this defect silently drops all of it"
    )
    assert "comptroller" in definition_text, (
        f"'chief fiscal officer' definition_text is missing real content ('comptroller', "
        f"part of the real (a)/(b) enumeration): {definition_text!r}"
    )
