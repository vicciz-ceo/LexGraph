"""RED live-path scope test for US family 2 (sprint 2026-08-04-defs-us-
preamble, gate U2), Mississippi -- the QA-flagged coverage gap (M-R16):
GA's scope test (`test_us_body_preamble_scope_red.py`) proved the
chapter-scope contract for ONE state's trigger phrasing ("As used in this
chapter..."); this file proves the SAME contract for MS's own, differently-
worded chapter-scoped convention ("For purposes of this chapter, unless
the context requires otherwise, the following terms shall have the
meanings ascribed herein:") -- a `BodyPreambleRule` that recognizes GA's
wording does not automatically recognize MS's, and scope stamping is a
per-phrasing dependency on core's C2 work (see below), not a per-state one.

Real base row: `STATE_MS_T45_C10_S34-1` (chapter `"10"`, 5 terms:
Conviction, Department, Offender, Registrable offense, Registrant) --
fetched live from the real `us_ms_statutes.parquet` snapshot (never
downloaded by this test) and vendored byte-for-byte, unmodified, into
`fixtures/us_statutes/ms_scope_preamble_rows.json`.

**Why this test does NOT use a second real corpus row as its negative
(out-of-chapter) case, unlike a naive read of the GA precedent might
suggest** (scout S4 finding, live-verified independently before writing
this test): `STATE_MS_T45_C10_S34-1`'s own body text is byte-identical
across at least 11 different real `chapter` values under MS Title 45
(`C1, C2, C3, C4, C5, C6, C7, C9, C10, C11, C33` all share this exact
`S34-1` body -- confirmed by re-fetching `us_ms_statutes.parquet` directly
in this worktree's venv and comparing `text` across all matching
`act_id`s, not merely taken on the scout's report). A real "different
MS chapter" row picked at random for this exact section number would
very likely be the SAME duplicated definitions text, not a distinct
statute that merely uses one of its terms -- so, mirroring the GA scope
test's own already-established, already-reviewed convention exactly (see
`test_us_body_preamble_scope_red.py`'s module docstring), this test uses
ONE real, vendored MS definitions row plus two SMALL, HAND-CONSTRUCTED
"using" rows (one same-chapter, one different-chapter). Neither
scaffolding row is vendored into `fixtures/us_statutes/` -- test
scaffolding, not corpus data, exactly as the GA precedent and this repo's
own established pattern (`test_us_profile_definitions_section_end_to_end
.py`'s `using_article`, `test_definition_links_pipeline_jurisdiction_
stamping.py`'s hand-written `wiki_text` bodies) already do.

**Named, non-hidden dependency, MS-specific** (do not assume GA's core
dependency automatically covers MS): even once `us_body_preamble.py`
supplies the derived heading and extracts MS's 5 real terms, this
definition can only be stamped `scope="chapter"` if `USProfile.
determine_scope` (core-owned, seam spec Seam 1/C2) recognizes the ENGLISH
phrase "For purposes of this chapter, unless the context requires
otherwise" (or a bounded prefix of it) as a chapter-scope trigger --
independently re-confirmed live in this worktree (`pipeline.py:62-68`,
`_CHAPTER_SCOPE_TRIGGERS` is 5 Hebrew phrases only, zero English triggers
exist in the shipped code today). Core's contract commits to "the
mechanism + one proven English example per granularity" -- if that one
proven example is GA's "As used in this chapter" wording and core's
trigger match is a literal/narrow one, MS's differently-worded trigger
may need its own recognition even after GA's own scope test goes green.
This test's own failure mode (once the rule and gate/registry pieces
exist but before core widens `_determine_scope` for MS's phrasing) would
show the definition captured at `scope="law-wide"` instead of
`scope="chapter"`, which is a DIFFERENT, sharper signal than "definition
not captured at all" -- flagged here so a future reader is not surprised
by a partial-progress failure shape.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"

_DEFINITIONS_ACT_ID = "STATE_MS_T45_C10_S34-1"

# Hand-constructed scaffolding (not vendored corpus rows -- see module
# docstring: a real "different MS chapter" row for this section number is
# very likely a byte-identical duplicate of the definitions row itself,
# not a distinct statute, so real corpus data cannot safely serve as the
# negative case here). Chapter "10" matches the real definitions row's own
# chapter; chapter "99" is deliberately a chapter MS's real Title 45 does
# not use for this convention.
_IN_CHAPTER_USING_ROW = {
    "act_id": "TESTONLY_MS_T45_C10_S45-34-99",
    "section_number": "45-34-99",
    "section_title": "Miss. Code Ann. § 45-34-99",
    "chapter": "10",
    "text": "A Registrant who fails to update an address within the time required by this chapter is subject to the penalties in Section 45-34-11.",
}
_OUT_OF_CHAPTER_USING_ROW = {
    "act_id": "TESTONLY_MS_T45_C99_S45-99-1",
    "section_number": "45-99-1",
    "section_title": "Miss. Code Ann. § 45-99-1",
    "chapter": "99",
    "text": "A Registrant of an unrelated program under this separate chapter of Title 45 is governed by its own rules, not this chapter's.",
}


def _ms_rows(act_id: str) -> dict:
    data = json.loads((FIXTURES / "ms_scope_preamble_rows.json").read_text(encoding="utf-8"))
    return next(r for r in data if r["act_id"] == act_id)


def test_chapter_scoped_ms_definition_links_a_same_chapter_use_but_not_a_different_chapter_use(
    db_session, matter_with_users
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion

    m = matter_with_users
    definitions_row = _ms_rows(_DEFINITIONS_ACT_ID)

    ingest_result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="MS T45 C10 scope test",
        rows=[definitions_row, _IN_CHAPTER_USING_ROW, _OUT_OF_CHAPTER_USING_ROW],
        jurisdiction="US-MS",
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
    # empty -- see this sprint's capture tests -- so this whole test is RED
    # for the same underlying reason before it can even reach its
    # scope-specific assertions).
    #
    # `.strip()` here is a TEST-SIDE WORKAROUND for a routed production
    # defect, not a resolution of it (manager ruling M-R32, `-log.md`):
    # `STATE_MS_T45_C10_S34-1`'s real body uses curly quotes with literal
    # internal padding ("“ Registrant ”"), and `us_profile._leading_quote_
    # candidate` (the primary extractor MS's numbered blocks route
    # through) does `term = term_match.group(1)` with NO `.strip()`, so
    # `d["terms"]` arrives as `[' Conviction ', ' Registrant ', ...]`, not
    # `'Registrant'`. `us_profile.py` is frozen for this sprint's panel --
    # the missing `.strip()` is on the program's core-follow-on-2 list.
    # Matching the convention `test_us_body_preamble_capture_red.py`'s
    # sibling MS test already uses.
    registrant_defs = [
        d for d in link_result["created_definitions"] if "Registrant" in {t.strip() for t in d["terms"]}
    ]
    assert len(registrant_defs) == 1
    assert registrant_defs[0]["scope"] == "chapter"

    uses_edges = [
        a for a in link_result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    subject_article_ids = set()
    for edge in uses_edges:
        row = db_session.get(Assertion, edge["id"])
        if "Registrant" in edge["proposition"]:
            subject_article_ids.add(row.subject_entity_id)

    assert in_chapter_article_id in subject_article_ids
    assert out_of_chapter_article_id not in subject_article_ids
