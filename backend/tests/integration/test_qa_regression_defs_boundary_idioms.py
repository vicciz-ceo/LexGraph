"""QA regression coverage -- sprint 2026-08-20-defs-boundary-idioms (issue #27).

Independent QA pass (separate agent from every Planner/Developer on this
sprint), following the existing pattern in
`test_qa_regression_defs_b1_refers_to.py` / `test_qa_regression_us_state_law.py`.
Verified PASS on all three items against the seven acceptance gates (contract
`docs/sprint/sprints/2026-08-20-defs-boundary-idioms.md`); this file pins
coverage the Developer/Planner's own committed tests do not already provide.

Two gaps closed here:

1. **The reversal's protected row, at direct-profile altitude**
   (`STATE_NV_T43_C484B_S484B.307`, term `"X"`). The Developer/Planner's own
   `test_us_markers_fallback_guard_single_letter_negative_control.py` pins
   the GENERAL rule (a bare single-letter fallback term must be admitted,
   not rejected) with fully synthetic fixtures (WA profile, terms
   `"B"`/`"C"`/`"AI"`, per M-R107). It does not pin the SPECIFIC real-world
   row whose loss under the reverted `877c970` rule is the entire reason
   for the director's reversal ruling (contract Item 2, "REVERSED by
   director ruling 2026-08-23"; log doc "Director ruling: revert
   single-letter rule, certify, ship"). This test embeds the real,
   verbatim Nevada Revised Statutes 484B.307 text (public-domain government
   text, minimally excerpted to the two-branch signal clause that produces
   the regression: `(a) A downward-pointing green arrow means ...
   (b) A red "X" symbol means ...`) and calls
   `USProfile.extract_definitions_from_section` with the exact
   `heading_was_derived=True` signature the real pipeline uses on this row
   -- independently re-verified against the live `vaquill/open-us-law`
   snapshot (`us_nv_statutes.parquet`, `act_id=STATE_NV_T43_C484B_S484B.307`,
   row 21958) during this QA pass. A future regression of the merge guard's
   filter (e.g. reintroducing an over-broad single-letter rejection) fails
   this test on the EXACT row the director ruling protects, not just a
   structurally-similar synthetic stand-in.

2. **Single-letter fallback admission survives the real ingest +
   persistence pipeline** -- the Developer/Planner's negative-control file
   only exercises `extract_definitions_from_section` directly (direct-
   profile altitude); no committed test drives a single-letter fallback
   term through `ingest_us_statute_rows` -> `run_definition_linking` ->
   persisted `Definition` rows. Per M-R107, this uses entirely fresh,
   synthetic identifiers (jurisdiction US-OR, term "Q", act_id
   `FUTURE_QA_REGRESSION_GRID_MARKER_Q`) never used by the Developer's own
   tests or the real corpus, in the same body-derived-heading shape
   `test_qa_regression_defs_b1_refers_to.py` already proved recognizable
   for US-OR (`derive_heading_from_body('"Grid marker"', text) ==
   "Definitions"`), verified independently this QA pass.

3. **Certificate-composition pin** (Gate 2, P-R11). The committed gate-2
   evidence (`docs/sprint/sprints/2026-08-20-defs-boundary-idioms-scripts/
   run/compare/summary.json` + `changed.jsonl`) is the `cc51c49` combined
   measurement the contract certifies against. This test is a cheap
   (single-file JSON load + one sha256 pass, no corpus re-measurement)
   integrity pin: the committed summary counts and the `changed.jsonl`
   checksum it records must never silently drift, and `backend/app/` at
   HEAD must stay byte-identical to `f267644` (the tree that measurement
   ran against) -- both independently re-verified by hand during this QA
   pass (28,654 distinct anchors: 27,568 pure-added / 64 pure-removed /
   1,022 both; decomposes to 6,309 primary-engine + 7,768 in-scope-fallback
   + 13,491 out-of-scope-fallback per `expansion_precision_2.md`'s census,
   re-derived independently, not quoted).

Every assertion below was verified empirically against the current
(post-fix, post-revert) production code before being committed, per this
sprint's own M-R107/no-flip-to-red-trap discipline: each pins the REQUIRED
(already-passing) behavior, not a still-broken one.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.normalize import strip_wikilinks
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.profiles import get_profile
from app.models.definition import Definition

ROOT = Path(__file__).resolve().parents[3]

# --- 1. Direct-profile altitude: the reversal's protected real row --------

# Real, verbatim text (public-domain NV statute), minimally excerpted from
# `STATE_NV_T43_C484B_S484B.307` (act row 21958 in `us_nv_statutes.parquet`,
# `vaquill/open-us-law` snapshot) down to the two-branch signal clause that
# produces the regression. Re-verified against the live snapshot this pass.
_NV_484B_307_EXCERPT = (
    "12. Whenever signals are placed over the individual lanes of a "
    "highway, the signals indicate, and apply to drivers of vehicles, as "
    "follows: (a) A downward-pointing green arrow means that a driver "
    "facing the signal may drive in any lane over which the green signal "
    "is shown. (b) A red “ X ” symbol means a driver facing the "
    "signal must not enter or drive in any lane over which the red "
    "signal is shown."
)


def test_nv_484b_307_x_symbol_primary_engine_finds_nothing_precondition():
    """Sanity for the test below: on this exact excerpt, the primary
    (quote-anchored) engine finds ZERO candidates independent of the guard
    -- so whether "X" survives is decided entirely by the fallback-merge
    guard (Item 2's fix / the reversal), not by primary-engine collision
    avoidance. Guards against a vacuously-passing regression pin."""
    profile = get_profile("US-NV")
    body, _ = strip_wikilinks(profile.normalize_for_parsing(_NV_484B_307_EXCERPT))
    primary = profile.extract_definitions_from_section(body, scope="law-wide", heading_was_derived=False)
    terms = {t for c in primary for t in c.terms}
    assert terms == set(), (
        f"sanity: primary engine must find zero entries on the NV 484B.307 "
        f"excerpt independent of the merge guard -- got {sorted(terms)!r}"
    )


def test_nv_484b_307_x_symbol_survives_the_merged_guard():
    """The reversal's protected row (contract Item 2, 'REVERSED by director
    ruling 2026-08-23'): a bare single-letter fallback term ('X') on the
    real NV 484B.307 traffic-signal-symbol clause must be ADMITTED by the
    merged fallback guard, called exactly as the real pipeline calls it
    (`heading_was_derived=True`). This is the exact anchor whose loss under
    the reverted `877c970` `^[A-Za-z]$` rejection rule is why that rule was
    reverted -- if a future change to `_is_implausible_fallback_capture` (or
    any narrower successor rule, per this sprint's own named tracked-debt
    future-work direction) ever re-rejects it, this test fails on the real
    row, not a synthetic stand-in."""
    profile = get_profile("US-NV")
    body, _ = strip_wikilinks(profile.normalize_for_parsing(_NV_484B_307_EXCERPT))
    merged = profile.extract_definitions_from_section(body, scope="law-wide", heading_was_derived=True)
    by_term = {term: candidate for candidate in merged for term in candidate.terms}
    assert "X" in by_term, (
        f"expected 'X' (the reversal's protected NV 484B.307 anchor) among "
        f"{sorted(by_term)} -- a bare single-letter fallback term must survive "
        f"the merged guard"
    )
    assert by_term["X"].definition_text == (
        "a driver facing the signal must not enter or drive in any lane "
        "over which the red signal is shown."
    ), f"unexpected definition_text: {by_term['X'].definition_text!r}"


# --- 2. Live-persistence altitude: fresh single-letter term, novel ids ----


def _persisted_definition_text_by_term(db_session, result: dict) -> dict[str, str]:
    persisted = []
    for created in result["created_definitions"]:
        definition = db_session.get(Definition, created["id"])
        assert definition is not None, f"pipeline returned missing Definition id {created['id']}"
        persisted.append(definition)
    return {term: definition.definition_text for definition in persisted for term in definition.terms}


_GRID_MARKER_TEXT = (
    'As used in this article, "Grid marker":\n\n'
    "(1) refers to a marking placed by the office; and\n\n"
    "(2) includes a temporary marking placed by a contractor.\n\n"
    '"Q" means a classification code assigned by the office to a '
    "completed grid marker."
)


def test_single_letter_fallback_term_precondition_derives_definitions_heading():
    """Sanity: US-OR's `derive_heading_from_body` recognizes this quoted-
    heading shape as 'Definitions' (same mechanism already proved for US-OR
    in `test_qa_regression_defs_b1_refers_to.py`'s 'credit voucher' case),
    so the live-persistence test below actually exercises the
    `heading_was_derived=True` path end to end, not a heading the ordinary
    literal check would have matched anyway."""
    profile = get_profile("US-OR")
    derived = profile.derive_heading_from_body('"Grid marker"', _GRID_MARKER_TEXT)
    assert derived == "Definitions", f"expected 'Definitions', got {derived!r}"


def test_single_letter_fallback_term_survives_live_persistence_altitude_novel_case(db_session, matter_with_users):
    """Coverage gap the Developer/Planner's own `test_us_markers_fallback_
    guard_single_letter_negative_control.py` does not fill: that file only
    calls `extract_definitions_from_section` directly. This drives a fresh,
    non-colliding single-letter fallback term ('Q', alongside the distinct
    multi-word term 'Grid marker', on the same row) through the REAL
    `ingest_us_statute_rows` -> `run_definition_linking` -> persisted
    `Definition` pipeline, with a fresh act_id-shaped identifier never seen
    in the real corpus or any Developer/Planner test (M-R107)."""
    matter = matter_with_users
    row = {
        "act_id": "FUTURE_QA_REGRESSION_GRID_MARKER_Q",
        "section_number": "7",
        "chapter": "3",
        "section_title": '"Grid marker"',
        "text": _GRID_MARKER_TEXT,
    }
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title="QA regression single-letter fallback survival (US-OR)",
        rows=[row],
        jurisdiction="US-OR",
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    persisted = _persisted_definition_text_by_term(db_session, result)
    assert "Q" in persisted, (
        f"expected single-letter term 'Q' among {sorted(persisted)} -- a bare "
        f"single-letter fallback term must survive the real persistence path"
    )
    assert persisted["Q"] == (
        "a classification code assigned by the office to a completed grid marker."
    )
    assert "Grid marker" in persisted, (
        f"the co-resident, non-colliding multi-word term must also survive -- "
        f"got {sorted(persisted)}"
    )


# --- 3. Certificate-composition pin (Gate 2, P-R11) ------------------------

_SCRIPTS_DIR = ROOT / "docs/sprint/sprints/2026-08-20-defs-boundary-idioms-scripts"
_SUMMARY_PATH = _SCRIPTS_DIR / "run/compare/summary.json"
_CHANGED_PATH = _SCRIPTS_DIR / "run/compare/changed.jsonl"
_CERTIFIED_TREE_SHA = "f267644"


def test_gate2_certificate_summary_composition_is_unchanged():
    """Cheap integrity pin on the committed `cc51c49` combined gate-2
    certificate (Gate 2, P-R11): the summary counts must never silently
    drift. Independently re-derived from `changed.jsonl` during this QA
    pass (bucketing every (jurisdiction, source_file, source_row, term)
    anchor by change-type) and confirmed to match exactly; this test pins
    the aggregate so a future accidental overwrite/regeneration of the
    evidence file is caught without re-parsing the full 54MB `changed.jsonl`
    on every run."""
    summary = json.loads(_SUMMARY_PATH.read_text())
    assert summary["distinct_anchors_row_term"] == 28654
    assert summary["anchors_pure_added"] == 27568
    assert summary["anchors_pure_removed"] == 64
    assert summary["anchors_both_removed_and_added"] == 1022
    assert summary["added"] == 28590
    assert summary["removed"] == 1086
    assert summary["changed"] == 29676
    # Consistency the certificate's own arithmetic must satisfy.
    assert (
        summary["anchors_pure_added"] + summary["anchors_pure_removed"] + summary["anchors_both_removed_and_added"]
        == summary["distinct_anchors_row_term"]
    )


def test_gate2_certificate_changed_jsonl_checksum_matches_summary():
    """The committed `changed.jsonl` (54MB, the certificate's own delta
    evidence) must not have been silently edited/truncated/regenerated
    without updating `summary.json`'s own recorded checksum. A single
    sha256 pass is cheap relative to re-parsing every JSON line."""
    summary = json.loads(_SUMMARY_PATH.read_text())
    digest = hashlib.sha256(_CHANGED_PATH.read_bytes()).hexdigest()
    assert digest == summary["changed_sha256"], (
        f"changed.jsonl checksum drifted: expected {summary['changed_sha256']}, got {digest}"
    )


def test_gate2_certificate_still_stands_backend_app_byte_identical_to_certified_tree():
    """Gate 2 / P-R11's own standing condition: the `cc51c49` combined
    measurement was executed against `f267644`. It remains the valid
    certificate for HEAD only as long as `backend/app/` stays byte-identical
    to that tree (contract Context Dump: 'git diff f267644..HEAD --
    backend/app/ is empty -- re-verify independently'). A future change to
    `backend/app/` without a fresh gate-2 run must fail this test, not ship
    silently uncertified."""
    diff = subprocess.run(
        ["git", "-C", str(ROOT), "diff", f"{_CERTIFIED_TREE_SHA}..HEAD", "--", "backend/app/"],
        check=True, capture_output=True, text=True,
    ).stdout
    assert diff == "", (
        f"backend/app/ has diverged from the certified tree {_CERTIFIED_TREE_SHA} -- "
        f"the cc51c49 gate-2 certificate no longer stands under P-R11 until a fresh "
        f"combined run is executed and re-certified:\n{diff[:2000]}"
    )
