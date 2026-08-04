"""RED live-path capture test for US family 2 (sprint 2026-08-04-defs-us-
preamble, gates U1/U4/U6): MS's SECOND, previously-uninventoried
convention (scout S4 finding, independent of D1/D2's original "As used in
this article, the term:" MS row already covered by `test_us_body_preamble_
capture_red.py::test_ms_as_used_in_this_article_the_term_is_captured`):

    "For purposes of this <unit>, [unless the context requires otherwise,]
    the following terms shall have the meaning(s) ascribed herein:"

Scout S4 measured this as a REAL, common, previously-uninventoried MS
shape: **845 MS rows match this convention alone, ALL classify BLOCK on
manual spot-check** -- comparable in scale to MS's original D1-inventoried
convention (637 rows total for the ENTIRE original signal), not a rare
edge case. This is the SAME real row already vendored for the MS
chapter-scope test (`STATE_MS_T45_C10_S34-1`,
`fixtures/us_statutes/ms_scope_preamble_rows.json`) -- reused here
deliberately (one real, verified row, two different assertions) rather
than vendoring a duplicate copy -- PLUS one additional real row
(`STATE_MS_T49_C5_S11-1`) fetched fresh for this file to confirm the
convention across more than one example, not just the row already in use
for scope.

Both rows were checked live against the real, unedited
`extract_definitions_from_section` before being written here -- both
extract cleanly, no fallback needed.

No test in this file reads or downloads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _second_convention_row(act_id: str) -> dict:
    data = json.loads((FIXTURES / "ms_second_convention_rows.json").read_text(encoding="utf-8"))
    return data[act_id]


def _scope_row(act_id: str) -> dict:
    data = json.loads((FIXTURES / "ms_scope_preamble_rows.json").read_text(encoding="utf-8"))
    return next(r for r in data if r["act_id"] == act_id)


MS_SECOND_CONVENTION_CASES = [
    pytest.param(
        "STATE_MS_T45_C10_S34-1",
        _scope_row,
        {"Conviction", "Department", "Offender", "Registrant"},
        id="ms-sex-offender-registration",
    ),
    pytest.param(
        "STATE_MS_T49_C5_S11-1",
        _second_convention_row,
        {"Commission", "Department", "Operator"},
        id="ms-wildlife-fisheries-parks",
    ),
]


@pytest.mark.parametrize("act_id, loader, expected_terms", MS_SECOND_CONVENTION_CASES)
def test_ms_shall_have_the_meaning_ascribed_herein_is_captured(
    db_session, matter_with_users, act_id, loader, expected_terms
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = loader(act_id)

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="MS second convention (test)",
        rows=[row],
        jurisdiction="US-MS",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    # `.strip()` here is a TEST-SIDE WORKAROUND for a routed production
    # defect, not a resolution of it (manager ruling M-R32, `-log.md`):
    # `STATE_MS_T45_C10_S34-1`'s real body uses curly quotes with literal
    # internal padding ("“ Conviction ”", "“ Registrant ”"), and
    # `us_profile._leading_quote_candidate` (the primary extractor MS's
    # numbered blocks route through) does `term = term_match.group(1)`
    # with NO `.strip()`, so terms arrive padded (`' Conviction '`). The
    # inline fallback DOES strip, but never runs here because the primary
    # extractor already produced candidates. This is frozen production
    # code for this sprint's panel (`us_profile.py` is out of scope) --
    # the missing `.strip()` is on the program's core-follow-on-2 list for
    # a consolidated core micro-sprint. Stripping only on the TEST side
    # (matching the convention `test_us_body_preamble_capture_red.py`'s
    # sibling MS test already uses) keeps this test asserting real
    # capture without silently treating the padding defect as fixed.
    created_terms = {t.strip() for d in result["created_definitions"] for t in d["terms"]}
    assert expected_terms <= created_terms, (
        f"the real production pipeline recognized ZERO of {act_id}'s real "
        "'For purposes of this chapter... the following terms shall have "
        f"the meaning(s) ascribed herein:' definitions (expected "
        f"{sorted(expected_terms)}, got {sorted(created_terms)}) -- MS's "
        "SECOND convention (scout S4 finding), ~845 real rows corpus-wide, "
        "distinct from the 'As used in this article, the term:' convention "
        "already covered by test_us_body_preamble_capture_red.py"
    )
