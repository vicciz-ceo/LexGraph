"""Outcome-level pin for sprint 2026-08-04-defs-us-multiterm, cycle P5
(Planner) -- the SECOND of two pins replacing the single candidate-level
`test_tx_governmental_body_captured_exactly_once_through_full_dispatch`
pin in `backend/tests/unit/test_definition_links_tx_2009_003_full_row_
findings.py` (see that file's own amended docstring for the full
re-scoping history and the arbitration this responds to).

**Why this file exists, separate from the candidate-level pin.** Program
ruling (this cycle) arbitrated a cross-panel dispute over TX
`STATE_TX_Cgv_C2009_S2009.003`: the markers panel's own rule legitimately
emits a SECOND `Governmental body` candidate on this row (measured
counter-evidence on three WA rows showed a blanket "stay silent where
baseline already emitted" rule would also suppress markers' own clean fix
over baseline's own multi-thousand-char swallow elsewhere -- correctness
varies per row, so no emission-layer rule can resolve it; it settles at
the preference/quality layer, core's G8). Consequence: a candidate-level
"exactly 1 over the FULL cross-panel union" assertion encodes the
rejected emission-layer theory and would go RED on markers' merge for a
reason that is NOT a defect. But this sprint's own ORIGINAL hazard was
never "how many raw candidates exist" -- it was always the DOWNSTREAM
consequence: a real mention of "Governmental body" drawing more than one
`USES_DEFINITION` assertion, or persisting a corrupt `definition_text`.
That consequence lives at Stage 3/persistence, not Stage 2 candidate
counting, so it is measured here, independently of whichever panel's
candidate the persist-layer `(article_id, sorted(terms))` first-wins key
happens to keep.

**Verified, not assumed (Planner, this cycle):** on this real row,
persistence is first-wins on `(article_id, sorted(terms))`. Baseline's
own per-block leading-quote pass (`us_profile._leading_quote_candidate`)
produces the correct, clean single-term candidate for entry `(2)
"Governmental body" has the meaning assigned by Section 552.003.`
(`definition_text == "has the meaning assigned by Section 552.003."`,
44 chars) and is always unconditionally present, run before any
`TermClauseRule` in `extract_definitions_from_section`'s own candidate
list. Measured live (this Planner, this cycle) against the REAL,
unmodified `extract_definitions_from_section` output for this row: the
FIRST candidate whose `.terms == ("Governmental body",)` in the returned
list IS baseline's clean 44-char candidate, and it is the only one today
(the candidate-level pin's own re-scoped assertion, in the sibling unit
test file, independently pins that OUR OWN rule contributes zero
duplicates for this term on this row). Whatever markers' own merge later
adds is a SEPARATE candidate for the SAME `(article_id, ("Governmental
body",))` key -- the persist layer's existing, unmodified first-wins
dedup (`pipeline.py`, owned by core, not touched by this sprint) keeps
whichever candidate is inserted first for that key and discards the
rest, so baseline's correct 44-char text keeps winning both today and
after that merge, and no second `Definition` row is ever created for the
same key. This test should therefore be GREEN today and STAY green
post-merge -- it is pinning the ACTUAL hazard (a bad or duplicated
downstream assertion), not a candidate-population shape that the
arbitration already ruled cannot be resolved at this layer.

**Pattern.** Mirrors the established `db_session`/`matter_with_users`
live-ingest pattern already used by `test_multiterm_f5_shared_clause.py`
and `test_multiterm_qa_u4_findings.py` (finding 1/1b in particular, which
pins the exact same TWO-LAYER shape -- "exactly one USES_DEFINITION
assertion" plus "the governing Definition's own persisted content is
correct" -- for an unrelated hazard): a real TX row supplying the
definition, ingested alongside a SEPARATE real-shaped article in the
SAME chapter that genuinely MENTIONS "governmental body" in running
prose, run through the full production pipeline
(`ingest_us_statute_rows` -> `run_definition_linking`), asserting on
real persisted `Assertion`/`Definition` rows -- never a candidate list,
never a named-wiring proof.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "multiterm_f5_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def test_tx_governmental_body_real_mention_draws_exactly_one_assertion_with_correct_persisted_text(
    db_session, matter_with_users
):
    """Real row `STATE_TX_Cgv_C2009_S2009.003` (entry `(2) "Governmental
    body" has the meaning assigned by Section 552.003.`), ingested
    alongside a same-chapter article whose body genuinely mentions
    "governmental body" in running prose -- the shape a real downstream
    reader would actually hit. Two-layer pin, per the finding1/1b
    precedent: (a) the mention draws exactly ONE `USES_DEFINITION`
    assertion (not two, which is the actual consequence the cross-panel
    duplicate candidate would cause if the persist layer's dedup ever
    stopped collapsing it), and (b) the governing `Definition`'s
    persisted `definition_text` is baseline's correct, clean text -- not
    a corrupt swallow (the ORIGINAL M-R18 defect's own shape: an
    unguarded whole-text-block cross-reference scan produced a second
    candidate whose `definition_text` ran on ~400 chars into unrelated
    trailing prose)."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion
    from app.models.definition import Definition

    row = _load_rows()["STATE_TX_Cgv_C2009_S2009.003"]
    using_row = {
        "act_id": "STATE_TX_TEST_M18_GOV_BODY_USING",
        "text": (
            "A governmental body shall respond to a request for public "
            "information not later than the tenth business day after the "
            "date the request is received."
        ),
        "section_title": "§ 2009.099. Unrelated public information response time.",
        "section_number": "2009.099",
        "chapter": "2009",
    }
    m = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="TX Government Code 2009.003 (M-R18 outcome pin -- Governmental body)",
        rows=[row, using_row],
        jurisdiction="US-TX",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses = [a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"]
    using_article_uses = [
        a
        for a in uses
        if a["proposition"].startswith("Article 2009.099 ")
        and '"Governmental body"' in a["proposition"]
    ]
    assert len(using_article_uses) == 1, (
        f'expected the real mention of "governmental body" in article 2009.099 to draw '
        f"exactly ONE USES_DEFINITION assertion -- this is the actual downstream hazard the "
        f"cross-panel duplicate candidate would cause if the persist layer's existing "
        f"`(article_id, sorted(terms))` first-wins dedup (pipeline.py, unmodified by this "
        f"sprint) ever stopped collapsing it into one Definition row. Got "
        f"{len(using_article_uses)}: {using_article_uses!r}"
    )

    governing_definition_id = db_session.get(Assertion, using_article_uses[0]["id"]).object_entity_id
    governing = db_session.get(Definition, governing_definition_id)
    assert governing.definition_text == "has the meaning assigned by Section 552.003.", (
        f"the PERSISTED definition_text governing this mention must be baseline's own correct, "
        f'clean text (44 chars, "has the meaning assigned by Section 552.003.") -- verified '
        f"live (Planner, this cycle) as the first-wins candidate for this row's "
        f'`(article_id, ("Governmental body",))` persist key. A corrupt, ~400-char swallow '
        f"here (the ORIGINAL M-R18 defect's own shape, an unguarded whole-text-block "
        f"cross-reference scan running on into unrelated trailing prose) or any other wrong "
        f"text would mean either this sprint's own guard regressed or the persist-layer "
        f"first-wins assumption this pin depends on no longer holds -- either way, a real "
        f"finding to report, not silently absorbed. Got "
        f"({len(governing.definition_text)} chars): {governing.definition_text!r}"
    )
