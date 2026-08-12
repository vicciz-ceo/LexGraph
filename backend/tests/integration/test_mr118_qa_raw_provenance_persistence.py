"""Independent M-R118 QA regressions through ingest and Definition persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition


CASES = (
    {
        "name": "paired_curly_quote_pseudo_entry_is_filterable",
        "jurisdiction": "US-WA",
        "text": 'In this section: (1) “copper flare”; (2) "signal vault" means a sealed emergency container.',
        "absent": ("copper flare",),
        "expected": {"signal vault": "a sealed emergency container."},
    },
    {
        "name": "curly_open_straight_close_fails_open",
        "jurisdiction": "US-UT",
        "text": 'In this statute:\n(1) “moonlit affidavit"\nAuthorized signature: ________________________________',
        "absent": (),
        "expected": {"moonlit affidavit": "Authorized signature: ________________________________"},
    },
    {
        "name": "repeated_term_with_a_substantive_occurrence_is_preserved",
        "jurisdiction": "US-NV",
        "text": 'In this section: (1) "ember beacon"; (2) "ember beacon" means an approved evacuation marker.',
        "absent": (),
        "expected": {"ember beacon": "an approved evacuation marker."},
    },
    {
        "name": "earlier_b2_winner_is_untouched_despite_b1_overlap",
        "jurisdiction": "US-MD",
        "text": 'In this section, the following words have the meanings indicated: (1) "quartz notice" means an official signal.',
        "absent": (),
        "expected": {"quartz notice": "an official signal."},
    },
    {
        "name": "plural_anaphora_adds_only_missing_term_without_replacing_existing",
        "jurisdiction": "US-OR",
        "text": 'In this section: (1) "aether relay" means a dedicated alert device; (2) "aether relay"; (3) "boreal signal"; have the meaning set forth for those terms in Section 8.444.',
        "absent": (),
        "expected": {
            "boreal signal": "have the meaning set forth for those terms in Section 8.444.",
        },
        "expected_prefix": {"aether relay": "a dedicated alert device;"},
        "unique_terms": ("aether relay", "boreal signal"),
    },
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_mr118_raw_provenance_controls_through_definition_persistence(
    case, db_session, matter_with_users
):
    """The SourceSpan raw text must survive normalization and real persistence."""
    matter = matter_with_users
    act_id = f"MR118_QA_{case['name'].upper()}"
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=f"M-R118 QA {case['name']}",
        rows=[
            {
                "act_id": act_id,
                "section_number": "118.901",
                "chapter": "qa-future",
                "section_title": "118.901 M-R118 QA novel section.",
                "text": case["text"],
            }
        ],
        jurisdiction=case["jurisdiction"],
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    definitions = [db_session.get(Definition, item["id"]) for item in result["created_definitions"]]
    by_term = {term: definition for definition in definitions for term in definition.terms}
    for term in case["absent"]:
        assert term not in by_term
    for term, definition_text in case["expected"].items():
        assert by_term[term].definition_text == definition_text
        assert by_term[term].scope == "law-wide"
    for term, definition_prefix in case.get("expected_prefix", {}).items():
        assert by_term[term].definition_text.startswith(definition_prefix)
        assert by_term[term].scope == "law-wide"
    for term in case.get("unique_terms", ()):
        assert sum(term in definition.terms for definition in definitions) == 1


def test_mr118_b1_metadata_does_not_break_the_live_hebrew_profile(
    db_session, matter_with_users
):
    """Non-B1 profiles must not receive B1-only extraction keyword arguments."""
    from app.definition_links.ingest import ingest_wiki_law

    fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures/wiki_laws/חוק להגנת רכוש מופקד.wiki"
    )
    matter = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title="M-R118 QA Hebrew compatibility",
        wiki_text=fixture.read_text(encoding="utf-8"),
    )

    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    assert any("נכס" in definition["terms"] for definition in result["created_definitions"])
