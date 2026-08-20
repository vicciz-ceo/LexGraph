"""Sprint `2026-08-12-defs-b1-refers-to` (issue #19): live-persistence RED
tests for `_POST_RELATION`'s "refers to"/"refer to" gap, through the real
ingest + `run_definition_linking` pipeline (the production persistence
route), not a direct call to the B1 module.

Section 1 re-drives `tests.unit.test_us_body_preamble_b1_refers_to_relation_
red.CASES` -- the M-R107 structural controls, novel identifiers, not keyed
on the known row -- at live-persistence altitude, satisfying this sprint's
"at least one RED test must drive the real persistence path" requirement
for BOTH the "refers to" and "refer to" shapes plus the bounded negative
control.

Section 2 is the acceptance-evidence test for the actual Indiana row
`STATE_IN_T5_A28_C28_S5-28-28-3` named in the mandate and issue #19 -- this
is evidence for gate 1, not a structural control (M-R107 forbids keying
CONTROLS on it, but says nothing about the row itself, which is the very
thing the sprint exists to recover). Verified live against current HEAD by
this Planner: `derive_heading_from_body` returns `None` for this row today
(the sole "loan" candidate is produced by `_extract_inline_quoted_
definitions` with definition_text 'a loan guarantee made by the
corporation.\\n\\nAs added by P.L.222-2007, SEC.1.' via its own,
untouched-by-this-sprint "means/includes" idiom-gap match on the row's `(2)
includes` clause, then dropped by `_candidate_is_substantive` because
neither `_POST_RELATION` nor `_ENUM_RELATION` match the `(1) refers to`
clause's tail and `_bounded_payload` stops at the bare colon right after the
quoted term). Widening `_POST_RELATION` to recognize "refers to" makes
`_candidate_is_substantive` keep the SAME already-computed candidate --
its `definition_text` is unchanged by this sprint's fix, since only the
keep/drop decision is `_POST_RELATION`'s to make, not the boundary. This
Planner verified that exact resulting text end-to-end by locally simulating
one plausible `_POST_RELATION` widening (adding a `refers?\\s+to` verb
alternative) against the real production seam, with no repository file
changed -- see the Planner report for the transcript.
"""

from __future__ import annotations

import pytest

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

from tests.unit.test_us_body_preamble_b1_refers_to_relation_red import CASES


def _persisted_definition_text_by_term(db_session, result: dict) -> dict[str, str]:
    """Read the persisted output, not merely the response's term list."""
    persisted = []
    for created in result["created_definitions"]:
        definition = db_session.get(Definition, created["id"])
        assert definition is not None, f"pipeline returned missing Definition id {created['id']}"
        persisted.append(definition)
    return {term: definition.definition_text for definition in persisted for term in definition.terms}


def _ingest_and_link(db_session, matter_with_users, *, row: dict, jurisdiction: str, title: str) -> dict:
    matter = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=title,
        rows=[row],
        jurisdiction=jurisdiction,
    )
    return run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )


# --- 1. STRUCTURAL CONTROLS (M-R107): novel constructed cases, unseen ------
# --- identifiers, at live-persistence altitude. ----------------------------


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_b1_refers_to_relation_at_live_persistence_altitude(case, db_session, matter_with_users):
    """The direct-profile-altitude controls in the unit module must hold
    after the pipeline's real ingest + dedup + persistence semantics, not
    only at a bare function call."""
    act_id = f"FUTURE_REFERS_TO_RELATION_{case['name'].upper()}"
    row = {
        "act_id": act_id,
        "section_number": "1",
        "chapter": "1",
        "section_title": case["section_title"],
        "text": case["text"],
    }
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction=case["jurisdiction"],
        title=f"M-R107 refers-to relation control ({case['name']})",
    )
    persisted = _persisted_definition_text_by_term(db_session, result)

    for false_term in case["false_terms"]:
        assert false_term not in persisted, (
            f"{case['name']!r} must not persist {false_term!r} through the real "
            "pipeline"
        )
    if case["heading"] is None:
        assert not persisted, (
            f"{case['name']!r} is a bounded negative control (gerund 'referring "
            f"to' is out of this sprint's scope) and must persist nothing; got "
            f"{sorted(persisted)}"
        )
        return

    assert case["term"] in persisted, (
        f"expected {case['term']!r} among {sorted(persisted)} through the real "
        f"ingest + run_definition_linking persistence path -- {case['name']!r} "
        "exercises the same 'refers to'/'refer to' post-quote relation shape "
        "as issue #19's Indiana row, with entirely novel identifiers (M-R107)"
    )
    assert persisted[case["term"]] == case["definition_text"], (
        f"expected definition_text {case['definition_text']!r}, got "
        f"{persisted[case['term']]!r}"
    )


# --- 2. ACCEPTANCE EVIDENCE (gate 1): the real Indiana row named in the ----
# --- mandate and issue #19. Not a control -- the recovery target itself. --


def test_state_in_loan_refers_to_relation_recovered_live_persistence(db_session, matter_with_users):
    """`STATE_IN_T5_A28_C28_S5-28-28-3` "loan": (1) refers to a loan made by
    the corporation... -- the SINGLE genuine loss found by the P-R15
    deletion-side screen (`docs/sprint/sprints/2026-08-04-defs-us-preamble-
    scripts/mr118/qa/mr124/removal_relation_screen.jsonl`). Currently RED:
    `_POST_RELATION` has no "refers to"/"refer to" verb alternative, so
    `_candidate_is_substantive` drops the row's only candidate and the row
    persists nothing at all today."""
    row = {
        "act_id": "STATE_IN_T5_A28_C28_S5-28-28-3",
        "section_number": "5-28-28-3",
        "chapter": "28",
        "section_title": '"Loan"',
        "text": (
            'Sec. 3. As used in this chapter, "loan":\n\n'
            "(1) refers to a loan made by the corporation, regardless of "
            "whether the loan is forgivable; and\n\n"
            "(2) includes a loan guarantee made by the corporation.\n\n"
            "As added by P.L.222-2007, SEC.1."
        ),
    }
    result = _ingest_and_link(
        db_session, matter_with_users, row=row, jurisdiction="US-IN",
        title="IN T5 A28 C28 S5-28-28-3 (issue #19 refers-to acceptance evidence)",
    )
    persisted = _persisted_definition_text_by_term(db_session, result)
    assert "loan" in persisted, (
        f"expected 'loan' among {sorted(persisted)} -- issue #19: the row's "
        "sole 'As used in this chapter, \"loan\": (1) refers to...' definition "
        "must be captured and persisted again; a fix bounded to `_POST_RELATION` "
        "widening its verb alternation to recognize 'refers to'/'refer to' "
        "recovers it"
    )
    assert persisted["loan"] == (
        "a loan guarantee made by the corporation.\n\nAs added by P.L.222-2007, SEC.1."
    ), (
        f"expected the row's existing, untouched-by-this-sprint definition-text "
        f"boundary (from `_extract_inline_quoted_definitions`'s own '(2) includes' "
        f"idiom-gap match), got {persisted['loan']!r} -- `_POST_RELATION` only "
        "decides whether the candidate survives `_candidate_is_substantive`, not "
        "where its text starts or ends"
    )
