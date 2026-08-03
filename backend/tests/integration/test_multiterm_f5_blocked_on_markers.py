"""RED tests -- sprint 2026-08-04-defs-us-multiterm, family 5, the
zero-yield archetype (VT/SD). Isolated in this file, separate from
`test_multiterm_f5_shared_clause.py`, because these two real rows are
STACKED misses that this sprint alone cannot turn green -- see the sprint
log's markers-boundary proposal (dated Planner entry) for the full
negotiation. Recorded here per the Planner brief's own allowance: "Where a
test genuinely cannot avoid depending on the seam [or another sprint's
work], isolate those tests in a clearly-named module and say so."

Both real bodies below are ONE unmarked sentence with no `(N)`/lettered
entry markers at all: `USProfile._split_into_numbered_blocks` (called from
`extract_definitions_from_section`) finds zero entry-start lines, so
`_split_into_numbered_blocks` returns an EMPTY list and the section yields
0 candidates -- confirmed live (Planner, 2026-08-04) against the real rows
below, unchanged from the recon dossier's finding for VT and (newly
confirmed here, resolving the sprint contract's "extractor yield
UNCONFIRMED" flag) for SD too:

  - VT `STATE_VT_T23_C35_S3700`, heading "Definition; mail" (matches
    `is_definitions_heading`): '"mail," "mails," "mailing," and "mailed"
    mean any method of delivery ...'
  - SD `STATE_SD_T3_C14_S3-14-5`, heading "Definitions": 'The terms
    "office," "officer," "executive," and "administrative," ... mean and
    apply to any executive or administrative officer of the state; ...'

Boundary (proposed to the markers Planner via the sprint log, not yet
agreed in writing by both panels as of this commit): splitting mechanics
(getting `extract_definitions_from_section` to return a NON-EMPTY block
for a marker-less body) belong to `claude/defs-us-markers` (family 3,
entry-marker mismatch); per-term fan-out of whatever that block contains
belongs here. These tests assert the FINAL desired outcome through the
real production entry point -- they will only turn green once BOTH
sprints' work has landed (markers' splitter fix, then this sprint's
multi-term post-processing pass, which is designed to be robust to
whatever intermediate shape markers hands back -- see the sprint log for
why). Today they are RED for the stacked reason (zero candidates at all),
not for the wrong reason -- captured below.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "multiterm_f5_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def _definition_text(db_session, definition_id: str) -> str:
    from app.models.definition import Definition

    return db_session.get(Definition, definition_id).definition_text


def _ingest_and_link(db_session, matter_with_users, *, title, row, jurisdiction):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=title,
        rows=[row],
        jurisdiction=jurisdiction,
    )
    return run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )


def test_vt_marker_less_multi_term_sentence_resolves_all_four_terms(db_session, matter_with_users):
    """Real row `STATE_VT_T23_C35_S3700`. Today: 0 candidates (confirmed
    live) -- `extract_definitions_from_section` never even reaches the
    multi-term parsing question because the body has no entry markers to
    split on at all. Blocked on markers' splitter fix landing first."""
    row = _load_rows()["STATE_VT_T23_C35_S3700"]
    result = _ingest_and_link(
        db_session, matter_with_users, title="VT Title 23 Section 3700 (F5 zero-yield)", row=row, jurisdiction="US-VT"
    )

    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    for term in ("mail", "mails", "mailing", "mailed"):
        assert term in all_terms, (
            f'"{term}" was never captured -- extract_definitions_from_section still returns 0 '
            f"candidates for this marker-less body (blocked on the markers sprint's splitter fix). "
            f"All captured terms: {sorted(all_terms)!r}"
        )
    defs_by_term = {t: d for d in result["created_definitions"] for t in d["terms"]}
    for term in ("mail", "mails", "mailing", "mailed"):
        text = _definition_text(db_session, defs_by_term[term]["id"])
        assert "any method of delivery authorized by the Commissioner" in text


def test_sd_marker_less_multi_term_sentence_resolves_all_four_terms(db_session, matter_with_users):
    """Real row `STATE_SD_T3_C14_S3-14-5`. Resolves the sprint contract's
    "extractor yield UNCONFIRMED" flag: CONFIRMED LIVE (Planner,
    2026-08-04) -- 0 candidates today, same marker-less-sentence mechanism
    as VT, under a genuine "Definitions" heading. Same markers-boundary
    dependency."""
    row = _load_rows()["STATE_SD_T3_C14_S3-14-5"]
    result = _ingest_and_link(
        db_session, matter_with_users, title="SD Title 3 Section 3-14-5 (F5 zero-yield)", row=row, jurisdiction="US-SD"
    )

    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    for term in ("office", "officer", "executive", "administrative"):
        assert term in all_terms, (
            f'"{term}" was never captured -- extract_definitions_from_section still returns 0 '
            f"candidates for this marker-less body (blocked on the markers sprint's splitter fix). "
            f"All captured terms: {sorted(all_terms)!r}"
        )
    defs_by_term = {t: d for d in result["created_definitions"] for t in d["terms"]}
    for term in ("office", "officer", "executive", "administrative"):
        text = _definition_text(db_session, defs_by_term[term]["id"])
        assert "executive or administrative officer of the state" in text
