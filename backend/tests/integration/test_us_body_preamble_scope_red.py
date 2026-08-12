"""RED live-path scope tests for US family 2 (sprint
2026-08-04-defs-us-preamble, gate U2): a body-preamble definition scoped by
its own trigger phrase ("As used in this CHAPTER...") must create
USES_DEFINITION assertions ONLY for mentions within that chapter -- proven
in BOTH directions, per the program's standing scope requirement.

Uses GA's real chapter-scoped fixture (`STATE_GA_T7_C8_S7-8-1`, chapter
"8", 'As used in this chapter, the term: (1) "Access area" means...') plus
two SMALL, HAND-CONSTRUCTED "using" rows (one same-chapter, one
different-chapter) -- these two rows are deliberately NOT vendored into
`fixtures/us_statutes/` because they are test scaffolding, not corpus
data (mirrors the repo's own existing pattern in
`test_us_profile_definitions_section_end_to_end.py`'s hand-written
`using_article` and `test_definition_links_pipeline_jurisdiction_stamping
.py`'s hand-written `wiki_text` bodies -- neither vendors its scaffolding
text as a fixture file either). No fabricated CORPUS row is introduced;
only the real GA definitions row is real/vendored, exactly as the sprint
contract requires.

**Named, non-hidden dependency** (see this sprint's D0/D3 notes): even
once `us_body_preamble.py` supplies the derived heading, GA's definitions
row can only be stamped `scope="chapter"` if `USProfile.determine_scope`
(core-owned, seam spec Seam 1/C2) recognizes the ENGLISH phrase "As used
in this chapter" as a chapter-scope trigger. Core's contract commits to
"the mechanism + one proven English example per granularity", not
necessarily this exact phrase -- if core's registered trigger differs,
these two tests may still assert the correct end state but flip from
"blocked on our rule" to "blocked on core's specific trigger phrase set",
which is exactly the kind of dependency this sprint's report names
explicitly rather than assuming away.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"

_DEFINITIONS_ACT_ID = "STATE_GA_T7_C8_S7-8-1"

# Hand-constructed scaffolding (not vendored corpus rows -- see module
# docstring). Chapter "8" matches the real definitions row's own chapter;
# chapter "99" is deliberately a different chapter of the same title.
_IN_CHAPTER_USING_ROW = {
    "act_id": "TESTONLY_GA_T7_C8_S7-8-99",
    "section_number": "7-8-99",
    "section_title": "Georgia Code Title 7. Banking and Finance § 7-8-99",
    "chapter": "8",
    "text": "Each Access area shall be maintained free of obstruction by the financial institution operating it.",
}
_OUT_OF_CHAPTER_USING_ROW = {
    "act_id": "TESTONLY_GA_T7_C99_S7-99-1",
    "section_number": "7-99-1",
    "section_title": "Georgia Code Title 7. Banking and Finance § 7-99-1",
    "chapter": "99",
    "text": "An Access area located outside a chartered institution is governed by an unrelated chapter of this title.",
}


def _ga_rows(act_id: str) -> dict:
    data = json.loads((FIXTURES / "ga_preamble_rows.json").read_text(encoding="utf-8"))
    return next(r for r in data if r["act_id"] == act_id)


def test_chapter_scoped_ga_definition_links_a_same_chapter_use_but_not_a_different_chapter_use(
    db_session, matter_with_users
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion

    m = matter_with_users
    definitions_row = _ga_rows(_DEFINITIONS_ACT_ID)

    ingest_result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="GA T7 C8 scope test",
        rows=[definitions_row, _IN_CHAPTER_USING_ROW, _OUT_OF_CHAPTER_USING_ROW],
        jurisdiction="US-GA",
    )
    article_id_by_act_id = dict(
        zip(
            [definitions_row["act_id"], _IN_CHAPTER_USING_ROW["act_id"], _OUT_OF_CHAPTER_USING_ROW["act_id"]],
            ingest_result["article_ids"],
        )
    )
    in_chapter_article_id = article_id_by_act_id[_IN_CHAPTER_USING_ROW["act_id"]]
    out_of_chapter_article_id = article_id_by_act_id[_OUT_OF_CHAPTER_USING_ROW["act_id"]]

    link_result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    # Sanity: the definition itself must exist first (today this list is
    # empty -- see test_us_body_preamble_capture_red.py -- so this whole
    # test is RED for the same underlying reason before it can even reach
    # its scope-specific assertions).
    access_area_defs = [d for d in link_result["created_definitions"] if "Access area" in d["terms"]]
    assert len(access_area_defs) == 1
    assert access_area_defs[0]["scope"] == "chapter"

    uses_edges = [
        a for a in link_result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    subject_article_ids = set()
    for edge in uses_edges:
        row = db_session.get(Assertion, edge["id"])
        if "Access area" in edge["proposition"]:
            subject_article_ids.add(row.subject_entity_id)

    assert in_chapter_article_id in subject_article_ids
    assert out_of_chapter_article_id not in subject_article_ids
