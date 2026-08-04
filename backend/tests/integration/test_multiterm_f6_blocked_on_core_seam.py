"""RED tests -- sprint 2026-08-04-defs-us-multiterm, family 6 (inline
parenthetical/cross-reference definitions with no means-idiom immediately
following the quoted term, or with the idiom pointing at an external
citation rather than local definition text).

Isolated in this file per the Planner brief's allowance for tests that
"genuinely cannot avoid depending on the seam" -- ALL THREE real rows below
are structurally unreachable by ANY extractor today, for a reason distinct
from (and more fundamental than) the recon dossier's characterization.

**Correction to the recon dossier (2026-08-04-definition-completeness-
recon.md dossier §2/§6):** the dossier describes family 6 as rows
"rejected even by the inline fallback's idiom-gap check.” Live-tested
(Planner, 2026-08-04): `pipeline._extract_inline_quoted_definitions`'s
idiom-gap regex (`_MEANS_IDIOM_GAP_RE`) already matches "has the meaning" —
running it DIRECTLY against the OR row below successfully extracts all 5
cross-reference terms. The idiom-gap check is not the blocker. The real
blocker is REACHABILITY: `_extract_inline_quoted_definitions` only ever
runs when `used_body_derived_heading` is True (pipeline.py:429), which is
gated to ONLY placeholder headings (`_is_placeholder_heading`, the
CA/IL/GA-only wave-6 mechanism). None of the three real rows below have a
placeholder heading -- OR's is a genuine substantive caption ("496.716
Wildlife inspection stations"); NH's and ND's are genuine compact-article
captions. So the fallback never gets a chance to run on this text at all,
regardless of whether it would succeed. Confirmed live for all three
(see the sprint log's Planner entry for the full trace, including the
direct idiom-gap probe).

This means family 6 is blocked on TWO things this sprint does not own:

  1. `claude/defs-core-scope`'s C3 gate ("extraction lives behind the
     seam") -- `pipeline.py`'s non-Definitions-section `else` branch
     (pipeline.py:436-442) calls `extract_local_definitions`/
     `extract_adhoc_definitions` UNCONDITIONALLY -- these are Hebrew-only
     functions imported directly by name, not profile-dispatched. An
     English "scan any ordinary article body for `(\"Term\")` apposition
     or cross-reference patterns" rule (the true fix for NH/ND's plain
     apposition shape, which never touches ANY definitions-heading
     machinery at all) needs that branch to become profile-dispatched --
     exactly core's C3 mandate, not yet landed.
  2. For OR specifically, ALSO `claude/defs-us-scoped-inline` (family 1):
     OR's row is a "(1) As used in this section: (a) ..." scoped-inline
     body -- family 1's own remit -- that happens to use the cross-
     reference idiom for its inner terms. Reaching this body at all
     requires family 1's scope-trigger recognition (core-seam territory)
     to first treat it as a definitions-bearing body; family 6's job
     (this sprint's) is only the idiom/cross-reference handling once
     reachable, which is ALREADY correct per the probe above.

These tests assert the desired final outcome through the real production
entry point; they are RED today for the "never reaches the extractor at
all" reason, not a logic defect in this sprint's own idiom handling.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "multiterm_f6_rows.json"
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


def test_or_cross_reference_style_definitions_resolve(db_session, matter_with_users):
    """Real row `STATE_OR_T41_C496_S496.716`. Today: 0 candidates -- the
    section is never even recognized as definitions-bearing (heading is an
    ordinary substantive caption, not a placeholder). Of the row's 5 defined
    terms, 4 use the CROSS-REFERENCE idiom this sprint's F6 owns
    ("Enforcement officer", "Food establishment", "Vehicle", "Wildlife" --
    each `"Term" has the meaning given that term in ORS ...`); the idiom-gap
    check itself is confirmed NOT the obstacle for these (see module
    docstring).

    Program ruling E3 (sprint log, `## Residual ledger` entry R3):
    the row's 5th term, `"Taken"`, is defined with a PLAIN `means` ("Taken"
    means killed or captured ...) -- an ordinary quoted-term-plus-`means`
    definition inside an ordinary article body. That shape is family 1's
    mechanism (owned by the sibling sprint `claude/defs-us-scoped-inline`),
    not a cross-reference this sprint's F6 idiom-gap regex should be
    matching at all -- F6's own `_IDIOM_GAP_RE` (`rules/us_inline_
    parenthetical.py`) was measured firing on 8.87% of ALL US rows
    specifically because it also matched bare `means`/`shall mean`, which
    is family 1's territory, not a cross-reference. E3 narrows F6 to the
    two `has the meaning ...` cross-reference forms only (projected fire
    rate 8.82% -> 0.35%, inside F6's mandated ~1-2 per 300). Under that
    narrowing "Taken" is correctly NOT captured by F6 -- it is NOT
    abandoned, it is a deliberate cross-panel handoff, tracked as R3 on
    this sprint's Residual ledger until `claude/defs-us-scoped-inline`'s
    live path provably captures this exact row. This test therefore
    expects EXACTLY the 4 cross-reference terms, not 5 -- "Taken" is
    intentionally absent from the assertion below, not silently dropped:
    its fate is recorded here and on the ledger, not left vague.
    """
    row = _load_rows()["STATE_OR_T41_C496_S496.716"]
    result = _ingest_and_link(
        db_session, matter_with_users, title="OR Wildlife inspection stations (F6 cross-reference)", row=row, jurisdiction="US-OR"
    )

    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    for term in ("Enforcement officer", "Food establishment", "Vehicle", "Wildlife"):
        assert term in all_terms, (
            f'"{term}" was never captured -- this section is never reached by any extractor today '
            f"(blocked on core-scope C3 + scoped-inline, see module docstring). "
            f"All captured terms: {sorted(all_terms)!r}"
        )
    defs_by_term = {t: d for d in result["created_definitions"] for t in d["terms"]}
    assert "ORS 153.005" in _definition_text(db_session, defs_by_term["Enforcement officer"]["id"])


def test_nh_plain_apposition_with_no_means_idiom_resolves(db_session, matter_with_users):
    """Real row `STATE_NH_TXXXVII_C408-C_S14` (Nurse Licensure Compact
    withdrawal article). '(b) ... may withdraw from the compact
    ("withdrawing state") by enacting a statute ...' -- a genuine apposition
    shorthand with NO means/shall-mean/has-the-meaning idiom anywhere near
    it. Today: 0 candidates -- this article is never recognized as a
    Definitions section (correctly -- it isn't one) and the `else` branch
    that scans ordinary article bodies calls only the Hebrew-only
    `extract_local_definitions`/`extract_adhoc_definitions` (module
    docstring, point 1)."""
    row = _load_rows()["STATE_NH_TXXXVII_C408-C_S14"]
    result = _ingest_and_link(
        db_session, matter_with_users, title="NH Nurse Licensure Compact withdrawal (F6 apposition)", row=row, jurisdiction="US-NH"
    )

    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "withdrawing state" in all_terms, (
        f"the apposition definition was never captured -- blocked on core-scope C3 "
        f"(pipeline.py's else-branch is not profile-dispatched). All captured terms: {sorted(all_terms)!r}"
    )
    defs_by_term = {t: d for d in result["created_definitions"] for t in d["terms"]}
    text = _definition_text(db_session, defs_by_term["withdrawing state"]["id"])
    assert "enacting a statute specifically repealing" in text


def test_nd_plain_apposition_with_no_means_idiom_resolves(db_session, matter_with_users):
    """Real row `STATE_ND_T26.1_C26.1-59_S26.1-59-01` (excerpt, Article
    XIV Withdrawal) -- the identical apposition shape as NH, reproduced in
    a second real state's interstate-compact convention, confirming this
    is not an NH-specific artifact."""
    row = _load_rows()["STATE_ND_T26.1_C26.1-59_S26.1-59-01"]
    result = _ingest_and_link(
        db_session, matter_with_users, title="ND Interstate Insurance Compact withdrawal (F6 apposition)", row=row, jurisdiction="US-ND"
    )

    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "withdrawing state" in all_terms, (
        f"the apposition definition was never captured -- blocked on core-scope C3 "
        f"(pipeline.py's else-branch is not profile-dispatched). All captured terms: {sorted(all_terms)!r}"
    )
    defs_by_term = {t: d for d in result["created_definitions"] for t in d["terms"]}
    text = _definition_text(db_session, defs_by_term["withdrawing state"]["id"])
    assert "enacting a statute specifically repealing" in text
