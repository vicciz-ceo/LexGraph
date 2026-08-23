"""RED + regression pin (sprint 2026-08-20-defs-boundary-idioms, pass 2
amendment, Item 3) -- the two named real-row degraded re-boundings from
investigation.md's Q3 ("the swap-hazard family"). WA "active efforts" is a
genuine RED (verified, both a direct-function replay and the real
`ingest_us_statute_rows` -> `run_definition_linking` pipeline reproduce the
displacement). NY "General service lamp" was diagnosed this pass to NOT
reproduce at persistence altitude for this specific row -- see that test's
own docstring for the mechanism (baseline's own block-splitter already
wins the persist-time dedup ahead of family-3's contribution for this
jurisdiction) -- kept below as a regression pin rather than a RED, plus
this file's own note and the Planner's completion report.

Mechanism (both rows, same shape, diagnosed this pass): `extract_quote_
anchored_entries` (`backend/app/definition_links/rules/
us_markers_boundary.py`) builds its `starts` list in TEXT ORDER with NO
per-term collision handling -- when the SAME exact term string is quoted
more than once in a single section body, each quote+idiom occurrence
becomes its OWN `starts` entry regardless of whether an earlier one
already claimed that term. Downstream, the persist-time term-set dedup
(`backend/app/definition_links/pipeline.py`, `key = (owning_art.id,
tuple(sorted(candidate.terms)))`, ~line 400) is first-occurrence-wins:
whichever candidate reaches `all_candidates` FIRST creates the `Definition`
row; every later candidate sharing that exact term-key is silently
discarded (its own `definition_text` is never used, even if the DB row is
still "resolved" against it).

Before Item 1's widening, at most ONE occurrence of a given term was ever
recognized per section (the other idiom was not yet in `_TIGHT_IDIOM_RE`),
so this collision never manifested. After the widening, a NEW occurrence
recognized ONLY by the widened idiom (`shall include` / `has the
(following|same) meaning`) can now collide with a PRE-EXISTING occurrence
recognized by the ORIGINAL idiom set (`means` / `shall mean` / bare `has
the meaning`) -- and when the NEW occurrence happens to sit textually
BEFORE the pre-existing one (verified true in every sampled instance:
this WA row, this NY row, and FED "correct" row 42191), first-occurrence-
wins picks the wrong, often partial/mis-scoped capture, displacing the
previously-correct one entirely.

Item 3's spec'd fix (Developer implements; see the sprint contract's Item
3 Next Steps entry): inside `extract_quote_anchored_entries`, after the
`starts` list is fully built (before `compute_hard_stops`/`close_entries`),
group by exact `term` string; for any term with 2+ occurrences where at
least one is recognized by the ORIGINAL (pre-Item-1) idiom set, drop every
occurrence recognized ONLY by the widened idiom for that term (the
pre-existing occurrence(s) survive, in original relative order); terms
whose occurrences are ALL widened-idiom-only are left untouched (the
already-validated-genuine addition population, Q2 in investigation.md, is
unaffected by construction -- a term with only one recognized occurrence
never collides).

Byte-verified against the real corpus this pass (`vaquill/open-us-law`);
fixtures vendored verbatim."""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load_row(fname: str) -> dict:
    rows = json.loads((FIXTURES / fname).read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def _run(db_session, matter_with_users, row: dict, jurisdiction: str) -> dict[str, list]:
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title=f"{row['act_id']} dedup swap-hazard recovery (Item 3)",
        rows=[row],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term: dict[str, list] = {}
    for d in definitions:
        for t in d.terms:
            by_term.setdefault(t, []).append(d)
    return by_term


WA_EXPECTED_TEXT = (
    "a documented, concerted, and good faith effort to facilitate the "
    "parent's or Indian custodian's receipt of and engagement in services "
    "capable of meeting the criteria set out in (a) of this subsection."
)
WA_DISPLACING_PREFIX = "(i) In any dependency proceeding under chapter 13.34 RCW"


def test_red_wa_active_efforts_recovers_the_complete_branch_b_definition(
    db_session, matter_with_users
):
    """`STATE_WA_T13_C38_S040` (WA row 148, "active efforts"). Today, the
    displacing candidate wins the dedup: a partial continuation of branch
    (a)'s own "shall include" enumeration (an idiom-inside-body match, NOT
    a genuine second top-level definition), 1,901 chars, swallowing the
    entire (i)-(iv) list. The correct, complete, self-contained branch (b)
    definition (200 chars, recognized via "means" -- unaffected by Item
    1's widening) is silently displaced entirely. Item 3 must restore it."""
    row = _load_row("us_markers_dedup_wa_active_efforts_row.json")
    by_term = _run(db_session, matter_with_users, row, "US-WA")

    assert "active efforts" in by_term, f"sanity: term must be captured at all -- got {sorted(by_term)!r}"
    texts = [d.definition_text.strip() for d in by_term["active efforts"]]

    assert WA_EXPECTED_TEXT in texts, (
        f"RED: the complete, correct branch (b) definition is not persisted -- "
        f"'active efforts' must resolve to it, not the displacing partial "
        f"continuation. Got: {texts!r}"
    )
    displacing = [t for t in texts if t.startswith(WA_DISPLACING_PREFIX)]
    assert not displacing, (
        f"the displacing partial continuation (branch (a)'s own 'shall "
        f"include' enumeration, not a genuine second definition of 'active "
        f"efforts') must not win the persisted slot: {displacing!r}"
    )


NY_EXPECTED_PREFIX = (
    "means a lamp that has an ANSI base, is able\nto operate at a voltage of "
    "twelve volts or twenty-four volts"
)
NY_CORRUPTING_TEXT = "the following definitions:"


def test_ny_general_service_lamp_already_resolves_correctly_today_and_must_stay_that_way(
    db_session, matter_with_users
):
    """`STATE_NY_AENG_A16_S16-102` (NY row 6675, "General service lamp").

    investigation.md's Q3 names this row as the sprint's "1 outright
    corruption" (item 44's own "shall include" match displacing the real
    'means' definition). Diagnosed this pass: at REAL PERSISTENCE
    altitude, this specific row does NOT reproduce that corruption, and
    this is verified two independent ways (a direct
    `extract_definitions_from_section` call, and the full `ingest_us_
    statute_rows` -> `run_definition_linking` pipeline below) -- baseline's
    own `_split_into_numbered_blocks`/`_leading_quote_candidate` ALREADY
    finds sub-item (c)'s clean "means" candidate as its own block (NY has
    38 baseline blocks, so `all_blocks = baseline_blocks + priority_blocks
    + extra_blocks` puts baseline FIRST), and NY carries no
    `priority_before_single_baseline=True` registration (only US-WA,
    `us_markers_inline_quote.py`, and US-FED, `us_markers_fed_good_
    samaritan.py`, do) -- so the family-3 engine's own colliding
    candidates (both the bad 'shall include' one and the good 'means' one)
    are appended AFTER baseline's, and pipeline.py's first-occurrence-wins
    persist-time dedup picks baseline's already-correct entry both before
    AND after Item 1's widening (family-3's *additional* bad candidate
    only ever gets appended, never displaces the existing key). This is
    NOT the "displacement family" mechanism (that requires a jurisdiction
    where family-3 wins ordering ahead of baseline -- see the WA test
    above); it is a DIFFERENT, currently-safe shape for this one row.

    Kept as a regression pin, not a RED test, because it is currently
    GREEN: Item 3's engine-level fix (pruning a colliding new-idiom-only
    occurrence from family-3's OWN output when an old-idiom occurrence
    exists for the same term) makes family-3's own contribution for this
    row consistent with baseline's pick too (it would no longer offer the
    bad candidate at all) -- a strict improvement, not a behavior change
    for what gets PERSISTED. Also exercises the raw-vs-ingest `\\n`
    unescape trap (NY parquet text is escaped-\\n by design)."""
    row = _load_row("us_markers_dedup_ny_general_service_lamp_row.json")
    by_term = _run(db_session, matter_with_users, row, "US-NY")

    assert "General service lamp" in by_term, (
        f"sanity: term must be captured at all -- got {sorted(by_term)!r}"
    )
    texts = [d.definition_text for d in by_term["General service lamp"]]

    assert any(t.startswith(NY_EXPECTED_PREFIX) for t in texts), (
        f"'General service lamp' must resolve to the real, substantive "
        f"lighting-code definition (baseline's own capture) both today and "
        f"after Item 3's fix lands. Got: {[t[:120] for t in texts]!r}"
    )
    corrupting = [t for t in texts if t.strip() == NY_CORRUPTING_TEXT]
    assert not corrupting, (
        f"the bare list-introducer ('the following definitions:', not a "
        f"definition at all) must never win the persisted slot: {corrupting!r}"
    )
