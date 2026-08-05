"""RED live-path + rule-attribution test for US family 2, next cycle
(sprint 2026-08-04-defs-us-preamble, gate U4/U6, manager rulings M-R39/
M-R43/M-R44): Q-D2 shape 8 -- a B2-FAMILY wording variant. `_B2_WORDS_
HAVE_MEANINGS_RE` requires the literal phrase `"the following words have
the meaning(s) indicated"`, in that EXACT word order (`"In this <unit>,
the following words have the meanings indicated"`). MS's real convention
uses a DIFFERENT sentence structure, not just a different final word:
`"The following words and phrases when used in this article ... have the
meanings respectively ascribed to them in this section..."` -- the subject
("the following words and phrases") and the "when used in this article"
clause come BEFORE "have the meaning(s)", and the closing phrase is
"respectively ascribed to them" instead of "indicated". A same-function
word-swap ("indicated" -> "ascribed") is not sufficient; this needs a
genuinely alternate pattern for the reordered structure.

`STATE_MS_T27_C7_S19-3`: '(a) The following words and phrases when used in
this article for the purpose of this article have the meanings
respectively ascribed to them in this section, except in those instances
where the context clearly describes and indicates a different meaning:
(1) "Vehicle" means every device in, upon...'. Fetched live from
`us_ms_statutes.parquet` (never downloaded by this test), vendored
byte-for-byte into `fixtures/us_statutes/cycle7_pr7_shapes_rows.json`.

Independently confirmed (D1 measurement pass) to fail baseline
`is_definitions_heading`/`_is_placeholder_heading` (legacy gate is a
no-op) and, via the real, unedited `extract_definitions_from_section`
(numbered-block splitter -- no fallback needed), to already parse all 35
of this row's real defined terms once ANY heading recognizes the section.
Like the sibling MS test in `test_us_body_preamble_ms_second_convention_
red.py` (manager ruling M-R32), this row's own real curly-quote terms
carry literal internal PADDING (`" Vehicle "`, not `"Vehicle"`) -- the
SAME already-disclosed, already-routed `us_profile._leading_quote_
candidate` defect (missing `.strip()`, core follow-on, out of this
sprint's scope). This test strips on the TEST side only, matching that
established sibling convention exactly, not silently treating the padding
defect as fixed.

**Build target (D4)**: add a SECOND alternative pattern to `_b2_words_
have_meanings_indicated` (same function, same registration slot #3) for
the reordered "the following words and phrases ... have the meaning(s)
... ascribed to them" structure -- left to the Developer's own regex
design; this test only pins the required OUTCOME (which rule wins, and
what it extracts), not the exact pattern shape.

No test in this file reads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"

_ACT_ID = "STATE_MS_T27_C7_S19-3"


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


def test_mississippi_have_the_meanings_respectively_ascribed_to_them_is_captured(
    db_session, matter_with_users
):
    """`STATE_MS_T27_C7_S19-3`: verified live against the real, unedited
    `extract_definitions_from_section` before this test was written --
    yields 35 real candidates, terms padded with literal spaces (the
    already-disclosed, already-routed M-R32-class defect); stripped on the
    TEST side only, matching the sibling MS test's own convention."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _row()
    assert row["act_id"] == _ACT_ID
    assert "have the meanings respectively ascribed to them" in row["text"], (
        "fixture must reproduce the real shape-8 B2 wording variant"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="MS shape-8 B2 wording variant (test)",
        rows=[row],
        jurisdiction="US-MS",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    # `.strip()` here is a TEST-SIDE WORKAROUND for the routed production
    # defect (M-R32-class curly-quote padding), not a resolution of it --
    # see this file's own module docstring and the sibling MS test this
    # mirrors, `test_ms_shall_have_the_meaning_ascribed_herein_is_captured`
    # in `test_us_body_preamble_ms_second_convention_red.py`.
    created_terms = {t.strip() for d in result["created_definitions"] for t in d["terms"]}
    expected_terms = {"Vehicle", "Motor vehicle", "Person", "Trailer"}
    assert expected_terms <= created_terms, (
        f"the real production pipeline recognized ZERO of {_ACT_ID}'s real "
        f"MS definitions (expected {sorted(expected_terms)}, got "
        f"{sorted(created_terms)}) -- shape 8 (Q-D2), ruled OURS: a B2 "
        "wording variant not matching the exact literal 'have the "
        "meaning(s) indicated' phrase"
    )


def test_mississippi_winning_rule_is_b2_not_some_other_rule():
    """Rule-attribution pin (M-R44): once widened, `_b2_words_have_
    meanings_indicated` -- not CA/NE, and not B1 (registered AFTER B2 at
    slot #4, so even if B1's own shape-2/3/6 widenings landing this SAME
    cycle happened to also reach this body, B2 must still win by
    registration order) -- must be the row's winning rule."""
    from app.definition_links.rules.us_body_preamble import (
        _b2_words_have_meanings_indicated,
        _ca_wide_window_definitions_preamble,
        _ne_named_code_quoted_list,
    )

    body = _row()["text"]

    assert _ca_wide_window_definitions_preamble(body) is None
    assert _ne_named_code_quoted_list(body) is None

    assert _winning_rule("US-MS", body) is _b2_words_have_meanings_indicated, (
        f"expected the widened B2 rule to be the FIRST registered rule "
        f"recognizing {_ACT_ID}'s real body -- if this fails, either B2's "
        "own wording-variant widening is missing/broken, or a DIFFERENT "
        "rule (e.g. an over-widened B1) is silently winning ahead of it"
    )
