"""RED live-path + rule-attribution test for US family 2, next cycle
(sprint 2026-08-04-defs-us-preamble, gate U4/U6, manager rulings M-R39/
M-R43/M-R44): Q-D2 shape 2 -- B1's own trigger ("As used in this <unit>")
present, a quoted term + defining verb follows almost immediately, but
with NEITHER the literal phrase "the term" NOR a colon between them.
`_B1_QUOTE_MEANS_RE` (`_b1_quote_means_branch`) currently REQUIRES the
literal "the term" prefix; this shape omits it entirely.

M-R39 splits this shape by SCOPE, not by trigger wording: **ours where the
section is wholly (or near-wholly) a definitions BLOCK; scoped-inline's
CLAUSE** where a single defining sentence sits embedded inside a much
larger operative section (a different team's own territory, not
duplicated here). `STATE_KS_C75_A45_S75-4511` was deliberately picked
BECAUSE it is the BLOCK case: its 551-char body is 80% the single "state
agency" definition itself, with only one short administrative sentence
tacked on after it (no multi-topic operative section around it) --
squarely in-family per M-R39's own framing. (Contrast: this Planner also
verified `STATE_TN_T49_C4_S49-4-938`, Q-D2's own shape-6 example, is a
9,512-char grant-eligibility section with only ONE embedded defining
clause -- exactly the CLAUSE shape M-R39 does NOT hand us for shape 2;
that row is used by this cycle's shape-6 test instead, where M-R39
states no BLOCK/CLAUSE split applies.)

Real row, fetched live from `us_ks_statutes.parquet` (never downloaded by
this test), vendored byte-for-byte into `fixtures/us_statutes/
cycle7_pr7_shapes_rows.json`. Independently confirmed (D1 measurement
pass) to fail baseline `is_definitions_heading`/`_is_placeholder_heading`
(legacy gate is a no-op) and to yield the real term via the real, unedited
`_extract_inline_quoted_definitions` once ANY heading recognizes the
section.

**Build target (D4)**: widen `_b1_quote_means_branch`'s own
`_B1_QUOTE_MEANS_RE` so "the term" becomes OPTIONAL before the quoted
term, while requiring TIGHT adjacency (no intervening qualifier clause --
that is shape 6's own, separately-tested widening) so this branch stays
BLOCK-scoped per M-R39's split. Same function, same registration slot
(#4, B1's existing position) -- not a new rule.

No test in this file reads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"

_ACT_ID = "STATE_KS_C75_A45_S75-4511"


def _row() -> dict:
    data = json.loads((FIXTURES / "cycle7_pr7_shapes_rows.json").read_text(encoding="utf-8"))
    return data[_ACT_ID]


def _winning_rule(code: str, body: str):
    """See `test_us_body_preamble_shape3_in_this_trigger_red.py`'s own
    docstring for the full rationale -- identical helper, repeated per
    file per this family's own established convention (every existing
    file in this directory defines its own local `_rows`/`_ingest_and_link`
    rather than sharing a module)."""
    from app.definition_links.rules import registry

    for rule in registry.body_preamble_rules_for(code):
        derived = rule.derive_heading(body)
        if derived is not None:
            return rule.derive_heading
    return None


def test_kansas_as_used_in_this_act_no_the_term_no_colon_is_captured(
    db_session, matter_with_users
):
    """`STATE_KS_C75_A45_S75-4511`: 'As used in this act "state agency"
    means only those state agencies whose offices are located in Shawnee
    county...' -- no "the term", no colon, single quoted term immediately
    after the trigger. Verified live against the real, unedited
    `_extract_inline_quoted_definitions` before this test was written."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _row()
    assert row["act_id"] == _ACT_ID
    assert 'in this act "state agency" means' in row["text"], (
        "fixture must reproduce the real shape-2 gap: trigger immediately "
        "followed by a quoted term + verb, with no 'the term' and no colon "
        "in between"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="KS shape-2 'no the term, no colon' (test)",
        rows=[row],
        jurisdiction="US-KS",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "state agency" in created_terms, (
        f"the real production pipeline recognized ZERO of {_ACT_ID}'s real "
        f"KS definition (got {sorted(created_terms)}) -- shape 2 (Q-D2), "
        "ruled OURS for the BLOCK case (M-R39): a trigger-anchored quoted "
        "term + verb with no 'the term' literal and no colon"
    )


def test_kansas_winning_rule_is_b1_not_some_other_rule():
    """Rule-attribution pin (M-R44): once widened, `_b1_trigger_colon_or_
    quote_means` -- not CA/NE/B2 -- must be the first registered rule to
    recognize this row. CA/NE/B2 are independently re-confirmed here to
    return `None` on this exact real body every run, a stable invariant
    that would break if either sibling widening landing THIS SAME cycle
    (shape 7 on CA, shape 8 on B2) overreached into KS's body."""
    from app.definition_links.rules.us_body_preamble import (
        _b1_trigger_colon_or_quote_means,
        _b2_words_have_meanings_indicated,
        _ca_wide_window_definitions_preamble,
        _ne_named_code_quoted_list,
    )

    body = _row()["text"]

    assert _ca_wide_window_definitions_preamble(body) is None
    assert _ne_named_code_quoted_list(body) is None
    assert _b2_words_have_meanings_indicated(body) is None

    assert _winning_rule("US-KS", body) is _b1_trigger_colon_or_quote_means, (
        f"expected the widened B1 rule to be the FIRST registered rule "
        f"recognizing {_ACT_ID}'s real body -- if this fails, either B1's "
        "own 'no the term' widening is missing/broken, or a DIFFERENT "
        "rule is silently winning ahead of it"
    )
