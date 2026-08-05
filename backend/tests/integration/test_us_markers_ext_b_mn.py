"""RED integration test -- sprint 2026-08-04-defs-us-markers, phase-2
Planner B (B4), Minnesota.

Family 3 sub-case: MN's DOMINANT convention -- confirmed live, full-corpus
sweep this pass (see `## PB1`) -- is a section-mark-prefixed
`Subdivision N. TermName. "term" means ...` (each entry opens with a
"[sign] Subd. N." pilcrow-numbered mini-heading naming the term, THEN the
quoted term itself; the literal lead character is the section-sign glyph
the real parquet row carries, reproduced verbatim in the fixture, not
typed out here to keep this docstring plain ASCII). Full-corpus MN:
1,108 Definitions-headed sections, 1,016 (91.7%) zero-candidate today. Of
those: 6 (0.6%) already correctly-empty (cross-reference, the shipped
classifier DOES recognize MN's phrasing); 965 (95.0%) return >=1 candidate
from the existing `extract_quote_anchored_entries` unmodified (729/1,016 =
71.8% fully clean means-only, 237/1,016 = 23.3% a means+includes mix,
19/1,016 = 1.9% zero means-idiom terms at all); 45 (4.4%) residual (mostly
non-glossary prose bodies under a Definitions heading, not this shape).

**This fixture row exposes a real, NEW boundary defect distinct from every
already-shipped guard**, found by this Planner running the unmodified
engine against the real body (not asserted from prose): MN's own
`Subd. N. TermName.` marker (section-sign-prefixed in the real text) is
not one of the shapes `us_markers_boundary.py`'s hard-stop detection
recognizes at all (only `(N)`, `(letter)`, bare digit-dot, and bare
single-letter-dot are covered) -- so an entry whose OWN quoted definition
ends with a period, immediately followed by the NEXT entry's
`Subd. N. TermName.` marker, swallows that marker text whole. Confirmed
live on this exact row: "Freeze branding"'s captured definition_text ends
`'...hide of a live animal.\\n\\n[section-sign] Subd. 4. Mark.'` (89
chars) instead of the genuine ~72-char clean sentence -- a real marker-leak
of the SAME defect class as `us_markers_boundary.py`'s own documented
`_TRAILING_MARKER_CHAIN_RE` guard (SC's `"(2)"` leak, AZ's `"13."` leak),
but for a marker shape neither existing regex covers.

Today's real pipeline (MN registered nowhere) creates 0 definitions for
this row -- RED for that reason first; the marker-leak guard is the
SECOND assertion, proving a naive "just register MN" fix would still fail
this test even once gap 1 alone is closed, per ruling U-R1."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_markers_ext_b_mn.json"
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


def test_mn_fixture_heading_is_recognized_as_definitions_section():
    row = _load_row("STATE_MN_P17_43_C35_S35.821")
    assert is_definitions_heading(row["section_title"]) is True, (
        f"{row['section_title']!r} must already be recognized as a Definitions heading"
    )


def test_real_pipeline_recovers_mn_definitions_without_leaking_the_next_subd_marker(
    db_session, matter_with_users
):
    """`STATE_MN_P17_43_C35_S35.821` -- MN livestock-marking statute. 4
    real terms (Brand, Freeze branding, Mark, animal) plus one genuinely
    empty `§ Subd. 2. [Repealed, 1980 c 467 s 44]` sub-entry (correctly
    NOT a defined term). "Freeze branding"'s real definition is one clean
    sentence; a naive "just register MN" fix (confirmed live by this
    Planner) swallows the NEXT entry's own `§ Subd. 4. Mark.`
    mini-heading marker into it."""
    row = _load_row("STATE_MN_P17_43_C35_S35.821")
    assert row["section_title"] == "§ 35.821 DEFINITIONS."

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-MN", title="MN ext-b subd-marker", row=row
    )
    terms = {t for d in definitions for t in d.terms}
    assert terms == {"Brand", "Freeze branding", "Mark", "animal"}, (
        f"expected the 4 real MN terms (the repealed Subd. 2 has no term of its own), "
        f"got {sorted(terms)!r}"
    )

    by_term = {t: d for d in definitions for t in d.terms}
    freeze = by_term["Freeze branding"]
    assert "Subd" not in freeze.definition_text, (
        f"'Freeze branding' illegally swallowed the NEXT entry's own "
        f"'§ Subd. 4. Mark.' marker: {freeze.definition_text!r}"
    )
    assert "Mark" not in freeze.definition_text, (
        f"'Freeze branding' illegally swallowed the literal term 'Mark' from the "
        f"following entry's own marker: {freeze.definition_text!r}"
    )
    assert 20 <= len(freeze.definition_text) <= 150, (
        f"'Freeze branding' definition is {len(freeze.definition_text)} chars, expected the "
        f"genuine ~72-char single-sentence definition: {freeze.definition_text!r}"
    )
