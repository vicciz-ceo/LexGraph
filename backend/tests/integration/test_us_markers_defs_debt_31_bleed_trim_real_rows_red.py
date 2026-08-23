"""Sprint 2026-08-23-defs-debt-31, Item 1 (issue #31 debt class 1 -- "next-
entry bleed on wave additions", issue #27 tracked debt). RED-before-green
recovery tests using REAL, vendored corpus rows (post-ingest, never raw
parquet text -- NY's own escaped-\\n formatting is normalized by
`ingest_us_statute_rows` before these assertions ever run).

Seam (gate 8): `app.definition_links.us_profile._extract_inline_quoted_
definitions` -- the fallback that admits a candidate whenever a quoted
term is followed, within a 200-char gap (`_MEANS_IDIOM_GAP_RE`), by a
defining idiom, then runs the definition to the START of the next
RECOGNIZED entry (or end of text) with NO trailing-stop/ceiling of its
own. That is the exact defect these three real rows independently
reproduce: each one's TRUE definition is a single short clause: the
capture keeps going into a completely unrelated, later-numbered
subsection because nothing bounds it earlier. `us_markers_boundary.py`'s
own `trailing_stop_limit`/`compute_hard_stops`/`close_entries` machinery
already solves exactly this for the PRIMARY engine; gate 8 names both
files as the seam a fallback fix may touch.

Gate 1 is explicit: TRIM, never DROP (D-RECALL-FP/D-RECALL-FP) -- every
assertion below requires the TERM to stay present with a shorter, correctly-
bounded `definition_text`, not disappear. All three are 100% live-verified
against the current worktree HEAD (`5962c98`) via the real
`ingest_us_statute_rows` -> `run_definition_linking` pipeline before this
file was written -- the "before" bytes quoted in each docstring are the
actual current captures, not a projection (P-R11: no hand-authored ledger).

Finding worth recording: `USC_T5_C75_S7511` ("furlough") was one of the
issue #27/#31 evidence base's own 118 FX7-remainder rows (fully DROPPED by
the ceiling, no capture at all). On this worktree's HEAD it is now
CAPTURED -- the already-landed idiom widening (prior sprint, Items 1-3)
incidentally gave it a downstream boundary via a newly-recognized idiom
elsewhere in the section, which flips it from "ceiling-dropped total loss"
into an ordinary "next-entry bleed" case. It is used here as a THIRD real
bleed exemplar (not as an FX7-remainder exemplar -- see this sprint's
Item 4 file, which explains the same migration and why a fresh real
FX7-remainder exemplar was not re-derived at planning altitude)."""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

BLEED_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_markers_defs_debt_31_bleed_rows.json"
)
FX7_MIGRATED_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_defs_debt_31_fx7_remainder_rows.json"
)


def _run(db_session, matter_with_users, act_id: str, jurisdiction: str, fixture_path: Path) -> dict:
    rows = {r["act_id"]: r for r in json.loads(fixture_path.read_text(encoding="utf-8"))}
    row = rows[act_id]
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title=f"{act_id} debt-31 bleed-trim recovery",
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term: dict[str, list[str]] = {}
    for d in definitions:
        for t in d.terms:
            by_term.setdefault(t, []).append(d.definition_text)
    return by_term


def test_red_ny_multi_subsection_bleed_is_trimmed_to_true_definition(db_session, matter_with_users):
    """`STATE_NY_ASOS_A6_T1_S390`, term `"Enrolled legally exempt provider"`
    (last of a lettered (a)-(g) definitions list). TRUE definition is one
    ~341-char sentence ending "...regulations of the office of children
    and family services." -- verified against the real row text. TODAY
    (live-verified this pass) the capture is 3,154 chars: it bleeds straight
    through "2. * (a) Child day care centers caring for seven or more
    children..." (a NEW, unrelated licensing subsection) and keeps going
    into a THIRD subsection's own numbered sub-clauses before stopping on
    an unrelated marker. This is real statutory content mis-captured, not
    a phantom (D-MAP: anchor is correct, bytes are wrong) -- exactly the
    'next-entry bleed' shape issue #31 names."""
    by_term = _run(
        db_session, matter_with_users, "STATE_NY_ASOS_A6_T1_S390", "US-NY", BLEED_FIXTURE
    )
    texts = by_term.get("Enrolled legally exempt provider")
    assert texts, "the anchor itself must never be dropped while fixing its bytes (D-RECALL-FP)"
    expected = (
        "shall mean a person who is a\ncaregiver or entity that is not required to be licensed or registered\n"
        "pursuant to this section and that is enrolled to be a caregiver and\n"
        "provide subsidized child care services to eligible families in\n"
        "accordance with title five-C of this article and the regulations of the\n"
        "office of children and family services."
    )
    assert texts == [expected], (
        f"'Enrolled legally exempt provider' must be trimmed to its true, "
        f"correctly-bounded definition (TRIM not DROP) -- got "
        f"{texts[0][:120]!r}... ({len(texts[0])} chars, was 3154 before this fix)"
        if texts
        else "missing"
    )


def test_red_oh_scrape_metadata_tail_and_bleed_trimmed_through_fallback_path(db_session, matter_with_users):
    """`STATE_OH_T49_C4905_S4905.331`, term `"Proceeding"` -- reached only
    via the fallback (bare `includes`, never recognized by the PRIMARY
    engine's `_TIGHT_IDIOM_RE`, so OH's own `EntrySplitterRule`
    (`us_markers_oh_trailing_clause.py`, which calls the primary engine)
    never sees this term at all; confirmed live this pass). TRUE definition
    is one ~93-char sentence. TODAY the capture runs 1,373 chars into an
    entirely unrelated settlement-inducement subsection AND ends with OH's
    own `"Last updated July 9, 2025 at 12:24 PM"` scrape-metadata stamp --
    the exact named defect (issue #31: "4 OH items also carry a scrape
    bleed"). OH's own `_LAST_UPDATED_TAIL_RE` cleanup exists but lives in a
    function this fallback-sourced candidate never passes through --
    confirming the evidence's own finding that the fallback bypasses OH's
    existing cleanup entirely."""
    by_term = _run(
        db_session, matter_with_users, "STATE_OH_T49_C4905_S4905.331", "US-OH", BLEED_FIXTURE
    )
    texts = by_term.get("Proceeding")
    assert texts, "the anchor itself must never be dropped while fixing its bytes (D-RECALL-FP)"
    expected = "a proceeding relating to electric service under Chapters 4909. and 4928. of the Revised Code."
    assert texts == [expected], (
        f"'Proceeding' must be trimmed to its true definition with the OH "
        f"scrape-metadata tail gone -- got {texts[0]!r}"
    )
    # Regression guard: OH's own other, already-correct captures on this row
    # must be untouched by this fix.
    assert by_term.get("Electric distribution utility") == ["as in section 4928.01 of the Revised Code."]


def test_red_fed_furlough_bleed_trimmed_not_left_swallowing_eligibility_list(db_session, matter_with_users):
    """`USC_T5_C75_S7511`, term `"furlough"` -- see this file's own module
    docstring for why this named FX7 example now reproduces the BLEED
    class rather than a total ceiling drop on this worktree's HEAD. TRUE
    definition is one ~144-char sentence. TODAY the capture runs on into
    "(b) This subchapter does not apply to an employee-- (1) whose
    appointment is made by and with the advice and consent of the
    Senate;..." -- a wholly unrelated eligibility-exclusion list, not part
    of defining 'furlough'."""
    by_term = _run(
        db_session, matter_with_users, "USC_T5_C75_S7511", "US-FED", FX7_MIGRATED_FIXTURE
    )
    texts = by_term.get("furlough")
    assert texts, "the anchor itself must never be dropped while fixing its bytes (D-RECALL-FP)"
    expected = (
        "means the placing of an employee in a temporary status without duties "
        "and pay because of lack of work or funds or other nondisciplinary reasons."
    )
    assert texts == [expected], (
        f"'furlough' must be trimmed to its true definition, not bleed into "
        f"the unrelated '(b) This subchapter does not apply...' eligibility "
        f"list -- got {texts[0]!r}"
    )
