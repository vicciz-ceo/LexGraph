"""Sprint 2026-08-04-defs-us-scoped-inline (Planner, D5, target 1: pure rule
module). RED today with `ModuleNotFoundError` -- see
`test_us_scoped_inline_rules_trigger_axis.py`'s module docstring for the
full public-API contract this sprint pins.

This file: the ZERO-FALSE-POSITIVE half of the U4/U5 zero-miss-vs-precision
tension (P-R2). The director's absolute zero-miss bar creates real
precision pressure -- these tests are the counterweight, pinning that the
new rule module stays quiet on real corpus text that merely LOOKS like
family 1 but is not:

1. A scope-trigger phrase followed by an UNQUOTED cross-reference
   ("...is the same as defined in Section N") -- no quoted term, no
   recognized defining idiom.
2. Bare "in this <unit>" used as ordinary prose, nowhere near a definition
   (measured: 72.7% of all bare-`in`-trigger hits across the 12 lead
   states are exactly this shape -- see the sprint log's D1/D2 sections).
3. Real baseline-state (U5 regression set) rows with NO family-1 trigger
   at all -- the new rule module must never manufacture a candidate out of
   ordinary substantive statute text just because SOME word combination
   resembles a trigger.
4. The genuinely ambiguous PA "References to X shall include Y" shape,
   which the Planner excludes from this sprint's positive scope by
   design (a construction/interpretation clause about how OTHER text
   should be read, not a `"X" means Y`-shaped definition) -- escalated to
   the manager in the sprint log's D2 section, not silently decided.

Planner pass 6 addition (Task 2): QA cycle 1's mutation testing found that
2 of the tests above (the bare-`in` mid-sentence-prose test and the PA
construction-clause test) survive the EXACT mutation each claims to guard
against, because a REDUNDANT downstream check masks the real mechanism --
"green for the wrong reason" (see the panel log's QA cycle-1 "Mutation
rigor" section). The two `..._gate_isolat*` tests below are NEW, narrower
probes, each constructed (and mutation-verified on a disposable scratch
copy outside this worktree, never `backend/app/`) to isolate ONLY the one
mechanism it names, so a regression in THAT mechanism specifically fails
THAT test, not by accident of a coincidental downstream save.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_scoped_inline_rows.json"
)

GATE_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "planner_pass6_gate_isolation_rows.json"
)


def _rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))}


def _gate_rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(GATE_FIXTURE.read_text(encoding="utf-8"))}


# --- unquoted cross-reference bait ------------------------------------------


def test_unquoted_cross_reference_yields_nothing():
    """`STATE_UT_T10_S10_21_302`: `"For purposes of this section, a
    manufactured home is the same as defined in Section 15A-1-302..."`
    -- the term is never quoted and the idiom is "is the same as defined
    in", not one of the recognized defining idioms (`means`/`shall
    mean`/`is defined as`/`has the meaning`/`includes`)."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_UT_T10_S10_21_302"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert candidates == []


# --- bare "in this <unit>" as ordinary prose --------------------------------


def test_bare_in_this_section_mid_sentence_prose_yields_nothing():
    """`STATE_UT_T11_S11_59_603`: `"Nothing in this section may be
    construed to relieve a purchaser..."` -- "in this section" here is
    ordinary cross-referencing prose, not a definitions trigger: there is
    no quote and no defining idiom anywhere nearby. This is the exact
    shape the trigger-axis file's module docstring measured as 72.7% of
    all bare-`in`-trigger hits across the 12 lead states."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_UT_T11_S11_59_603"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert candidates == []


# --- baseline-state (U5 regression set) rows with zero trigger -------------


def test_baseline_montana_row_with_no_trigger_yields_nothing():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_MT_T76_C13_P1_S76-13-107"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert candidates == []


def test_baseline_indiana_row_with_no_trigger_yields_nothing():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_IN_T13_A23_C12_S13-23-12-3"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert candidates == []


def test_baseline_new_york_row_with_no_trigger_yields_nothing():
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_NY_ATAX_A9_S197-D"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert candidates == []


# --- escalation-flagged boundary case: excluded from v1 by design ----------


def test_references_to_term_shall_include_is_excluded_by_design():
    """`STATE_PA_T15_C57_S5749`: `"For the purposes of this
    subchapter: (1) References to \\"other enterprises\\" shall
    include employee benefit plans..."` -- grammatically this is a
    RULE about how the phrase "other enterprises" should be READ
    elsewhere in the subchapter (a construction/interpretation clause),
    not a definition that introduces "other enterprises" as a term with a
    meaning ("X" means Y). The Planner's lean is to exclude this shape
    from v1 (real ambiguity, escalated to the manager rather than silently
    decided either way -- see the sprint log's D2 section). This test pins
    that lean as the CURRENT design decision; if the manager overrules it,
    this is the one test to update.

    CORRECTED (Planner pass 6, QA cycle-1 mutation finding): this
    docstring used to credit `_MARKER_QUOTE_RE`'s marker-immediately-
    followed-by-quote rule for keeping this row silent. QA's mutation
    testing disproved that: widening that regex's marker-to-quote gap
    from immediate to <=20 chars still leaves this test green, because
    `_multi_entries` never even reaches a marker-adjacency decision here
    that matters -- `(1)` is followed by `References to ` (14 chars, well
    inside a widened <=20-char gap) then the quote, so under the widened
    mutation `_MARKER_QUOTE_RE` WOULD now match and `_split_idiom` WOULD
    be tried -- but it fails there instead, because "shall include" is not
    in `_IDIOM_RE`'s recognized vocabulary (only "shall mean"/"shall be
    construed to mean" match a "shall ..." idiom) and there's no comma
    right after the quote either. The REAL mechanism protecting this row
    is the idiom-vocabulary gate, not marker adjacency -- independently
    reconfirmed on this worktree's own scratch-copy mutation (see this
    sprint's Planner pass 6 report). `test_marker_quote_adjacency_gate_
    is_load_bearing_alabama` below isolates the marker-adjacency
    mechanism this docstring used to (wrongly) credit to this test."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_PA_T15_C57_S5749"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "other enterprises" not in terms
    assert "serving at the request of the corporation" not in terms


# --- Planner pass 6 (Task 2): isolating two gates QA found "green for the
# wrong reason" -- each mutation-verified on a disposable scratch copy
# outside this worktree, `backend/app/` never touched -----------------------


def test_bare_in_strict_comma_or_colon_adjacency_gate_is_load_bearing():
    """SYNTHETIC probe (labelled, not corpus text): `'Nothing in this
    section "widget" means anything special under this chapter.'` --
    isolates `_leading_events`' bare-`in` strict adjacency gate (`_BARE_
    CONNECTOR_RE`'s comma-or-colon requirement immediately after a bare
    `in this <unit>` match) from the DOWNSTREAM quote-match requirement
    that would otherwise redundantly protect any row whose quote is not
    ALSO immediately adjacent to the trigger.

    Why synthetic, not corpus: this needs a bare `in this <unit>` trigger
    immediately (whitespace-only, no comma) followed by BOTH a quote AND a
    recognized idiom, on text that is NOT a genuine definition. A full
    53-jurisdiction corpus search (this sprint's scratchpad,
    `si_cycle2_plan6_search_bare_in_v3.py`) for exactly this shape (995
    rows where a bare-`in` trigger is followed within 2 characters by a
    quote, with no comma/colon) found it is essentially self-contradictory
    in real statute prose: every close, real hit found either (a) genuinely
    IS a definition (e.g. real Alabama `STATE_AL_T3_C81_S11-81-50`: `"In
    this article "municipality" means and includes any city or town..."`
    -- one of the design's own accepted ~21% "genuine bare-in" cases, not
    bait) or (b) is protected redundantly downstream (filler text between
    the trigger and the quote means `_single_entry`'s own immediate-quote
    requirement already blocks it, mutation or not -- e.g. `"...is
    referred to in this article as "the corporation.""` has 3 non-
    whitespace chars, "as ", before its quote). No real row combines
    "definitely bait" with "quote and idiom immediately adjacent, no
    comma" -- exactly why QA reached for a synthetic probe first (panel
    log, QA cycle-1 Mutation-rigor section) rather than a committed test;
    this commits that same probe, mutation-verified on THIS worktree's own
    scratch copy: removing the `if not conn or not (conn.group("colon") or
    conn.group("comma")): continue` check in `_leading_events`' bare-`in`
    loop turns this exact probe into a false positive (`"widget"` becomes
    a captured term); with the gate intact (today's real code), it stays
    silent."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    probe = 'Nothing in this section "widget" means anything special under this chapter.'
    candidates = extract_us_scoped_inline_definitions(probe)
    assert candidates == [], (
        "the bare-`in` strict comma/colon adjacency gate should have kept this "
        f"synthetic false-positive bait silent -- got {candidates!r}"
    )


def test_marker_quote_adjacency_gate_is_load_bearing_alabama():
    """`STATE_AL_T13A_C11_S13A-11-1` (real, unmodified corpus row,
    `planner_pass6_gate_isolation_rows.json`): `"The following
    definitions apply in this article:\\n\\n(1) OBSTRUCT. To "obstruct"
    means to render impassable... (2) PUBLIC PLACE. A place to which...
    (3) TRANSPORTATION FACILITY. Any conveyance..."` -- a genuine bare
    `in this article:` trigger (colon-adjacent, passes the OTHER gate
    tested above) routes to `_multi_entries`, but marker `(1)` is followed
    by `OBSTRUCT. To ` (14 non-whitespace chars -- a real, common
    ALL-CAPS-label-then-prose convention) before the quoted term
    `"obstruct"`, not immediately. `_MARKER_QUOTE_RE`'s whitespace-only gap
    correctly does NOT treat `(1)` as an entry start today, so this row's
    entire definitions list (3+ terms, `"obstruct"` among them) is
    silently dropped -- a real, pervasive corpus shape (a 53-jurisdiction
    scan of just the `(N) <label>. The term "X" means`/`(N) LABEL. To "X"
    means` family found tens of thousands of real hits; out of THIS
    sprint's scope to fix -- QA's 8 confirmed root causes did not name
    this shape, so it is reported here only as the vehicle for isolating
    the marker-adjacency MECHANISM, not pinned as a new bug). Unlike the
    PA row above, this row's idiom ("means") IS in `_IDIOM_RE`'s
    recognized vocabulary, so nothing downstream would independently save
    this assertion -- mutation-verified on this worktree's own scratch
    copy: widening `_MARKER_QUOTE_RE`'s marker-to-quote gap from immediate
    (`\\s*`) to <=20 arbitrary characters turns `"obstruct"` into a
    captured term; with the gate intact (today's real code), it stays
    silent."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _gate_rows()["STATE_AL_T13A_C11_S13A-11-1"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "obstruct" not in terms, (
        "the marker-to-quote adjacency gate should have kept `(1) OBSTRUCT. To "
        '"obstruct" means...\' from being recognized as a fresh entry (the label '
        f"text between the marker and the quote is not whitespace-only) -- got {candidates!r}"
    )
