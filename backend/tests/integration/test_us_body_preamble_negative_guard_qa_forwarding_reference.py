"""QA addition (sprint 2026-08-04-defs-us-preamble, gate U5) -- NOT authored
by the Planner. New file only; the Planner's own test files in this
directory are never edited by QA (see this sprint's brief, D2/D3).

Purpose: plug a coverage gap found live during QA's D1 corpus-wide
false-positive exposure measurement (see `-log.md`'s QA section). The
Planner's own `test_us_body_preamble_negative_guard.py` already guards
against a "forwarding reference" false positive using a real NE row
(`STATE_NE_C60_S60-643`, "Operator's license shall have the meaning found
in section 60-474." -- a pure pointer to another section, no definition
text of its own). That NE fixture row does NOT begin with an "As used in
this <unit>"/"For (the) purposes of this <unit>" trigger phrase at all, so
it never reaches a trigger-phrase-anchored candidate rule's regex in the
first place -- it guards against a DIFFERENT, narrower hazard (treating a
bare "X shall have the meaning found in Y" sentence as definitional on its
own) than the one this file targets.

D1's corpus-wide scan found a REAL, corpus-confirmed row that reproduces
the SAME forwarding-reference hazard while ALSO matching the GA/MS "the
term" trigger-phrase shape this family's rule is built around:
`STATE_MS_T17_C2_S25-34` -- "(2) For purposes of this section, the term
"political subdivision" shall have the same meaning as provided under
Section 11-46-1." This row (a) DOES match a realistic candidate
BodyPreambleRule's trigger regex (verified live during D1: "For purposes
of this section, the term" satisfies the same "the term" anchor GA's own
real rows do), and (b) defines NOTHING of its own -- it is a pure pointer
to another section's own definition of "political subdivision", exactly
the NE test's hazard class, just under a body shape the existing negative
guard's fixture never actually exercises. Today (before `us_body_
preamble.py` exists) this is GREEN by the same logic as every other
negative-guard test in this family (nothing captures ANY US preamble
today) -- the point is that it MUST STAY green once the rule lands, and
unlike the NE fixture, THIS row's trigger phrase genuinely reaches a
plausible implementation's regex, so it is the sharper of the two guards
for a trigger-anchored rule.

Fixture: `backend/tests/fixtures/us_statutes/qa_d2_forwarding_reference_
rows.json` -- one REAL, VERBATIM, full parquet row dict (all original
columns, values unmodified), fetched live from the on-disk vaquill/
open-us-law snapshot by QA's own scratchpad script (never downloaded by
this test, and this test never reads the parquet snapshot itself).
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _row() -> dict:
    data = json.loads(
        (FIXTURES / "qa_d2_forwarding_reference_rows.json").read_text(encoding="utf-8")
    )
    return data[0]


def test_ms_for_purposes_of_this_section_the_term_shall_have_the_same_meaning_as_provided_under_is_a_forwarding_reference_not_captured(
    db_session, matter_with_users
):
    """STATE_MS_T17_C2_S25-34: '(2) For purposes of this section, the term
    "political subdivision" shall have the same meaning as provided under
    Section 11-46-1.' -- a pure forward pointer to ANOTHER section's own
    definition, with no definition text of its own at all. Unlike the
    Planner's NE forwarding-reference guard (`test_ne_shall_have_the_
    meaning_found_in_section_is_a_forwarding_reference_not_captured` in
    `test_us_body_preamble_negative_guard.py`), THIS row's own trigger
    phrase ('For purposes of this section, the term') matches the same
    "the term" anchor GA's genuine real rows use -- so a trigger-phrase-
    anchored candidate rule genuinely reaches this row's body, making this
    the sharper test of whether such a rule also excludes a pointer-only
    clause once its trigger phrase has already matched. Must produce zero
    Definitions.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _row()
    assert row["act_id"] == "STATE_MS_T17_C2_S25-34"
    assert "shall have the same meaning as provided under" in row["text"], (
        "fixture must reproduce the real forwarding-reference shape found live "
        "during QA D1 -- a genuine MS row whose trigger phrase matches the "
        "family's own 'the term' anchor but which defines nothing of its own"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Mississippi Code (QA forwarding-reference guard)",
        rows=[row],
        jurisdiction="US-MS",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    assert result["created_definitions"] == [], (
        "a body-preamble rule whose trigger phrase matches 'For purposes of "
        "this section, the term \"political subdivision\"' must NOT create a "
        "pointer-only Definition when the rest of the sentence is a pure "
        "forward reference ('shall have the same meaning as provided under "
        "Section 11-46-1') with no definition text of its own -- the same "
        "hazard class as the Planner's NE guard, now proven to recur outside "
        "NE and under a trigger shape a realistic candidate rule genuinely "
        "matches (QA D1 finding, -log.md)"
    )
