"""C5 regression guard -- US-MI (sprint 2026-08-04-defs-us-markers,
phase-2 Planner A, item A1). NOT a target: these tests pin what today's
REAL pipeline already captures for US-MI, purely via baseline
`_split_into_numbered_blocks` + `_leading_quote_candidate` -- US-MI has
ZERO family-3 rules registered against it (no EntrySplitterRule/
TermClauseRule matches `"US-MI"` or `"US-*"` anywhere in
`backend/app/definition_links/rules/`, confirmed by grep before writing
this file). US-MI is one of the five C5 working-baseline regression-guard
states (program doc `2026-08-04-definition-completeness.md`); this sprint's
zero-yield extension work must not silently shrink, duplicate, or corrupt
any of the captures pinned below. GREEN NOW; would fail if a future rule
(this panel's own A4 widening, or anyone else's) changed or swallowed
these baseline captures.

Each row's exact term SET is pinned (a regression that drops, merges, or
duplicates a term changes the set) plus one full `definition_text` pin per
row (a content-fidelity spot check, not exhaustive -- rows here carry up
to 16 terms; pinning every
one's full text would bloat this file past the 300-line convention for
marginal extra protection over the term-set check).

**Re-pinned 2026-08-05 (phase-3 Planner, U-R17/M35 work order item 1)**:
Developer C's US-MI registration surfaces one additional genuine term
('Transient guest'), verified against source, RULING U-R16 vacated
(the earlier spurious-fragment theory did not survive verification).
No class-B (defective-text) terms on this file's rows -- MI is not on
`## M37`'s closed 15-of-75 list."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_markers_c5guard_mi_rows.json"
)


def _load_rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def _run(db_session, matter_with_users, act_id: str):
    rows = _load_rows()
    row = rows[act_id]
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title=f"{act_id} C5 guard",
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction="US-MI",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term = {}
    for d in definitions:
        for t in d.terms:
            by_term[t] = d
    return by_term


def test_c5_guard_state_mi_c206_aact_281_of_1967_s206_278(db_session, matter_with_users):
    """STATE_MI_C206_AAct-281-of-1967_S206.278: pins 4 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_MI_C206_AAct-281-of-1967_S206.278")
    assert sorted(by_term) == ['Board', 'Michigan strategic fund', 'Qualified business', 'Qualified investment'], f"got {sorted(by_term)!r}"
    spot = by_term['Qualified investment']
    assert spot.definition_text.strip() == "means, except as otherwise provided under this subdivision, an investment of at least $20,000.00 certified by the Michigan strategic fund that is made alongside of, or through, a seed venture capital or angel investor group that is registered with the Michigan strategic fund and is not in a business in which any member of the investor's family is an employee or owner of the business or in which the investor or any member of the investor's family has a preexisting fiduciary relationship with the business. Qualified investment does not include an investment in a business that engages in life sciences technology unless those activities are included in the definition of life sciences as that term is defined under section 88a of the Michigan strategic fund act, 1984 PA 270, MCL 125.2088a.\n\nHistory: Add. 2010, Act 235, Imd. Eff. Dec. 14, 2010; Am. 2011, Act 38, Eff. Jan. 1, 2012", (
        f"content-fidelity spot check failed for 'Qualified investment': got {spot.definition_text!r}"
    )

def test_c5_guard_state_mi_c141_aact_244_of_1989_s141_892(db_session, matter_with_users):
    """STATE_MI_C141_AAct-244-of-1989_S141.892: pins 14 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_MI_C141_AAct-244-of-1989_S141.892")
    # Re-pinned per U-R16/U-R17 (M34/M35/M37): devC's US-MI registration adds
    # 'Transient guest' as a genuine new capture, not on the closed
    # class-B list (ends with a real terminal period, verified).
    assert sorted(by_term) == ['Assessment', 'Assessment revenues', 'Board', 'Director', 'Master plan', 'Owner', 'Regional assessment district', 'Regional marketing organization', 'Room', 'Room charge', 'Tourism marketing program', 'Tourism marketing program notice', 'Transient facility', 'Transient guest', 'Travel bureau'], f"got {sorted(by_term)!r}"
    spot = by_term['Transient facility']
    assert spot.definition_text.strip() == 'means a building or combination of buildings under common ownership, operation, or management that contains 10 or more rooms used in the business of providing dwelling, lodging, or sleeping to transient guests, whether or not membership is required for the use of the rooms. Transient facility includes a building or combination of buildings, the owner of which has elected to come under the provisions of this act pursuant to section 9. Transient facility does not include a college or school dormitory; a hospital; a nursing home; a hospice; a building or combination of buildings that is otherwise a transient facility, but that is located within 1 mile of a ski lift as defined in section 2 of the ski area safety act of 1962, 1962 PA 199, MCL 408.322; or a facility owned and operated by an organization qualified for an exemption from federal taxation under section 501(c) of the internal revenue code.\n\n( l ) "Transient guest" means a natural person who occupies a room in a transient facility for less than 30 consecutive days regardless of who pays the room charge.', (
        f"content-fidelity spot check failed for 'Transient facility': got {spot.definition_text!r}"
    )

def test_c5_guard_state_mi_c408_aact_98_of_2011_s408_873(db_session, matter_with_users):
    """STATE_MI_C408_AAct-98-of-2011_S408.873: pins 2 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_MI_C408_AAct-98-of-2011_S408.873")
    assert sorted(by_term) == ['Facility', 'Governmental unit'], f"got {sorted(by_term)!r}"
    spot = by_term['Facility']
    assert spot.definition_text.strip() == "means any actual physical improvement to real property owned, or leased, directly or through a building authority, by a governmental unit, including, but not limited to, roads; bridges; runways; rails; or a building or structure along with the building's or structure's grounds, approaches, services, and appurtenances.", (
        f"content-fidelity spot check failed for 'Facility': got {spot.definition_text!r}"
    )

def test_c5_guard_state_mi_c440_aact_174_of_1962_s440_8102(db_session, matter_with_users):
    """STATE_MI_C440_AAct-174-of-1962_S440.8102: pins 16 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_MI_C440_AAct-174-of-1962_S440.8102")
    assert sorted(by_term) == ['Adverse claim', 'Bearer form', 'Broker', 'Certificated security', 'Clearing corporation', 'Communicate', 'Entitlement holder', 'Entitlement order', 'Financial asset', 'Indorsement', 'Instruction', 'Securities intermediary', 'Security', 'Security certificate', 'Security entitlement', 'Uncertificated security'], f"got {sorted(by_term)!r}"
    spot = by_term['Financial asset']
    assert spot.definition_text.strip() == ", except as otherwise provided in section 8103, means 1 or more of the following:\n\n( i ) A security.\n\n( ii ) An obligation of a person or a share, participation, or other interest in a person or in property or an enterprise of a person, which is, or is of a type, dealt in or traded on financial markets, or which is recognized in any area in which it is issued or dealt in as a medium for investment.\n\n( iii ) Any property that is held by a securities intermediary for another person in a securities account if the securities intermediary has expressly agreed with the other person that the property is to be treated as a financial asset under this article. As context requires, the term means either the interest itself or the means by which a person's claim to it is evidenced, including a certificated or uncertificated security, a security certificate, or a security entitlement.", (
        f"content-fidelity spot check failed for 'Financial asset': got {spot.definition_text!r}"
    )

def test_c5_guard_state_mi_c205_aact_167_of_1933_s205_54u(db_session, matter_with_users):
    """STATE_MI_C205_AAct-167-of-1933_S205.54u: pins 1 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_MI_C205_AAct-167-of-1933_S205.54u")
    assert sorted(by_term) == ['Extractive operations'], f"got {sorted(by_term)!r}"
    spot = by_term['Extractive operations']
    assert spot.definition_text.strip() == 'means the activity of taking or extracting for resale ore, oil, gas, coal, timber, stone, gravel, clay, minerals, or other natural resource material. An extractive operation begins when contact is made with the actual type of natural raw product being recovered. Extractive operation includes all necessary processing operations before shipment from the place of extraction. Extractive operations include all necessary processing operations and movement of the natural resource material until the point at which the natural raw product being recovered first comes to rest in finished goods inventory storage at the extraction site. Extractive operations for timber include transporting timber from the point of extraction to a place of temporary storage at the extraction site and loading or transporting timber from a place of temporary storage at the extraction site to a vehicle or other equipment located at the extraction site that will remove the timber from the extraction site.\n\n(b) An extractive operator is a person who, either directly or by contract, performs extractive operations.\n\nHistory: Add. 1999, Act 116, Imd. Eff. July 14, 1999; Am. 2004, Act 173, Eff. Sept. 1, 2004; Am. 2008, Act 556, Eff. Jan. 20, 2009', (
        f"content-fidelity spot check failed for 'Extractive operations': got {spot.definition_text!r}"
    )

def test_c5_guard_state_mi_c257_aact_198_of_1965_s257_1102(db_session, matter_with_users):
    """STATE_MI_C257_AAct-198-of-1965_S257.1102: pins 5 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_MI_C257_AAct-198-of-1965_S257.1102")
    assert sorted(by_term) == ['Fund', 'Person', 'Secretary', 'Treasurer', 'Uninsured motor vehicle'], f"got {sorted(by_term)!r}"
    spot = by_term['Person']
    assert spot.definition_text.strip() == 'includes natural persons, firms, copartnerships, associations, and corporations, except this state or an agency or political subdivision of this state. Person does not include a municipal corporation or a corporation owned or operated by this state or a political subdivision of this state.\n\nHistory: 1965, Act 198, Eff. Nov. 1, 1965; Am. 1967, Act 274, Imd. Eff. July 20, 1967; Am. 1971, Act 211, Imd. Eff. Dec. 29, 1971; Am. 2012, Act 572, Imd. Eff. Jan. 2, 2013', (
        f"content-fidelity spot check failed for 'Person': got {spot.definition_text!r}"
    )
