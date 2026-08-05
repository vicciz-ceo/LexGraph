"""Sprint 2026-08-04-defs-us-scoped-inline (Planner pass 8, Task 4, director
ruling D-S15, condition 1).

D-S15: `"this subsection"` scopes to the TOP-LEVEL subdivision (OUTERMOST
open step at the trigger offset) by default. That default is a MEASURED
majority, not a universal truth: the manager's own corpus-wide census of
the drafters' OWN cross-reference vocabulary (53 jurisdiction files, S-R15
verdict) found 202,943 phrases placing "subsection" directly under
"section" (`subsection (X) of this section` / `paragraph (X) of this
subsection` / `subdivision (X) of this subsection` / `subparagraph (X) of
this subsection`) across 48 of 53 jurisdictions -- but also found the
INVERTED phrasing (`subsection (X) of this subdivision` / `... of this
paragraph`), where "subsection" genuinely names a unit NESTED BELOW
something else, 12 times total: South Dakota 6, New York 3, Vermont 2,
federal 1. That count (and the 202,943 figure above) is the manager's own
measurement, cited here with attribution -- this pass did NOT
independently re-derive it, per the pass-8 brief's own framing of D-S15's
evidence base as already established.

**This module does NOT implement a per-state override.** Per the pass-8
brief's explicit instruction: condition 1 (South Dakota / New York /
Vermont's inverted "subsection" convention) is recorded as a NAMED,
ACCEPTED limitation -- "enumerated either way, never buried" -- not fixed.
Under D-S15's outermost default, a definition triggered by "as used in
this subsection" on one of these THREE states' own inverted rows will
stamp the OUTERMOST step of the resolved path, which is broader than the
drafter's actual intent (the drafter meant the narrower, nested unit).
The consequence is an OVER-link (a definition reaching sibling nested
units it should not) -- a bounded, measured (~0.006% of the corpus's own
cross-reference vocabulary) precision cost, not a miss, so it does not
violate the absolute zero-miss bar; it is exactly the "accepted
trace-volume over-link" the pass-8 brief names.

Why a TEST rather than only a docstring paragraph (the brief allows
either, preferring a docstring, but invites a pin if I judge it earns its
place): a prose note can go stale silently if a fixture bit-rots or is
edited without anyone re-checking it against this ledger. The tests below
byte-verify, from REAL, checked-in, unmodified corpus rows (never read
from the corpus at test time, per P-R9), that the inverted phrasing this
whole limitation is ABOUT still genuinely exists on the named rows -- so
if it is ever accidentally "fixed" out of the fixture, or the fixture
silently changes, this file fails LOUDLY instead of the limitation quietly
becoming undocumented fiction. It does not exercise the live pipeline
(D-S15's outermost stamping is Developer cycle 4's not-yet-landed change;
asserting the OVER-link's live behavior now would pin a claim about code
that does not exist in this worktree yet) -- it pins the EVIDENCE the
limitation rests on.

Rows (all 3, full original parquet columns, values unmodified, fetched
twice independently and diffed byte-identical before being written into
the fixture below):

- `STATE_SD_T58_C5A_S58-5A-4` (South Dakota) -- "...the information
  required by subsection (a) of this subdivision;" -- `subdivision` is
  the OUTER unit here; `subsection (a)` is nested inside it, naming a
  narrower thing than D-S15's outermost default would stamp.
- `STATE_VT_T24_C60_S1992` (Vermont) -- "Notwithstanding subsection (A) of
  this subdivision (2)," -- same inversion: `subdivision (2)` is the outer
  unit, `subsection (A)` narrower.
- `STATE_NY_AGMU_A15_S507` (New York) -- "...pursuant to the provisions of
  clause (1) of subsection (c) of this subdivision..." -- same shape.
  Carries the same pre-existing literal `\\n` corpus artifact already
  documented for NY elsewhere in this directory's README (M14) -- an
  unrelated, already-known defect, not something this file introduces or
  needs to work around (the phrase this file checks for does not span a
  `\\n`).

None of these three rows are used by, or need to agree with, any
`extract_us_scoped_inline_definitions` trigger match -- none of the three
quoted phrases below is inside a `"for purposes of"`/`"as used in"`-style
definition trigger at all (they are ordinary cross-reference prose), so
these rows are evidence for the NAMED LIMITATION's existence, not fixture
material for a live-path pin.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_scoped_inline_subsection_inverted_convention_rows.json"
)

# (act_id, the exact inverted-convention phrase this row must still contain)
_INVERTED_CONVENTION_ROWS = (
    ("STATE_SD_T58_C5A_S58-5A-4", "subsection (a) of this subdivision"),
    ("STATE_VT_T24_C60_S1992", "subsection (A) of this subdivision (2)"),
    ("STATE_NY_AGMU_A15_S507", "subsection (c) of this subdivision"),
)


def _rows() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_named_limitation_ledger_enumerates_exactly_three_inverted_states():
    """The ledger itself: exactly South Dakota, Vermont, and New York --
    D-S15 condition 1's own enumeration, never silently expanded or
    shrunk without this test being touched deliberately."""
    rows = _rows()
    states = {row["state"] for row in rows}
    assert states == {"sd", "vt", "ny"}, (
        f"named-limitation fixture states changed to {states!r} -- D-S15 condition 1 names "
        "exactly South Dakota/Vermont/New York (plus one untraced federal occurrence, not "
        "vendored here); update this test deliberately if the ledger itself is meant to change"
    )
    assert len(rows) == 3


def test_south_dakota_subdivision_row_genuinely_inverts_subsection_nesting():
    _assert_inverted_phrase_present(*_INVERTED_CONVENTION_ROWS[0])


def test_vermont_subdivision_row_genuinely_inverts_subsection_nesting():
    _assert_inverted_phrase_present(*_INVERTED_CONVENTION_ROWS[1])


def test_new_york_subdivision_row_genuinely_inverts_subsection_nesting():
    _assert_inverted_phrase_present(*_INVERTED_CONVENTION_ROWS[2])


def _assert_inverted_phrase_present(act_id: str, phrase: str) -> None:
    rows = _rows()
    row = next((r for r in rows if r["act_id"] == act_id), None)
    assert row is not None, f"{act_id} missing from the named-limitation fixture"
    assert phrase in row["text"], (
        f"{act_id} no longer contains {phrase!r} -- the named limitation this row is evidence "
        "for (D-S15 condition 1) rests on this exact real text; if the fixture changed, this "
        "ledger entry needs a deliberate re-check, not a silent pass"
    )
