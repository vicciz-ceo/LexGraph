"""Sprint 2026-07-29-definition-links, cycle 2, item DL12 (G6, POC finding 2,
ruling M9(b)).

Integration-level companion to
`tests/unit/test_definition_links_extract_repeal_guard.py`: a definitions
entry whose entire body is a repeal marker must produce NO persisted
Definition row and NO USES_DEFINITION edges through the REAL
`run_definition_linking` pipeline, not merely at the `extract` unit level.

Uses the already-vendored fixture `wiki_laws/חוק הבנקאות (שירות
ללקוח)_excerpt.wiki` (ruling M3), whose §1 line 29 is a verbatim excerpt of
the real corpus law:

    :- "חוק כרטיסי חיוב" - (((נמחקה);))

Before the fix, this persists as an ordinary live Definition row -- exactly
the mechanism poc-run.md §8 Issue 2 confirmed concretely against חוק
החברות's "בית המשפט" (98 USES_DEFINITION edges attached to a formally
repealed definition; 2,981 corpus-wide per the manager addendum, §12).
"""

from __future__ import annotations

import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_run_definition_linking_creates_no_definition_for_a_pure_repeal_marker_entry(
    db_session, matter_with_users
):
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק הבנקאות (שירות ללקוח), התשמ"א-1981',
        wiki_text=_read("חוק הבנקאות (שירות ללקוח)_excerpt.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    repeal_definitions = [
        d for d in result["created_definitions"] if "חוק כרטיסי חיוב" in d["terms"]
    ]
    assert repeal_definitions == [], (
        "a definitions entry whose entire body is a repeal marker must not "
        f"persist as a live Definition row, got: {repeal_definitions}"
    )

    repeal_edges = [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION" and "חוק כרטיסי חיוב" in a["proposition"]
    ]
    assert repeal_edges == []

    # Sibling live definitions in the SAME הגדרות section must still be
    # extracted -- the guard drops only the offending candidate.
    live_definitions = [d for d in result["created_definitions"] if "תאגיד בנקאי" in d["terms"]]
    assert len(live_definitions) == 1


def test_run_definition_linking_is_idempotent_after_the_repeal_guard(db_session, matter_with_users):
    """A second pipeline run over the same, unchanged matter creates
    nothing new -- the guard must not introduce a non-deterministic
    re-evaluation path."""
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק הבנקאות (שירות ללקוח), התשמ"א-1981',
        wiki_text=_read("חוק הבנקאות (שירות ללקוח)_excerpt.wiki"),
    )

    first = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert len(first["created_definitions"]) > 0

    second = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert second["created_assertions"] == []
    assert second["created_definitions"] == []
