"""RED live-path + rule-attribution tests for US family 2, next cycle
(sprint 2026-08-04-defs-us-preamble, gate U4/U6, manager rulings M-R39/
M-R43/M-R44): Q-D2 shape 3 -- `"In this <unit>:"` as the definitions
preamble's OWN trigger, distinct from the two phrases `_B1_TRIGGER_RE`
currently matches (`"As used in"`/`"For (the) purposes of"`, both always
followed by the word "this"). M-R39 ruled this **OURS, highest value**:
it is FEDERAL's own DOMINANT convention (4/4 of QA's sampled FEDERAL rows
share this exact shape) and directly threatens this sprint's own contract
item 14 (FEDERAL 198/435 achievable subset) if left unfixed.

Every row below is real, fetched live from `us_federal_statutes.parquet`
(never downloaded by this test), vendored byte-for-byte into
`fixtures/us_statutes/cycle7_pr7_shapes_rows.json` alongside this cycle's
other 5 shape fixtures. Each row's real, unedited `text` was independently
confirmed (this Planner's own measurement pass, `-log.md` D1) to:
(a) fail baseline `is_definitions_heading` and `_is_placeholder_heading`
(so the LEGACY gate is a no-op and dispatch is decided entirely by the
registry loop below), and (b) yield ZERO candidates from the real,
unedited `extract_definitions_from_section` unless `heading_was_derived`
is forced True (i.e. TODAY, with no heading recognized at all, extraction
never even runs) -- see the pre-registered-terms check in each capture
test, run against the real, unedited extractor before this file existed.

**Build target (D4 item list, `-log.md`)**: widen the EXISTING
`_b1_trigger_colon_or_quote_means` rule's own `_B1_TRIGGER_RE` to accept
`"In this <unit>"` as a third trigger alternative (alongside "As used in
this"/"For (the) purposes of this") -- NOT a new function, NOT a new
registration slot. B2 (registered BEFORE B1, M-R27) already excludes its
own `"In this <unit>, the following words have the meanings indicated"`
phrasing from ever reaching B1 by firing first, so no new exclusion logic
is needed inside B1 itself for that overlap.

**Per-rule attribution (M-R44)**: `_winning_rule` below mirrors
`USProfile.derive_heading_from_body`'s own registry loop (first-non-None-
wins in REGISTRATION order, M-R27) but returns the WINNING rule's
`derive_heading` callable itself, not just its string result -- so a test
can assert WHICH rule claimed a row. Every test in this file asserts BOTH
that `_b1_trigger_colon_or_quote_means` is the row's winning rule (not CA/
NE/B2, all independently confirmed below to return `None` on every fixture
body here -- a stable invariant this file re-checks every run, not merely
assumed) AND that the real live pipeline captures the expected terms --
either assertion alone would miss a starvation regression the other
catches (an aggregate-only capture check cannot see a DIFFERENT rule
silently claiming the row; a bare rule-identity check without the live
path cannot see an extraction-layer regression).

No test in this file reads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _rows() -> dict[str, dict]:
    return json.loads((FIXTURES / "cycle7_pr7_shapes_rows.json").read_text(encoding="utf-8"))


def _winning_rule(code: str, body: str):
    """Mirrors `USProfile.derive_heading_from_body`'s own registry loop
    (`us_profile.py:1402-1405`, first-non-None-wins in registration order)
    -- returns the WINNING `BodyPreambleRule.derive_heading` callable
    itself. The profile's separate LEGACY/baseline gate
    (`derive_heading_from_body` module function, `_is_placeholder_heading`-
    gated) is untouched by this family; every fixture row in this file is
    independently confirmed non-placeholder (real FEDERAL headings), so
    that gate is a no-op for all of them and mirroring only the registry
    loop here is faithful to the real end-to-end dispatch outcome."""
    from app.definition_links.rules import registry

    for rule in registry.body_preamble_rules_for(code):
        derived = rule.derive_heading(body)
        if derived is not None:
            return rule.derive_heading
    return None


FED_CASES = [
    pytest.param(
        "USC_T7_C31_S936f",
        {"eligible program"},
        id="usc-t7-c31-s936f-eligible-program",
    ),
    pytest.param(
        "USC_T27_C6_S122a",
        {"attorney general", "intoxicating liquor"},
        id="usc-t27-c6-s122a-attorney-general",
    ),
    pytest.param(
        "USC_T43_C35_S1742a",
        {"eligible"},
        id="usc-t43-c35-s1742a-eligible",
    ),
    pytest.param(
        "USC_T10_C147_S2496",
        {"forced labor", "XUAR"},
        id="usc-t10-c147-s2496-forced-labor",
    ),
]


@pytest.mark.parametrize("act_id, expected_terms", FED_CASES)
def test_federal_in_this_section_trigger_is_captured(
    db_session, matter_with_users, act_id, expected_terms
):
    """Live-path: all four rows share the exact real shape `"(a) Definitions
    \\n\\nIn this section:\\n\\n(N) <label>\\n\\nThe term \"X\" means..."`
    (or the bare em-dash variant, `USC_T27_C6_S122a`'s `"In this
    section—"`) -- confirmed live against the real, unedited
    `_extract_inline_quoted_definitions` (called directly, before this file
    existed) to already parse these exact terms once ANY heading recognizes
    the section -- this family's job is recognition only, per this file's
    own module docstring.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _rows()[act_id]

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=f"FED shape-3 'In this section' ({act_id}) (test)",
        rows=[row],
        jurisdiction="US-FED",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert expected_terms <= created_terms, (
        f"the real production pipeline recognized ZERO of {act_id}'s real "
        f"FEDERAL 'In this section:' definitions (expected "
        f"{sorted(expected_terms)}, got {sorted(created_terms)}) -- shape 3 "
        "(Q-D2), FEDERAL's own DOMINANT convention (4/4 sampled rows), "
        "ruled OURS and HIGHEST VALUE (M-R39) because it directly threatens "
        "this sprint's contract item 14 (FEDERAL 198/435 achievable subset)"
    )


@pytest.mark.parametrize("act_id, expected_terms", FED_CASES)
def test_federal_in_this_section_winning_rule_is_b1_not_some_other_rule(
    act_id, expected_terms
):
    """Rule-attribution pin (M-R44): once widened, `_b1_trigger_colon_or_
    quote_means` -- NOT CA/NE/B2, all independently confirmed below to
    return `None` on this exact real body -- must be the FIRST registered
    rule (registration order) to recognize this row. A future change that
    widens CA/NE/B2 broadly enough to ALSO reach a FEDERAL 'In this
    section' body would flip this test even if the live-path capture test
    above stayed green (aggregate capture cannot see a different rule
    silently winning) -- that is exactly the starvation failure mode this
    pin exists to catch.
    """
    from app.definition_links.rules.us_body_preamble import (
        _b1_trigger_colon_or_quote_means,
        _b2_words_have_meanings_indicated,
        _ca_wide_window_definitions_preamble,
        _ne_named_code_quoted_list,
    )

    body = _rows()[act_id]["text"]

    assert _ca_wide_window_definitions_preamble(body) is None, (
        "CA's own wide-window rule must never claim a real FEDERAL 'In "
        "this section:' row -- if this fails, CA's own widening (shape 7, "
        "this same cycle) has overreached and is starving B1 for this row"
    )
    assert _ne_named_code_quoted_list(body) is None, (
        "NE's own named-code rule must never claim a real FEDERAL row"
    )
    assert _b2_words_have_meanings_indicated(body) is None, (
        "B2's own rule must never claim a real FEDERAL 'In this section:' "
        "row -- if this fails, B2's own widening (shape 8, this same "
        "cycle) has overreached and is starving B1 for this row"
    )

    assert _winning_rule("US-FED", body) is _b1_trigger_colon_or_quote_means, (
        f"expected the widened B1 rule (`_b1_trigger_colon_or_quote_means`) "
        f"to be the FIRST registered rule recognizing {act_id}'s real "
        "'In this section:' body -- if this fails, either B1's own 'In "
        "this' trigger widening is missing/broken, or a DIFFERENT rule is "
        "silently winning ahead of it (the exact starvation failure mode "
        "M-R44 requires this pin to catch)"
    )
