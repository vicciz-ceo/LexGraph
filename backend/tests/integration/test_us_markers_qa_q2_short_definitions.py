"""QA1 (phase-2 QA cycle 1) -- Q2: the <10-char definitions (VA 1, WA 5,
AL 7) (sprint 2026-08-04-defs-us-markers, gate U1, ruling U-R1).

**Classification, all 13 rows inspected against their real body context:**

- **VA 1/1 genuine.** `STATE_VA_T64.2_SV_C27_A1_S64.2-2700` "Instrument" =
  "a record." -- real, clean, correctly bounded (the next term
  "Nongeneral power of appointment" begins immediately after).
- **WA 5/5 genuine.** "Sex" = "gender." (x2, same real sentence in two
  parallel titles), "Comestible" = "edible.", "Cancel or cancellation" =
  "to void.", "Instrument" = "a record." -- all real dictionary-terse
  statutory definitions, all correctly bounded at the next `(N)`/quoted
  term, verified against the raw body.
- **AL 1/7 genuine, 6/7 DEGENERATE (U-R1 violation).**
  `STATE_AL_T45_C37A_S45-37A-51.120` "EMPLOYER" = "The city." is genuine
  (a real municipal-pension-plan shorthand). The other 6 -- "Acquire"
  (`5-13B-2`), "Bank holding company" (`5-13B-2`, def_text literally `":"`,
  1 char), "Out-of-state bank holding company" (`5-13B-2`), "Bank
  supervisory agency" (`5-13B-21`), "Home state" (`5-13B-21`), "Interstate
  merger transaction" (`5-13B-21`) -- are ALL degenerate: their real bodies
  each read `(x) "Term" means:` (or, for "Bank holding company", just
  `"Term":` with no "means" at all) followed by a NESTED numbered `(1) ...;
  (2) ...; and (3) ...` list that IS the definition's own content, e.g.
  `(a) "Acquire" means:\\n\\n(1) For a company to merge or consolidate with
  a bank holding company;\\n\\n(2) For a company to assume ...`. What gets
  persisted is only the colon/"means:" fragment before the nested list --
  the entire substantive content is silently dropped.

**Root cause, diagnosed:** `us_profile.py`'s baseline `_split_into_
numbered_blocks`/`_entry_start_remainder` treats EVERY bare `"(N)"` at the
start of a line as an unconditional block boundary (see that module's own
comment: "a bare digit marker is ADDITIONALLY always treated as an entry
boundary even with no quote immediately after it"). That rule exists to
close out non-defining interleaved paragraphs between two real lettered
entries, but it has no LIST-INTRODUCER exception the way this sprint's own
`us_markers_boundary.py` engine does (a marker is never a hard-stop when
what precedes it, skipping whitespace, ends in `:`/`—`): baseline
therefore misreads a defining entry's OWN nested numbered sub-list as a
sibling top-level entry, closing "Acquire"'s block one token after "means:"
and stranding the entire (1)/(2)/(3) list as orphaned blocks with no
leading quote of their own (verified: `_LEADING_QUOTE_RE.match` fails on
each of them, so they are silently skipped, not just misattributed).

**Not rescuable by any family-3 rule this sprint owns**: AL is registered
only for `us_markers_unquoted_terms.py`'s `_split_al`, which matches
ALL-CAPS unquoted terms (`(N) ORGAN. Definition...`) -- these 6 rows use
QUOTED, mixed-case terms (`"Acquire"`, `"Bank holding company"`), a
completely different shape `_AL_ENTRY_RE` cannot and should not match. No
registered `EntrySplitterRule` for `US-AL` covers this shape at all, so
there is no "our clean candidate loses a collision" story here (unlike
Q1) -- this is a pure baseline miss on an otherwise-successful heading. As
a data point for the manager (NOT a claim, NOT wired into production): the
existing `us_markers_boundary.extract_quote_anchored_entries` engine (list-
introducer-aware, already used by VA/WA/FED/UT/TX/SC/AZ) DOES parse these
2 rows correctly when called directly and would need `US-AL` added to
`us_markers_inline_quote.py`'s `_JURISDICTIONS` to fire live -- an
ownership/scope question for the manager, not something this QA pass
implements.

Root cause lives in `us_profile.py` (shared, not markers' to touch). Pinned
per QA's mandate to pin every degenerate capture regardless of fix
ownership. All 9 real rows vendored verbatim, byte-verified against
`us_al_statutes.parquet`/`us_va_statutes.parquet`/`us_wa_statutes.parquet`
this pass.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_qa_q2_short_definitions_rows.json"
)

# Genuine short definitions -- real, clean, correctly bounded. Regression
# guard only (not REDs): pins the classification so a future change cannot
# silently "fix" these by inflating them, or break them outright.
_GENUINE = [
    ("STATE_VA_T64.2_SV_C27_A1_S64.2-2700", "US-VA", "Instrument", "a record."),
    ("STATE_WA_T19_C60_S040", "US-WA", "Sex", "gender."),
    ("STATE_WA_T49_C60_S040", "US-WA", "Sex", "gender."),
    ("STATE_WA_T70A_C405_S010", "US-WA", "Comestible", "edible."),
    ("STATE_WA_T43_C08_S005", "US-WA", "Cancel or cancellation", "to void."),
    ("STATE_WA_T11_C95A_S010", "US-WA", "Instrument", "a record."),
    ("STATE_AL_T45_C37A_S45-37A-51.120", "US-AL", "EMPLOYER", "The city."),
]

# Degenerate captures -- U-R1 violations. (act_id, jurisdiction, term,
# forbidden exact degenerate text, a real substring that PROVES the true
# nested-list content exists in the row but was dropped).
_DEGENERATE = [
    (
        "STATE_AL_T5_C13B_S5-13B-2",
        "US-AL",
        "Acquire",
        "means:",
        "For a company to merge or consolidate with a bank holding company",
    ),
    (
        "STATE_AL_T5_C13B_S5-13B-2",
        "US-AL",
        "Bank holding company",
        ":",
        "Has the meaning set forth in Section 2(a) of the Bank Holding Company Act",
    ),
    (
        "STATE_AL_T5_C13B_S5-13B-2",
        "US-AL",
        "Out-of-state bank holding company",
        "means:",
        "A bank holding company that is not an Alabama bank holding company",
    ),
    (
        "STATE_AL_T5_C13B_S5-13B-21",
        "US-AL",
        "Bank supervisory agency",
        "means:",
        "The Office of the Comptroller of the Currency",
    ),
    (
        "STATE_AL_T5_C13B_S5-13B-21",
        "US-AL",
        "Home state",
        "means:",
        "With respect to a national bank, the state in which the main office",
    ),
    (
        "STATE_AL_T5_C13B_S5-13B-21",
        "US-AL",
        "Interstate merger transaction",
        "means:",
        "The merger or consolidation of banks with different home states",
    ),
]


def _load_rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def _ingest_and_link(db_session, matter, *, jurisdiction: str, row: dict) -> list[Definition]:
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=f"QA1 Q2 short-def probe ({row['act_id']})",
        rows=[row],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    return [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]


def test_genuine_short_definitions_stay_captured_correctly(db_session, matter_with_users):
    """Regression guard (not a RED): the 7 genuine short definitions must
    keep capturing with their real, terse, correct text."""
    rows = _load_rows()
    for act_id, jurisdiction, term, expected_text in _GENUINE:
        definitions = _ingest_and_link(
            db_session, matter_with_users, jurisdiction=jurisdiction, row=rows[act_id]
        )
        by_term = {t: d for d in definitions for t in d.terms}
        assert term in by_term, f"{act_id}: {term!r} not captured -- got {sorted(by_term)!r}"
        assert by_term[term].definition_text == expected_text, (
            f"{act_id}: {term!r} expected {expected_text!r}, got "
            f"{by_term[term].definition_text!r}"
        )


def test_al_nested_numbered_list_definitions_are_not_truncated_to_the_colon(
    db_session, matter_with_users
):
    """The load-bearing RED: 6 real AL definitions whose own content is a
    nested `(1)/(2)/(3)` list must not be silently truncated to a bare
    `"means:"`/`":"` fragment -- the persisted definition_text must at
    least contain the real first list-item content, proving the nested
    list survived extraction."""
    rows = _load_rows()
    for act_id, jurisdiction, term, degenerate_text, real_content_substring in _DEGENERATE:
        definitions = _ingest_and_link(
            db_session, matter_with_users, jurisdiction=jurisdiction, row=rows[act_id]
        )
        by_term = {t: d for d in definitions for t in d.terms}
        assert term in by_term, f"{act_id}: {term!r} not captured at all -- got {sorted(by_term)!r}"
        dtext = by_term[term].definition_text
        assert dtext != degenerate_text, (
            f"{act_id}: {term!r} is still truncated to the bare fragment {degenerate_text!r} -- "
            "the nested numbered list that IS this term's real definition was dropped"
        )
        assert real_content_substring in dtext, (
            f"{act_id}: {term!r}'s persisted definition_text does not contain the real "
            f"nested-list content {real_content_substring!r}; got {dtext!r}"
        )
