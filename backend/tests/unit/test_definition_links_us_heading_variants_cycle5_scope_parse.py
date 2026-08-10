"""Cycle-5 item 14, the genuinely NEW half -- pure, heading-text-only
functions that extract the SCOPE VALUE a family-4 heading itself declares,
for the two U2 rows measured as containment-mechanism-ready in the
companion file `test_definition_links_matcher_u2_scope_cycle5.py`.

**RED signal**: `ImportError` -- `chapter_range_scope_bounds` and
`enumerated_local_scope_targets` do not exist anywhere in the shipped
module yet; this is a genuinely new capability, not a whitelist widening
(unlike items 10/11/15).

## Why this is split from the matcher-level proof, and what is DELIBERATELY
## NOT claimed here

The matcher-level file proves the CONTAINMENT mechanism is live and
correct for real AK/KY values. It does NOT prove those values ever reach
a real `Definition` row on the live pipeline path for a definitions-
SECTION heading (as opposed to a hand-constructed test value) -- and this
Planner is not silently claiming it does. `us_profile.determine_scope`
(the function that computes scope for a HEADING-recognized Definitions
section, shared/core-owned, out of this panel's write-set per U3) has an
unconditional 2-way contract today (`"chapter"` / `"law-wide"`, trigger-
phrase-driven off the body's first line only) -- verified by direct read,
`us_profile.py:1019-1024`. There is no slot in that contract for `"local"`,
for an ENUMERATED chapter tuple, or for an enumerated local-article tuple.
The registrable `ScopeKindRule` seam (M-D2) that lets a family panel
extend `determine_scope`'s behavior without editing the shared module
returns a KIND STRING ONLY (`detect(body_text) -> str | None`) -- it has
no companion mechanism for supplying a VALUE, let alone a TUPLE value, so
even a `ScopeKindRule` returning `"local"` would still need `pipeline.py`
(shared, out of scope) to know how to fill `source_article_number` with
more than "this article's own number" for the enumerated case.

**This gap is reported to the manager as an open escalation, not guessed
at or silently wired around** -- see the Planner's report for the full
per-row U2 verdict table (all 10 act_ids) and this specific wiring
question. What CAN be pinned today, honestly, is the pure heading-text
extraction this module's own rules already do for every other family-4
shape (self-contained, no shared-module dependency, ruling H-R4) -- these
two functions are exactly that, scoped no further.

## Function specs (pin the BEHAVIOR, not a specific regex -- same
## convention as `defines_in_body`'s own spec)

- `chapter_range_scope_bounds(heading: str) -> tuple[str, str] | None`:
  for a heading of the shape "[General] definitions for AS X [—/–/-/
  mojibake-dash] AS Y[.]" (AK's own real drafting convention), returns the
  bare `(X, Y)` boundary strings, no trailing punctuation, no "AS "
  prefix. Returns `None` for any heading not matching this shape.
- `enumerated_local_scope_targets(heading: str) -> tuple[str, ...] | None`:
  for a heading containing "Definition[s] for section" (case-insensitive),
  returns a tuple of every ADDITIONAL article/section number named
  alongside it via "and KRS N" (KY's own real drafting convention) --
  empty tuple `()` when the heading says "for section" with no additional
  named target (KY_17.185/139.486/246.420's own shape: scope is just the
  section itself, no enumeration needed at all). Returns `None` (not `()`)
  for a heading that does not contain the "for section" trigger phrase at
  all, so callers can distinguish "this heading declares no extra scope
  members" from "this heading isn't this shape."

Fixture: `cycle5_u2_scope_rows.json` (5 rows: AK + 4 KY, byte-identical to
the real parquet, independently re-verified column-by-column).
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "cycle5_u2_scope_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def test_chapter_range_scope_bounds_recognizes_the_real_ak_probate_code_range():
    from app.definition_links.rules.us_heading_variants import chapter_range_scope_bounds

    row = _load_rows()["STATE_AK_T13_C13.06_S13.06.050"]
    assert row["section_title"] == "General definitions for AS 13.06 \x97 AS 13.36."
    bounds = chapter_range_scope_bounds(row["section_title"])
    assert bounds == ("13.06", "13.36"), (
        "must extract the bare boundary chapter numbers, no 'AS ' prefix, no "
        "trailing period, tolerant of the mojibake em-dash (\\x97) between them"
    )


def test_chapter_range_scope_bounds_returns_none_for_a_non_range_heading():
    from app.definition_links.rules.us_heading_variants import chapter_range_scope_bounds

    row = _load_rows()["STATE_KY_TXIII_C156_S156.106"]
    assert chapter_range_scope_bounds(row["section_title"]) is None, (
        "a plain 'Definition for section and KRS N' heading names no chapter "
        "range at all -- must not be misread as one"
    )


def test_enumerated_local_scope_targets_recognizes_ky_156_106s_additional_krs_section():
    from app.definition_links.rules.us_heading_variants import (
        enumerated_local_scope_targets,
    )

    row = _load_rows()["STATE_KY_TXIII_C156_S156.106"]
    assert row["section_title"] == (
        "156.106 Critical shortage areas -- Definition for section and KRS 161.605 -- "
        "Appointment of retired teachers and administrators"
    )
    assert enumerated_local_scope_targets(row["section_title"]) == ("161.605",), (
        "must extract the additional KRS section number named alongside 'for "
        "section' -- bare, no 'KRS ' prefix, so it composes directly into a "
        "source_article_number tuple alongside the section's own number"
    )


def test_enumerated_local_scope_targets_returns_empty_tuple_for_plain_for_section_headings():
    """The other 3 of the 4 KY rows say only "Definitions for section" (or
    "Definition for section") with NO additional named target -- these
    declare an ordinary single-article local scope (this section only),
    not an enumeration. Empty tuple, not None: the heading IS this shape,
    it just names zero additional members."""
    from app.definition_links.rules.us_heading_variants import (
        enumerated_local_scope_targets,
    )

    rows = _load_rows()
    for act_id in (
        "STATE_KY_TIII_C17_S17.185",
        "STATE_KY_TXI_C139_S139.486",
        "STATE_KY_TXXI_C246_S246.420",
    ):
        heading = rows[act_id]["section_title"]
        assert "for section" in heading.lower(), (
            f"precondition: {act_id} must carry the 'for section' trigger phrase"
        )
        assert enumerated_local_scope_targets(heading) == (), (
            f"{heading!r}: plain 'for section' with no 'and KRS N' clause names no "
            "additional scope member"
        )


def test_enumerated_local_scope_targets_returns_none_for_a_heading_without_the_trigger():
    from app.definition_links.rules.us_heading_variants import (
        enumerated_local_scope_targets,
    )

    row = _load_rows()["STATE_AK_T13_C13.06_S13.06.050"]
    assert enumerated_local_scope_targets(row["section_title"]) is None, (
        "AK's 'definitions for AS X -- AS Y' heading is the chapter-RANGE shape, "
        "not the 'for section' local-enumeration shape -- must not be misread as "
        "the other function's territory"
    )
