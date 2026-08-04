"""RED test — sprint 2026-08-04-defs-core-scope, item M14 (ruling M14).

**The defect (verified against the real, live `us_ny_statutes.parquet`
snapshot, not assumed).** Every one of NY's 40,102 real rows stores its
`text` column's line breaks as the LITERAL two-character sequence
`\\n` (backslash + letter "n"), never a real newline byte (0x0A):

    NY rows: 40102
    rows containing a REAL newline byte: 0
    rows containing literal backslash-n: 40102

`us_profile.py`'s `_split_into_numbered_blocks` does `text.split("\\n")`
(a REAL newline) to find each `(a) "Term" means ...` entry's own line.
Since NY bodies contain zero real newlines, that call always returns the
ENTIRE body as one line, so `extract_definitions_from_section` can never
recognize an entry boundary inside NY text at all -- proven corpus-wide:
every one of NY's already-heading-recognized "Definitions" sections
(1,479/1,479) yields ZERO candidates from this extractor. This is the
single largest known contributor to the sprint's 34,017 zero-yield count,
and it is independent of any particular heading/convention family -- the
same `text.split("\\n")` call fails identically on ANY NY body that uses
the numbered/lettered-entry convention, whether or not its own
`section_title` happens to already read as "Definitions".

**Fixture provenance.** `backend/tests/fixtures/us_statutes/
ny_m14_newline_defect_row.json` vendors ONE real row,
`STATE_NY_ABNK_A15_T6_S6021` ("Preemptive rights", N.Y. Banking Law
§ 6021), copied byte-for-byte (literal backslash-n preserved exactly as
stored) from the real `us_ny_statutes.parquet` snapshot -- extracted by
this sprint's scout (`scout_S2_findings.md`), never downloaded or read by
this test (ruling R6). This row's `section_title` ("Preemptive rights")
is NOT itself heading-recognized as "Definitions" -- that is a SEPARATE,
already-known NY defect (heading detection is out of scope for M14; see
this contract's earlier items). This test deliberately does not depend on
`pipeline.py`'s `is_definitions_heading` dispatch gate at all -- it drives
`get_profile("US-NY").extract_definitions_from_section` directly, the
EXACT function `pipeline.py` calls once dispatch succeeds (`pipeline.py`
line ~418), so the assertion below is discriminated purely by the
literal-`\\n` defect, not confounded by the separate heading-gate issue.

**Layer-agnostic by design.** The real defined-term recognition test below
chains three REAL, unmodified production entry points in the exact order
`pipeline.py` uses them: `ingest_us_statute_rows` (populates
`SourceSpan.quote_text` from the raw row -- candidate fix layer #1) ->
`normalize_for_parsing` (Stage 0, called unconditionally for EVERY
article regardless of jurisdiction at `pipeline.py`:377 -- candidate fix
layer #2) -> `get_profile("US-NY").extract_definitions_from_section`
(Stage 2). Nothing here is reimplemented or mocked, and the test does not
assume WHICH of the two layers unescapes the literal `\\n` -- it only
pins the observable behavior: a real NY body with this shape must yield
its 6 real defined terms by the time it reaches Stage 2, however the fix
gets there.

RED signal (today): the pipeline call chain above yields ZERO candidates
for this real row (proven directly below and in
`ny_m14_newline_defect_row.json`'s companion verification) where the
fixed behavior requires 6 -- a `0 == 6`-shaped assertion failure, not an
import error (every function used here already exists and is unmodified).
"""

from __future__ import annotations

import json
import pathlib

FIXTURE_JSON = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "ny_m14_newline_defect_row.json"
)

# The row's own real, byte-accurate defined terms (verified directly
# against the vendored fixture text: 0 candidates from today's literal-`\n`
# body, 6 candidates once real newlines are substituted for the literal
# `\n` sequence -- see this file's module docstring).
_EXPECTED_TERMS = {
    "Unlimited dividend rights",
    "Equity shares",
    "Voting rights",
    "Voting shares",
    "Preemptive right",
    "New shares or securities",
}


def _load_row() -> dict:
    rows = json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def test_real_ny_row_with_literal_backslash_n_yields_its_definitions_via_the_live_pipeline(
    db_session, matter_with_users
):
    """Live path: real `ingest_us_statute_rows` -> real `SourceSpan.quote_text`
    -> real `normalize_for_parsing` (Stage 0, the exact call `pipeline.py`
    makes unconditionally for every article) -> real
    `get_profile("US-NY").extract_definitions_from_section` (Stage 2, the
    exact call `pipeline.py` makes once its heading-dispatch gate passes).

    Today this fails with `set() == {6 real terms}` -- the literal `\\n`
    two-character sequence is never unescaped anywhere in that chain, so
    `_split_into_numbered_blocks`'s `text.split("\\n")` sees the whole
    14-entry body as one unsplittable line and recognizes no entries at
    all. Fixing this (at ingest time, or in `normalize_for_parsing`, or
    both) must turn this set-equality green without this test itself
    changing -- that is the point of driving real entry points instead of
    a private helper.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.normalize import normalize_for_parsing
    from app.definition_links.profiles import get_profile
    from app.models.article import Article
    from app.models.source_span import SourceSpan

    m = matter_with_users
    row = _load_row()
    assert row["act_id"] == "STATE_NY_ABNK_A15_T6_S6021"

    result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="New York Consolidated Laws -- Statutes (M14 newline-defect fixture)",
        rows=[row],
        jurisdiction="US-NY",
    )
    assert result["skipped_rows"] == []
    assert len(result["article_ids"]) == 1

    article = db_session.get(Article, result["article_ids"][0])
    span = db_session.get(SourceSpan, article.source_span_id)

    # Stage 0 -- the SAME unconditional call `pipeline.py` makes for every
    # article (line ~377), regardless of jurisdiction.
    normalized_body = normalize_for_parsing(span.quote_text)

    # Stage 2 -- the SAME call `pipeline.py` makes once its heading-dispatch
    # gate routes an article to `profile.extract_definitions_from_section`
    # (line ~418). Called directly here (not via `run_definition_linking`)
    # so this assertion is discriminated purely by the literal-`\n` defect,
    # never by NY's separate, already-known heading-recognition gap.
    profile = get_profile("US-NY")
    candidates = profile.extract_definitions_from_section(normalized_body, scope="section")

    found_terms = {term for c in candidates for term in c.terms}
    assert found_terms == _EXPECTED_TERMS, (
        "extract_definitions_from_section yielded "
        f"{sorted(found_terms)!r} defined terms for a real NY row whose body "
        "genuinely defines 6 terms across 14 lettered/numbered entries -- the "
        "literal backslash-n two-character sequence (never a real newline byte "
        "in this row, confirmed corpus-wide: 40,102/40,102 real NY rows) makes "
        "_split_into_numbered_blocks's text.split('\\n') return the whole body "
        "as one unsplittable line, so no entry boundary is ever recognized."
    )
