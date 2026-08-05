"""C5 regression guard -- US-OK (sprint 2026-08-04-defs-us-markers,
phase-2 Planner A, item A1). NOT a target: these tests pin what today's
REAL pipeline already captures for US-OK, purely via baseline
`_split_into_numbered_blocks` + `_leading_quote_candidate` -- US-OK has
ZERO family-3 rules registered against it (no EntrySplitterRule/
TermClauseRule matches `"US-OK"` or `"US-*"` anywhere in
`backend/app/definition_links/rules/`, confirmed by grep before writing
this file). US-OK is one of the five C5 working-baseline regression-guard
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
marginal extra protection over the term-set check)."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_markers_c5guard_ok_rows.json"
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
        jurisdiction="US-OK",
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


def test_c5_guard_state_ok_t15_s15_32(db_session, matter_with_users):
    """STATE_OK_T15_S15-32: pins 3 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_OK_T15_S15-32")
    assert sorted(by_term) == ['educational institution', 'educational loan', 'person'], f"got {sorted(by_term)!r}"
    spot = by_term['educational institution']
    assert spot.definition_text.strip() == 'means any university, college,\n\ncommunity college, junior college, high school, technical,\n\nvocational or professional school, wherever located, approved or\n\naccredited by that officer, department, board, agency or other\n\nofficial entity of this state, authorized under law to approve or to\n\naccredit for educational purposes that particular type of\n\nuniversity, college, school or institution of learning, or, in the\n\nabsence, as to the particular type of institution, of any such\n\nofficer, department, board, agency or other official entity, by the\n\nState Board of Education, for the purposes of this act, or by the\n\nappropriate official, department or agency of the state in which the\n\ninstitution is located; and', (
        f"content-fidelity spot check failed for 'educational institution': got {spot.definition_text!r}"
    )

def test_c5_guard_state_ok_t3_s3_65_1v1(db_session, matter_with_users):
    """STATE_OK_T3_S3-65.1v1: pins 9 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_OK_T3_S3-65.1v1")
    assert sorted(by_term) == ['Air navigation facility', 'Airport', 'Airport hazard', 'Helipad', 'Heliport', 'Municipality', 'Person', 'VTOL aircraft', 'Vertiport'], f"got {sorted(by_term)!r}"
    spot = by_term['Air navigation facility']
    assert spot.definition_text.strip() == 'means any facility - other than\n\none owned and operated by the United States - used in, available for\n\nuse in, or designed for use in, aid of air navigation, including any\n\nstructures, mechanisms, lights, beacons, markers, communicating\n\nsystems, or other instrumentalities, or devices used or useful as an\n\naid, or constituting an advantage or convenience, to the safe taking\n\noff, navigation, and landing of aircraft, or the safe and efficient\n\noperation or maintenance of an airport, and any combination of any\n\nor all of such facilities.', (
        f"content-fidelity spot check failed for 'Air navigation facility': got {spot.definition_text!r}"
    )

def test_c5_guard_state_ok_t63_s63_1054(db_session, matter_with_users):
    """STATE_OK_T63_S63-1054: pins 16 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_OK_T63_S63-1054")
    assert sorted(by_term) == ['Area of operation', 'Authority', 'Bonds', 'City', 'Clerk', 'Federal government', 'Governing body', 'Housing project', 'Major disaster', 'Mayor', 'Obligee of an authority', 'Persons engaged in national defense activities', 'Persons of low income', 'Real property', 'Slum', 'State public body'], f"got {sorted(by_term)!r}"
    spot = by_term['Persons of low income']
    assert spot.definition_text.strip() == 'shall mean persons or families who\n\nlack the amount of income which is necessary (as determined by the\n\nauthority undertaking the housing project) to enable them, without\n\nfinancial assistance, to live in decent, safe and sanitary\n\ndwellings, without overcrowding, however, the local housing\n\nauthority shall not exceed the guidelines in establishing incomes\n\nset forth by the Department of Housing and Urban Development.', (
        f"content-fidelity spot check failed for 'Persons of low income': got {spot.definition_text!r}"
    )

def test_c5_guard_state_ok_t68_s68_1001_2(db_session, matter_with_users):
    """STATE_OK_T68_S68-1001.2: pins 4 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_OK_T68_S68-1001.2")
    assert sorted(by_term) == ['Gas', 'Lease', 'Oil', 'Person'], f"got {sorted(by_term)!r}"
    spot = by_term['Lease']
    assert spot.definition_text.strip() == 'means a spaced unit, a separately metered formation\n\nwithin the spaced unit, or each tract within a Corporation\n\nOklahoma Statutes - Title 68. Revenue and Taxation Page 364\n\nCommission approved unitization, or a lease which, for tax reporting\n\npurposes, has been assigned a production unit number;', (
        f"content-fidelity spot check failed for 'Lease': got {spot.definition_text!r}"
    )

def test_c5_guard_state_ok_t14a_s14a_2_105(db_session, matter_with_users):
    """STATE_OK_T14A_S14A-2-105: pins 6 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_OK_T14A_S14A-2-105")
    assert sorted(by_term) == ['Goods', 'Merchandise certificate', 'Sale of an interest in land', 'Sale of goods', 'Sale of services', 'Services'], f"got {sorted(by_term)!r}"
    spot = by_term['Sale of goods']
    assert spot.definition_text.strip() == 'includes any agreement in the form of a\n\nbailment or lease of goods if the bailee or lessee agrees to pay as\n\ncompensation for use a sum substantially equivalent to or in excess\n\nof the aggregate value of the goods involved and it is agreed that\n\nthe bailee or lessee will become, or for no other or a nominal\n\nconsideration has the option to become, the owner of the goods upon\n\nfull compliance with his obligations under the agreement.', (
        f"content-fidelity spot check failed for 'Sale of goods': got {spot.definition_text!r}"
    )

def test_c5_guard_state_ok_t68_s68_701(db_session, matter_with_users):
    """STATE_OK_T68_S68-701: pins 1 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_OK_T68_S68-701")
    assert sorted(by_term) == ['Commission'], f"got {sorted(by_term)!r}"
    spot = by_term['Commission']
    assert spot.definition_text.strip() == 'or "Tax Commission" means the Oklahoma Tax\n\nCommission.\n\nOklahoma Statutes - Title 68. Revenue and Taxation Page 336\n\n(d) The term "special fuel" or "fuel" means and includes all\n\ncombustible gases and liquids, including liquefied gases, which\n\nexist in the gaseous state at a temperature of sixty (60) degrees\n\nFahrenheit and at a pressure of fourteen and seven-tenths (14.7)\n\npounds per square inch absolute, but the term does not include\n\ncompressed natural gas subject to the levy of tax pursuant to\n\nparagraph 3 of subsection A of Section 500.4 of this title or\n\nliquefied natural gas subject to the levy of tax pursuant to\n\nparagraph 4 of subsection A of Section 500.4 of this title.\n\n(e) The term "use" shall mean and include the following: (1)\n\nthe delivery or placing of special fuel into the fuel supply tank or\n\ntanks of any motor vehicle in this state for use in whole or in part\n\nto propel such vehicle on the public highways of this state; (2) the\n\nconsumption on the public highways of Oklahoma of any special fuel\n\nimported into this state in the fuel supply tank or tanks of any\n\nmotor vehicle using the public highways of this state for commercial\n\npurposes; (3) the consumption of special fuel in any type of motor\n\nvehicle on the public highways of this state for any purpose by any\n\nperson who refuses to divulge the source of such fuel.\n\n(f) The term "public highway" means and includes every road,\n\nhighway, street, way or place within this state, of whatever nature,\n\ngenerally open to the use of the public as a matter of right for the\n\npurposes of vehicular travel, including a toll highway, and\n\nincluding streets and alleys of any town or city, notwithstanding\n\nthat the same may be temporarily closed for the purpose of\n\nconstruction, reconstruction, maintenance, or repair.\n\n(g) The term "gallon" means one (1) United States standard\n\ngallon at a temperature of sixty (60) degrees Fahrenheit.\n\n(h) The term "special fuel dealer" shall mean any person\n\nengaged in the business of handling special fuel who delivers any\n\npart thereof into the fuel supply tank or tanks of any motor\n\nvehicle.\n\n(i) The term "special fuel user" shall mean and include any\n\nperson other than a special fuel dealer, who uses special fuel in\n\nthis state, within the meanings of the word "use" as defined in this\n\nact, and shall include any person who consumes special fuel to\n\npropel a motor vehicle upon the public highways of this state when\n\nsuch special fuel has been purchased or obtained from any source\n\nfree from the payment to this state of the tax levied by this act.', (
        f"content-fidelity spot check failed for 'Commission': got {spot.definition_text!r}"
    )
