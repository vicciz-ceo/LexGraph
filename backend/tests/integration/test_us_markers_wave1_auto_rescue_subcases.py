"""RED integration tests -- sprint 2026-08-04-defs-us-markers, planner
pass 2, priority 2.

Pass 1's log claimed wave 1's mechanism (removing the
`used_body_derived_heading` gate in front of `_extract_inline_quoted_
definitions`, pipeline.py:246-289/405-432) also AUTO-RESCUES three
sub-cases as a side effect, with no separate implementation: UT's nested
lettered sub-clauses, TX's ALL-CAPS singular "DEFINITION." heading, and
most of AZ's bare digit-dot markers. That claim was recorded in prose
only -- "the agent said so" is not evidence (this pass's brief). These
tests exercise the REAL production call path end-to-end (`ingest_us_
statute_rows` -> `run_definition_linking`, imported unmodified, same as
wave 1's own tests) so QA can verify the claim rather than take it: they
are RED now (today's pipeline creates 0 definitions for all three rows,
same gate blocks them as VA/WA/FED), and are EXPECTED to turn green
automatically once wave 1's fix lands -- with no test edits -- if and
only if the claim holds.

Per ruling U-R1 ("captured" means captured CLEANLY) and this pass's
brief ("assert the terms AND clean boundaries ... not merely
`len(...) > 0`"), each test also checks boundary quality. Doing so this
pass found the claim needed CORRECTION for two of the three rows -- not
rejected, but not the free ride pass 1 reported either:

- **UT** (`STATE_UT_T75B_S75B_1_301`): calling the CURRENT, unmodified
  `_extract_inline_quoted_definitions` directly (the same live-path
  reproduction method pass 1 used, and the manager independently
  verified, for VA/WA/FED) shows "Insolvent"'s captured definition_text
  SWALLOWS the two following entries whole -- "Paid and delivered" and
  "Personal property" both use "does not include"/"includes" idioms, not
  "means"/"shall mean"/"has the meaning", so `_MEANS_IDIOM_GAP_RE` never
  recognizes them as an entry boundary and they get appended to
  "Insolvent"'s definition instead (599 chars, ends mid-marker at "...
  (7)"). Same DEFECT CLASS as VA's "sell" collapse / FED's editorial-notes
  swallow (pass 1's own log), just not caught for UT specifically because
  pass 1 measured only whether candidates come back, not their boundary
  quality, on this row.
- **AZ** (`STATE_AZ_T15_C14_A7_S1871`): same direct reproduction shows
  "Qualified higher education expenses"'s captured definition_text ends
  `"...pursuant to section 529 of the internal revenue code.\\n\\n13."`
  -- it swallows the NEXT entry's bare `"13."` digit-dot marker (AZ's own
  convention, `_MARKER_TOKEN_RE`/quote-boundary logic finds the entry
  boundary at the quote, not before the preceding marker token). This is
  the SAME defect class the contract already names for SC ("the literal
  `"(2)"` fragment leaking into the prior entry") -- proving AZ needs
  wave 3's marker-splitter fix too, not just for its no-quote minority as
  pass 1's wave plan assumed, but for a subset of its "auto-rescued"
  dominant shape as well.
- **TX** (`STATE_TX_Cfi_C37_S37.001`): confirmed genuinely clean --
  1 term, the entire body IS this one definition (same shape as pass 1's
  own PA row), no boundary to get wrong.

`DEGENERATE_THRESHOLD` matches wave 1's own fixture file's justification
(10 chars) for consistency.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_wave2_subcases_rows.json"
)

DEGENERATE_THRESHOLD = 10  # chars; see wave1 fixture's own docstring for justification

_TRAILING_MARKER_LEAK_RE = re.compile(r"\d{1,3}\.\s*$")


def _load_rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def _ingest_and_link(
    db_session, matter, *, jurisdiction: str, title: str, row: dict
) -> list[Definition]:
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=title,
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    return [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]


def test_all_three_subcase_fixture_headings_are_recognized_as_definitions_sections():
    """Sanity, mirroring wave 1's own sanity test: the miss is purely in
    extraction, not heading detection, for all three rows."""
    rows = _load_rows()
    for act_id in (
        "STATE_UT_T75B_S75B_1_301",
        "STATE_TX_Cfi_C37_S37.001",
        "STATE_AZ_T15_C14_A7_S1871",
    ):
        heading = rows[act_id]["section_title"]
        assert is_definitions_heading(heading) is True, (
            f"{act_id}: {heading!r} must already be recognized as a Definitions heading"
        )


def test_real_pipeline_recovers_ut_nested_subclause_definitions_without_swallowing_the_next_two_entries(
    db_session, matter_with_users
):
    """`STATE_UT_T75B_S75B_1_301` -- real Utah asset-protection-trust
    Definitions section using nested lettered sub-clauses under each
    numbered entry ((1) "Term" means: (a) ...; (b) ...). Today's real
    pipeline creates 0 definitions here (same gate as VA/WA/FED). Once
    rescued, the 5 terms using the "means" idiom must be captured, AND
    "Insolvent" must NOT swallow the two following non-"means"-idiom
    entries ("Paid and delivered", "Personal property") whole -- see this
    file's module docstring for the confirmed live defect."""
    rows = _load_rows()
    row = rows["STATE_UT_T75B_S75B_1_301"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-UT", title="UT wave1 auto-rescue", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    assert set(by_term) == {
        "Asset protection trust",
        "Creditor",
        "Domestic support obligation",
        "Insolvent",
        "Transfer",
    }, (
        f"expected the 5 real 'means'-idiom UT terms, got {sorted(by_term)!r} -- "
        '"Paid and delivered"/"Personal property" use non-"means" idioms and are '
        "correctly NOT expected here (they need wave 2's idiom broadening, a "
        "separate, not-yet-implemented item)"
    )

    for term, d in by_term.items():
        assert len(d.definition_text) >= DEGENERATE_THRESHOLD, (
            f"{term!r} definition_text is only {len(d.definition_text)} chars: "
            f"{d.definition_text!r}"
        )

    insolvent = by_term["Insolvent"]
    for forbidden in ("Paid and delivered", "Personal property"):
        assert forbidden not in insolvent.definition_text, (
            f'"Insolvent"\'s definition_text illegally contains {forbidden!r} -- it '
            f"swallowed the next entry (its idiom, \"does not include\"/\"includes\", "
            f"isn't yet recognized as a boundary) ({len(insolvent.definition_text)} "
            f"chars total): {insolvent.definition_text!r}"
        )
    assert len(insolvent.definition_text) < 260, (
        f'"Insolvent"\'s real definition is one clause ending "...federal bankruptcy '
        f'law." (~240 chars); got {len(insolvent.definition_text)} chars, so it '
        "swallowed at least part of the next entries"
    )


def test_real_pipeline_recovers_tx_allcaps_singular_definition_cleanly(
    db_session, matter_with_users
):
    """`STATE_TX_Cfi_C37_S37.001` (`§ 37.001. DEFINITION.`) -- real Texas
    banking-code section, ALL-CAPS singular "DEFINITION." heading, ONE
    inline-quoted term ("emergency") whose definition is the section's
    entire remaining body (738 chars, a numbered list of qualifying
    events (1)-(7), all part of this single definition -- same shape as
    pass 1's own clean PA row). Today's real pipeline creates 0
    definitions here."""
    rows = _load_rows()
    row = rows["STATE_TX_Cfi_C37_S37.001"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-TX", title="TX wave1 auto-rescue", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    assert set(by_term) == {"emergency"}, f"got {sorted(by_term)!r}"

    emergency = by_term["emergency"]
    assert 600 < len(emergency.definition_text) < 800, (
        f'"emergency"\'s real definition is ~738 chars (the whole numbered list '
        f"(1)-(7) of qualifying events); got {len(emergency.definition_text)} chars"
    )
    assert "riot, civil commotion" in emergency.definition_text, (
        "definition must include entry (7), the list's real last item -- a "
        "truncated capture would cut this off"
    )


def test_real_pipeline_recovers_az_bare_digit_dot_definitions_without_leaking_the_next_markers(
    db_session, matter_with_users
):
    """`STATE_AZ_T15_C14_A7_S1871` -- real Arizona 529-plan Definitions
    section, 17 terms marked by bare `"N."` digit-dot markers (not
    `"(N)"`) immediately before each quoted term. Today's real pipeline
    creates 0 definitions here. Once rescued, all 17 terms must be
    captured, none degenerate, AND -- the corrected part of pass 1's
    "auto-rescued...clean" claim -- no entry may swallow the NEXT entry's
    bare digit-dot marker into its own definition_text (confirmed live:
    "Qualified higher education expenses" naively ends
    "...internal revenue code.\\n\\n13." -- the literal next marker,
    same defect CLASS the contract already names for SC's "(2)" leak)."""
    rows = _load_rows()
    row = rows["STATE_AZ_T15_C14_A7_S1871"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-AZ", title="AZ wave1 auto-rescue", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    expected_terms = {
        "Account",
        "Account owner",
        "Board",
        "Designated beneficiary",
        "Eligible educational institution",
        "Financial institution",
        "Fund",
        "Member of the family",
        "Nonqualified withdrawal",
        "Person",
        "Plan",
        "Qualified higher education expenses",
        "Qualified withdrawal",
        "Section 529 of the internal revenue code",
        "Treasurer",
        "Trust interest",
        "Tuition savings agreement",
    }
    assert set(by_term) == expected_terms, (
        f"expected all 17 real AZ terms, missing={expected_terms - set(by_term)!r}, "
        f"unexpected={set(by_term) - expected_terms!r}"
    )

    for term, d in by_term.items():
        assert len(d.definition_text) >= DEGENERATE_THRESHOLD, (
            f"{term!r} definition_text is only {len(d.definition_text)} chars"
        )
        assert not _TRAILING_MARKER_LEAK_RE.search(d.definition_text), (
            f"{term!r}'s definition_text illegally ends with a leaked next-entry "
            f"marker (a bare 1-3 digit number plus period): "
            f"{d.definition_text[-40:]!r}"
        )

    qhee = by_term["Qualified higher education expenses"]
    assert qhee.definition_text.rstrip().endswith("internal revenue code."), (
        f'"Qualified higher education expenses" must end at its own real sentence '
        f"boundary, not swallow the next entry's marker: "
        f"{qhee.definition_text[-60:]!r}"
    )
