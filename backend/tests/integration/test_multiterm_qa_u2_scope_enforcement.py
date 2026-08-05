"""QA (sprint 2026-08-04-defs-us-multiterm) -- gate U2, "scope stamped/
enforced via the core seam, live-path BOTH directions". The sprint's own
manager brief flags this gate as having had "the least attention of any
gate this sprint" -- neither Planner nor Developer authored a live-path
test that a definition's scope actually RESTRICTS linking to an
out-of-scope article, only that in-scope linking works. This file closes
that gap independently, driving the real production entry points
(`ingest_us_statute_rows` -> `run_definition_linking`), never a unit-level
`_in_scope(...)` call, per this sprint's own "named wiring test != a
live-path test" repo lesson.

Real row: `STATE_NH_TXXXVII_C408-C_S14` (F6's `ScopeTriggerRule`,
`rules/us_inline_parenthetical.py::_extract_ordinary_body`) stamps
`scope="local"` with no explicit `source_article_number`, which
`USProfile.extract_local_scope_definitions` then defaults to the article's
OWN number (`us_profile.py:1425-1426`) -- i.e. this real definition is
supposed to be readable ONLY within its own article, section 14. The real
row's own body already re-mentions "the withdrawing state" several times
after its own defining sentence (subparagraphs (b)-(f)), which gives a
genuine in-article positive-direction proof for free; a second, synthetic
article in the SAME document (a different section number, ordinary prose,
no apposition of its own) is added to prove the negative direction, which
no real row in this sprint's own fixtures exercises.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "multiterm_f6_rows.json"
)


def _row(act_id: str) -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}[act_id]


def test_local_scope_definition_links_in_scope_and_excludes_out_of_scope_article(
    db_session, matter_with_users
):
    """Both directions, one document, one run:

    1. IN-SCOPE: the real NH row's OWN body re-mentions "the withdrawing
       state" (lowercase, no apposition) several times after its defining
       sentence -- these must each draw a `USES_DEFINITION` assertion whose
       proposition names Article 14 (the defining article itself).
    2. OUT-OF-SCOPE: a synthetic SECOND article in the SAME document, a
       different section number ("99"), whose body plainly mentions "the
       withdrawing state" in ordinary prose with no apposition of its own,
       must NOT draw any `USES_DEFINITION` assertion for that term --
       `scope="local"` must actually be ENFORCED (not merely stamped) by
       `matcher._in_scope`, live, through the real pipeline.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    defining_row = _row("STATE_NH_TXXXVII_C408-C_S14")
    out_of_scope_row = {
        "act_id": "STATE_NH_TEST_QA_U2_OUT_OF_SCOPE",
        "text": (
            "The withdrawing state must file its final report with the "
            "commission within 90 days of the effective date of withdrawal."
        ),
        "section_title": "408-C:99 Unrelated reporting requirement.",
        "section_number": "99",
        "chapter": "408-C",
    }

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="NH Code -- Statutes (QA U2 scope-enforcement fixture)",
        rows=[defining_row, out_of_scope_row],
        jurisdiction="US-NH",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "withdrawing state" in all_terms, (
        f"precondition failed -- the F6 apposition definition itself was not "
        f"captured, cannot test scope enforcement without it. "
        f"All captured terms: {sorted(all_terms)!r}"
    )

    uses = [a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"]
    withdrawing_state_uses = [a for a in uses if '"withdrawing state"' in a["proposition"]]

    # 1. IN-SCOPE (positive direction): at least one assertion links a
    # mention back to Article 14 itself (the defining article's own later
    # re-mentions of the term).
    in_scope = [a for a in withdrawing_state_uses if a["proposition"].startswith("Article 14 ")]
    assert in_scope, (
        f"expected at least one USES_DEFINITION assertion for 'withdrawing state' "
        f"anchored to Article 14 (the defining article's own later mentions); "
        f"got {withdrawing_state_uses!r}"
    )

    # 2. OUT-OF-SCOPE (negative direction, the gap this sprint's own manager
    # flagged as having "the least attention" this sprint): Article 99 also
    # mentions "the withdrawing state" in ordinary prose, but scope="local"
    # must confine the definition to Article 14 -- no assertion may name
    # Article 99 as the subject for this term.
    out_of_scope = [
        a for a in withdrawing_state_uses if a["proposition"].startswith("Article 99 ")
    ]
    assert not out_of_scope, (
        f"scope=\"local\" was NOT enforced -- Article 99 (a different section in "
        f"the same document, outside the defining article's own scope) drew a "
        f"USES_DEFINITION assertion for 'withdrawing state' anyway: {out_of_scope!r}"
    )
