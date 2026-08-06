"""QA1 (phase-2 QA cycle 1) -- Q6: independent re-derivation of the 224
provably correctly-empty rows (ruling U-R3), plus the false-positive
sweep the brief says "has never been done" (sprint
2026-08-04-defs-us-markers, gate U4).

**Re-derivation, corpus-wide (all 53 jurisdictions), against the CURRENT
build's real zero-yield population (scratchpad
`markers-qa-q6-correctly-empty-sweep.py`, not committed per data policy --
no test reads the corpus):**

The claimed 224 (184 DC terminal + 40 cross-reference: WY19/MN6/UT5/WA4/
TX2/WI2/AL1/NC1) reproduces EXACTLY as a SUBSET of what I measure -- but
only on the DIRECT-title-recognition-only denominator (21,072
zero-yield rows). On the body-derived-heading-INCLUSIVE denominator
(21,642 zero-yield rows -- the basis this pass's own zero-yield sweeps
elsewhere in this file use, matching the manager's own scratchpad sweep
style), I measure **267**: the same 224 PLUS 43 more (42 CA + 1 GA, both
`cross_reference`) that only exist because CA/GA are reachable at all via
`derive_heading_from_body` (their real `section_title` is a bare
placeholder, e.g. `"Section 12851"` -- never itself Definitions-
recognized). **This is a genuine, material denominator-basis ambiguity,
not a discrepancy in the classifier** -- flagged explicitly per Q7's own
instruction, since which of 224/267 is "the" certification number depends
entirely on whether body-derived headings count as "recognized," a
question this pass does not resolve unilaterally (see Q7's own findings
in the sprint log for the full analysis).

**False-positive sweep (the check that had never been done): every row
this build's `classify_correctly_empty` calls correctly-empty, in the 7
jurisdictions NEVER adversarially checked before** (the manager's own M4/
M5 full-corpus adversarial sweep -- the one that previously found and
fixed 4 real WA false positives -- covered only WA/VA/FED/DC/WI/WY).
**AL/CA/GA/MN/NC/TX/UT's 58 `cross_reference` hits were inspected
EXHAUSTIVELY (all 58, not a sample) against their real bodies this pass:
ZERO false positives.** Every one of the 58 is, verbatim, nothing but a
single "The definitions in/contained in/set forth in <citation> apply/
govern/are applicable ..." sentence with no operative defining content
anywhere -- no exceptions, no self-referential-preamble-plus-real-content
shape like the WA rows the classifier was originally bounced for.
Additionally re-confirmed (not merely trusted from the prior pass) the
previously-checked WA (4), WI (2), and WY (19) `cross_reference` rows
against their real current bodies, plus a random 10-row spot-sample of
DC's 184 `terminal_status` rows -- all clean.

**Representative sample committed here as a permanent regression guard**
(one real row per newly-verified jurisdiction: AL/CA/GA/MN/NC/TX/UT) --
not exhaustive of all 58 (the full inspection lives in this pass's
scratchpad and the sprint log), but enough that a future regex change
which silently breaks any of these 7 jurisdictions' genuine
cross-reference shape turns immediately RED, not just "encouraged by
Finding 2's honest report."

All 7 rows vendored verbatim, byte-verified against their respective
`us_<state>_statutes.parquet` files this pass.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.correctly_empty import classify_correctly_empty
from app.definition_links.us_profile import is_definitions_heading

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_qa_q6_correctly_empty_new_jurisdictions_rows.json"
)

# (act_id, jurisdiction) -- one real, never-before-adversarially-checked
# genuine cross-reference row per jurisdiction.
_CASES = [
    ("STATE_AL_T13A_C7_S13A-7-20", "US-AL"),
    ("STATE_CA_Cwat_D6_P6_C4_A2_S12851", "US-CA"),
    ("STATE_GA_T22_C4_S22-4-3", "US-GA"),
    ("STATE_MN_P245_267_C246_S246.0012", "US-MN"),
    ("STATE_NC_C75A_S75A-33", "US-NC"),
    ("STATE_TX_Cwa_C12_S12.001", "US-TX"),
    ("STATE_UT_T11_S11_3_3.1", "US-UT"),
]


def _load_rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def test_all_7_rows_are_genuinely_definitions_headed_or_body_derived():
    """Sanity: every fixture row is a real Definitions-labeled section
    (directly, or -- CA's own placeholder-heading shape -- via body
    derivation), matching the precondition `classify_correctly_empty`
    assumes its caller has already confirmed."""
    rows = _load_rows()
    from app.definition_links.us_profile import USProfile

    for act_id, code in _CASES:
        row = rows[act_id]
        profile = USProfile(code=code)
        title = row["section_title"]
        text = row["text"]
        direct = is_definitions_heading(title)
        if not direct:
            derived = profile.derive_heading_from_body(title, text)
            assert derived is not None and is_definitions_heading(derived), (
                f"{act_id}: neither directly Definitions-headed nor body-derivable -- "
                "the fixture no longer matches this test's own precondition"
            )


def test_zero_candidates_extracted_precondition_holds():
    """Sanity: `classify_correctly_empty`'s result is only meaningful once
    extraction already returned zero candidates for this body -- confirms
    that still holds on this build for all 7 rows (not merely assumed)."""
    from app.definition_links.us_profile import USProfile

    rows = _load_rows()
    for act_id, code in _CASES:
        row = rows[act_id]
        profile = USProfile(code=code)
        text = row["text"]
        title = row["section_title"]
        derived = False
        if not is_definitions_heading(title):
            dh = profile.derive_heading_from_body(title, text)
            assert dh is not None
            derived = True
        scope = profile.determine_scope(text)
        cands = profile.extract_definitions_from_section(text, scope=scope, heading_was_derived=derived)
        assert cands == [], f"{act_id}: extraction now yields candidates -- re-derive this test"


def test_all_7_never_before_checked_jurisdictions_classify_correctly_empty_true():
    """The regression guard: none of these 7 real, newly-verified rows
    (AL/CA/GA/MN/NC/TX/UT -- never adversarially checked before this
    pass) should ever stop classifying as correctly-empty, and every one
    must classify for the `cross_reference` reason specifically (matching
    this pass's exhaustive 58-row inspection, all genuine single-sentence
    cross-references, zero false positives)."""
    rows = _load_rows()
    for act_id, _code in _CASES:
        result = classify_correctly_empty(rows[act_id]["text"])
        assert result.is_correctly_empty is True, (
            f"{act_id}: no longer classified correctly-empty -- got {result!r}. If this "
            "body genuinely gained operative content, update this test; if not, the "
            "classifier regressed on a jurisdiction proven clean this pass."
        )
        assert result.reason == "cross_reference", (
            f"{act_id}: expected reason 'cross_reference', got {result.reason!r}"
        )
