"""RED test -- sprint 2026-08-05-defs-core-follow-on-2, gate G3
("FED unbounded-last-entry", program doc `2026-08-04-definition-
completeness.md`).

**The defect.** `us_profile._split_into_numbered_blocks` (line 346)
accumulates lines into `current` and, once the loop over `text.split("\n")`
ends, unconditionally does `if current is not None: blocks.append(current)`
-- there is no terminator/boundary check of any kind on the FINAL block, so
it always runs to the literal end of the input string. Every OTHER block
is correctly bounded by the START of the next recognized entry marker;
only the last one is not. This is shared baseline code
(`extract_definitions_from_section` / `USProfile.extract_definitions_
from_section` both call it, unconditionally, before any registered
`EntrySplitterRule` is even consulted) -- it is why the markers panel
(`sprint 2026-08-04-defs-us-markers`) could not fix this from behind the
registry seam: baseline wins the dedup race and there is no rule-level
hook that runs before it.

**Re-authored, not cherry-picked.** The markers panel's own Planner pass 3
authored an equivalent held-RED integration test on `claude/defs-us-
markers` (`backend/tests/integration/test_us_markers_unbounded_last_entry.py
::test_real_pipeline_does_not_let_fed_part_time_career_employment_swallow_
the_amendment_history_tail`) -- per this sprint's "vendor REDs, don't
cherry-pick" rule, this file is a fresh, independent authorship targeting
the SAME real defect and the SAME real row (byte-identity is a property of
the corpus, not of the other panel's commit -- see the provenance note
below), not an import or copy of their test. Their file also carries a
second test (`STATE_FL_TXXXIII_C540_S540.11`) that the markers panel
itself flagged as OUT of their family's reach via a DIFFERENT code path
(`extract_local_scope_definitions`/`ScopeTriggerRule`, the ordinary-article
scope-trigger family, not `_split_into_numbered_blocks`) -- that FL case is
NOT re-authored here: it is not this gate's defect (`_split_into_numbered_
blocks`' last entry specifically), and fixing it is a different family's
mandate, not this sprint's G3.

**Fixture provenance.** `backend/tests/fixtures/us_statutes/
g3_fed_unbounded_last_entry_row.json` vendors ONE real row, `USC_T5_C34_
S3401` (5 U.S.C. § 3401, "Definitions", real FED chapter-34 part-time
career employment provisions), all 5 fields copied byte-for-byte from the
real `us_federal_statutes.parquet` snapshot at
`/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/
snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/`. Independently
verified (this pass, not assumed from the other panel's fixture): read the
row directly out of the real parquet file with pandas and confirmed
`hashlib.sha256(row["text"].encode()).hexdigest()` ==
`21f0d0cb6f08b584f1209df76a335df863d155c7b333ac5f098e4ce54223bd03` --
this fixture's `text` field is byte-identical to the real corpus row, and
`section_title` == `"Definitions"` is independently confirmed
`is_definitions_heading`-True.

**What the real row proves.** Baseline ALREADY extracts 2 candidates from
this row today -- "agency" (clean, ~519 chars) and "part-time career
employment" (the section's LAST recognized entry). This is not a
zero-candidate/rescue-population row (unlike wave 1's own targets on the
markers branch); it demonstrates the defect on a section that is already
"working" by today's own zero-candidate metric, which is exactly why it is
dangerous: nothing about today's coarse "did this row produce >=1
candidate" health check would catch it. "part-time career employment"'s
TRUE definition (independently located in the raw fixture text below, from
its own "means" through "...temporary or intermittent basis." --
`definition_text` keeps the leading defining-idiom word, confirmed against
this row's own sibling "agency" entry, which is already correctly bounded
today and itself reads `"means—\n\n(A) an Executive agency..."`) is exactly
493 characters; because `_split_into_numbered_blocks` has no closing
block, its captured `definition_text` runs on through the amendment
citation, "Editorial Notes", "Amendments" history, "Statutory Notes and
Related Subsidiaries", and "Congressional Findings and Purpose" sections
that the vaquill dataset bundles into the same `text` field -- 4,627
characters total as measured against this exact fixture this pass.

Drives the REAL production call chain unmodified: `ingest_us_statute_rows`
-> `run_definition_linking` (which resolves `get_profile("US-FED")` ->
`USProfile.extract_definitions_from_section` -> `_split_into_numbered_
blocks`), exactly `pipeline.py`'s own dispatch order. Nothing here is
mocked, stubbed, or reimplemented.
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
    / "g3_fed_unbounded_last_entry_row.json"
)

# Independently confirmed (this pass) trailing non-operative markers the
# vaquill dataset bundles after the operative FED "Definitions" text --
# NOT derived from `_split_into_numbered_blocks`' own entry grammar (that
# would violate M18's denominator law): these are content keywords, chosen
# because a genuine defined-term's OWN substantive legal prose does not
# use them, verified against this fixture's real trailing content.
_TRAILING_NOTES_MARKERS = (
    "Editorial Notes",
    "Amendments",
    "Statutory Notes",
    "Congressional Findings",
    "Pub. L.",
)


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def test_fixture_row_is_a_recognized_definitions_heading():
    """Sanity: this row's real `section_title` ("Definitions") is already
    `is_definitions_heading`-True today -- if this ever goes False the rest
    of this file's RED signal would be confounded by a heading-detection
    regression, not this gate's boundary defect."""
    row = _load_row()
    assert row["act_id"] == "USC_T5_C34_S3401"
    assert is_definitions_heading(row["section_title"]) is True


def test_real_pipeline_stops_part_time_career_employment_at_its_own_sentence_boundary(
    db_session, matter_with_users
):
    """The live defect, on the live path. Today `_split_into_numbered_
    blocks`'s last block has no closing boundary, so "part-time career
    employment" (5 U.S.C. § 3401's LAST recognized entry) absorbs
    everything after it in the row's `text` field -- the trailing
    amendment-citation/notes block included. The fix must stop this
    entry's `definition_text` at its own real sentence boundary (`"...
    temporary or intermittent basis."`) without dropping "agency"
    (unaffected -- it is not the last entry) or truncating "part-time
    career employment" itself short of its own true ~487-char content
    (that would be a DIFFERENT, equally serious defect -- see this
    sprint's non-regression guard file for the corpus evidence on that
    risk)."""
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="FED unbounded last entry (G3)",
        rows=[row],
        jurisdiction="US-FED",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [
        db_session.get(Definition, d["id"]) for d in result["created_definitions"]
    ]
    by_term = {t: d for d in definitions for t in d.terms}

    assert "agency" in by_term, f"got {sorted(by_term)!r} -- unrelated regression"
    assert "part-time career employment" in by_term, (
        f"got {sorted(by_term)!r} -- this term is already captured by today's "
        "baseline splitter (it is not a zero-candidate row), so its absence "
        "here would be a DIFFERENT regression, not this gate's defect"
    )

    ptce = by_term["part-time career employment"]
    for forbidden in _TRAILING_NOTES_MARKERS:
        assert forbidden not in ptce.definition_text, (
            f'"part-time career employment"\'s definition_text illegally '
            f"contains {forbidden!r} -- it swallowed the trailing "
            f"amendment-history tail ({len(ptce.definition_text)} chars "
            "total; the real definition is 493 chars)"
        )
    assert len(ptce.definition_text) == 493, (
        f'"part-time career employment"\'s real definition (including the '
        f'leading "means" idiom word, per the sibling "agency" entry\'s own '
        f"convention) is exactly 493 characters (independently measured "
        f"against the raw fixture text this pass); got "
        f"{len(ptce.definition_text)} chars"
    )
    assert ptce.definition_text.endswith("temporary or intermittent basis."), (
        f"expected the real sentence boundary; got tail "
        f"{ptce.definition_text[-60:]!r}"
    )
