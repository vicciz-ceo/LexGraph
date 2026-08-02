"""QA bounce evidence — sprint 2026-08-02-us-state-law, QA cycle 1.

These tests are INTENTIONALLY RED. Each proves a real defect that bounces
its item back to `## Next Steps` in the sprint contract. Do not "fix" them
by loosening the assertion -- fix the implementation, then this file goes
green on its own.

[QA-FAIL] Item 3 -- US jurisdiction profile [G2, G3, G4]:

  1. `test_us_profile_is_definitions_heading_false_positives_on_non_definitions_headings`
     (probe P3): `us_profile.is_definitions_heading` is an unanchored
     `\\bDefinitions?\\b` SUBSTRING search. Real statute headings like
     "Application of Definitions to Prior Acts" or "Repeal of Definitions"
     contain the word "Definitions" without BEING a definitions section --
     both false-positive today.

  2. `test_real_pipeline_never_recognizes_a_real_us_definitions_section_for_a_us_document`
     (mandatory live-path trace): `app.definition_links.pipeline
     .run_definition_linking` -- the ONLY function that actually creates
     persisted `Definition`/`Assertion` rows in this product -- NEVER calls
     `app.definition_links.profiles.get_profile` anywhere. Grep-verified:
     `get_profile`/`USProfile` are referenced ONLY inside
     `profiles.py`/`us_profile.py` themselves and test files -- zero
     production call sites. `pipeline.py` Stage 2's heading check is the
     bare, Hebrew-only `sections.is_definitions_heading` (`_DEFINITIONS_
     HEADING_RE` matches `הגדרות`-family words only), unconditionally, for
     EVERY document regardless of its `jurisdiction` column. So for a real
     US-DE row ingested via the real `ingest_us_statute_rows` (item 5) and
     run through the real `run_definition_linking` (item 4), the pipeline
     recognizes ZERO Definitions sections and creates ZERO assertions --
     `USProfile` is unreachable dead code from every real product entry
     point. G2 ("the pipeline finds an English 'Definitions' section"),
     G3 ("a term ... produces a link"), and G4 ("US citations are
     recognised") are consequently NOT met at the product-observable level
     the sprint contract's gates require -- only in isolated unit tests
     and `test_us_profile_definitions_section_end_to_end.py`, which calls
     `get_profile(...)`'s methods directly, bypassing `pipeline.py`
     entirely (its own docstring says so explicitly).

     Root cause note for the next Developer: nothing in item 2's or item
     4's delivered diff adds a `get_profile(document.jurisdiction)` call
     anywhere in `pipeline.py`. `test_definition_links_pipeline_profile_
     dispatch.py`'s own docstring PINS this as a design requirement
     ("pipeline.py Stage 2 ... resolves get_profile(...) PER DOCUMENT")
     but its test bodies only assert Hebrew-output-unchanged, which
     passes trivially without any dispatch code (the bare Hebrew
     functions were never touched) -- so the RED test never actually
     caught the missing wiring. Item 4's own
     `test_assertions_from_a_us_document_are_stamped_with_its_us_
     jurisdiction` reinforces the same blind spot: its "US document"
     fixture body is Hebrew text with a Hebrew "הגדרות" heading merely
     LABELED jurisdiction="US-DE" -- it passes through the unchanged
     Hebrew-only pipeline by coincidence, never exercising real English
     parsing at all.

[QA-FAIL] Item 5 -- US dataset ingester [G6 -- code only]:

  3. `test_ingest_us_statute_rows_drops_a_row_when_its_section_number_collides_with_another_rows_across_titles`
     (probe P4): `ingest_us_statute_rows`'s "existing article" idempotency
     lookup is keyed by `(document.id, section_number)` ONLY -- it never
     considers `title_number`/`chapter`. Real statute files legitimately
     repeat a bare section number across different titles/chapters within
     ONE file (the ingester's own module docstring even names this exact
     risk in its "Idempotency" section, but the implementation doesn't
     guard it). A second, genuinely DIFFERENT row that happens to share an
     already-seen `section_number` is silently treated as "already
     ingested" and DROPPED -- its real text is never persisted, and it
     does not appear in `skipped_rows` either (so a G6 bulk-run report
     would show a plausible-looking row/skip count while silently having
     lost real sections).
"""

from __future__ import annotations

import json
import pathlib

FIXTURE_JSON = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "de_sample_rows.json"
)


def _load_rows() -> list[dict]:
    return json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))


# --- Item 3, probe P3: substring heading match false-positives -------------


def test_us_profile_is_definitions_heading_false_positives_on_non_definitions_headings():
    from app.definition_links.us_profile import is_definitions_heading

    # Real statute headings that CONTAIN the word "Definitions" without
    # being a definitions section themselves.
    non_definitions_headings = [
        "Application of Definitions to Prior Acts",
        "Repeal of Definitions",
    ]
    for heading in non_definitions_headings:
        assert is_definitions_heading(heading) is False, (
            f"{heading!r} was mis-classified as a Definitions-section heading; "
            "the unanchored \\bDefinitions?\\b substring check over-matches"
        )

    # Sanity: genuine definitions headings must still match (the fix must
    # not regress the real DE fixture's scrape-noise-prefixed heading).
    assert is_definitions_heading("§ Â\r\n        796. Definitions.") is True
    assert is_definitions_heading("§ Â\r\n        5227. Definition.") is True


# --- Item 3/4, mandatory live-path trace: US profile unreachable in prod ---


def test_real_pipeline_never_recognizes_a_real_us_definitions_section_for_a_us_document(
    db_session, matter_with_users
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    rows = _load_rows()  # real Delaware rows; row 0 is a genuine Definitions section

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (QA live-path trace)",
        rows=rows,
        jurisdiction="US-DE",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "Affiliate" in all_terms, (
        "the real production pipeline (run_definition_linking) never recognized "
        "the real US-DE 'Definitions' section at all -- it created "
        f"{result['created_definitions']!r} definitions and "
        f"{result['created_assertions']!r} assertions from a real US Definitions "
        "row with 3 real defined terms. app.definition_links.profiles.get_profile "
        "is never called from pipeline.py, so USProfile is unreachable from any "
        "real product entry point; G2/G3/G4 are unmet at the product level"
    )


# --- Item 5, probe P4: cross-title section_number collision drops a row ---


def test_ingest_us_statute_rows_drops_a_row_when_its_section_number_collides_with_another_rows_across_titles(
    db_session, matter_with_users
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.models.source_span import SourceSpan

    m = matter_with_users
    rows = _load_rows()
    row_a = dict(rows[0])  # act_id STATE_DE_T5_C7_SVIII_S796, section_number "796"
    row_b = dict(rows[1])  # act_id STATE_DE_T29_C60A_S6060, real DIFFERENT text

    # Simulate a real cross-title collision: a different title/chapter's
    # section happens to share Title 5 Section 796's bare section number.
    row_b["section_number"] = row_a["section_number"]
    row_b["act_id"] = "STATE_DE_T29_DIFFERENT_SECTION_SHARING_796"
    assert row_a["text"] != row_b["text"]  # genuinely different real content

    result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (QA collision probe)",
        rows=[row_a, row_b],
        jurisdiction="US-DE",
    )

    assert len(result["skipped_rows"]) == 0, (
        "row_b was not reported as skipped either -- it silently vanished, "
        "which is worse than an explicit skip: a bulk-run report would show "
        "a plausible row count while quietly losing a real section"
    )
    assert len(set(result["article_ids"])) == 2, (
        "row_b (a genuinely different section) was silently merged into "
        "row_a's Article because ingest_us_statute_rows keys idempotency by "
        "(document_id, section_number) only, ignoring title/chapter -- real "
        "statute files repeat bare section numbers across titles/chapters"
    )
    span_b = db_session.get(SourceSpan, result["source_span_ids"][1])
    assert row_b["text"] in span_b.quote_text, "row_b's real text was never persisted at all"
