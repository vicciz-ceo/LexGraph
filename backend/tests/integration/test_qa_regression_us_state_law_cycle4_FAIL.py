"""QA bounce evidence -- sprint 2026-08-02-us-state-law, QA cycle 4.

INTENTIONALLY RED. Ruling R15a (this cycle's headline probe) asks QA to
measure PRECISION of wave 6's inline-quote extraction fallback -- whether
the ~9,661 IL / ~6,961 CA candidate terms are genuine defined legal terms
or extraction noise. Manual random sampling (30+ terms/state) came back
clean for all four audited states (IL/CA/DE/TX). A full-corpus automated
scan (every real row in `us_ca_statutes.parquet`) initially flagged a
second suspected defect (a curly-quote-style mismatch swallowing a term
into the next entry) -- but that one does NOT survive the real production
path: `pipeline.py` calls `normalize_for_parsing` (which collapses ALL
curly-quote variants to plain ASCII `"` -- see `normalize.py`'s
`_QUOTE_VARIANTS_RE`) BEFORE Stage 2's extraction ever runs, which happens
to fix that exact shape. Proven not-a-defect by
`test_real_pipeline_correctly_recovers_a_quote_style_mismatched_term_in_a_
real_california_section` below (a green regression guard, not a bounce --
kept here rather than silently dropped, since it disproves a real initial
hypothesis and documents WHY, matching this sprint's evidentiary standard
of live-path verification over unit-level assumption).

[QA-FAIL] defect 8 -- the SAME full-corpus scan on the shared numbered-
entry extractor (`USProfile.extract_definitions_from_section`, the
ORIGINAL DE/TX/IL/CA-shared extractor, not new wave-6 code, but newly
EXPOSED to CA bodies for the first time by wave 6's heading-derivation
dispatch, since CA never reached this function before) found a genuine,
live-path-confirmed multi-entry boundary-detection failure: a real
California row (`STATE_CA_Cgov_T5_D2_P1_C5_A8_S54221`, Surplus Land Act
definitions, committed at
`backend/tests/fixtures/us_statutes/qa_cycle4_rows.json`) produces one
single `Definition` record for the term "Dispose" whose `definition_text`
is **26,715 characters** long and contains the COMPLETE, separately-
defined text of at least 3 other distinct terms ("Open-space purposes",
"Sectional planning area", "Sectional planning area document")
concatenated inside it -- none of those 3 terms is ever recovered as its
own `Definition` row, through the REAL `ingest_us_statute_rows` ->
`run_definition_linking` path (proven below, not just a unit-level
symptom). This is exactly the "pollutes the knowledge base with
assertions reviewers must clean up" failure mode the cycle-4 brief warns
about: one garbled, 26 KB "Dispose" record instead of 4 clean ones.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE_JSON = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "qa_cycle4_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def test_real_pipeline_correctly_recovers_a_quote_style_mismatched_term_in_a_real_california_section(
    db_session, matter_with_users
):
    """Green regression guard (NOT a bounce): documents that a suspected
    defect -- a real CA row whose entry (a) uses the SAME left-curly quote
    character on both sides of its term ("Adjustment factor“ ... instead of
    a matching “Adjustment factor”) -- does NOT actually reach the
    production pipeline as garbage, because `normalize_for_parsing`
    collapses curly-quote variants to plain `"` before Stage 2 extraction
    runs, which happens to make the open/close pair consistent again."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    rows = _load_rows()
    row = rows["STATE_CA_Cshc_D1_C1_A6.5_S217"]
    assert row["section_title"] == "Section 217", (
        "fixture must reproduce the real CA placeholder-heading shape"
    )
    assert "“Adjustment factor“ means" in row["text"], (
        "fixture must reproduce the real quote-style-mismatch mojibake in "
        "the RAW row -- both quote marks around the term are the SAME "
        "left-curly character, not a matching open/close pair -- this is "
        "what makes the case worth guarding, even though normalization "
        "fixes it before extraction sees it"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="California Codes (QA cycle4 quote-mismatch probe)",
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction="US-CA",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    all_terms = {term for d in result["created_definitions"] for term in d["terms"]}

    assert "Adjustment factor" in all_terms, (
        "the real production pipeline should recover the genuine term "
        '"Adjustment factor" cleanly from this real CA section -- '
        "normalize_for_parsing's curly-quote collapse (app/definition_links/"
        "normalize.py's _QUOTE_VARIANTS_RE) runs before Stage 2 extraction, "
        "making the mismatched-in-the-raw-row quote pair consistent again"
    )
    assert not any(len(term) > 100 for term in all_terms), (
        f"no genuine defined legal term in this section should run longer "
        f"than ~100 characters: {sorted((t for t in all_terms if len(t) > 100), key=len)!r}"
    )


def test_real_pipeline_swallows_three_other_terms_into_one_bloated_california_definition(
    db_session, matter_with_users
):
    """Live-path proof of defect 8: 'Dispose' must not absorb the entire
    rest of the section's other, separately-defined terms."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    rows = _load_rows()
    row = rows["STATE_CA_Cgov_T5_D2_P1_C5_A8_S54221"]
    assert row["section_title"] == "Section 54221"
    assert '“Open-space purposes” means' in row["text"], (
        "fixture must reproduce the real CA section containing (at least) "
        "4 distinct defined terms after 'Dispose': 'Open-space purposes', "
        "'Sectional planning area', and 'Sectional planning area document'"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="California Codes (QA cycle4 boundary-swallow probe)",
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction="US-CA",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    all_terms = {term for d in result["created_definitions"] for term in d["terms"]}

    assert "Open-space purposes" in all_terms, (
        '"Open-space purposes" is a real, separately-defined term in this same '
        "real CA section, immediately after \"Dispose\" -- but the pipeline "
        'never recovers it as its own Definition: it is silently absorbed, '
        'along with "Sectional planning area" and "Sectional planning area '
        'document", into a single, 26,715-character "Dispose" definition_text '
        "instead. Found via a full-corpus scan of the shared numbered-entry "
        "extractor's live output across all 161,429 real CA rows -- this "
        "extractor is not new wave-6 code, but wave 6's heading-derivation "
        "dispatch is what exposes it to CA bodies for the first time"
    )

    dispose_defs = [
        db_session.get(Definition, d["id"])
        for d in result["created_definitions"]
        if "Dispose" in d["terms"]
    ]
    assert dispose_defs, '"Dispose" itself must still be recovered as a term'
    for definition_row in dispose_defs:
        assert len(definition_row.definition_text) < 2000, (
            f'"Dispose"\'s own definition_text is {len(definition_row.definition_text)} '
            "characters long and contains at least 3 OTHER terms' complete "
            "definitions concatenated inside it -- a genuine defined term's own "
            "definition_text should not run into tens of thousands of "
            "characters by swallowing unrelated, separately-quoted entries"
        )
