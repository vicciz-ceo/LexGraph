"""RED live-path capture test for US family 2 (sprint 2026-08-04-defs-us-
preamble, gates U1/U4/U6): California's own preamble-signal population,
inventoried for the first time this sprint (scout S4, deliverable 4 -- CA
was previously only known as "gated" background per the manager's earlier
findings, never inventoried by shape).

**CA is not a minor bonus population** (M-R11's earlier phrase, corrected
by S4): S4 measured **1,401 preamble-signal rows corpus-wide, comparable in
scale to GA's own 1,224-1,257-row population**, of which **748 (53%) are
NEW exposure** under ungated dispatch -- 663 of those genuinely BLOCK-
shaped. This file proves ONE real example is achievable, using a row
verified live to be UNCAPTURED today for a DIFFERENT, narrower reason than
GA/MD/NE/MS/SD: CA's body DOES contain the literal word "definitions" near
"apply" (today's existing wave-6 Gate B pattern's own trigger words), but
the match fails ONLY because the prefix before "definitions" (84 real
characters: "Unless the context requires otherwise, for purposes of this
division, the following ") exceeds Gate B's own 80-character prefix cap --
confirmed live below, not asserted.

Fetched live from the real `us_ca_statutes.parquet` (never downloaded by
this test) and vendored byte-for-byte into `fixtures/us_statutes/
ca_block_rows.json`. Checked live against the real, unedited
`extract_definitions_from_section` before being written here -- extracts
cleanly (low contamination risk: only 16.7% of this row's own body follows
the last recognized entry, verified by scout S4's own `tail_ratio` field).

No test in this file reads or downloads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"

_ACT_ID = "STATE_CA_Cpuc_D19.7_C1_S187010"


def _row() -> dict:
    data = json.loads((FIXTURES / "ca_block_rows.json").read_text(encoding="utf-8"))
    return data[_ACT_ID]


def test_gate_b_prefix_cap_is_exactly_why_this_real_california_row_misses_today():
    """Unit-level pin: today's existing (pre-sprint) wave-6 Gate B already
    almost recognizes this row -- it fails ONLY on the 80-char prefix cap,
    not because the trigger vocabulary is missing. Documents precisely
    which gate this specific CA row needs an ungated body-preamble rule to
    clear, distinct from GA/MD/NE/MS/SD's own reasons.
    """
    from app.definition_links.us_profile import _derive_heading_from_body, _is_placeholder_heading

    row = _row()
    assert row["section_title"] == "Section 187010", (
        "fixture must reproduce CA's real bare-placeholder heading shape"
    )
    assert _is_placeholder_heading(row["section_title"]) is True
    idx = row["text"].lower().find("definitions")
    assert idx == 84, (
        f"expected the real prefix before 'definitions' to be exactly 84 "
        f"characters (1 over Gate B's own 80-char cap), got {idx} -- if "
        "this fixture is re-fetched and the number changes, re-verify "
        "whether Gate B now passes for a different reason"
    )
    assert _derive_heading_from_body(row["text"]) is None, (
        "confirms today's existing wave-6 body derivation still returns "
        "None for this exact real row -- the 84 > 80 prefix-cap miss, not "
        "a missing trigger vocabulary"
    )


def test_california_for_purposes_of_this_division_the_following_definitions_apply_is_captured(
    db_session, matter_with_users
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _row()

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="CA D19.7 block capture (test)",
        rows=[row],
        jurisdiction="US-CA",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    expected_terms = {"Inspector General", "Office", "Project"}
    assert expected_terms <= created_terms, (
        f"the real production pipeline recognized ZERO of {_ACT_ID}'s real "
        f"'Unless the context requires otherwise, for purposes of this "
        f"division, the following definitions apply:' definitions "
        f"(expected {sorted(expected_terms)}, got {sorted(created_terms)}) "
        "-- CA's own preamble-signal population is 1,401 rows corpus-wide "
        "(scout S4), comparable in scale to GA's, and was never "
        "inventoried by shape before this sprint"
    )
