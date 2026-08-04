"""Cycle-4 Planner tests, items 22-23 -- marker-gate over-suppression
fold-in (M-R9) and the residue table's 8th row (sprint
2026-08-04-defs-us-pr, gate P4).

## Item 22 -- marker-gate over-suppression

`extract_heading_anchored_definition`'s cycle-3 precondition gate (`if
_ENTRY_MARKER_RE.search(body): return []`) correctly protects ruling
M-R7's 3 genuine-condition/subsection-label rows, but QA found it is
BLUNTER than it needs to be: it suppresses ANY body containing a marker
ANYWHERE, not just a marker inside the CORROBORATING SENTENCE itself.
`STATE_PR_CIVIL_ART1267` (QA's own finding, already pinned `xfail(strict=
True)` in `test_pr_profile_qa_cycle4_findings.py`, not re-vendored here)
opens with a clean, unconditioned defining sentence followed by an
INCIDENTAL `(a)/(b)/(c)` examples sub-list -- structurally identical to
the shape `extract_definitions_from_section`'s own cycle-2 dispatch fix
already protects for `STATE_PR_LEY_77_1957_ART9_040`, just never ported
to this gate. This cycle's own P-R7 sweep found a 4TH real row sharing
the exact same tension: `STATE_PR_RENTAS_SEC2041_03` (heading
`"Definición de Donaciones Tributables"`, body `"(a) Definición
General.- Donaciones tributables significa..."` followed by an incidental
`(b) Donaciones Excluidas` sub-clause about a DIFFERENT, narrower
exclusion -- not a repeat of the M-R7 shape, since `"Definición
General"` unambiguously names the term being defined, unlike M-R7's `"En
General"` subsection labels).

**Adopted design (this Planner's own call, per M-R10's "fold in
normally" instruction and QA's own lean, which explicitly left the exact
mechanism to a Developer/Planner design choice rather than prescribing
one):** narrow the gate from "does the WHOLE body contain any marker" to
"does the CORROBORATING SENTENCE itself contain a marker" -- the M-R7
rows fail this narrower check too (their defining content IS a
marker-conditioned list, `"(a) Disponga...; (b) los representantes..."`,
so the corroborating sentence itself is marker-bearing), while
`STATE_PR_CIVIL_ART1267` and `STATE_PR_RENTAS_SEC2041_03` pass it (their
own defining SENTENCE is a clean, unconditioned clause; the markers sit
in a later, separate examples/exclusions sub-clause). Re-verified
independently against all 3 M-R7 rows below -- they must stay at zero
under the narrower gate too, not just under the old one.

## Item 23 -- residue table's 8th row (documentation only, no code change)

QA found `STATE_PR_LEY_77_1957_ART36_010` (heading `"Sociedades
fraternales benéficas—Definiciones"`) shares the exact CHARACTER of the
already-documented nominalization-mismatch residue
(`STATE_PR_CIVIL_ART1526`) -- a singular/plural inflection mismatch: the
heading's plural "Sociedades…benéficas" never appears verbatim in the
body, which only uses the singular "una sociedad fraternal benéfica".
Correctly yields `[]` today (re-verified live) -- this is a GREEN
correct-zero guard, not a RED gap, added for documentation completeness
per the updated `## Bucket D final split` table in the contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.pr_profile import extract_heading_anchored_definition, is_definitions_heading

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows_cycle4.json"
)


def _load(path: Path) -> dict[str, dict]:
    return {row["act_id"]: row for row in json.loads(path.read_text(encoding="utf-8"))}


@pytest.fixture()
def pr_rows():
    return _load(FIXTURE_PATH)


# --- item 22: marker-gate over-suppression ---------------------------------


def test_donaciones_tributables_captured_despite_an_incidental_sub_clause(pr_rows):
    """`STATE_PR_RENTAS_SEC2041_03`: the 4th real row sharing the M-R9
    tension, found by this cycle's own sweep (not QA's -- QA's 3 named
    rows are `STATE_PR_CIVIL_ART1267`, the twin `STATE_PR_RENTAS_
    SEC2041_03`... note: this row itself). RED today (marker-gate
    suppresses it); should yield exactly 1 candidate once the gate is
    narrowed to check only the corroborating sentence."""
    row = pr_rows["STATE_PR_RENTAS_SEC2041_03"]
    assert is_definitions_heading(row["section_title"])
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    matching = [c for c in candidates if "Donaciones tributables" in c.terms]
    assert len(matching) == 1, (
        "marker-precondition gate over-suppresses this row -- see M-R9/"
        f"QA's finding 5 and this file's module docstring; currently returns {candidates!r}"
    )


@pytest.mark.parametrize(
    "act_id",
    [
        "STATE_PR_LEY_77_1957_ART36_030",
        "STATE_PR_RENTAS_SEC2022_01",
        "STATE_PR_RENTAS_SEC2042_01",
    ],
)
def test_mr7_rows_stay_at_zero_under_the_narrower_gate_too(act_id, pr_rows):
    """The narrower "corroborating-sentence-only" gate must NOT re-open
    ruling M-R7's 3 correct-zero rows -- their own defining sentence IS
    itself the marker-conditioned list, so this must still return `[]`.
    These 3 rows already yield `[]` today (M-R7 verified, unchanged) --
    this test is a REGRESSION GUARD for the narrower gate the Developer
    is about to build, GREEN from day one, not new RED. Freshly vendored
    this cycle (never vendored as byte-verified fixture data before --
    only quoted narratively in the panel log)."""
    row = pr_rows[act_id]
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert candidates == []


# --- item 23: residue table's 8th row (documentation, GREEN) ---------------


def test_residue_8th_row_correctly_stays_zero(pr_rows):
    """`STATE_PR_LEY_77_1957_ART36_010`: singular/plural inflection
    mismatch (heading's plural "Sociedades…benéficas" vs. body's
    singular "una sociedad fraternal benéfica") -- correct-zero, GREEN
    from day one. Documentation-completeness pin for the contract's
    updated 8-row residue table, not a code-change item."""
    row = pr_rows["STATE_PR_LEY_77_1957_ART36_010"]
    assert is_definitions_heading(row["section_title"])
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    assert candidates == []
