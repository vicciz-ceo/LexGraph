"""QA1 (phase-2 QA cycle 1) -- Q3: TX `STATE_TX_Cgv_C2009_S2009.003`'s 4
degenerate 1-term rows (sprint 2026-08-04-defs-us-markers, gate U1;
ownership per ruling M-R5, recorded in this sprint's own log `## Q-B`:
"The TX `2009.003` residual ... is ours by M-R5 and folds into our
entry-boundary work").

**Part A -- confirms the 4 named degenerate rows still reproduce on THIS
build, unchanged.** The real body reads:

    (4) The following terms have the meanings assigned by Section 2001.003:

    (A) "contested case";

    (B) "party";

    (C) "person"; and

    (D) "rule."

Baseline's `_split_into_numbered_blocks` treats each lettered `(A)/(B)/
(C)/(D)` sub-item as its OWN sibling top-level entry (the SAME
unconditional-marker-boundary behavior diagnosed in this pass's Q1/Q2
findings), so the parent redirect clause -- "have the meanings assigned by
Section 2001.003" -- is never attached to any of the 4 terms it actually
defines. What each term captures instead is only the stray punctuation
AFTER its own closing quote: `;`, `;`, `; and`, `` (empty). Reproduced
exactly (verified against the real row this pass): `contested case` -> `;`,
`party` -> `;`, `person` -> `; and`, `rule.` -> `''`.

Per M-R8 (multiterm panel's own ruling, cross-panel agreed): the fix is
markers' `EntrySplitterRule` for TX emitting the parent-redirect clause
TOGETHER with its lettered children as ONE block, so multiterm's
`TermClauseRule` can fan it out into 4 candidates sharing the parent's
redirect text. Not yet built on this branch -- pinned here as the
un-fixed baseline it must be judged against.

**Part B -- originally a NEW finding (QA1 Q3): OUR OWN
`us_markers_boundary.py` engine had a real, live truncation bug on this
SAME row**, unrelated to the 4 degenerate terms above.
`"Governmental body" has the meaning assigned by Section 552.003.` --
our engine (`extract_quote_anchored_entries`, called directly) used to
capture this as `'assigned by Section'`, silently dropping `' 552.003.'`.

Root cause (as originally diagnosed): `_TRAILING_MARKER_CHAIN_RE` is meant
to strip a NEXT ENTRY's leaked marker fragment off the end of a captured
definition (its own docstring's examples: SC's "Municipality" ending in a
literal `"(2)"`; AZ's "Qualified higher education expenses" ending in a
literal `"13."`). A real statutory citation of the shape `"NNN.NNN."`
(e.g. "552.003.") was, without a guard, INDISTINGUISHABLE from two
back-to-back digit-dot marker tokens ("552." then "003."), so the whole
citation got stripped as if it were marker-chain noise.

**RULING U-R13 (sprint log §M22): this defect IS NOW FIXED.**
`_TRAILING_MARKER_CHAIN_RE` in `us_markers_boundary.py` now carries a
`(?<![\d.])` guard immediately before each digit-dot token specifically so
a dotted citation number like `552.003.` is never partially or wholly
consumed as marker-chain noise (see that module's own docstring, "the
`_TRAILING_MARKER_CHAIN_RE` strips a marker fragment..." bullet, which
names this exact TX row as its worked example). Re-measured directly
against this row for this re-authoring: `extract_quote_anchored_entries`
now returns `'assigned by Section 552.003.'` for "Governmental body" --
the citation tail is fully retained.

**What is NOT retained, and must not be expected to be: the idiom itself.**
The original Part B expectation (`'has the meaning assigned by Section
552.003.'`, idiom included) contradicted the engine's own universal
contract: `_TIGHT_IDIOM_RE` (this module's own idiom gate, matched
immediately after the quoted term) always consumes the idiom phrase
itself as part of finding the boundary, so `definition_text` begins AFTER
it -- confirmed independently by `test_us_markers_ext_a_ok_gapidiom.py`,
whose real-row expectation for OK's "person" begins `"any individual,"`
with `"shall mean"` already stripped, not retained. Part B is re-authored
below to pin the REAL, verified contract: citation tail preserved, idiom
stripped -- not to re-litigate whether the idiom should be stripped (that
is a separate, unraised design question, out of scope here).

**The masking finding stands, unchanged, and is still worth guarding**:
`pipeline.py`'s idempotent-by-key persistence loop enumerates
`baseline_blocks` before `extra_blocks`, and baseline ALSO produces a
(correct, untruncated, idiom-RETAINED -- baseline is a different code path
with a different contract) "Governmental body" candidate for this row --
baseline wins the collision, so today's real persisted output for THIS
specific row shows the full idiom. Confirmed live in the third test below,
unchanged by this re-authoring. In a genuine zero-baseline-candidate
rescue row (VA/WA/FED-shaped), only our engine's own output would be
persisted -- which is exactly why Part B pins our engine directly rather
than relying on the pipeline-level masking test to catch a regression.

Row vendored verbatim, byte-verified against `us_tx_statutes.parquet` this
pass.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_qa_q3_tx_2009_003_row.json"
)

ACT_ID = "STATE_TX_Cgv_C2009_S2009.003"

_DEGENERATE_TERMS = {
    "contested case": ";",
    "party": ";",
    "person": "; and",
    "rule.": "",
}


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def test_fixture_row_is_directly_definitions_headed():
    row = _load_row()
    assert row["act_id"] == ACT_ID
    assert is_definitions_heading(row["section_title"]) is True


def test_part_a_the_4_baseline_degenerate_terms_still_reproduce_on_this_build():
    """Confirms (does not yet fix -- Part A is baseline entry-boundary
    territory, markers' to eventually close per M-R5/M-R8) that the exact
    degenerate captures reported to the multiterm panel still reproduce,
    unchanged, on this build's real engine call path."""
    row = _load_row()
    from app.definition_links.us_profile import USProfile

    profile = USProfile(code="US-TX")
    scope = profile.determine_scope(row["text"])
    cands = profile.extract_definitions_from_section(row["text"], scope=scope, heading_was_derived=False)
    by_term: dict[str, list[str]] = {}
    for c in cands:
        for t in c.terms:
            by_term.setdefault(t, []).append(c.definition_text)

    for term, degenerate_text in _DEGENERATE_TERMS.items():
        assert term in by_term, f"{term!r} missing entirely -- got {sorted(by_term)!r}"
        assert degenerate_text in by_term[term], (
            f"{term!r}: expected the known degenerate capture {degenerate_text!r} to still "
            f"reproduce (confirming the residual is unchanged); got {by_term[term]!r}"
        )


def test_part_a_red_the_4_terms_should_carry_the_real_cross_reference_not_a_stub(
    db_session, matter_with_users
):
    """The Part-A RED, at the real persisted-output level: through the
    REAL pipeline, each of these 4 terms' `Definition.definition_text`
    should reference the real parent redirect ("meanings assigned by
    Section 2001.003") it is defined by -- not a bare punctuation stub."""
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="TX 2009.003 (QA1 Q3)",
        rows=[row],
        jurisdiction="US-TX",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term: dict[str, list[Definition]] = {}
    for d in definitions:
        for t in d.terms:
            by_term.setdefault(t, []).append(d)

    for term, degenerate_text in _DEGENERATE_TERMS.items():
        matches = by_term.get(term, [])
        assert matches, f"{term!r} not captured at all -- got {sorted(by_term)!r}"
        texts = [d.definition_text for d in matches]
        assert not all(t == degenerate_text for t in texts), (
            f"{term!r}: still only the degenerate stub {degenerate_text!r} is persisted "
            f"({texts!r}) -- the parent redirect clause was never attached"
        )
        assert any("2001.003" in t for t in texts), (
            f"{term!r}: no persisted Definition references the real cross-reference "
            f"'2001.003' it is actually defined by; got {texts!r}"
        )


def test_part_b_our_own_engine_preserves_citation_tail_and_strips_the_idiom():
    """Part B, re-authored per RULING U-R13 (sprint log §M22/§M23 item 2):
    the original expectation (idiom RETAINED) contradicted the engine's own
    universal idiom-stripping contract, corroborated independently by
    `test_us_markers_ext_a_ok_gapidiom.py` (real OK row, expected text
    starts `"any individual,"` with `"shall mean"` already stripped).

    This pins the REAL, currently-live contract for our own
    `extract_quote_anchored_entries`, called directly on this row's real
    body: the trailing citation number (`"552.003."`) must survive --
    `_TRAILING_MARKER_CHAIN_RE`'s `(?<![\\d.])` guard exists precisely so a
    real `"NNN.NNN."` citation is never mistaken for a marker-chain
    fragment -- and the defining idiom (`"has the meaning"`) must NOT
    survive, exactly like every other idiom-anchored capture this engine
    produces. Both halves are asserted explicitly (not just the exact
    string) so a future regression in either direction fails loudly with
    its own message rather than a bare string diff."""
    row = _load_row()
    entries = dict(extract_quote_anchored_entries(row["text"]))
    assert "Governmental body" in entries
    text = entries["Governmental body"]
    assert "552.003" in text, (
        f"the real citation tail was dropped -- regression of the original "
        f"Part-B truncation defect, now fixed: {text!r}"
    )
    assert "has the meaning" not in text, (
        f"the idiom was NOT stripped -- contradicts the engine's own universal "
        f"idiom-stripping contract (corroborated by ext_a_ok_gapidiom): {text!r}"
    )
    assert text == "assigned by Section 552.003.", f"got {text!r}"


def test_part_b_masking_confirmed_todays_real_pipeline_happens_to_be_fine_here(
    db_session, matter_with_users
):
    """NOT a RED -- a documentation/regression guard proving the masking
    mechanism claimed in this file's module docstring: on THIS row,
    baseline's own (correct) "Governmental body" candidate wins the
    persistence-layer collision against our engine's (truncated) one,
    because `pipeline.py` enumerates baseline blocks first. This passing
    today is NOT evidence Part B is safe -- see the module docstring for
    why the masking cannot be relied on in genuine zero-candidate rescue
    rows, which is this rule's entire reason to exist."""
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="TX 2009.003 masking check (QA1 Q3)",
        rows=[row],
        jurisdiction="US-TX",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term: dict[str, list[Definition]] = {}
    for d in definitions:
        for t in d.terms:
            by_term.setdefault(t, []).append(d)
    matches = by_term.get("Governmental body", [])
    assert len(matches) == 1, f"expected the collision to collapse to 1 persisted row, got {len(matches)}"
    assert matches[0].definition_text == "has the meaning assigned by Section 552.003.", (
        f"masking assumption broken -- got {matches[0].definition_text!r}. If this now fails, "
        "the masking this file relies on has changed and Part B's danger is no longer "
        "hypothetical on THIS row -- escalate immediately."
    )
