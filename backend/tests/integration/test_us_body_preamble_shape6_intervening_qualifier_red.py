"""RED live-path + rule-attribution test for US family 2, next cycle
(sprint 2026-08-04-defs-us-preamble, gate U4/U6, manager rulings M-R39/
M-R43/M-R44): Q-D2 shape 6 -- an intervening QUALIFIER clause sits between
B1's own trigger and the literal "the term" + quote, e.g. `"As used in
this section, unless the context otherwise requires, \"veteran\"
means..."`. `_B1_QUOTE_MEANS_RE` anchors immediately at the trigger's own
end (`^,?\\s*the term...`) -- a comma-bounded qualifier clause in between
breaks the match today.

M-R39 rules this shape **OURS, "narrow B1 widening"**, with NO BLOCK/
CLAUSE split (unlike shape 2's own SPLIT ruling) -- so, unlike shape 2's
own fixture, `STATE_TN_T49_C4_S49-4-938` is deliberately a large (9,512-
char) grant-eligibility section where only ONE clause, (b), actually
defines a term ("veteran"); clauses (c)-(j) are unrelated operative
eligibility rules. This is the SAME real row Q-D2 itself names for shape
6. Fetched live from `us_tn_statutes.parquet` (never downloaded by this
test), vendored byte-for-byte into `fixtures/us_statutes/
cycle7_pr7_shapes_rows.json`.

Independently confirmed (D1 measurement pass) to fail baseline
`is_definitions_heading`/`_is_placeholder_heading` (legacy gate is a
no-op) and to yield the real term via the real, unedited
`_extract_inline_quoted_definitions` once ANY heading recognizes the
section -- confirmed the rest of the 9,512-char body contributes no
further spurious quote+verb candidates (only "veteran" extracts, twice --
a duplicate-body corpus artifact matching this fixtures directory's own
documented pattern, not a defect this test's assertion needs to route
around).

**Build target (D4)**: widen `_b1_quote_means_branch` to tolerate an
OPTIONAL short comma-bounded qualifier clause between the trigger and "the
term"/the quote (e.g. `",\\s*unless the context otherwise requires,\\s*"`
or, more generally, any short comma-delimited clause) -- same function,
same registration slot (#4). Flagged for the Developer (D4): this widening
and shape 2's widening (dropping "the term" entirely) touch the SAME
branch and must not be allowed to silently subsume each other's intended
boundary -- see this cycle's D4 overlap notes in `-log.md`.

No test in this file reads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"

_ACT_ID = "STATE_TN_T49_C4_S49-4-938"


def _row() -> dict:
    data = json.loads((FIXTURES / "cycle7_pr7_shapes_rows.json").read_text(encoding="utf-8"))
    return data[_ACT_ID]


def _winning_rule(code: str, body: str):
    from app.definition_links.rules import registry

    for rule in registry.body_preamble_rules_for(code):
        derived = rule.derive_heading(body)
        if derived is not None:
            return rule.derive_heading
    return None


def test_tennessee_intervening_qualifier_clause_veteran_is_captured(
    db_session, matter_with_users
):
    """`STATE_TN_T49_C4_S49-4-938` ('Helping Heroes Act of 2008'): '(b) As
    used in this section, unless the context otherwise requires, "veteran"
    means a former member of the United States armed forces...'. Verified
    live against the real, unedited `_extract_inline_quoted_definitions`
    before this test was written -- the rest of this large section's own
    operative eligibility clauses (c)-(j) contribute no other candidates.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _row()
    assert row["act_id"] == _ACT_ID
    assert "unless the context otherwise requires" in row["text"], (
        "fixture must reproduce the real shape-6 intervening qualifier "
        "clause between the trigger and the quoted term"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="TN shape-6 intervening qualifier (test)",
        rows=[row],
        jurisdiction="US-TN",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "veteran" in created_terms, (
        f"the real production pipeline recognized ZERO of {_ACT_ID}'s real "
        f"TN definition (got {sorted(created_terms)}) -- shape 6 (Q-D2), "
        "ruled OURS, 'narrow B1 widening': an intervening qualifier clause "
        "between the trigger and the quoted term"
    )


def test_tennessee_winning_rule_is_b1_not_some_other_rule():
    """Rule-attribution pin (M-R44): once widened, `_b1_trigger_colon_or_
    quote_means` -- not CA/NE/B2 -- must be the first registered rule to
    recognize this row. CA/NE/B2 are independently re-confirmed here to
    return `None` on this exact real body every run."""
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

    assert _winning_rule("US-TN", body) is _b1_trigger_colon_or_quote_means, (
        f"expected the widened B1 rule to be the FIRST registered rule "
        f"recognizing {_ACT_ID}'s real body -- if this fails, either B1's "
        "own qualifier-clause widening is missing/broken, or a DIFFERENT "
        "rule is silently winning ahead of it"
    )
