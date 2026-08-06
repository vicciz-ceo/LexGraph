"""RED integration tests -- sprint 2026-08-04-defs-us-markers, planner pass
3, priority 3 (gate U1, ruling U-R1; program-manager-relayed corpus fact 3,
re-verified live this pass).

Fact 3 as relayed: "unbounded-last-entry contamination reproduces
corpus-wide -- FED 86% of last entries contaminated, DC 91.7%, NY 79.8%,
with a proven FL example (`540.11`, ~100% of the body claimed vs ~12%
true)." Re-verified live this pass, per this sprint's own standard
(corpus facts must be re-confirmed, not assumed):

- **FED direction CONFIRMED, magnitude measurement-dependent (70-86%
  across independent operationalizations tried this pass) -- a real,
  severe, corpus-wide defect.** Materially NEW finding beyond wave 1's own
  tests: wave 1 pinned this defect only for the RESCUE population (sections
  the fallback extractor recovers). This pass found the SAME defect lives
  in the BASELINE `(N)`-block splitter itself (`us_profile.py`'s
  `_split_into_numbered_blocks`/`extract_definitions_from_section`, shared
  code -- not rule-module territory), on a section that is ALREADY
  successfully extracting non-zero candidates TODAY:
  `USC_T5_C34_S3401` (5 U.S.C. § 3401, real FED "Definitions" section).
  Baseline correctly captures "agency" (519 chars, clean) but
  "part-time career employment"'s real ~487-char definition (ending "...
  temporary or intermittent basis.") is captured as **4,627 chars**,
  swallowing the entire trailing amendment-citation block, "Editorial
  Notes", "Amendments" history, "Statutory Notes and Related
  Subsidiaries", and "Congressional Findings and Purpose" text verbatim.
  Because this lives in the shared baseline splitter (not a
  `EntrySplitterRule`/`TermClauseRule` registration point -- baseline runs
  unconditionally, before any registered rule is even consulted), it is
  OUT OF REACH for any family-3 registry module regardless of gate U3;
  flagged for the program manager/core panel, not silently claimed as our
  own fix.

- **DC (91.7%) and NY (79.8%) do NOT reproduce under any operational
  measure this pass could construct -- CORRECTION.** Sampled DC/NY real
  Definitions-headed bodies directly: DC's ended cleanly at genuine
  sentence boundaries with zero trailing-annotation markers in 8/8 sampled
  rows; a trailing-marker-keyword measure gave DC 0.1%/NY 0.0-6.6%, and a
  length-disproportion measure gave DC 7.5-9.3%/NY 17.6-19.8% -- both far
  below the relayed rates and, on inspection, the "long" outliers were
  genuine (if long) definitions, not corrupted swallows. Not pinned as a
  RED test here (there is nothing live to pin) -- reported as a
  correction in the sprint log's `## P3`.

- **The FL `540.11` example reproduces AS A REAL DEFECT SHAPE, but is
  NOT itself a Definitions-headed section (confirmed live:
  `is_definitions_heading` is False for its own heading, "Unauthorized
  copying of phonograph records..."), and is not currently reachable by
  ANY registered rule (confirmed live: `extract_local_scope_definitions`
  returns 0 candidates today).** It reaches capture, if ever, via the
  ORDINARY-ARTICLE `extract_local_scope_definitions`/`ScopeTriggerRule`
  path (an inline "As used in this section, unless the context otherwise
  requires: (a) ... means ..." preamble), which is `defs-us-scoped-inline`
  family territory per the seam doc's own module inventory
  (`us_scoped_inline.py # defs-us-scoped-inline`), not squarely this
  sprint's Definitions-HEADING family-3 mandate. Core's own registered
  proof rule (`rules/us_scope_trigger_proof.py`) does NOT match this row
  today (confirmed live) because its exact regex requires the quoted term
  immediately after "As used in this section,", and this row interposes
  "unless the context otherwise requires:" before the first quote. **Flagged
  to the program manager as a family-boundary question (same VT-overlap
  precedent as pass 1), while still authored here per this pass's explicit
  brief instruction to include the FL example.** Whichever family ships
  the fix, the required behavior below is the same: the ~12%-true, ~100%-
  claimed defect shape (a scope-trigger clause whose LAST quoted term
  swallows the entire unrelated remainder of the article) must not
  reproduce.

Both tests exercise the REAL production call path
(`ingest_us_statute_rows` -> `run_definition_linking`, imported
unmodified). Real rows vendored verbatim, byte-verified against the source
parquet this pass (`us_markers_unbounded_last_entry_rows.json`).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_unbounded_last_entry_rows.json"
)

_TRAILING_NOTES_MARKERS = (
    "Editorial Notes",
    "Amendments",
    "Statutory Notes",
    "Congressional Findings",
    "Pub. L.",
)


def _load_rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def _ingest_and_link(
    db_session, matter, *, jurisdiction: str, title: str, row: dict
) -> list[Definition]:
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=title,
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    return [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]


def test_fed_and_fl_fixture_rows_have_the_expected_heading_recognition():
    """Sanity: FED's section_title already says "Definitions" (in-family);
    FL's does NOT (confirms it is out-of-family, per this file's module
    docstring)."""
    rows = _load_rows()
    assert is_definitions_heading(rows["USC_T5_C34_S3401"]["section_title"]) is True
    assert is_definitions_heading(rows["STATE_FL_TXXXIII_C540_S540.11"]["section_title"]) is False


def test_real_pipeline_does_not_let_fed_part_time_career_employment_swallow_the_amendment_history_tail(
    db_session, matter_with_users
):
    """`USC_T5_C34_S3401` (5 U.S.C. § 3401) -- a real FED "Definitions"
    section that ALREADY extracts successfully today (unlike wave 1's own
    zero-candidate rows): "agency" and "part-time career employment" are
    both captured by the current baseline `(N)`-block splitter. But
    "part-time career employment", the section's LAST recognized entry, is
    captured as 4,627 chars today -- its real definition is ~487 chars,
    ending "...temporary or intermittent basis." -- because the baseline
    splitter has no closing boundary for the LAST block and runs to end of
    text unconditionally, swallowing the trailing amendment-citation
    block, "Editorial Notes", "Amendments" history, "Statutory Notes and
    Related Subsidiaries", and "Congressional Findings and Purpose" text.
    This is gate U1's boundary-precision mandate applied to an
    ALREADY-CAPTURED section, not merely the rescue population wave 1
    already covers."""
    rows = _load_rows()
    row = rows["USC_T5_C34_S3401"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-FED", title="FED unbounded last entry", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    assert "part-time career employment" in by_term, (
        f"got {sorted(by_term)!r} -- this term is already captured by today's baseline "
        "splitter, so its absence would be a DIFFERENT regression, not this defect"
    )

    ptce = by_term["part-time career employment"]
    for forbidden in _TRAILING_NOTES_MARKERS:
        assert forbidden not in ptce.definition_text, (
            f'"part-time career employment"\'s definition_text illegally contains '
            f"{forbidden!r} -- it swallowed the trailing amendment-history tail "
            f"({len(ptce.definition_text)} chars total, real definition is ~487 chars)"
        )
    assert len(ptce.definition_text) < 600, (
        f'"part-time career employment"\'s real definition is ~487 chars (ending '
        f'"...temporary or intermittent basis."); got {len(ptce.definition_text)} chars, '
        "so it swallowed at least part of the trailing notes/amendment-history block"
    )
    assert ptce.definition_text.rstrip().endswith("temporary or intermittent basis."), (
        f"expected the real sentence boundary; got tail "
        f"{ptce.definition_text[-60:]!r}"
    )


def test_real_pipeline_recovers_fl_540_11_scope_trigger_definitions_without_swallowing_subsection_2(
    db_session, matter_with_users
):
    """`STATE_FL_TXXXIII_C540_S540.11` -- real FL phonograph-piracy statute.
    NOT a Definitions-headed section (see this file's module docstring for
    the family-boundary flag) -- an ordinary article whose body opens "As
    used in this section, unless the context otherwise requires:" followed
    by 5 quoted term definitions ((a)-(e): Owner, Performer, Master
    recording, Person, Article). Today's real pipeline creates 0
    definitions here (confirmed live: no registered rule matches this
    row's exact preamble shape). The proven defect this row illustrates
    (relayed corpus fact 3): "Article", the LAST quoted term, has a true
    ~340-char definition ending "...duplicates, in whole or in part, the
    original." -- immediately followed by unrelated subsection (2)'s
    substantive criminal-law content (unlawful acts, penalties) running to
    a "History: ..." citation tail at the very end of the 7,739-char body.
    A naive "last entry runs to end of text" extractor would capture
    ~100% of the body as "Article"'s definition when the true share is
    ~12% -- whatever mechanism eventually captures this row (this family's
    own broadened trigger, or `defs-us-scoped-inline`'s) must not do that.
    """
    rows = _load_rows()
    row = rows["STATE_FL_TXXXIII_C540_S540.11"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-FL", title="FL 540.11 scope trigger", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    assert set(by_term) == {"Owner", "Performer", "Master recording", "Person", "Article"}, (
        f"got {sorted(by_term)!r}"
    )

    article = by_term["Article"]
    assert article.definition_text.strip().rstrip(".") + "." == (
        "the tangible medium upon which sounds or images are recorded or any "
        "original phonograph record, disk, tape, audio or video cassette, wire, "
        "film, or other medium now known or later developed on which sounds or "
        "images are or can be recorded or otherwise stored, or any copy or "
        "reproduction which duplicates, in whole or in part, the original."
    ), f"got {article.definition_text!r}"

    for forbidden in (
        "It is unlawful",
        "felony of the third degree",
        "History:",
    ):
        assert forbidden not in article.definition_text, (
            f'"Article"\'s definition_text illegally contains {forbidden!r} -- it '
            f"swallowed subsection (2) onward ({len(article.definition_text)} chars "
            f"total, real definition is ~340 chars)"
        )
    assert len(article.definition_text) < 500, (
        f'"Article"\'s real definition is ~340 chars; got {len(article.definition_text)} '
        "chars -- true boundary check failed"
    )
