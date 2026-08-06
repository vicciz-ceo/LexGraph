"""RED integration test -- sprint 2026-08-04-defs-us-markers, phase-2
Planner B (B4), Maine.

Family 3 sub-case: ME's DOMINANT convention -- confirmed live, full-corpus
sweep this pass (see `## PB1`) -- is bare digit-dot markers (`1.` `2.`
..., already structurally supported by the shared engine's `_DIGIT_DOT_
MARKER_RE` hard-stop), each entry opening with a `TermName.` mini-heading
then the quoted term itself (`1. Alternative working hours employment.
"Alternative working hours employment" means ...`). Full-corpus ME: 1,001
Definitions-headed sections, 1,000 (99.9%) zero-candidate today. Of those:
0 already correctly-empty; 962 (96.2%) return >=1 candidate from the
existing `extract_quote_anchored_entries` unmodified (626/1,000 = 62.6%
fully clean means-only, 336/1,000 = 33.6% a means+includes mix, 26/1,000 =
2.6% zero means-idiom terms at all); 38 (3.8%) residual -- and this
residual is a genuinely NAMED unknown, not a shape: spot inspection found
several of these 38 rows (e.g. `STATE_ME_T23_P7_C617_S7221`,
`STATE_ME_T23_P1_C7_S301`) carry a real "Definition"-shaped heading
(verified against the real `section_title`) over a body with NO
term-glossary structure at all and no obvious single implicit definition
either -- this pass could not classify what, if anything, these rows are
meant to capture, and does not claim a shape for them.

**This fixture row exposes a real, NEW boundary defect distinct from every
already-shipped guard**, found by this Planner running the unmodified
engine against the real body: EVERY entry on this real ME row carries a
trailing bracketed legislative-history citation (`[PL 1981, c. 270, §4
(NEW).]`) appended directly after its own defining sentence, on the SAME
line, with no sentence-terminating period before the bracket that the
shared engine's marker/hard-stop scanning would catch (`us_markers_
boundary.TRAILING_STOP_RE` recognizes FED's "Editorial Notes" family and a
handful of other literal phrases, but has no entry for this `[PL ...]`
citation shape at all). Confirmed live: "Job-sharing employment"'s
captured definition_text is `'employment where 2 or more persons share one
position. [PL 1993, c. 707, Pt. G, §1 (AMD).]'` (90 chars) instead of the
genuine ~55-char clean sentence -- present on EVERY entry on this row, not
a corner case.

Today's real pipeline (ME registered nowhere) creates 0 definitions for
this row -- RED for that reason first; the citation-leak guard is the
SECOND assertion, proving a naive "just register ME" fix would still fail
this test, per ruling U-R1."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_markers_ext_b_me.json"
)


def _load_row(act_id: str) -> dict:
    rows = {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}
    return rows[act_id]


def _ingest_and_link(db_session, matter, *, jurisdiction: str, title: str, row: dict) -> list[Definition]:
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


def test_me_fixture_heading_is_recognized_as_definitions_section():
    row = _load_row("STATE_ME_T5_P2_C69_S902")
    assert is_definitions_heading(row["section_title"]) is True, (
        f"{row['section_title']!r} must already be recognized as a Definitions heading"
    )


def test_real_pipeline_recovers_me_definitions_without_leaking_pl_citation_tail(
    db_session, matter_with_users
):
    """`STATE_ME_T5_P2_C69_S902` -- ME flexible-scheduling statute. 4 real
    terms (Alternative working hours employment, Flexible hours
    employment, Job-sharing employment, Part-time employment), bare
    digit-dot markers with a `TermName.` mini-heading. EVERY entry's real
    text carries a trailing `[PL ..., c. ..., §... (...).]` legislative-
    history citation that a naive "just register ME" fix (confirmed live
    by this Planner) leaves attached to the captured definition_text."""
    row = _load_row("STATE_ME_T5_P2_C69_S902")
    assert row["section_title"] == "5 §902. Definitions"

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-ME", title="ME ext-b pl-citation", row=row
    )
    terms = {t for d in definitions for t in d.terms}
    assert terms == {
        "Alternative working hours employment",
        "Flexible hours employment",
        "Job-sharing employment",
        "Part-time employment",
    }, f"expected all 4 real ME terms, got {sorted(terms)!r}"

    by_term = {t: d for d in definitions for t in d.terms}
    for term, d in by_term.items():
        assert "[PL" not in d.definition_text, (
            f"{term!r} illegally retained a trailing legislative-history citation: "
            f"{d.definition_text!r}"
        )
        assert not d.definition_text.rstrip().endswith(")"), (
            f"{term!r}'s definition_text ends in a bracketed-citation-shaped tail: "
            f"{d.definition_text!r}"
        )

    job_sharing = by_term["Job-sharing employment"]
    assert 20 <= len(job_sharing.definition_text) <= 100, (
        f"'Job-sharing employment' definition is {len(job_sharing.definition_text)} chars, "
        f"expected the genuine ~55-char clean sentence: {job_sharing.definition_text!r}"
    )
