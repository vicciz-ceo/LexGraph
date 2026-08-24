"""QA regression coverage -- sprint 2026-08-23-defs-debt-31 (issue #31),
Item 4 (FX7 remainder ledger, gate 4). Independent QA pass verified PASS:
101 ceiling-tripped candidates individually adjudicated UNRECOVERABLE,
cross-checked (0 overlap) against Item 5's own certified delta. This file
pins coverage the Developer's own committed evidence tests
(`test_us_markers_defs_debt_31_fx7_remainder_evidence.py`, 2 structural
reproductions) do not already provide: the committed ledger's own headline
counts, and two small REAL rows (own live-pipeline spot-check during QA,
independent of `adjudicate_item4_ledger.py`) confirmed still genuinely
ceiling-tripped -- absent from the real, ceiling-respecting production
output, present only when `MAX_CLEAN_DEFINITION_LENGTH` is monkeypatched
unbounded, at the EXACT length the ledger records.

Live-path: both exemplars call `USProfile.extract_definitions_from_section`
directly (the real production method every one of the 101 ledger rows was
adjudicated through), same calling convention as `test_us_markers_defs_
debt_31_bleed_trim_structural_red.py`'s own structural tests -- not a
reimplementation of the extraction logic.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from app.definition_links.normalize import strip_wikilinks
from app.definition_links.profiles import get_profile
from app.definition_links.rules import us_markers_boundary

ROOT = Path(__file__).resolve().parents[3]
LEDGER_PATH = ROOT / "docs/sprint/sprints/2026-08-23-defs-debt-31-scripts/item4_ledger.jsonl"


def _load_ledger() -> list[dict]:
    return [json.loads(line) for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines() if line]


def test_item4_ledger_headline_counts_are_unchanged():
    """Cheap integrity pin on the committed 101-row ledger (Gate 4, P-R11):
    all 101 UNRECOVERABLE, the per-jurisdiction census breakdown matches
    `item4_fx7_remainder_ledger.md`'s own table exactly, and every row
    carries the shared structural reason. Independently re-derived from
    `item4_ledger.jsonl` during this QA pass and confirmed to match; this
    test pins the aggregate so a future accidental edit/regeneration of the
    evidence file is caught without a live corpus re-run."""
    rows = _load_ledger()
    assert len(rows) == 101, f"expected 101 ledger rows, got {len(rows)}"
    assert all(r["verdict"] == "UNRECOVERABLE" for r in rows), (
        "every ledger row must be individually adjudicated UNRECOVERABLE "
        "(gate 4's own bar: recovered or adjudicated, never silently skipped)"
    )
    unique_keys = {(r["act_id"], r["term"]) for r in rows}
    assert len(unique_keys) == 101, "ledger rows must be 101 distinct (act_id, term) anchors, no duplicates"

    by_jur: dict[str, int] = {}
    for r in rows:
        by_jur[r["jurisdiction"]] = by_jur.get(r["jurisdiction"], 0) + 1
    expected_by_jur = {
        "US-FED": 12, "US-UT": 1, "US-TX": 3, "US-SC": 12, "US-AZ": 4,
        "US-NJ": 45, "US-MI": 19, "US-NY": 1, "US-OK": 2, "US-NM": 1, "US-WA": 1,
    }
    assert by_jur == expected_by_jur, f"per-jurisdiction census drifted: {by_jur}"
    assert sum(expected_by_jur.values()) == 101


def test_item4_nj_vendor_still_genuinely_ceiling_tripped():
    """`STATE_NJ_T54_C32F_S32F-1`, term "Vendor" (real, small NJ tire-fee
    row, own live spot-check during QA verification -- ledger's own
    recorded `unbounded_definition_text_len`: 3088). "Vendor" is the LAST
    of 5 semicolon-joined definitions in one run-on sentence
    ("...and "Vendor" means any entity engaged in..."); the real,
    ceiling-respecting engine never finds a closing boundary for it before
    tripping `MAX_CLEAN_DEFINITION_LENGTH` (3000), so it is silently
    absent from today's real production output entirely -- not merely
    truncated. FX7-protected territory (gate 8): Item 1's trim is scoped
    to never reach `EntrySplitterRule`-sourced candidates like this one."""
    text = (
        '1. a. As used in this section: "Division" means the Division of Taxation in the '
        'Department of the Treasury; "Director" means the Director of the Division of '
        'Taxation in the Department of the Treasury; "Motor vehicle" includes any vehicle '
        'propelled otherwise than by muscular power, including trailers and semi trailers, '
        'or any other type of vehicle drawn by a motor vehicle, designed for use on the '
        'public highways, but excepting a vehicle that runs only upon rails or tracks; '
        '"New motor vehicle tire" shall not include a recapped tire; "Tire" means a '
        'continuous covering encircling a wheel for a motor vehicle in which a person or '
        'property is or may be transported or which is or may be drawn upon a road or '
        'highway; and "Vendor" means any entity engaged in the retail sale of new motor '
        'vehicle tires, the retail sale of new motor vehicle tires sold as a component part '
        'of a motor vehicle, and the purchase for lease or rental of new motor vehicle tires '
        'transferred as a component part of a leased motor vehicle. b. There is imposed on '
        'the purchaser a fee of $1.50 upon the sale of a new motor vehicle tire if: that sale '
        'is subject to the sales tax imposed pursuant to the "Sales and Use Tax Act," '
        'P.L.1966, c.30 (C.54:32B-1 et seq.), including new motor vehicle tires sold as a '
        'component part of a motor vehicle if the sale of the motor vehicle is subject to the '
        'sales tax and new motor vehicle tires transferred as a component part of the lease '
        'of a motor vehicle if the purchase for lease of the motor vehicle is subject to the '
        'sales tax. The fee imposed under this section shall be collected by the vendor and, '
        'except in the case of vendors engaged in the retail sale of new motor vehicle tires '
        'sold as a component part of a motor vehicle, and in the lease or rental of new motor '
        'vehicle tires transferred as a component part of a leased motor vehicle, shall be '
        'separately stated on any bill, receipt, invoice or similar document provided to the '
        'purchaser, but shall not be considered part of the receipt for purpose of determining '
        'tax pursuant to P.L.1966, c.30. c. The fee shall not be imposed on the sale of a new '
        'motor vehicle tire, including new motor vehicle tires sold as a component part of a '
        'motor vehicle or transferred as a component part of a leased motor vehicle, if the '
        'purchaser or transferee is exempt from the tax imposed under the "Sales and Use Tax '
        'Act" pursuant to subsection (a) or (b) of section 9 of P.L.1966, c.30 (C.54:32B-9). '
        'd. Each person required to collect the fee imposed by this section shall be '
        'personally liable for the fee imposed, collected or required to be collected under '
        'this section. Any such person shall have the same right in respect to collecting the '
        'fee from a purchaser as if the fee were a part of the sales price and payable at the '
        'same time. e. In carrying out the provisions of this section, the director shall '
        'have all of the powers and authority granted in P.L.1966, c.30 (C.54:32B-1 et seq.). '
        'The fee shall be filed and paid in a manner prescribed by the director. The director '
        'shall promulgate such rules and regulations as the director determines are necessary '
        'to effectuate the provisions of this section. f. The fee imposed by this section '
        'shall be governed by the provisions of the "State Uniform Tax Procedure Law," '
        'R.S.54:48-1 et seq. g. Notwithstanding any provision of P.L.1968, c.410 '
        '(C.52:14B-1 et seq.) to the contrary, the director may adopt immediately upon filing '
        'with the Office of Administrative Law such regulations as the director deems '
        'necessary to implement the provisions of this act, which shall be effective for a '
        'period not to exceed 180 days following enactment of P.L.2004, c.46 (C.54:32F-1 et '
        'al.) and may thereafter be amended, adopted or readopted by the director in '
        'accordance with the requirements of P.L.1968, c.410. L.2004,c.46,s.1.'
    )
    heading = "Definitions relative to local tire management program; fee, imposition, collection."
    profile = get_profile("US-NJ")
    body, _ = strip_wikilinks(profile.normalize_for_parsing(text))
    scope = profile.determine_scope(body)
    recognized = profile.is_definitions_heading(heading, body)

    real = profile.extract_definitions_from_section(body, scope=scope, heading_was_derived=not recognized)
    real_terms = {t for c in real for t in c.terms}
    assert "Vendor" not in real_terms, (
        f"'Vendor' must still be genuinely absent from the real, ceiling-respecting "
        f"output (ledger's own UNRECOVERABLE verdict) -- got terms {sorted(real_terms)}"
    )

    with mock.patch.object(us_markers_boundary, "MAX_CLEAN_DEFINITION_LENGTH", 10**9):
        unbounded = profile.extract_definitions_from_section(body, scope=scope, heading_was_derived=not recognized)
    unbounded_len = next((len(c.definition_text) for c in unbounded if "Vendor" in c.terms), None)
    assert unbounded_len == 3088, (
        f"unbounded-ceiling probe must reproduce the ledger's own recorded "
        f"unbounded_definition_text_len (3088) -- got {unbounded_len}"
    )


def test_item4_tx_insurable_property_still_genuinely_ceiling_tripped():
    """`STATE_TX_Cin_C2210_S2210.004`, term "insurable property" (real,
    small TX windstorm-insurance row, own live spot-check during QA
    verification -- ledger's own recorded `unbounded_definition_text_len`:
    3203). The definition runs through lettered/numbered sub-clauses
    (b)-(h) with no quoted next-term boundary anywhere in the row, so the
    real engine never closes it before the ceiling trips."""
    text = (
        '(a) Except as provided by Subsection (h), for purposes of this chapter and subject '
        'to this section, "insurable property" means immovable property at a fixed location '
        'in a catastrophe area or corporeal movable property located in that immovable '
        'property, as designated in the plan of operation, that is determined by the '
        'association according to the criteria specified in the plan of operation to be in '
        'an insurable condition against windstorm and hail, as determined by normal '
        'underwriting standards. The term includes property described by Section 2210.209.'
        '\n\n(b) A structure located in a catastrophe area, construction of which began on '
        'or after the 30th day after the date of publication of the plan of operation, that '
        'is not built in compliance with building specifications set forth in the plan of '
        'operation or continued in compliance with those specifications, does not constitute '
        'an insurable risk for purposes of windstorm and hail insurance except as otherwise '
        'provided by this chapter.\n\n(c) A structure, or an addition to a structure, that is '
        'constructed in conformity with plans and specifications that comply with the '
        'specifications set forth in the plan of operation at the time construction begins '
        'may not be declared ineligible for windstorm and hail insurance as a result of '
        'subsequent changes in the building specifications set forth in the plan of '
        'operation.\n\n(d) Except as otherwise provided by this section, if repair of damage '
        'to a structure involves replacement of items covered in the building specifications '
        'set forth in the plan of operation, the repairs must be completed in a manner that '
        'complies with those specifications for the structure to continue to be insurable '
        'property for windstorm and hail insurance.\n\n(e) If repair to a structure, other '
        'than a roof repair that exceeds 100 square feet, is less than five percent of the '
        'total amount of property coverage on the structure, the repairs may be completed in '
        'a manner that returns the structure to the structure\'s condition immediately before '
        'the loss without affecting the eligibility of the structure to qualify as insurable '
        'property.\n\n(f) This chapter does not preclude special rating of individual risks '
        'as may be provided in the plan of operation.\n\n(g) For purposes of this chapter, a '
        'residential structure is insurable property if:\n\n(1) the residential structure is '
        'not:\n\n(A) a condominium, apartment, duplex, or other multifamily residence; or\n\n'
        '(B) a hotel or resort facility;\n\n(2) the residential structure is located within '
        'an area designated as a unit under the Coastal Barrier Resources Act (Pub. L. No. '
        '97-348); and\n\n(3) a building permit or plat for the residential structure was '
        'filed with the municipality, the county, or the United States Army Corps of '
        'Engineers before June 11, 2003.\n\n(h) For purposes of this chapter, a structure is '
        'not insurable property if the commissioner of the General Land Office notifies the '
        'association of a determination that the structure is located on the public beach '
        'under procedures established under Section 61.011, Natural Resources Code, and that '
        'the structure:\n\n(1) constitutes an imminent hazard to safety, health, or public '
        'welfare; or\n\n(2) substantially interferes with the free and unrestricted right of '
        'the public to enter or leave the public beach or traverse any part of the public '
        'beach.'
    )
    heading = "§ 2210.004. DEFINITION OF INSURABLE PROPERTY."
    profile = get_profile("US-TX")
    body, _ = strip_wikilinks(profile.normalize_for_parsing(text))
    scope = profile.determine_scope(body)
    recognized = profile.is_definitions_heading(heading, body)

    real = profile.extract_definitions_from_section(body, scope=scope, heading_was_derived=not recognized)
    real_terms = {t for c in real for t in c.terms}
    assert "insurable property" not in real_terms, (
        f"'insurable property' must still be genuinely absent from the real, "
        f"ceiling-respecting output (ledger's own UNRECOVERABLE verdict) -- "
        f"got terms {sorted(real_terms)}"
    )

    with mock.patch.object(us_markers_boundary, "MAX_CLEAN_DEFINITION_LENGTH", 10**9):
        unbounded = profile.extract_definitions_from_section(body, scope=scope, heading_was_derived=not recognized)
    unbounded_len = next(
        (len(c.definition_text) for c in unbounded if "insurable property" in c.terms), None
    )
    assert unbounded_len == 3203, (
        f"unbounded-ceiling probe must reproduce the ledger's own recorded "
        f"unbounded_definition_text_len (3203) -- got {unbounded_len}"
    )
