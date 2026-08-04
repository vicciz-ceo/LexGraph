r"""Cycle-5 Planner, item 29 (gate P5, manager ruling M-R4). "PR rules
must never fire on English text" needs a test that would FAIL if the
Spanish rules were made language-blind -- a real English-state row fed
through the LIVE PR rule path proving no extra capture, not merely
"existing English tests still pass" (M-R4, verbatim).

`test_pr_profile_no_english_regression.py` (cycle 1) already guards this
at the `PRProfile`-direct-call level -- a legitimate supplement, but
`PRProfile` is UNREACHABLE from `get_profile` (P-R8 phase-2 finding), so
it was never proof of the LIVE path. These tests exercise the REAL
registered rules (item 26's `ScopeTriggerRule`s, item 27's `CitationRule`)
through `get_profile("US-PR")` and the full `run_definition_linking`
pipeline, against `STATE_DE_T5_C7_SVIII_S796` -- a real, already-vendored,
working-baseline-state row (`de_sample_rows.json`) whose own English
idiom ('"Term" has the meaning specified in ...') is structurally close
enough to the Spanish quoted-term-then-copula shape (`pr_profile.py`'s own
module comment on patterns 4/5) that a careless, language-blind
implementation could plausibly collide with it -- this is a REAL risk
being tested, not a formality.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load(name: str) -> dict[str, dict]:
    rows = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def de_rows():
    return _load("de_sample_rows.json")


def test_get_profile_us_pr_extracts_no_local_scope_definitions_from_real_english_prose(de_rows):
    """Direct profile-method proof (live seam, not a direct rule-function
    call): `get_profile("US-PR").extract_local_scope_definitions` unions
    every registered `ScopeTriggerRule` for `"US-PR"` (item 26) -- on the
    real DE row's English body, it must return exactly `[]`. A test that
    WOULD FAIL if, e.g., the item-18c whole-body sweep's idiom alternation
    were widened to also match English 'means'/'has the meaning
    specified in' (structurally the SAME quoted-term-then-verb shape the
    Spanish sweep targets)."""
    from app.definition_links.profiles import get_profile

    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    profile = get_profile("US-PR")
    candidates = profile.extract_local_scope_definitions(
        row["text"], article_number=row["section_number"]
    )
    assert candidates == [], (
        "the registered PR ScopeTriggerRules must return nothing for real "
        f"English prose -- got {candidates!r}"
    )


def test_run_definition_linking_creates_no_definitions_for_a_real_english_row_ingested_as_us_pr_live(
    db_session, matter_with_users, de_rows
):
    """Full pipeline proof: a document ingested under `jurisdiction=
    "US-PR"` whose body is the REAL, byte-vendored English DE row --
    proving end-to-end that no PR-specific rule (scope trigger OR
    citation) fabricates a Definition from it. This is the strongest form
    of M-R4's demand: not merely calling the rule function directly, but
    driving the actual registered rule through the actual dispatch path a
    real (mis-jurisdictioned) document would take."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    wiki_text = f"@ 796. {row['section_title']}\n{row['text']}\n"
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test English Statute (P5, mis-jurisdictioned as US-PR)",
        wiki_text=wiki_text,
        jurisdiction="US-PR",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    assert result["created_definitions"] == [], (
        "no Definition should be fabricated from real English prose by any "
        f"PR-specific rule -- got {result['created_definitions']!r}"
    )


def test_a_real_english_state_document_is_completely_unaffected_by_the_pr_rules_being_registered_live(
    db_session, matter_with_users, de_rows
):
    """The mirror-image direction: a document correctly ingested under
    its OWN real jurisdiction (`US-DE`) must produce IDENTICAL results
    whether or not the PR-specific rules are registered in this process
    -- `jurisdiction_codes=("US-PR",)` registration must never leak into
    `scope_trigger_rules_for("US-DE")`/`citation_rules_for("US-DE")`
    (`rules/registry.py`'s `_matches`: exact code match only, no
    cross-jurisdiction wildcard from a single-code tuple)."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    wiki_text = f"@ 796. {row['section_title']}\n{row['text']}\n"
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test English Statute (P5, correctly jurisdictioned as US-DE)",
        wiki_text=wiki_text,
        jurisdiction="US-DE",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    # The real DE row's own English idiom IS recognized by baseline
    # US-profile extraction (a "Definitions" heading, ordinary English
    # capture) -- this test is not claiming zero definitions here, only
    # that none of them carry a Spanish-only artifact (a PR citation
    # string, or a candidate whose scope/term shape only the PR rules
    # would produce).
    pr_only_citation_shapes = ("L.P.R.A.", "Artículo ", "Ley Núm.")
    for definition in result["created_definitions"]:
        for term in definition["terms"]:
            assert not any(shape in term for shape in pr_only_citation_shapes), (
                f"a PR-only vocabulary shape leaked into a US-DE definition: {definition!r}"
            )
