"""RED live-path + rule-attribution test for US family 2, next cycle
(sprint 2026-08-04-defs-us-preamble, gate U4/U6, manager rulings M-R39/
M-R40/M-R43/M-R44): Q-D2 shape 5 -- Named-Act phrasing, `"As used in the
<Named Act>"` (not `"As used in this <unit>"`), combined with the
`"also means"` idiom (a quoted term's SECOND definition, additive to one
given elsewhere). Neither `_B1_TRIGGER_RE` (which requires the literal
word "this" right after "in"/"of") nor `_B1_QUOTE_MEANS_RE` (immediate-
adjacency "the term" + quote) reaches this shape today -- confirmed
independently by BOTH Q-D2 (P-R7's own denominator sweep) and Q-D3 (the
headings panel's guarded-cluster cross-check), the SAME real row found by
two unrelated methods, cross-confirming the finding (M-R40).

`STATE_NM_C3_A32_S3-32-3`: `"As used in the Industrial Revenue Bond Act,
'project' also means:\\n\\nA. any land and buildings..."`. Fetched live
from `us_nm_statutes.parquet` (never downloaded by this test), vendored
byte-for-byte into `fixtures/us_statutes/cycle7_pr7_shapes_rows.json`.
Independently confirmed (D1 measurement pass) to fail baseline
`is_definitions_heading`/`_is_placeholder_heading` (legacy gate is a
no-op) and to yield the real term via the real, unedited
`_extract_inline_quoted_definitions` once ANY heading recognizes the
section.

**Build target (D4)**: a NEW function, `_named_act_also_means_preamble`
(the exact name this test imports -- the Developer's build target, not a
suggestion), matching `"As used in the <Capitalized ... Act|Code>"`
followed by a quoted term + `means`/`also means`. M-R40 ruled RECOGNITION
ours, SCOPE (a Named-Act-bounded unit rather than "this <unit>") core's
follow-on -- this rule only needs to supply a heading, same as every other
rule in this family; scope handling is out of bounds here. Recommended
registration position: EARLY (`US-*`, before B2/B1, narrow-trigger-before-
broad-catch-all per M-R27's own stated precedence discipline) -- see D4's
own registration-order table in `-log.md` for the full reasoning and the
overlap check against B1's shape-2/3/6 widenings (none found: "the <Act>"
is disjoint from "this <unit>").

No test in this file reads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"

_ACT_ID = "STATE_NM_C3_A32_S3-32-3"


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


def test_new_mexico_named_act_also_means_is_captured(db_session, matter_with_users):
    """`STATE_NM_C3_A32_S3-32-3`: 'As used in the Industrial Revenue Bond
    Act, "project" also means: A. any land and buildings...'. Verified
    live against the real, unedited `_extract_inline_quoted_definitions`
    before this test was written."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _row()
    assert row["act_id"] == _ACT_ID
    assert "As used in the Industrial Revenue Bond Act" in row["text"]
    assert "also means" in row["text"], (
        "fixture must reproduce the real shape-5 Named-Act + 'also means' "
        "idiom -- the same row Q-D2 and Q-D3 independently found"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="NM shape-5 Named-Act 'also means' (test)",
        rows=[row],
        jurisdiction="US-NM",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "project" in created_terms, (
        f"the real production pipeline recognized ZERO of {_ACT_ID}'s real "
        f"NM definition (got {sorted(created_terms)}) -- shape 5 (Q-D2), "
        "ruled OURS for recognition (M-R40): Named-Act phrasing + 'also "
        "means', cross-confirmed by both Q-D2 and Q-D3 on this same row"
    )


def test_new_mexico_winning_rule_is_the_new_named_act_rule_not_some_other_rule():
    """Rule-attribution pin (M-R44): the NEW `_named_act_also_means_
    preamble` function -- not CA/NE/B2/B1, all independently re-confirmed
    here to return `None` on this exact real body -- must be the row's
    winning rule. `from app.definition_links.rules.us_body_preamble import
    _named_act_also_means_preamble` is expected to raise `ImportError`
    until the Developer builds it (this file's own build target, D4) --
    imported INSIDE the test body (not module level), matching this
    codebase's own established convention (`test_definition_links_rules_
    registry.py`'s module docstring) so a missing symbol fails this ONE
    test, not the whole file's collection.
    """
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
    assert _b1_trigger_colon_or_quote_means(body) is None, (
        "B1's own trigger requires the literal word 'this' right after "
        "'As used in' -- NM's row says 'the Industrial Revenue Bond Act', "
        "never 'this'; if this fails, B1 has been widened far enough to "
        "ALSO reach Named-Act phrasing, which would make the dedicated "
        "shape-5 rule below redundant or, worse, silently starved"
    )

    from app.definition_links.rules.us_body_preamble import _named_act_also_means_preamble

    assert _winning_rule("US-NM", body) is _named_act_also_means_preamble, (
        f"expected the NEW `_named_act_also_means_preamble` rule to be the "
        f"FIRST registered rule recognizing {_ACT_ID}'s real body -- if "
        "this fails, either the rule isn't registered for US-NM (or US-*), "
        "or a DIFFERENT rule is silently winning ahead of it"
    )
