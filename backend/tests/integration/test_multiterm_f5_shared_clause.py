"""RED tests -- sprint 2026-08-04-defs-us-multiterm, family 5 (multi-term
shared-clause definitions), gate U1.

"The term(s) "X", "Y", and "Z" mean(s) ..." -- one clause defines several
terms; today's `USProfile.extract_definitions_from_section` entry splitter
(`us_profile.py:373`) captures only the FIRST quoted span via
`_LEADING_QUOTE_RE.match(block)` and dumps every other quoted term into the
leftover `definition_text` as dead prose. Confirmed live (Planner,
2026-08-04) against the real rows vendored below -- see the sprint log's
Planner entry for the full re-confirmation trace.

This file covers the THREE real shapes that are OURS ALONE (extraction
already yields >0 candidates today; no other sprint's work blocks a fix):

  - MT `STATE_MT_T16_C11_P4_S16-11-402`: a multi-term shared clause NESTED
    inside another entry's own body ("Affiliate" -> "Solely for purposes of
    this definition, the terms "owns," "is owned" and "ownership" mean
    ..."). 8 of the section's 9 top-level entries are single-term and
    already work today -- kept in the fixture as an in-test regression
    guard for U5.
  - MI `STATE_MI_C388_AAct-94-of-1979_S388.1606` (excerpt, entries 9-13 of
    26): a top-level multi-term entry ("School district of the first
    class", "first class school district", "district of the first class")
    sandwiched between 4 correctly-working single-term entries -- same
    regression-guard shape as MT.
  - TX `STATE_TX_Cgv_C2009_S2009.003` / `STATE_TX_Cgv_C2002_S2002.001`: the
    prior sprint's recorded residual ("TX 17.33%/13 of 75 degenerate
    recovered terms", 2026-08-02-us-state-law-log.md Q1) -- a PARENT clause
    ("The following terms have the meanings assigned by Section 2001.003:")
    followed by a lettered list of bare quoted term names with no
    definition text of their own. The extractor already emits one
    candidate PER listed term (so this is not a zero-yield miss), but each
    one's `definition_text` is just trailing punctuation (";", "; and",
    "") -- the parent clause's redirect text is silently discarded instead
    of being attached to its children.

VT/SD (the zero-yield archetype, e.g. VT `STATE_VT_T23_C35_S3700`) are
deliberately NOT in this file -- see
`test_multiterm_f5_blocked_on_markers.py` and the sprint log's markers-
boundary proposal.

Live-path requirement: every test here drives the real production entry
point (`ingest_us_statute_rows` -> `run_definition_linking`), never calls
the extractor functions directly, and asserts on real persisted
`Definition`/`Assertion` rows -- not a named-wiring proof.

Row-shape note: assertions below check TERM MEMBERSHIP and shared
DEFINITION TEXT CONTENT, deliberately never `len(created_definitions)` or
a specific term-to-row cardinality -- the sprint log's Planner entry raises
a PANEL QUESTION on whether "each term becomes its own Definition row" (the
contract's literal wording) or "each term becomes its own resolvable
`.terms` entry on a shared row" (the existing, already-working design used
by `Definition.terms`/`matcher.link_articles_to_definitions`) is correct;
these tests pass unchanged under either resolution.
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


def test_mt_nested_multi_term_clause_resolves_all_three_terms(db_session, matter_with_users):
    """Real row `STATE_MT_T16_C11_P4_S16-11-402`. Today: 9 candidates, none
    named "owns"/"is owned"/"ownership" -- all three are dead prose inside
    "Affiliate"'s own `definition_text`. After the fix: all three are
    independently present terms sharing the real definition ("ownership of
    an equity interest ... of ten percent or more")."""
    row = _load_rows()["STATE_MT_T16_C11_P4_S16-11-402"]
    result = _ingest_and_link(
        db_session, matter_with_users, title="MT Tobacco Definitions (F5 nested)", row=row, jurisdiction="US-MT"
    )

    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    for term in ("owns", "is owned", "ownership"):
        assert term in all_terms, (
            f'"{term}" was never captured as its own resolvable term -- the nested multi-term '
            f"shared clause inside \"Affiliate\"'s body was swallowed whole. All captured terms: "
            f"{sorted(all_terms)!r}"
        )

    defs_by_term = {t: d for d in result["created_definitions"] for t in d["terms"]}
    for term in ("owns", "is owned", "ownership"):
        text = _definition_text(db_session, defs_by_term[term]["id"])
        assert "ownership of an equity interest" in text, (
            f'"{term}" must share the real definition text, got: {text[:200]!r}'
        )

    # U5 regression guard: the 8 already-working single-term entries in this
    # same real row must still be intact (unaffected by the fix).
    for working_term in (
        "Allocable share",
        "Cigarette",
        "Master Settlement Agreement",
        "Qualified escrow fund",
        "Released claims",
        "Releasing parties",
        "Tobacco Product Manufacturer",
        "Units sold",
    ):
        assert working_term in all_terms, f'regression: "{working_term}" (already working today) was lost'


def test_mi_top_level_multi_term_clause_resolves_all_three_terms(db_session, matter_with_users):
    """Real row `STATE_MI_C388_AAct-94-of-1979_S388.1606` (excerpt, entries
    9-13). Today: 5 candidates, "School district of the first class"
    captures only the first of 3 co-defined terms; "first class school
    district" and "district of the first class" are dead prose inside its
    own `definition_text`."""
    row = _load_rows()["STATE_MI_C388_AAct-94-of-1979_S388.1606"]
    result = _ingest_and_link(
        db_session, matter_with_users, title="MI Additional Definitions (F5 top-level)", row=row, jurisdiction="US-MI"
    )

    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    for term in ("School district of the first class", "first class school district", "district of the first class"):
        assert term in all_terms, (
            f'"{term}" was never captured as its own resolvable term. All captured terms: {sorted(all_terms)!r}'
        )

    defs_by_term = {t: d for d in result["created_definitions"] for t in d["terms"]}
    for term in ("School district of the first class", "first class school district", "district of the first class"):
        text = _definition_text(db_session, defs_by_term[term]["id"])
        assert "40,000 pupils" in text, f'"{term}" must share the real definition text, got: {text[:200]!r}'

    # U5 regression guard: the 4 ordinary single-term entries in this same
    # excerpt must still be intact.
    for working_term in ("Rule", "The revised school code", "School fiscal year", "State board"):
        assert working_term in all_terms, f'regression: "{working_term}" (already working today) was lost'


def _assert_tx_parent_clause_redirect_attached(db_session, result, terms):
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    defs_by_term = {t: d for d in result["created_definitions"] for t in d["terms"]}
    for term in terms:
        assert term in all_terms, f'"{term}" was never captured. All captured terms: {sorted(all_terms)!r}'
        text = _definition_text(db_session, defs_by_term[term]["id"])
        assert "Section 2001.003" in text, (
            f'"{term}"\'s definition_text must carry the parent clause\'s redirect '
            f'("have the meanings assigned by Section 2001.003"), not degenerate punctuation. '
            f"Got: {text!r}"
        )


def test_tx_parent_clause_redirect_list_2009_003(db_session, matter_with_users):
    """Real row `STATE_TX_Cgv_C2009_S2009.003`. Today: "contested case" /
    "party" / "person" / "rule." are each their own candidate (NOT a
    zero-yield miss) but `definition_text` is just ";" / "; and" / "" --
    the parent clause ("(4) The following terms have the meanings assigned
    by Section 2001.003:") is silently discarded rather than attached to
    its 4 listed children. This is the prior sprint's recorded residual
    (2026-08-02-us-state-law-log.md: "TX 17.33% / 13 of 75 degenerate
    recovered terms")."""
    row = _load_rows()["STATE_TX_Cgv_C2009_S2009.003"]
    result = _ingest_and_link(
        db_session, matter_with_users, title="TX Government Code 2009.003 (F5 parent-clause)", row=row, jurisdiction="US-TX"
    )
    _assert_tx_parent_clause_redirect_attached(
        db_session, result, ("contested case", "party", "person", "rule")
    )
    # sanity: the 3 ordinary, already-working entries in this same row
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    for working_term in ("Alternative dispute resolution procedure", "Governmental body", "State agency"):
        assert working_term in all_terms, f'regression: "{working_term}" (already working today) was lost'


def test_tx_parent_clause_redirect_list_2002_001(db_session, matter_with_users):
    """Real row `STATE_TX_Cgv_C2002_S2002.001` -- the prior sprint's log
    names this as a second, near-identical real row reproducing the exact
    same shape."""
    row = _load_rows()["STATE_TX_Cgv_C2002_S2002.001"]
    result = _ingest_and_link(
        db_session, matter_with_users, title="TX Government Code 2002.001 (F5 parent-clause)", row=row, jurisdiction="US-TX"
    )
    _assert_tx_parent_clause_redirect_attached(
        db_session, result, ("contested case", "license", "licensing", "party", "person", "rule")
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    for working_term in ("Administrative code", "Internet", "State agency"):
        assert working_term in all_terms, f'regression: "{working_term}" (already working today) was lost'
