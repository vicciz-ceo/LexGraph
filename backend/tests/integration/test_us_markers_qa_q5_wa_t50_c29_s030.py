"""QA1 (phase-2 QA cycle 1) -- Q5: `STATE_WA_T50_C29_S030` (headings panel
H-R1, ruling Q-C) (sprint 2026-08-04-defs-us-markers, gate U1).

**Binding design constraint from the manager**: this row is a
RECOGNITION-side miss arriving as an extraction request -- it is NOT
heading-recognized (confirmed below: `is_definitions_heading` is False,
`derive_heading_from_body` returns `None`). This test drives
`extract_definitions_from_section` DIRECTLY on the row body (the same
layer-agnostic pattern as core's
`test_ingest_us_statutes_ny_newline_defect.py::test_real_ny_row_with_
literal_backslash_n_yields_its_definitions_via_the_live_pipeline` -- chains
`ingest_us_statute_rows` -> `profile.normalize_for_parsing` (the exact
`pipeline.py`:188 call) -> `get_profile("US-WA").extract_definitions_
from_section` (the exact `pipeline.py` Stage-2 call once heading dispatch
succeeds), never `profile.is_definitions_heading` or
`run_definition_linking`'s own dispatch gate. This deliberately does NOT
touch heading recognition, which is headings-panel territory
(ruling H-R1/Q-C), not this sprint's.

**Implied term, derived from the real row (not guessed):**
`section_title` = `'RCW 50.29.030: "Wages" defined for purpose of
prorating benefit charges.'` -- the verb-form `"X" defined` heading names
its term unambiguously via the quoted span immediately before "defined":
**"Wages"**. The real body is `'For the purpose of prorating benefit
charges "wages" shall mean "wages" as defined for purpose of payment of
benefits in RCW 50.04.320 .'` -- a genuine (if pointer-style) definition:
"wages", for the purpose of this section, means "wages" as already defined
in RCW 50.04.320. No ambiguity here -- unlike some verb-form headings, the
body's own first quoted+idiom-following term matches the heading's implied
term exactly (case-folded: heading "Wages", body "wages").

**Finding: this ALREADY PASSES on this build, un-fixed** -- a genuinely
positive result, reported honestly rather than forced into a RED shape.
`US-WA` is one of `us_markers_inline_quote.py`'s 7 registered
jurisdictions (`_JURISDICTIONS = ("US-VA", "US-WA", "US-FED", "US-UT",
"US-TX", "US-SC", "US-AZ")`), and its shared `us_markers_boundary` engine
recognizes `"wages" shall mean` ("shall mean" is one of `_TIGHT_IDIOM_RE`'s
three idiom alternatives) as a valid entry start with no `(N)` marker
needed at all -- exactly the shape this sprint's family-3 rule exists to
rescue. **This is a genuine, if narrow, positive control**: the extraction
LAYER already satisfies the manager's acceptance condition ("extraction
must yield at least the term the heading/citation pair implies") for this
specific row, entirely independent of the still-unresolved RECOGNITION-side
gap (confirmed separately below: the real production pipeline still
creates ZERO definitions end-to-end for this row today, because
`pipeline.py`'s heading-dispatch gate never reaches `extract_definitions_
from_section` for it at all -- it falls through to the ordinary-article
`extract_local_scope_definitions` path instead, which also yields zero).
So the headings panel's pointer-row edge CAN attach once recognition
closes this gap -- reported to the manager to relay to the headings
panel's manager, per this pass's brief.

Row vendored verbatim, byte-verified against `us_wa_statutes.parquet` this
pass.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.profiles import get_profile
from app.definition_links.us_profile import USProfile, is_definitions_heading
from app.models.article import Article
from app.models.definition import Definition
from app.models.source_span import SourceSpan

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_qa_q5_wa_t50_c29_s030_row.json"
)

ACT_ID = "STATE_WA_T50_C29_S030"
IMPLIED_TERM = "wages"


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["act_id"] == ACT_ID
    return rows[0]


def test_row_is_confirmed_recognition_side_miss_not_heading_recognized():
    """Sanity, matching the manager's binding design constraint: this row
    is NOT heading-recognized by either path -- proves this test's own
    "must not assume the heading path" instruction is necessary, not
    decorative."""
    row = _load_row()
    profile = USProfile(code="US-WA")
    assert is_definitions_heading(row["section_title"]) is False, (
        "if this ever becomes True, the row is no longer a recognition-side "
        "miss and this test's whole premise (and the headings-panel routing) "
        "needs re-deriving"
    )
    assert profile.derive_heading_from_body(row["section_title"], row["text"]) is None


def test_extraction_layer_directly_yields_the_heading_implied_term(db_session, matter_with_users):
    """The load-bearing check, driven the SAME way core's NY newline test
    drives NY: chain the real `ingest_us_statute_rows` -> real
    `profile.normalize_for_parsing` (pipeline.py:188's exact call) -> real
    `get_profile("US-WA").extract_definitions_from_section` (pipeline.py's
    exact Stage-2 call), never touching heading dispatch. Acceptance
    condition (manager, verbatim): extraction must yield at least the term
    the heading/citation pair implies -- "wages"."""
    row = _load_row()
    result = ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="WA T50 C29 S030 (QA1 Q5)",
        rows=[row],
        jurisdiction="US-WA",
    )
    assert result["skipped_rows"] == []
    assert len(result["article_ids"]) == 1

    article = db_session.get(Article, result["article_ids"][0])
    span = db_session.get(SourceSpan, article.source_span_id)

    profile = get_profile("US-WA")
    normalized_body = profile.normalize_for_parsing(span.quote_text)

    candidates = profile.extract_definitions_from_section(
        normalized_body, scope="law-wide", heading_was_derived=False
    )
    found_terms = {term for c in candidates for term in c.terms}
    assert IMPLIED_TERM in found_terms, (
        f"extraction did not yield the heading-implied term {IMPLIED_TERM!r} -- got "
        f"{sorted(found_terms)!r}. If this fails, the manager's acceptance condition "
        "for Q-C is genuinely unmet at the extraction layer (not merely blocked on "
        "recognition) and the headings panel needs to know before relying on this edge."
    )


def test_real_full_pipeline_still_creates_zero_definitions_today_recognition_gap_confirmed(
    db_session, matter_with_users
):
    """NOT a RED on the extraction layer (see the previous test) -- proves
    the OTHER half of this row's story: through the REAL, UNMODIFIED
    end-to-end pipeline (`run_definition_linking`, which gates on
    `is_definitions_heading`/`derive_heading_from_body` before ever calling
    `extract_definitions_from_section`), this row creates ZERO Definition
    rows today. The gap is entirely on the RECOGNITION side (headings
    panel's H-R1/Q-C), not the extraction side (this sprint's) -- this test
    documents that boundary precisely so neither panel over- or
    under-claims ownership."""
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="WA T50 C29 S030 full-pipeline check (QA1 Q5)",
        rows=[row],
        jurisdiction="US-WA",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    assert definitions == [], (
        f"expected ZERO definitions from the real end-to-end pipeline today (recognition "
        f"gap unresolved) -- got {[(d.terms, d.definition_text) for d in definitions]!r}. "
        "If this now creates definitions, recognition has been fixed and this test (and "
        "the extraction-layer test above) together prove Q-C's acceptance condition is "
        "fully met end-to-end -- update this test's assertion and notify the manager."
    )
