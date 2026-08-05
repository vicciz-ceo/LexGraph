"""QA cycle 3 (sprint 2026-08-04-defs-us-scoped-inline), independent U4/U1
re-sweep. A FRESH stratified random sample (6/jurisdiction, all 53
jurisdictions, 318 rows, seed 20260805 -- independent of cycle 1's
20260804/N=10 and cycle 2's own sample), drawn before any trigger regex
touched the text, judged by 5 independent parallel readers (plain-language
"does this define any term, with any scope claim" prompt, never given this
family's trigger vocabulary) plus a 6th blind cross-validation reader over
a 40-row subsample (39/40 = 97.5% agreement; the one disagreement,
`STATE_MT_T28_C2_P4_S28-2-409`, is a genuinely borderline call about
whether a bare "X is a mistake ... consisting in" sentence with NO scope
phrase counts, and is excluded from this cycle's confirmed-miss count).

40/318 rows were judge-positive. Triaged against the REAL, unmodified
`is_definitions_heading`/`derive_heading_from_body` (3 F3-rescued, not
ours) and the REAL `extract_us_scoped_inline_definitions` (13 already
captured). Of the remaining 24 CANDIDATE_MISS rows, 9 have no in-family
trigger phrase at all (out of remit -- deeming/eligibility clauses, a
verb-form "'X' defined" heading, short titles) and 15 contain a recognized
STRONG or bare-`in` trigger. Full manual root-cause read of all 15 found:
6 are the ALREADY-KNOWN, already-accepted unquoted-term precision
tradeoff; 1 is the already-escalated S-R17 `(N) LABEL. "X"` marker+label
gap (now confirmed reaching federal ERISA text, `USC_T29_C18_S1310` --
NOT pinned here, that gate stays byte-untouched per the S-R17 disposition);
1 is the already-documented bare-`in` strict-adjacency-gate recall cost
(`STATE_MD_Agcs_T9_S2_S9-202`, "In this section the following words..."
with no immediate comma/colon).

The remaining 3 are DISTINCT from every root cause found in cycles 1 and 2
(verified against both cycles' lists) and are pinned below, one real
corpus row per class:

1. **Line-wrap whitespace inside a multi-word trigger phrase.** The corpus's
   `text` field sometimes line-wraps WITHIN "for purposes of"/"as used
   in"/"when used in" itself (e.g. "For\\n\\npurposes of this section"),
   not just around it. `_STRONG_TRIGGER_RE`'s alternation uses LITERAL
   single-space characters between the words of each phrase fragment
   (`"for (?:the )?purposes? of"`, `"as used in"`, `"when used in"`), not
   `\\s+` -- so a linebreak inside the phrase itself makes the trigger
   invisible, distinct from every whitespace tolerance already built
   around the unit word. Measured corpus-wide with a whitespace-tolerant
   variant of the SAME literal wording (`si_cycle3_qa_u4_whitespace_gap_
   scan.py`, scratchpad): **523 extra trigger events / 487 distinct rows /
   7 states** (OK 279 rows, ND 125, KY 74, NY 3, PA 3, DC 2, CA 1) that the
   shipped regex never sees at all -- 0.21% of this family's total trigger
   volume (253,255 shipped vs. 253,778 tolerant), small in aggregate but a
   real, confirmed, previously-undocumented class, concentrated in three
   states not previously flagged for this family (OK, ND, KY).
2. **`shall have the meaning(s) {provided/given} in this <unit>` tail
   clause.** `_STRONG_CONNECTOR_RE`'s "shall have (the following) meaning(s)"
   alternative does not tolerate a trailing "provided in this X" / "given
   to them in this X" qualifier before the `unless the context`/colon that
   follows -- confirmed on two independent states in this sample
   (Louisiana, Pennsylvania) with different exact wording ("the meaning
   provided in this Subsection" / "the meanings given to them in this
   subsection"), a genuine recurring drafting pattern, not one state's
   idiosyncrasy.
3. **`unless [a different meaning ...] context` filler-phrase variance.**
   `_STRONG_CONNECTOR_RE`'s context-qualifier tolerance only matches the
   literal `unless the context[^,:]{0,80}` shape; New York's "unless a
   different meaning clearly appears from the context" places "the
   context" at the END of the qualifier rather than immediately after
   "unless", so the filler group fails to match at all and the connector
   never reaches the colon that opens a cleanly MARKED, quoted list.

Per this sprint's QA role boundary: RED tests proving a defect, not a fix.
`us_scoped_inline.py`/`us_scoped_inline_shapes.py`/`us_scoped_inline_
entries.py` are READ-ONLY to QA. Every row below is real, unmodified,
vendored corpus text (`qa_cycle3_new_conventions_rows.json`, byte-verified
against the live HF snapshot at fetch time) -- no invented text, no
synthetic reproduction standing in for a real miss.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "qa_cycle3_new_conventions_rows.json"
)


def _rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))}


def test_linebreak_inside_the_trigger_phrase_itself_breaks_recognition_kentucky():
    """`STATE_KY_TIII_C16_S16.582`: `"...disease. For\\n\\npurposes of this
    section, \\"injury\\" means any physical harm or damage to the human
    organism..."` -- a clean trigger (quoted term immediately after the
    connector, recognized `means` idiom) except that the corpus text
    line-wraps INSIDE "For purposes of" itself. `_STRONG_TRIGGER_RE`'s
    `"for (?:the )?purposes? of"` fragment uses literal space characters
    between "for"/"purposes"/"of", so the trigger never matches at all --
    zero events are created for this occurrence, distinct from every other
    root cause found this sprint (all of which fire the trigger and fail
    downstream). 523 corpus-wide occurrences of this general shape (487
    rows, 7 states) -- see this file's module docstring."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_KY_TIII_C16_S16.582"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "injury" in terms, (
        "the rule captured nothing for a clean 'For\\n\\npurposes of this section, \"injury\" "
        f"means...' trigger broken only by a line-wrap inside the phrase itself -- got {candidates!r}"
    )


def test_shall_have_the_meaning_provided_in_this_unit_tail_not_recognized_louisiana():
    """`STATE_LA_Crevised-statutes_T25_S900.1`: `"The following terms, as
    used in this Section, shall have the meaning provided in this
    Subsection, unless the context clearly indicates otherwise: (1)
    \\"Louisiana artist\\" means..."` -- a clean STRONG trigger (`as used in
    this Section`) whose connector clause is `shall have the meaning
    provided in this Subsection` -- a real, recurring drafting shape
    `_STRONG_CONNECTOR_RE`'s `shall have (the following )?meanings?` branch
    does not tolerate (it expects the phrase to end at `meaning(s)`, not
    continue into `provided in this <unit>`), so the colon that opens the
    marked, quoted list is never reached."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_LA_Crevised-statutes_T25_S900.1"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "Louisiana artist" in terms, (
        "the rule captured nothing for a clean 'as used in this Section, shall have the meaning "
        f"provided in this Subsection, unless...: (1) \"Louisiana artist\" means...' row -- got {candidates!r}"
    )


def test_unless_a_different_meaning_appears_from_the_context_filler_not_recognized_new_york():
    """`STATE_NY_APVH_A12_S654-C`: `"1. Definitions. As used in this
    section, unless a different meaning clearly appears from the context:
    (a) \\"Housing New York program\\" shall mean..."` -- a clean STRONG
    trigger with a cleanly MARKED, quoted list following the colon.
    `_STRONG_CONNECTOR_RE`'s context-qualifier tolerance is anchored to the
    literal shape `unless\\s+the\\s+context[^,:]{0,80}` -- "the context"
    immediately after "unless". New York's phrasing puts "the context" at
    the END of the qualifier ("unless a different meaning clearly appears
    FROM THE CONTEXT"), so the filler group fails to match anything,
    `region_start` lands mid-qualifier instead of after the colon, and
    `_single_entry` finds no leading quote there."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_NY_APVH_A12_S654-C"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "Housing New York program" in terms, (
        "the rule captured nothing for a clean 'As used in this section, unless a different "
        f"meaning clearly appears from the context: (a) \"Housing New York program\" shall mean...' "
        f"row -- got {candidates!r}"
    )
