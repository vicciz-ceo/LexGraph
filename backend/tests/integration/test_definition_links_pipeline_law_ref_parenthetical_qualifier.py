"""Sprint 2026-07-29-definition-links, cycle 2, item DL13 (G7, POC finding 3,
ruling M9(c)).

Integration-level companion to the DL13 unit tests in
`tests/unit/test_definition_links_derivation.py`: a cross-law derivation
whose target law's real title carries a parenthetical qualifier must
resolve through the REAL `run_definition_linking` pipeline when that
target law is ALSO ingested into the same matter -- not merely at the
`derivation` unit level.

Uses the already-vendored fixture `wiki_laws/חוק הבנקאות (שירות
ללקוח)_excerpt.wiki` (ruling M3, verbatim excerpt of the real corpus law),
whose §1 line 8 is:

    :- "בנק" - כמשמעותו [[בחוק הבנקאות (רישוי)]];

-- a real cross-law reference to "חוק הבנקאות (רישוי)" (Banking [Licensing]
Law), whose own real, ingested title genuinely carries the `(רישוי)`
qualifier (confirmed directly against
`/Users/nerya/AI for others/israeli-laws-wiki/data/laws/חוק הבנקאות
(רישוי).wiki`'s `<שם>` header). Before the fix, `_LAW_REF_RE` stops at the
first `(` and produces the short name `"חוק הבנקאות"`, which never
exact-matches `known_law_titles`'s `"חוק הבנקאות (רישוי)"` key even though
the second law is genuinely ingested into this same matter.

`wiki_laws/חוק הבנקאות (רישוי)_stub.wiki` is a NEW, minimal stub fixture
(ruling M3) excerpting only the real `<שם>` header and the opening of §1
from the real corpus file, mirroring the existing `חוק המחשבים_stub.wiki`
pattern.
"""

from __future__ import annotations

import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_run_definition_linking_resolves_a_derivation_to_a_law_with_a_parenthetical_qualifier(
    db_session, matter_with_users
):
    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion

    m = matter_with_users
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק הבנקאות (שירות ללקוח), התשמ"א-1981',
        wiki_text=_read("חוק הבנקאות (שירות ללקוח)_excerpt.wiki"),
    )
    licensing_law = ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק הבנקאות (רישוי), התשמ"א-1981',
        wiki_text=_read("חוק הבנקאות (רישוי)_stub.wiki"),
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    derives_edges = [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "DERIVES_FROM_LAW" and '"בנק"' in a["proposition"]
    ]
    assert len(derives_edges) >= 1

    resolved = [
        e
        for e in derives_edges
        if db_session.get(Assertion, e["id"]).object_entity_id == licensing_law["document_id"]
    ]
    assert resolved, (
        "expected the \"בנק\" derivation to resolve to the ingested "
        f'"חוק הבנקאות (רישוי)" document, got: {derives_edges}'
    )
    resolved_row = db_session.get(Assertion, resolved[0]["id"])
    assert resolved_row.object_entity_type == "Document"
