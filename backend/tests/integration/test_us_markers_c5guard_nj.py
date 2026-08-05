"""C5 regression guard -- US-NJ (sprint 2026-08-04-defs-us-markers,
phase-2 Planner A, item A1). NOT a target: these tests pin what today's
REAL pipeline already captures for US-NJ, purely via baseline
`_split_into_numbered_blocks` + `_leading_quote_candidate` -- US-NJ has
ZERO family-3 rules registered against it (no EntrySplitterRule/
TermClauseRule matches `"US-NJ"` or `"US-*"` anywhere in
`backend/app/definition_links/rules/`, confirmed by grep before writing
this file). US-NJ is one of the five C5 working-baseline regression-guard
states (program doc `2026-08-04-definition-completeness.md`); this sprint's
zero-yield extension work must not silently shrink, duplicate, or corrupt
any of the captures pinned below. GREEN NOW; would fail if a future rule
(this panel's own A4 widening, or anyone else's) changed or swallowed
these baseline captures.

Each row's exact term SET is pinned (a regression that drops, merges, or
duplicates a term changes the set) plus one full `definition_text` pin per
row (a content-fidelity spot check, not exhaustive -- rows here carry up
to 11 terms; pinning every
one's full text would bloat this file past the 300-line convention for
marginal extra protection over the term-set check)."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_markers_c5guard_nj_rows.json"
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
        jurisdiction="US-NJ",
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


def test_c5_guard_state_nj_t58_c22_s22_3(db_session, matter_with_users):
    """STATE_NJ_T58_C22_S22-3: pins 11 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_NJ_T58_C22_S22-3")
    assert sorted(by_term) == ['Commissioner', 'Construct', 'Cost', 'Council', 'Department', 'Division', 'Net revenues', 'Operating expenses', 'Project', 'Real property', 'Water supply facility'], f"got {sorted(by_term)!r}"
    spot = by_term['Cost']
    assert spot.definition_text.strip() == 'shall mean, in addition to the usual connotations thereof, the cost of acquisition or construction of all or any part of a water supply facility and of all or any real or personal property, agreements and franchises deemed by the department to be necessary or useful and convenient therefor or in connection therewith, including interest or discount on bonds, cost of issuance of bonds, cost of geological and hydrological services, engineering and inspection costs and legal expenses, cost of financial, professional and other estimates and advice, organization, administrative, operating and other expenses prior to and during such acquisition or construction, and all such other expenses as may be necessary or incident to the financing, acquisition, construction and completion of such water supply facility or part thereof and the placing of the same in operation, and also such provision for reserves for working capital, operating, maintenance or replacement expenses and for payment or security of principal of or interest on bonds during or after such acquisition or construction as the State Comptroller may determine, and also reimbursements to the State General Fund of any moneys theretofore expended for or in connection with such water supply facility.', (
        f"content-fidelity spot check failed for 'Cost': got {spot.definition_text!r}"
    )

def test_c5_guard_state_nj_t58_c14_s14_34_11(db_session, matter_with_users):
    """STATE_NJ_T58_C14_S14-34.11: pins 9 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_NJ_T58_C14_S14-34.11")
    assert sorted(by_term) == ['Bonds', 'Commissioners', 'Contracting municipality', 'Governing body', 'Municipality', 'Original act', 'Project', 'Sewerage system', 'System revenues'], f"got {sorted(by_term)!r}"
    spot = by_term['Project']
    assert spot.definition_text.strip() == 'shall mean any or all sewers, conduits, pipe lines, mains, pumping and ventilating stations, sewage or other water-borne waste treatment or disposal systems, plants, works or apparatus, connections or outfalls deemed by the commissioners to be necessary or desirable as part of the sewerage system, including equipment or appurtenances thereof and any real or tangible personal property necessary or desirable therefor and including also all improvements necessary to relieve or prevent pollution of the Passaic river and Newark bay;', (
        f"content-fidelity spot check failed for 'Project': got {spot.definition_text!r}"
    )

def test_c5_guard_state_nj_t12a_c2_s2_104(db_session, matter_with_users):
    """STATE_NJ_T12A_C2_S2-104: pins 1 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_NJ_T12A_C2_S2-104")
    assert sorted(by_term) == ['Merchant'], f"got {sorted(by_term)!r}"
    spot = by_term['Merchant']
    assert spot.definition_text.strip() == 'means a person who deals in goods of the kind or otherwise by his occupation holds himself out as having knowledge or skill peculiar to the practices or goods involved in the transaction or to whom such knowledge or skill may be attributed by his employment of an agent or broker or other intermediary who by his occupation holds himself out as having such knowledge or skill. (2) "Financing agency" means a bank, finance company or other person who in the ordinary course of business makes advances against goods or documents of title or who by arrangement with either the seller or the buyer intervenes in ordinary course to make or collect payment due or claimed under the contract for sale, as by purchasing or paying the seller\'s draft or making advances against it or by merely taking it for collection whether or not documents of title accompany the draft. "Financing agency" includes also a bank or other person who similarly intervenes between persons who are in the position of seller and buyer in respect to the goods (12A:2-707). (3) "Between merchants" means in any transaction with respect to which both parties are chargeable with the knowledge or skill of merchants. L.1961, c. 120, s. 2-104.', (
        f"content-fidelity spot check failed for 'Merchant': got {spot.definition_text!r}"
    )

def test_c5_guard_state_nj_t54_c8a_s8a_61(db_session, matter_with_users):
    """STATE_NJ_T54_C8A_S8A-61: pins 1 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_NJ_T54_C8A_S8A-61")
    assert sorted(by_term) == ['Critical area state'], f"got {sorted(by_term)!r}"
    spot = by_term['Critical area state']
    assert spot.definition_text.strip() == 'means this State and such other state bordering thereon within which there exists part of an area, another part of which is in this State, and within which area there is, as of January 1 of any year, a severe transportation problem in respect to the transportation of persons and property interstate. (b) The Legislature finds and declares that a severe transportation problem exists in connection with transportation interstate between this State and another state bordering thereon due to the number of daily commuters between said states as to create a severe peak-load demand requiring facilities and services, by any means or mode of transportation far in excess of those needed for normal travel outside of usual commuter hours, caused by the carrying on of activities in one of the states by persons residing in another, from which activities such persons derive income or gain from sources within the state other than that in which they reside. The Legislature finds and declares that whenever the total number of annual crossings by persons residing in one of such states who are employed, or carry on a trade, business, occupation or profession in the other state plus the number of annual crossings by persons residing in the other state who are employed, or carry on a trade, business, occupation or profession in the first state exceeds 100,000,000 but is less than 300,000,000, that fact reasonably demonstrates that a severe transportation problem exists. If the number of annual crossings as set forth in this section is found to exist by the Commissioner of Transportation in accordance with subsection (c) hereof, the provisions of this act shall take effect and the provisions of the Emergency Transportation Tax Act, P.L.1961, c. 32 (C. 54:8A-1 et seq.) shall not be applicable to persons subject to tax under this act. (c) On or before December 31, 1971, and within 40 days after the first day of each year hereafter, so long as this act shall remain in effect, the State Transportation Commissioner shall certify to the State Treasurer his findings with respect to the existence of the conditions herein set forth and the identity of any states which he determines to come within the definition in this section. Upon receipt of such certification, the State Treasurer shall cause public notice thereof to be given, by publication in such newspaper or newspapers, and in such form, as he shall find will fairly apprise all persons subject to taxation under this act, of the making of said certification and of the significance thereof to such persons. Any certification so made shall be effective for the entire calendar year as of the first day of which it ascertains the facts. L.1971, c. 222, s. 4, approved June 17, 1971. Amended by L.1971, c. 354, s. 3; expired December 31, 1980 pursuant to L.1971,c.222,s.62.', (
        f"content-fidelity spot check failed for 'Critical area state': got {spot.definition_text!r}"
    )

def test_c5_guard_state_nj_t12a_c2_s2_105(db_session, matter_with_users):
    """STATE_NJ_T12A_C2_S2-105: pins 1 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_NJ_T12A_C2_S2-105")
    assert sorted(by_term) == ['Goods'], f"got {sorted(by_term)!r}"
    spot = by_term['Goods']
    assert spot.definition_text.strip() == 'means all things (including specially manufactured goods) which are movable at the time of identification to the contract for sale other than the money in which the price is to be paid, investment securities (Chapter 8) and things in action. "Goods" also includes the unborn young of animals and growing crops and other identified things attached to realty as described in the section on goods to be severed from realty (12A:2-107). (2) Goods must be both existing and identified before any interest in them can pass. Goods which are not both existing and identified are "future" goods. A purported present sale of future goods or of any interest therein operates as a contract to sell. (3) There may be a sale of a part interest in existing identified goods. (4) An undivided share in an identified bulk of fungible goods is sufficiently identified to be sold although the quantity of the bulk is not determined. Any agreed proportion of such a bulk or any quantity thereof agreed upon by number, weight or other measure may to the extent of the seller\'s interest in the bulk be sold to the buyer who then becomes an owner in common. (5) "Lot" means a parcel or a single article which is the subject matter of a separate sale or delivery, whether or not it is sufficient to perform the contract. (6) "Commercial unit" means such a unit of goods as by commercial usage is a single whole for purposes of sale and division of which materially impairs its character or value on the market or in use. A commercial unit may be a single article (as a machine) or a set of articles (as a suit of furniture or an assortment of sizes) or a quantity (as a bale, gross, or carload) or any other unit treated in use or in the relevant market as a single whole. L.1961, c. 120, s. 2-105.', (
        f"content-fidelity spot check failed for 'Goods': got {spot.definition_text!r}"
    )

def test_c5_guard_state_nj_t58_c21b_s21b_2(db_session, matter_with_users):
    """STATE_NJ_T58_C21B_S21B-2: pins 3 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_NJ_T58_C21B_S21B-2")
    assert sorted(by_term) == ['Commissioner', 'Real property', 'Water supply facility'], f"got {sorted(by_term)!r}"
    spot = by_term['Water supply facility']
    assert spot.definition_text.strip() == 'means and refers to the real property and the plants, structures, machinery and equipment and other property, real, personal and mixed, acquired, constructed or operated, or to be acquired, constructed or operated in whole or in part by or on behalf of the State, for the purpose of augmenting the natural water resources of the State and making available an increased supply of water for all uses, and any and all appurtenances necessary, useful or convenient for the collecting, impounding, storing, improving or transmitting of water, and for the preserving and protecting of these resources and facilities and providing for the conservation and development of future water supply resources, and facilitating incidental recreational uses thereof;', (
        f"content-fidelity spot check failed for 'Water supply facility': got {spot.definition_text!r}"
    )

def test_c5_guard_state_nj_t48_c10_s10_3(db_session, matter_with_users):
    """STATE_NJ_T48_C10_S10-3: pins 1 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_NJ_T48_C10_S10-3")
    assert sorted(by_term) == ['Board'], f"got {sorted(by_term)!r}"
    spot = by_term['Board']
    assert spot.definition_text.strip() == 'shall mean the Board of Public Utility Commissioners of New Jersey. (b) "Natural gas pipeline utility" shall mean any individual, co-partnership, association, corporation, or joint stock company, their lessees, trustees or receivers appointed by any court whatsoever, that now or hereafter may own, operate, manage, or control any pipeline used for the transmission of natural gas within or through this State, but shall not include any individual, co-partnership, association, corporation, or joint stock company which, within this State, is engaged in the business of manufacturing, buying, or selling manufactured, mixed, or natural gas or a mixture of such gases with other gases and distributing the same to consumers within this State. (c) "Pipeline" shall include compressor plants and other facilities integrated with pipeline operations. L.1952, c. 166, p. 540, s. 2, eff. May 9, 1952.', (
        f"content-fidelity spot check failed for 'Board': got {spot.definition_text!r}"
    )
