"""C5 regression guard -- US-ND (sprint 2026-08-04-defs-us-markers,
phase-2 Planner A, item A1). NOT a target: these tests pin what today's
REAL pipeline already captures for US-ND, purely via baseline
`_split_into_numbered_blocks` + `_leading_quote_candidate` -- US-ND has
ZERO family-3 rules registered against it (no EntrySplitterRule/
TermClauseRule matches `"US-ND"` or `"US-*"` anywhere in
`backend/app/definition_links/rules/`, confirmed by grep before writing
this file). US-ND is one of the five C5 working-baseline regression-guard
states (program doc `2026-08-04-definition-completeness.md`); this sprint's
zero-yield extension work must not silently shrink, duplicate, or corrupt
any of the captures pinned below. GREEN NOW; would fail if a future rule
(this panel's own A4 widening, or anyone else's) changed or swallowed
these baseline captures.

Each row's exact term SET is pinned (a regression that drops, merges, or
duplicates a term changes the set) plus one full `definition_text` pin per
row (a content-fidelity spot check, not exhaustive -- rows here carry up
to 2 terms; pinning every
one's full text would bloat this file past the 300-line convention for
marginal extra protection over the term-set check)."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_markers_c5guard_nd_rows.json"
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
        jurisdiction="US-ND",
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


def test_c5_guard_state_nd_t57_c57_39_2_s57_39_2_01(db_session, matter_with_users):
    """STATE_ND_T57_C57-39.2_S57-39.2-01: pins 1 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_ND_T57_C57-39.2_S57-39.2-01")
    assert sorted(by_term) == ['De minimis'], f"got {sorted(by_term)!r}"
    spot = by_term['De minimis']
    assert spot.definition_text.strip() == "means the seller's purchase price or sales price of the\n\ntaxable products is ten percent or less of the total purchase price or\n\nsales price of the bundled products.\n\n(b) Sellers shall use either the purchase price or the sales price of the\n\nproducts to determine if the taxable products are de minimis. Sellers\n\nmay not use a combination of the purchase price and sales price of\n\nthe products to determine if the taxable products are de minimis.\n\n(c) Sellers shall use the full term of a service contract to determine if the\n\ntaxable products are de minimis; or", (
        f"content-fidelity spot check failed for 'De minimis': got {spot.definition_text!r}"
    )

def test_c5_guard_state_nd_t57_c57_02_s57_02_01(db_session, matter_with_users):
    """STATE_ND_T57_C57-02_S57-02-01: pins 1 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_ND_T57_C57-02_S57-02-01")
    assert sorted(by_term) == ['Raising agricultural crops'], f"got {sorted(by_term)!r}"
    spot = by_term['Raising agricultural crops']
    assert spot.definition_text.strip() == 'includes the storage of harvested crops\n\nproduced by a farmer or a direct relative of the farmer until the crop is\n\ndelivered to the first end-point user.', (
        f"content-fidelity spot check failed for 'Raising agricultural crops': got {spot.definition_text!r}"
    )

def test_c5_guard_state_nd_t51_c51_19_s51_19_02(db_session, matter_with_users):
    """STATE_ND_T51_C51-19_S51-19-02: pins 2 term(s) as currently captured by baseline
    alone. Regression guard -- not a target."""
    by_term = _run(db_session, matter_with_users, "STATE_ND_T51_C51-19_S51-19-02")
    assert sorted(by_term) == ['Offer', 'Offer to purchase'], f"got {sorted(by_term)!r}"
    spot = by_term['Offer to purchase']
    assert spot.definition_text.strip() == 'includes every attempt to offer to acquire, or solicitation\n\nof an offer to sell, a franchise or interest in a franchise for value.\n\nb. (1) An offer or sale of a franchise is made in this state when an offer to sell is\n\nmade in this state or an offer to buy is accepted in this state, or, if the\n\nfranchisee is domiciled in this state, the franchised business is or will be\n\noperated in this state.', (
        f"content-fidelity spot check failed for 'Offer to purchase': got {spot.definition_text!r}"
    )
