"""RED test -- sprint 2026-08-04-defs-us-markers, phase-2 Planner A, item
A5. `STATE_NY_ARPP_A8_S280-D` (N.Y. Real Property Law § 280-d) is
EXPLICITLY assigned to this panel by the manager brief as the named
representative of NY's unquoted LETTERED-paragraph convention:

    (a) Reverse mortgage loan. A reverse mortgage loan as defined in
    section two hundred eighty of this article, which is issued in this
    state pursuant to the home equity conversion mortgage for seniors
    program operated by the federal Department of Housing and Urban
    Development.

Marker is a bare `(a)`/`(b)`/`(c)` letter-paren, the defined term is
Title-Case (NOT all-caps like AL, NOT NC's `.--` dash separator) followed
by a single period, then a defining sentence -- here a POINTER definition
(D-MT-E1: "as defined in section two hundred eighty of this article"),
but sibling entry `(c) Department.` in the same body is a flat
declarative sentence with no defining verb at all ("The department of
financial services established pursuant to..."), so this convention's
idiom is NOT uniform -- apposition after the marker+term+period is the
only reliable signal, not any particular verb.

**This row is a RECOGNITION-side miss, not merely an extraction-side
one** -- verified directly against the real `us_ny_statutes.parquet`
snapshot before writing this test: `section_title` is "Federal home
equity conversion mortgage default and foreclosure regulation" (no word
"definition" anywhere), and `derive_heading_from_body` also returns
`None` for it (body-derived-heading placeholder detection does not fire
on this title shape either). So `USProfile.is_definitions_heading`
returns `False` by both paths -- heading recognition is a SEPARATE,
already-flagged concern (M10's Q-C, headings panel's H-R1), not this
panel's to fix. Per M10/M11 precedent (`STATE_WA_T50_C29_S030`, the
sibling named-row RED for the SAME acceptance condition) and core's own
`test_ingest_us_statutes_ny_newline_defect.py` (the established pattern
for this exact situation in this codebase): this test does NOT assume
the heading-dispatch gate passes. It drives
`get_profile("US-NY").extract_definitions_from_section` DIRECTLY -- the
exact call `pipeline.py` makes once dispatch succeeds -- so the
assertion below is discriminated purely by the EXTRACTION defect (no
rule anywhere recognizes a bare `(letter)` marker + Title-Case term +
single-period-no-dash convention), never confounded by the separate
recognition-side gap. Acceptance condition (M10's Q-C, verbatim):
"extraction must yield at least the term the heading/citation pair
implies so their pointer-row edge can attach" -- the term implied here
is "Reverse mortgage loan".

**U-R11 applied.** The fixture (`us_markers_ext_a_ny_arpp_a8_s280d_rows.json`)
stores the RAW corpus row byte-for-byte (containing NY's literal
two-character `\\n` sequences, verified against the real parquet
snapshot before this file was written). This test applies the SAME
`text.replace("\\n", "\n")` transform `ingest_us_statutes.py:237` applies
at ingest time (never rewriting the fixture itself) before computing the
scope/candidates below -- so this test is evaluated against
POST-INGEST, production-faithful text, not the raw parquet shape.

RED today: `extract_definitions_from_section` returns 0 candidates for
this body (verified directly, both `heading_was_derived=True` and
`=False` -- confirmed independent of the recognition-side question this
test deliberately does not exercise)."""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_ext_a_ny_arpp_a8_s280d_rows.json"
)


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def test_fixture_row_is_the_expected_real_ny_row():
    """Sanity: byte-verified against the real corpus row before this test
    was written (act_id + a slice of the raw, pre-transform text)."""
    row = _load_row()
    assert row["act_id"] == "STATE_NY_ARPP_A8_S280-D"
    assert row["state"] == "ny"
    # Raw corpus bytes -- literal backslash-n, per U-R11 (not yet transformed).
    assert "\\n" in row["text"]
    assert "\n" not in row["text"], "fixture must store RAW corpus bytes, not pre-transformed text"
    assert "(a) Reverse mortgage loan. A reverse mortgage loan as defined in" in row["text"]


def test_ny_lettered_paragraph_heading_is_not_recognized_today_recognition_side_only():
    """Documents WHY this test bypasses heading dispatch: both baseline
    paths genuinely return false/None for this row's real title, verified
    live -- NOT this panel's defect to fix (M10's Q-C), but recorded so a
    future reader does not mistake this RED for an extraction bug when
    recognition is what silently gates it out in the full pipeline."""
    from app.definition_links.us_profile import is_definitions_heading

    row = _load_row()
    heading = row["section_title"]
    assert heading == "Federal home equity conversion mortgage default and foreclosure regulation"
    assert is_definitions_heading(heading) is False


def test_real_pipeline_extraction_recovers_reverse_mortgage_loan_from_ny_lettered_paragraph(
    db_session, matter_with_users
):
    """Live path, mirroring `test_ingest_us_statutes_ny_newline_defect.py`'s
    established pattern for a recognition-side-miss row: real
    `ingest_us_statute_rows` -> real `SourceSpan.quote_text` (U-R11
    transform applied here, exactly as `ingest_us_statutes.py:237` does)
    -> real `normalize_for_parsing` (Stage 0, unconditional for every
    article) -> real `get_profile("US-NY").extract_definitions_from_section`
    (Stage 2, the exact call `pipeline.py` makes once its own dispatch
    gate -- a SEPARATE concern -- routes an article here).

    Today this fails with `0 == 1` candidates -- no registered
    EntrySplitterRule/TermClauseRule for `US-NY` (or `US-*`) recognizes a
    bare `(letter)` marker + Title-Case term + single-period-no-idiom
    entry boundary; baseline's own `_split_into_numbered_blocks` +
    `_leading_quote_candidate` require a QUOTED leading term, which this
    convention never has."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.normalize import normalize_for_parsing
    from app.definition_links.profiles import get_profile
    from app.models.article import Article
    from app.models.source_span import SourceSpan

    m = matter_with_users
    row = _load_row()

    result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="NY ARPP A8 S280-D (A5 lettered-paragraph fixture)",
        rows=[row],
        jurisdiction="US-NY",
    )
    assert result["skipped_rows"] == []
    assert len(result["article_ids"]) == 1

    article = db_session.get(Article, result["article_ids"][0])
    span = db_session.get(SourceSpan, article.source_span_id)

    # U-R11: `ingest_us_statute_rows` already applied `text.replace("\\n",
    # "\n")` when it populated `SourceSpan.quote_text` (ingest_us_statutes.py
    # line 237) -- `span.quote_text` is ALREADY post-ingest, production-
    # faithful text, exactly what production hands to Stage 0 below.
    assert "\\n" not in span.quote_text, "ingest must have already applied the U-R11 transform"

    # Stage 0 -- the same unconditional call `pipeline.py` makes for every
    # article, regardless of jurisdiction.
    normalized_body = normalize_for_parsing(span.quote_text)

    # Stage 2 -- called directly (not via `run_definition_linking`) so this
    # assertion is discriminated purely by the extraction defect, never by
    # the separate, already-known recognition-side gap (see the test above).
    profile = get_profile("US-NY")
    scope = profile.determine_scope(normalized_body)
    candidates = profile.extract_definitions_from_section(
        normalized_body, scope=scope, heading_was_derived=True
    )

    by_term = {t: c for c in candidates for t in c.terms}
    assert "Reverse mortgage loan" in by_term, (
        f"extract_definitions_from_section yielded {sorted(by_term)!r} -- expected "
        "at least 'Reverse mortgage loan' (M10's Q-C acceptance condition: "
        "extraction must yield at least the term the heading/citation pair implies) "
        "from the real NY lettered-paragraph body "
        "'(a) Reverse mortgage loan. A reverse mortgage loan as defined in section "
        "two hundred eighty of this article, ...' -- no registered rule recognizes "
        "a bare (letter) marker + Title-Case term + single-period-no-idiom entry "
        "boundary today."
    )
    definition = by_term["Reverse mortgage loan"]
    assert definition.definition_text.strip().startswith(
        "A reverse mortgage loan as defined in\nsection two hundred eighty of this article,"
    ) or definition.definition_text.strip().startswith(
        "A reverse mortgage loan as defined in section two hundred eighty of this article,"
    ), f"got {definition.definition_text!r}"
