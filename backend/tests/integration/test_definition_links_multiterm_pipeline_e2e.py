"""RED live-path integration test for sprint 2026-08-04-defs-us-multiterm,
gate U1's "every term in a multi-term clause resolves INDIVIDUALLY"
requirement, proven at the ASSERTION level (not merely the Definition-row
level, which `test_multiterm_f5_shared_clause.py::
test_mt_nested_multi_term_clause_resolves_all_three_terms` already covers
for this same real row).

Drives the REAL production entry points (`ingest_us_statute_rows` ->
`run_definition_linking`) against a REAL vendored row plus one synthetic
"using" article (needed to exercise term-USE linking at all -- the real
row alone has no downstream mention to link to), then re-reads the
persisted `Assertion` rows, matching this sprint's "named wiring test !=
a live-path test" repo lesson.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "multiterm_f5_rows.json"
)


def _row(act_id: str) -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}[act_id]


def test_mt_nested_shared_clause_terms_each_link_to_a_later_use_individually(
    db_session, matter_with_users
):
    """U1's "every term in a multi-term clause resolves individually"
    requirement, proven at the assertion level: a SECOND real article in
    the same document that uses "ownership" and "person" in ordinary prose
    must each get its OWN USES_DEFINITION assertion once the terms are
    captured -- proving the existing, unmodified `matcher.
    link_articles_to_definitions` (which already iterates
    `definition.terms` one at a time, matcher.py:132-134) is sufficient
    plumbing for per-term resolution as soon as extraction supplies all N
    terms; no matcher change is implied by this gate."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    definitions_row = _row("STATE_MT_T16_C11_P4_S16-11-402")
    using_row = {
        "act_id": "STATE_MT_TEST_USING_ARTICLE",
        "text": (
            "A change in ownership of a licensee requires the new person to "
            "re-apply within 30 days."
        ),
        "section_title": "16-11-403 Post-transfer requirements",
        "section_number": "16-11-403",
        "chapter": "11",
    }

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Montana Code -- Statutes (multiterm sprint fixture)",
        rows=[definitions_row, using_row],
        jurisdiction="US-MT",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses = [a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"]
    matched_terms = {a["proposition"] for a in uses}
    assert any("ownership" in p for p in matched_terms) and any(
        "person" in p for p in matched_terms
    ), (
        f"expected individual USES_DEFINITION assertions for both 'ownership' "
        f"and 'person' against the second article; got {uses!r}"
    )
