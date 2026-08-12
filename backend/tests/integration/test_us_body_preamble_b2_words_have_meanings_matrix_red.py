"""RED live-path parameterized capture matrix for US family 2 (sprint
2026-08-04-defs-us-preamble, gates U1/U4/U6), idiom **B2** (scout S3's
naming): `"In this <unit>[,] the following word(s) have the meaning(s)
indicated:"`, immediately followed by a colon and a numbered list of
quoted terms -- MD's dominant shape (see `test_definition_links_us_
preamble_family.py`'s own dedicated MD test), also found by S3 in DE/LA/WV
(a strict subset of B1's own state list -- same shared numbered-list
splitter, no new extraction logic needed).

Every row below is fetched live from its state's real parquet file (never
downloaded by this test) and vendored byte-for-byte into
`fixtures/us_statutes/us_preamble_b2_rows.json`. Every expected-terms
subset was checked by calling the REAL, unedited `extract_definitions_
from_section` directly against each row's real body before being written
here -- all three rows below extract CLEANLY via the existing DE-shape
`(N)"Term" ...` splitter, no fallback needed.

No test in this file reads or downloads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _rows() -> dict[str, dict]:
    return json.loads((FIXTURES / "us_preamble_b2_rows.json").read_text(encoding="utf-8"))


B2_CASES = [
    pytest.param(
        "US-DE",
        "STATE_DE_T6_C22_S2205",
        {"Protected consumer", "Record", "Representative"},
        id="de-security-freezes-minors",
    ),
    pytest.param(
        "US-LA",
        "STATE_LA_Crevised-statutes_T9_S3571.3",
        {"Credit report", "Protected person", "Record"},
        id="la-security-freezes-protected-persons",
    ),
    pytest.param(
        "US-WV",
        "STATE_WV_C53_A8_S17",
        {"Court record", "Seal", "Sealing"},
        id="wv-sealing-of-records",
    ),
]


@pytest.mark.parametrize("jurisdiction, act_id, expected_terms", B2_CASES)
def test_b2_words_have_meanings_preamble_is_captured(
    db_session, matter_with_users, jurisdiction, act_id, expected_terms
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _rows()[act_id]

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=f"{jurisdiction} B2 words-have-meanings matrix (test)",
        rows=[row],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert expected_terms <= created_terms, (
        f"the real production pipeline recognized ZERO of {act_id}'s real "
        f"'In this <unit>... the following words have the meanings "
        f"indicated:' definitions (expected {sorted(expected_terms)}, got "
        f"{sorted(created_terms)}) -- this is idiom B2 (scout S3), MD's own "
        "dominant shape (see test_definition_links_us_preamble_family.py), "
        "also DE/LA/WV's -- a strict subset of B1's state list sharing the "
        "same numbered-list splitter"
    )


def test_wv_row_carries_the_literal_word_definitions_as_its_own_embedded_subheading_a_near_miss_not_a_capture():
    """Unit-level pin (scout S3 §4 near-miss finding): WV's own B2 row
    (`STATE_WV_C53_A8_S17`) opens with the literal sub-heading
    '(a) Definitions. --' immediately before its B2 preamble sentence -- a
    much CHEAPER signal than the "In this section..." idiom this matrix
    tests, and one that would ALSO capture MN's own `STATE_MN_P289A_295_
    C290_S290.92` (a different real row, not vendored here) per S3's own
    finding. Not built here (that is production-rule design, out of
    Planner scope) -- pinned so a future rule author sees the cheaper
    signal is real and already present in this exact vendored row, not
    just a scout's unverified claim.
    """
    rows = _rows()
    row = rows["STATE_WV_C53_A8_S17"]
    assert row["text"].lstrip().startswith("(a) Definitions"), (
        "fixture must reproduce WV's real embedded 'Definitions.' "
        "sub-heading at the very start of the body -- if this breaks, the "
        "near-miss finding above needs re-verifying against a fresh row"
    )
