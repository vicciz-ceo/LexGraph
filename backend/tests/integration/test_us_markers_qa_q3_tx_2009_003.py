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

**Part B -- a genuinely NEW finding, not previously named anywhere in this
sprint's log: OUR OWN `us_markers_boundary.py` engine has a real, live
truncation bug on this SAME row**, unrelated to the 4 degenerate terms
above. `"Governmental body" has the meaning assigned by Section 552.003.`
-- our engine (`extract_quote_anchored_entries`, called directly) captures
this as `'assigned by Section'`, silently dropping `' 552.003.'`.

Root cause: `_TRAILING_MARKER_CHAIN_RE = re.compile(r"(?:\\s*(?:\\([\\w]{1,4}\\)|
\\d{1,3}\\.)\\s*)+$")` is meant to strip a NEXT ENTRY's leaked marker
fragment off the end of a captured definition (its own docstring's
examples: SC's "Municipality" ending in a literal `"(2)"`; AZ's "Qualified
higher education expenses" ending in a literal `"13."`). But a real
statutory citation of the shape `"NNN.NNN."` (e.g. "552.003.") is
INDISTINGUISHABLE to this regex from two back-to-back digit-dot marker
tokens ("552." then "003."), so the whole citation gets stripped as if it
were marker-chain noise, together with the space before it.

**This defect is currently MASKED on this exact row, not absent**:
`pipeline.py`'s idempotent-by-key persistence loop (see this pass's Q1
finding) enumerates `baseline_blocks` before `extra_blocks`, and baseline
ALSO produces a (correct, untruncated) "Governmental body" candidate for
this row -- baseline wins the collision, so today's real persisted output
for THIS specific row is accidentally fine. Confirmed live in the third
test below. **This is exactly backwards from a safety net**: this
sprint's own rule module exists precisely to cover jurisdictions/rows
where baseline yields ZERO candidates (VA 97.2%, WA 98.8%, FED 83.3%
zero-candidate today) -- in every one of those genuine rescue rows there
is no baseline candidate to mask this bug behind. Any real VA/WA/FED/UT/
TX/SC/AZ row whose definition legitimately ends in a citation shaped
`NNN.NNN.` and has NO baseline candidate for the same term would silently
lose that citation today. Pinned at the engine level (the level where it
is genuinely unmasked) and flagged to the manager as a new defect in
shipped family-3 code, not a baseline/pipeline issue like Q1/Q2.

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


def test_part_b_red_our_own_engine_truncates_governmental_body_citation_tail():
    """The Part-B RED (NEW finding, engine-level): our own
    `extract_quote_anchored_entries`, called directly on this row's real
    body, must not drop the trailing citation number from "Governmental
    body"'s real definition. Currently truncates to `'assigned by
    Section'`, losing `' 552.003.'` -- `_TRAILING_MARKER_CHAIN_RE`
    mis-reads a real `"NNN.NNN."` citation as a marker-chain fragment."""
    row = _load_row()
    entries = dict(extract_quote_anchored_entries(row["text"]))
    assert "Governmental body" in entries
    assert entries["Governmental body"] == "has the meaning assigned by Section 552.003.", (
        f"our own engine's candidate for 'Governmental body' is truncated: "
        f"{entries['Governmental body']!r}"
    )


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
