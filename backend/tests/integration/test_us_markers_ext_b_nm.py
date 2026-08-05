"""RED integration test -- sprint 2026-08-04-defs-us-markers, phase-2
Planner B (B4), New Mexico.

Family 3 sub-case: NM's DOMINANT convention -- confirmed live, full-corpus
sweep this pass (see this sprint's log `## PB1`) -- is a lettered-dot
`A. "term" means ...` run (letter markers WITHOUT parens, one per line,
separated by `;`), under a heading that is directly "Definitions" (no body
derivation needed). Full-corpus NM: 1,625 Definitions-headed sections,
1,578 (97.1%) zero-candidate today. Of those 1,578, this Planner's
three-tier measurement (correctly-empty classifier + the ALREADY-BUILT
quote-anchored engine `us_markers_boundary.extract_quote_anchored_entries`,
simulated as if NM were added to its jurisdiction list) found: 0 correctly-
empty (neither terminal-status nor cross-reference), 1,509 (95.6%) return
>=1 candidate from the existing engine as-is (821/1,578 = 52.0% would be
FULLY clean -- every quoted term on the row uses a means-family idiom;
688/1,578 = 43.6% are a MIX of means-family and includes/shall-include
idiom, so registering NM alone would only PARTIALLY rescue those rows,
not cleanly per ruling U-R1), and 69 (4.4%) are a genuine residual this
pass could not resolve with the existing engine (single-sentence
prose-style single-term definitions, no marker structure at all -- see
this pass's `## PB1` log entry).

This fixture row (`STATE_NM_C13_A4B_S13-4B-2`, 5 real terms, letter markers
A-E, ALL means-family idiom) is drawn from the 821-row FULLY-CLEAN bucket:
this Planner independently ran the unmodified, already-shipped
`extract_quote_anchored_entries` against this row's real body and confirmed
all 5 entries come back with clean boundaries (no marker leak, no
degenerate collapse) -- so NM's gap on THIS shape is purely the
`us_markers_inline_quote.py` `_JURISDICTIONS` tuple not including
`"US-NM"` (registration-only fix, per this pass's B2 family-collapse
finding), not a new boundary rule. Today's real pipeline (NM unregistered
anywhere) creates ZERO `Definition` rows for this row -- confirmed live,
this test is RED for that reason.

Live-path per program rule (`ingest_us_statute_rows` -> `run_definition_
linking`, both imported unmodified, same discipline as wave 1)."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_markers_ext_b_nm.json"
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


def test_nm_fixture_heading_is_recognized_as_definitions_section():
    """Sanity: the miss is purely extraction, not heading detection."""
    row = _load_row("STATE_NM_C13_A4B_S13-4B-2")
    assert is_definitions_heading(row["section_title"]) is True, (
        f"{row['section_title']!r} must already be recognized as a Definitions heading"
    )


def test_real_pipeline_recovers_all_five_nm_lettered_definitions_end_to_end(
    db_session, matter_with_users
):
    """`STATE_NM_C13_A4B_S13-4B-2` -- NM Art in Public Places Act. 5 real
    terms (artist, fine art, gross negligence, public building, public
    view), lettered markers A-E, all means-family idiom, this Planner's
    own live measurement confirmed clean boundaries on the existing
    engine. Today's real pipeline creates 0 definitions here."""
    row = _load_row("STATE_NM_C13_A4B_S13-4B-2")
    assert row["section_title"] == "§ 13-4B-2. Definitions"

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-NM", title="NM ext-b clean", row=row
    )
    terms = {t for d in definitions for t in d.terms}
    assert terms == {
        "artist",
        "fine art",
        "gross negligence",
        "public building",
        "public view",
    }, f"expected all 5 real NM terms, got {sorted(terms)!r}"

    by_term = {t: d for d in definitions for t in d.terms}
    # boundary-quality guard (ruling U-R1): no entry may swallow the NEXT
    # lettered entry's own quoted term into its own definition_text.
    for other_term in terms:
        assert other_term not in by_term["artist"].definition_text or other_term == "artist", (
            f"{'artist'!r} illegally swallowed neighbour term {other_term!r}: "
            f"{by_term['artist'].definition_text!r}"
        )
    assert 10 <= len(by_term["public view"].definition_text) <= 200, (
        f"'public view' definition is {len(by_term['public view'].definition_text)} chars, "
        f"expected the genuine ~81-char single-clause definition: "
        f"{by_term['public view'].definition_text!r}"
    )
