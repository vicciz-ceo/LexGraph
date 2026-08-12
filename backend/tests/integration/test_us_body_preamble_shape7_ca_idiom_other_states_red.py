"""RED live-path + rule-attribution test for US family 2, next cycle
(sprint 2026-08-04-defs-us-preamble, gate U4/U6, manager rulings M-R39/
M-R40/M-R43/M-R44): Q-D2 shape 7 -- CA's OWN wide-window
`"Definitions...govern/apply"` idiom, verbatim, appearing in OTHER states.
`_ca_wide_window_definitions_preamble` is registered `jurisdiction_codes=
("US-CA",)` only, "for no principled reason" (this cycle's own charter,
`-log.md`) -- its own regex has no CA-specific vocabulary at all.

**"IN x2"**: the headings panel's guarded-cluster cross-check (Q-D3,
independently re-confirmed by the manager, M-R40) found the SAME idiom on
TWO real, differently-numbered Indiana rows for the SAME underlying
statute (`STATE_IN_T21_A44_C7_S21-44-7-1` and its versioned sibling
`...-1-b`, one effective until 7-1-2027 and one effective after): `"Sec.
1. The following definitions apply throughout this chapter: (1) \"Board\"
refers to... (2) \"Fund\"..."`. Both fetched live from `us_in_statutes.
parquet` (never downloaded by this test), vendored byte-for-byte into
`fixtures/us_statutes/cycle7_pr7_shapes_rows.json`.

**Confirmed live (this Planner, before writing this test)**: calling
`_ca_wide_window_definitions_preamble` DIRECTLY on either IN row's real
body ALREADY returns a non-`None` heading TODAY -- the function itself has
no jurisdiction awareness (`derive_heading: body -> str | None`) and needs
NO regex change. The ENTIRE gap is the registration's own `jurisdiction_
codes` tuple: `registry.body_preamble_rules_for("US-IN")` does not include
this rule at all today, so the real end-to-end dispatch (`profile.
derive_heading_from_body`) never even tries it -- confirmed independently
of, and reproduced by, the rule-attribution test below.

**Build target (D4, M-R40's own words)**: "Widening its `jurisdiction_
codes` is a one-line rule change." Recommended: add `"US-IN"` (this cycle's
named target) -- NOT a blanket `"US-*"` rewrite, per this cycle's own D3/D4
overlap analysis (a wildcard would make this now-jurisdiction-broad rule,
still registered FIRST/position #1, capable of preempting NE's own
narrower, more-specific rule at position #2 for any Nebraska row that also
happens to contain the wide-window idiom -- see D4's overlap table in
`-log.md`). Same function, same registration slot.

No test in this file reads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"

IN_ACT_IDS = ["STATE_IN_T21_A44_C7_S21-44-7-1", "STATE_IN_T21_A44_C7_S21-44-7-1-b"]


def _rows() -> dict[str, dict]:
    return json.loads((FIXTURES / "cycle7_pr7_shapes_rows.json").read_text(encoding="utf-8"))


def _winning_rule(code: str, body: str):
    from app.definition_links.rules import registry

    for rule in registry.body_preamble_rules_for(code):
        derived = rule.derive_heading(body)
        if derived is not None:
            return rule.derive_heading
    return None


@pytest.mark.parametrize("act_id", IN_ACT_IDS)
def test_indiana_the_following_definitions_apply_throughout_this_chapter_is_captured(
    db_session, matter_with_users, act_id
):
    """Both IN rows: 'Sec. 1. The following definitions apply throughout
    this chapter: (1) "Board" refers to... (2) "Fund" refers to...'.
    Verified live against the real, unedited `extract_definitions_from_
    section` (numbered-block splitter, no fallback needed) before this
    test was written."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _rows()[act_id]
    assert "The following definitions apply throughout this chapter" in row["text"]

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=f"IN shape-7 CA-idiom-elsewhere ({act_id}) (test)",
        rows=[row],
        jurisdiction="US-IN",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert {"Board", "Fund"} <= created_terms, (
        f"the real production pipeline recognized ZERO of {act_id}'s real "
        f"IN definitions (got {sorted(created_terms)}) -- shape 7 (Q-D2), "
        "CA's own wide-window idiom appearing in Indiana, ruled OURS, "
        "'a one-line rule change' (M-R40)"
    )


@pytest.mark.parametrize("act_id", IN_ACT_IDS)
def test_indiana_direct_ca_function_call_already_recognizes_this_body_today(act_id):
    """Unit-level pin, NOT gated on registration: proves the regex itself
    needs ZERO changes -- `_ca_wide_window_definitions_preamble` already
    returns non-`None` when called DIRECTLY on this real IN body today,
    confirming the entire gap is the rule's own `jurisdiction_codes`
    registration, not its pattern. If this assertion ever starts failing,
    re-verify the 'one-line' framing above before reusing it."""
    from app.definition_links.rules.us_body_preamble import (
        _ca_wide_window_definitions_preamble,
    )

    body = _rows()[act_id]["text"]
    assert _ca_wide_window_definitions_preamble(body) is not None


@pytest.mark.parametrize("act_id", IN_ACT_IDS)
def test_indiana_winning_rule_is_ca_rule_not_some_other_rule(act_id):
    """Rule-attribution pin (M-R44): the SAME `_ca_wide_window_
    definitions_preamble` function -- reached via US-IN's own registry
    list, not NE/B2/B1 -- must be the row's winning rule. Today this is
    RED for a DISPATCH reason, not a pattern reason (see the unit-level
    pin above): `registry.body_preamble_rules_for("US-IN")` simply does
    not include this rule yet."""
    from app.definition_links.rules.us_body_preamble import (
        _b1_trigger_colon_or_quote_means,
        _b2_words_have_meanings_indicated,
        _ca_wide_window_definitions_preamble,
        _ne_named_code_quoted_list,
    )

    body = _rows()[act_id]["text"]

    assert _ne_named_code_quoted_list(body) is None
    assert _b2_words_have_meanings_indicated(body) is None
    assert _b1_trigger_colon_or_quote_means(body) is None

    assert _winning_rule("US-IN", body) is _ca_wide_window_definitions_preamble, (
        f"expected the CA wide-window rule (now widened to include "
        f"US-IN) to be the FIRST registered rule recognizing {act_id}'s "
        "real body -- if this fails, either 'US-IN' was never added to "
        "the rule's own `jurisdiction_codes`, or a DIFFERENT rule is "
        "silently winning ahead of it"
    )
