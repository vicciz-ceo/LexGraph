"""RED integration tests -- sprint 2026-08-04-defs-us-markers, phase-2
Planner B (B4), Nevada.

NV is the manager's own named special-attention case (M13 V5): 1,262/1,262
Definitions-headed sections (100.0%) yield zero candidates, full-corpus,
THIS branch. This Planner's own root-cause measurement (`## PB1` log entry,
B3) found NOT a long tail of hard shapes but TWO independent, STACKED,
systematic gaps that together explain ~95% of the population:

1. **Extraction-side gap (this test file's first test).** NV's dominant
   term-glossary shape -- `1. "term" means ...` runs, bare digit-dot
   markers (already structurally supported by the shared engine's
   `_DIGIT_DOT_MARKER_RE` hard-stop), curly-quoted terms with a leading
   AND trailing space inside the quote marks (`" Board of Regents "`,
   stripped cleanly by the existing engine's own `.strip()`) -- is
   IDENTICAL in shape to VA/WA/FED's already-solved convention. Simulating
   registration (adding `"US-NV"` to `us_markers_inline_quote.py`'s
   `_JURISDICTIONS` tuple, nothing else) against the real fixture row
   below returns exactly the right 5 terms with clean boundaries, this
   Planner verified directly against the unmodified `extract_quote_
   anchored_entries`. Across NV's full 1,262-row zero-yield population,
   337 rows (26.7%) return >=1 candidate from the existing engine
   unmodified. NV is simply missing from that tuple -- a registration-only
   gap on this sub-population, not a new boundary rule.

2. **Classifier-side gap (this test file's second test).** NV's OWN
   majority idiom for "definitions live in another section" is "As used
   in <chapter ref>, ... the words and terms defined in NRS <citation>
   ... have the meanings ascribed to them in those sections." -- genuinely
   correctly-empty (no operative defining content of its own), but using
   different keywords ("defined in ... have the meanings ascribed to")
   than the already-shipped `correctly_empty._CROSS_REFERENCE_RE`, which
   is anchored to "definitions ... in <citation> apply/govern/are
   applicable". This Planner measured (broadened, scratchpad-only
   regex, not committed) this idiom alone explains roughly 862-925/1,262
   (68-73%) of NV's zero-yield population, depending on how many minor
   trailing-clause phrasing variants are folded in -- named as an
   estimated RANGE, not a single exact count, because the scratchpad
   regex used to measure it is not the shipped classifier and a residual
   ~5% of NV's population uses further phrasing variants of the SAME
   idiom this Planner did not fully enumerate (see `## PB1` for the
   honest breakdown, including the small remaining "includes"-idiom and
   prose-definition sub-populations that neither gap explains).

Both gaps are demonstrated live on real fixture rows below, driving the
REAL unmodified functions this sprint already ships (`extract_quote_
anchored_entries` via the full pipeline for gap 1; `classify_correctly_
empty` directly for gap 2 -- a pure function of body_text, not itself part
of `USProfile.extract_definitions_from_section`, so this second test
exercises the real, live, unstubbed classifier rather than the extraction
seam, consistent with ruling U-R3 that the classifier is independently
verifiable)."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.correctly_empty import classify_correctly_empty
from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_markers_ext_b_nv.json"
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


def test_nv_fixtures_headings_are_recognized_as_definitions_sections():
    """Sanity: both fixture rows already have a recognized Definitions
    heading -- gap 1 is purely extraction, gap 2 is purely classification,
    neither is a heading-detection miss."""
    for act_id in ("STATE_NV_T34_C396_S396.005", "STATE_NV_T3_C40_S40.426"):
        row = _load_row(act_id)
        assert is_definitions_heading(row["section_title"]) is True, (
            f"{act_id}: {row['section_title']!r} must already be recognized"
        )


def test_real_pipeline_recovers_all_five_nv_higher_education_definitions_end_to_end(
    db_session, matter_with_users
):
    """`STATE_NV_T34_C396_S396.005` -- 5 real terms (Board of Regents,
    Community college, State college, System, University), bare digit-dot
    markers, curly-quoted terms with internal padding spaces
    (`" Board of Regents "`), all means-family idiom. This Planner
    confirmed live that `extract_quote_anchored_entries` (already shipped,
    unmodified) returns all 5 with clean boundaries on this exact body --
    NV's own gap here is that it is absent from `us_markers_inline_quote.
    py`'s `_JURISDICTIONS` tuple. Today's real pipeline (NV registered
    nowhere) creates 0 definitions."""
    row = _load_row("STATE_NV_T34_C396_S396.005")
    assert row["section_title"] == "Definitions"

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-NV", title="NV ext-b clean", row=row
    )
    terms = {t for d in definitions for t in d.terms}
    assert terms == {
        "Board of Regents",
        "Community college",
        "State college",
        "System",
        "University",
    }, f"expected all 5 real NV terms, got {sorted(terms)!r}"

    by_term = {t: d for d in definitions for t in d.terms}
    # padding-space guard: NV's real convention quotes `" Term "` with
    # internal leading/trailing spaces -- the captured TERM itself must be
    # the stripped, clean string, never carrying a leading/trailing space.
    for term in terms:
        assert term == term.strip(), f"term {term!r} was not stripped of padding spaces"
    assert 10 <= len(by_term["System"].definition_text) <= 120, (
        f"'System' definition is {len(by_term['System'].definition_text)} chars, expected the "
        f"genuine ~38-char single-clause definition: {by_term['System'].definition_text!r}"
    )


def test_nv_cross_reference_idiom_is_not_yet_recognized_as_correctly_empty():
    """`STATE_NV_T3_C40_S40.426` -- a real, genuine NV cross-reference body
    ("the words and terms defined in NRS 40.427 , 40.428 and 40.429 have
    the meanings ascribed to them in those sections") with NO operative
    defining content of its own. This is NOT a miss -- the real
    definitions live in the cited sections -- but the shipped
    `correctly_empty.classify_correctly_empty` (`_CROSS_REFERENCE_RE`,
    anchored to "definitions ... in <citation> apply/govern/are
    applicable") does not recognize NV's own "defined in ... have the
    meanings ascribed to" idiom. Live, unstubbed call to the real shipped
    classifier -- RED because it wrongly reports this genuinely
    correctly-empty row as a MISS today, not because of any extraction
    seam."""
    row = _load_row("STATE_NV_T3_C40_S40.426")
    assert row["section_title"] == "Definitions"

    result = classify_correctly_empty(row["text"])
    assert result.is_correctly_empty is True, (
        f"NV's own cross-reference idiom ({row['text']!r}) must classify as "
        f"correctly-empty (real definitions live in the cited NRS sections, not "
        f"here) -- got {result!r}"
    )
    assert result.reason == "cross_reference"
