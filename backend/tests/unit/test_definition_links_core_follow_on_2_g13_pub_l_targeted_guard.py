"""RED tests -- sprint 2026-08-05-defs-core-follow-on-2, gate G13
(targeted 'Pub. L.'/'Amendments' guard, program-manager ruling: this
BLOCKS MERGE).

**The defect (introduced by G3-main, already landed/merged on this
branch).** `_trailing_notes_boundary` (`us_profile.py`) treats a bare,
case-sensitive substring match of ANY `_TRAILING_NOTES_MARKERS` entry
ANYWHERE in a line as proof that line starts a genuine trailing-notes
block, and truncates the entry there. This is correct for 8 of the 10
markers, and correct for `'Pub. L.'`/`'Amendments'` too WHEN they open a
standalone citation-parenthetical or section-header line (the real USC
convention `_trailing_notes_boundary` was designed against) -- but WRONG
when either string appears mid-sentence, inside a genuine definition's
own substantive prose, which is an extremely common US statutory-drafting
shape: "X means the [Act Name], Pub. L. No. Y-ZZZ" (citing a named act by
its own Public Law number as part of describing what X IS), or a defined
TERM whose own real name happens to contain "Amendments" (e.g. "Superfund
Amendments and Reauthorization Act of 1986").

**Measured (Planner, corpus-wide, main function's own population, current
branch code).** Of 6,647 last entries the existing G3-main trim touches,
**28 are complete drops** (`definition_text` -> `""`, so the term vanishes
from `extract_definitions_from_section`'s output entirely -- not merely
shortened). **All 28, exhaustively hand-checked (not sampled), are FALSE
truncations** -- every one has genuine, substantive `definition_text`
before the trim. Per-marker: `'Pub. L.'` implicated in 21/28 (75%),
`'Amendments'` in 8/28 (including one case where the marker is in the
defined TERM itself, not even the definition body), `'Amended by Act'` in
4/28 (always co-occurring with `'Pub. L.'`), `'History:'`/`'Source:'` in
3/28 and 1/28 respectively (always co-occurring with `'Pub. L.'`, never
the sole trigger). **Zero** drops implicate `'Editorial Notes'`,
`'Statutory Notes'`, `'References in Text'`, `'Congressional Findings'`,
or `'Cited.'` alone. A separate seeded hand-judged sample (seed 20260805,
n=60 of the 6,647, rubric: read `old_text` in full, classify GENUINE
trailing-notes removal vs FALSE truncation of substantive content) found
58/60 (96.7%) genuine and only 2/60 (3.3%) false -- both of which are
among the 28 drops above. **The false-drop risk is concentrated and
narrow, not evidence to touch any other marker.**

**The fix (item G13-1, this Planner's design, program-manager-approved
shape).** Mirrors the guard SHAPE D-INCLUDES/G12 already established for
`'References to'` in `_preceded_by_references_to`: targeted, literal,
positional -- never idiom-absence, never a broad heuristic. For
`'Pub. L.'` and `'Amendments'` ONLY: a match on a given line counts as a
trailing-notes trigger ONLY IF the line, after stripping leading
whitespace, STARTS WITH `'('` (a standalone citation/parenthetical block
-- covers both the immediate `"(Pub. L. ..."` shape and the
`"(Added Pub. L. ..."`/long semicolon-chained citation-history shape,
regardless of how far into that already-parenthetical line the marker
text itself sits) OR STARTS WITH the marker text itself (the bare
section-header shape, e.g. a line that is just `"Amendments"`). Every
OTHER marker (`'Editorial Notes'`, `'Statutory Notes'`,
`'References in Text'`, `'Congressional Findings'`, `'History:'`,
`'Amended by Act'`, `'Source:'`, `'Cited.'`) is UNCHANGED -- bare
substring-anywhere-in-line, exactly as shipped. Narrowing them was
considered and rejected: they show zero measured false-drop risk in the
exhaustive 28-row census, and narrowing them unmeasured would repeat the
D-INCLUDES mistake (tightened guards costing 32-56% of true definitions
for no measured precision gain, already rejected once by this program).

**Verified end-to-end (Planner simulation, not merely theorized) against
the FULL measured population before being proposed as the fix:**
- Applying the proposed rule to all 6,647 currently-changed rows:
  **complete drops go from 28 to 0.**
- Applying it to the 60-row hand-judged sample: **0 of the 60 rows'
  output changes** -- every one of the 58 already-genuine trims stays
  byte-identical (including the long semicolon-chained USC citation
  lines, which start with `'('` and so are unaffected by the new guard
  regardless of how far into the line `'Pub. L.'` itself sits -- e.g.
  `USC_T7_C35_S1301`'s real trailing block, where `'Pub. L.'` sits at
  character offset 852 of an 852+-char citation-history line that starts
  with `'('`, is preserved intact by this rule, precisely because it
  checks the LINE's start, not the marker's own offset).
- The already-committed FED RED fixture (`g3_fed_unbounded_last_entry_row.
  json`, `USC_T5_C34_S3401`) reproduces byte-identically under the
  proposed rule: 493 chars, ending `"...temporary or intermittent
  basis."` -- its own trailing block is `"(Added Pub. L. 95-437,
  ...)"`, which starts with `'('`, so the new guard does not touch it.

**Acceptance target for the Developer, stated so QA has something
falsifiable:** after G13-1 lands, re-running this Planner's corpus
measurement (`main_g3_measure.py`'s recipe, or equivalent) against the
same 53-file glob/snapshot must show **0 complete drops** on the main
population (down from 28), and the 58/60 already-genuine sample rows
(plus the existing FED RED fixture and every guard-state pin) must remain
BYTE-IDENTICAL. Any new drop, or any change to a currently-genuine trim,
is a regression.

**Fixture provenance.** All 4 real rows in
`g13_pub_l_targeted_guard_rows.json`, every original parquet column,
values unmodified, from the real corpus snapshot at
`/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/
snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/`. `text` field SHA-256
verified below (this pass) against a fresh read of the real parquet files
via `pyarrow`, matching this sprint's own established provenance
discipline. No test in this file reads the corpus.

**Live path.** Every RED calls the bare `extract_definitions_from_section`
directly on `row["text"]` after the M14 literal-`\\n` unescape (matching
this sprint's own established `test_us_core_g3_guard_states_no_regression.
py` convention for calling the module-level function directly when no
registry rules are registered for the state under test on this branch --
verified: all 4 rows' raw `section_title` is directly `is_definitions_
heading`-True, so `heading_was_derived` is `False` and this exercises the
PRIMARY `'(N)'`-block splitter path, the same one every guard-state row
and the FED RED fixture already exercise -- not the G3-sibling's separate,
still-NO-GO'd fallback path).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.definition_links.us_profile import extract_definitions_from_section

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"
FIXTURE_PATH = FIXTURES_DIR / "g13_pub_l_targeted_guard_rows.json"
FED_RED_FIXTURE_PATH = FIXTURES_DIR / "g3_fed_unbounded_last_entry_row.json"

# Independently re-verified this pass (fresh `pyarrow` read of the real
# parquet files, hashed the same way the FED RED fixture's own provenance
# note does) -- `hashlib.sha256(row["text"].encode()).hexdigest()` for
# each of the 4 vendored rows.
_EXPECTED_TEXT_SHA256 = {
    "STATE_TX_Cfa_C264_S264.152": "aaf903aff65022906986a5f30006841f5ee43cee1dbf5db82aee17ea7ba06f19"[:64],
    "STATE_FL_TX_C110_PIV_S110.501": "75f27141c0439a9a790d300fc829f22ace5d6ec14a5ec0907de1e65fc05a740f"[:64],
    "STATE_AR_T12_C84_S12-84-103": "949f559288d10b1dd30d450b8a8710a5eb0758c1e4a5f9055e6b39c6cacfc85a"[:64],
    "USC_T51_C509_S50902": "087d901db41fffdb849c179e99a316e81bca4481d454123867912f424e1a9042"[:64],
}


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def test_fixture_rows_are_byte_verified_against_the_real_corpus():
    """Sanity (not the RED itself): every vendored row's `text` field
    hashes to the value independently recomputed against a fresh read of
    the real parquet snapshot this pass -- if this ever goes red, the
    fixture has drifted from the real corpus row, and every other
    assertion in this file is confounded."""
    rows = _load_rows()
    assert set(rows) == set(_EXPECTED_TEXT_SHA256)
    for act_id, expected_hash in _EXPECTED_TEXT_SHA256.items():
        actual_hash = hashlib.sha256(rows[act_id]["text"].encode()).hexdigest()
        assert actual_hash == expected_hash, (
            f"{act_id}: text field does not match the real corpus byte-for-byte "
            f"(got {actual_hash}, expected {expected_hash})"
        )


def test_all_four_rows_raw_headings_are_directly_recognized_not_derived():
    """Sanity: confirms every RED below exercises the PRIMARY `'(N)'`-block
    splitter path (the one G3-main's own already-landed fix touches), not
    the separate, still-NO-GO'd G3-sibling fallback -- `heading_was_
    derived` is `False` for all four in the real pipeline."""
    from app.definition_links.us_profile import is_definitions_heading

    rows = _load_rows()
    expected_titles = {
        "STATE_TX_Cfa_C264_S264.152": "§ 264.152. DEFINITIONS.",
        "STATE_FL_TX_C110_PIV_S110.501": "110.501 Definitions.",
        "STATE_AR_T12_C84_S12-84-103": "Definitions",
        "USC_T51_C509_S50902": "Definitions",
    }
    for act_id, expected_title in expected_titles.items():
        row = rows[act_id]
        assert row["section_title"] == expected_title
        assert is_definitions_heading(row["section_title"]) is True, (
            f"{act_id}: raw heading must be directly recognized (heading_was_derived=False) "
            "-- otherwise this row would exercise the separate G3-sibling path, not G3-main"
        )


# --- Drop case 1: STATE_TX_Cfa_C264_S264.152, "Family preservation ---------
# --- service" (538 chars, three real (A)/(B)/(C) sub-items) ----------------

_TX_ACT_ID = "STATE_TX_Cfa_C264_S264.152"
_TX_EXPECTED_DEFINITION_TEXT = (
    "means time-limited, family-focused services, including services subject "
    "to the Family First Prevention Services Act (Title VII, Div. E, Pub. L. "
    "No. 115-123) and services approved under the Title IV-E state plan "
    "provided to the family of a child who is:\n\n"
    "(A) a candidate for foster care to prevent or eliminate the need to "
    "remove the child and to allow the child to remain safely with the "
    "child's family;\n\n"
    "(B) a pregnant or parenting foster youth; or\n\n"
    "(C) a member of a household that is subject to an order rendered "
    "under Section 264.203."
)


def test_tx_family_preservation_service_survives_the_targeted_guard():
    """THE LOAD-BEARING RED. Today, real unmodified shipped code drops
    "Family preservation service" from `extract_definitions_from_section`'s
    output ENTIRELY (not merely truncates it) -- `'Pub. L.'` fires at
    offset 209 of the definition's own first line (`"means time-limited,
    family-focused services, including services subject to the Family
    First Prevention Services Act (Title VII, Div. E, Pub. L. No.
    115-123) ..."`), which does not start with `'('`, so
    `_trailing_notes_boundary` returns offset 0 and `_leading_quote_
    candidate` then finds no leading quote at all in the (empty) trimmed
    text. Real production TX text has 6 defined terms in this section;
    today only 5 candidates are produced (verified this pass). Once
    G13-1 lands, this line no longer counts as a trailing-notes trigger
    (it does not start with `'('` or `'Amendments'`/`'Pub. L.'` itself),
    the term is recovered, and its FULL real definition -- including both
    real sub-items and the genuine inline Pub.L. citation -- must survive
    intact, not merely become non-empty."""
    row = _load_rows()[_TX_ACT_ID]
    text = row["text"].replace("\\n", "\n")
    candidates = extract_definitions_from_section(text, scope="law-wide")
    by_term = {c.terms[0]: c for c in candidates}

    assert len(candidates) == 6, (
        f"G13-1 landed (dev8, us_profile.py) -- this row has 6 real defined terms, "
        f"and this count now pins that ALL 6 survive, not merely that "
        f"'Family preservation service' came back by name. A count of 5 means the "
        f"Pub. L. false-truncation drop this gate closed has regressed -- got "
        f"{len(candidates)}"
    )
    assert "Family preservation service" in by_term, (
        f"'Family preservation service' must be recovered as its own candidate -- "
        f"got terms {sorted(by_term)!r} (today it is silently dropped entirely, not "
        "merely truncated, because 'Pub. L.' fires mid-sentence inside its own "
        "genuine definition text)"
    )
    fps = by_term["Family preservation service"]
    assert fps.definition_text == _TX_EXPECTED_DEFINITION_TEXT, (
        f"'Family preservation service' must survive with its FULL real 538-char "
        f"definition (all three (A)/(B)/(C) sub-items and the genuine inline Pub.L. "
        f"citation intact) -- got {len(fps.definition_text)} chars: "
        f"{fps.definition_text!r}"
    )


# --- Drop case 2: STATE_FL_TX_C110_PIV_S110.501, "Volunteer" (854 chars, --
# --- two inline Pub.L. citations, followed by a GENUINE separate ----------
# --- "History:" tail that must still be correctly trimmed) ----------------

_FL_ACT_ID = "STATE_FL_TX_C110_PIV_S110.501"
_FL_EXPECTED_DEFINITION_TEXT = (
    "means any person who, of his or her own free will, provides goods or "
    "services, or conveys an interest in or otherwise consents to the use "
    "of real property pursuant to chapter 260, to any state department or "
    "agency, or nonprofit organization, with no monetary or material "
    "compensation. A person registered and serving in Older American "
    "Volunteer Programs authorized by the Domestic Volunteer Service Act "
    "of 1973, as amended (Pub. L. No. 93-113), shall also be defined as a "
    "volunteer and shall incur no civil liability as provided by s. "
    "768.1355. A volunteer shall be eligible for payment of volunteer "
    "benefits as specified in Pub. L. No. 93-113, this section, and s. "
    "430.204."
)


def test_fl_volunteer_survives_the_guard_and_the_genuine_history_tail_still_trims():
    """THE PRECISION RED -- proves the fix is targeted, not a blanket
    "never trim 'Pub. L.' again" rollback. This row's real trailing-notes
    tail is `"\\n\\nHistory: s. 1, ch. 78-263; ..."` (180 chars) -- a
    GENUINE, separate citation-history line starting with `'History:'`,
    a marker G13-1 does not touch at all. Today the whole 854-char
    definition (both real sub-sentences AND the genuine History: tail)
    is dropped to nothing, because `'Pub. L.'` fires first, mid-sentence,
    at offset 683 of the run-on definition paragraph (which starts long
    before any real newline). Once fixed: the two genuine inline `'Pub.
    L.'` citations must NOT terminate the entry (neither line they sit on
    starts with `'('`) -- but the real trailing `'History:'` line
    (unrelated to this gate, unchanged behavior) must STILL correctly
    terminate it. `new_text` must therefore be exactly the 674-char
    definition, NOT the full 854 chars (that would mean the History:
    marker stopped working) and NOT empty (that would mean the drop bug
    persists)."""
    row = _load_rows()[_FL_ACT_ID]
    text = row["text"].replace("\\n", "\n")
    candidates = extract_definitions_from_section(text, scope="law-wide")
    by_term = {c.terms[0]: c for c in candidates}

    assert len(candidates) == 4, (
        f"G13-1 landed -- this row has 4 real defined terms, and this count now "
        f"pins that ALL 4 survive, not merely that 'Volunteer' came back by name. "
        f"A count of 3 means the Pub. L. false-truncation drop this gate closed "
        f"has regressed -- got {len(candidates)}"
    )
    assert "Volunteer" in by_term, (
        f"'Volunteer' must be recovered -- got terms {sorted(by_term)!r} (today "
        "silently dropped entirely)"
    )
    volunteer = by_term["Volunteer"]
    assert "History:" not in volunteer.definition_text, (
        "the genuine trailing History: citation log must still be trimmed -- "
        f"it leaked into definition_text: {volunteer.definition_text[-100:]!r}"
    )
    assert volunteer.definition_text == _FL_EXPECTED_DEFINITION_TEXT, (
        f"'Volunteer' must survive with exactly its 674-char real definition "
        f"(both genuine inline Pub.L. citations intact, History: tail correctly "
        f"still trimmed) -- got {len(volunteer.definition_text)} chars: "
        f"{volunteer.definition_text!r}"
    )


# --- Drop case 3: STATE_AR_T12_C84_S12-84-103 -- the marker is IN the -----
# --- defined TERM itself, not merely the definition body -------------------

_AR_ACT_ID = "STATE_AR_T12_C84_S12-84-103"
_AR_TERM = "Superfund Amendments and Reauthorization Act of 1986, Title III"
_AR_EXPECTED_DEFINITION_TEXT = (
    "refers to the Community Right-to-Know Act of 1986, 42 U.S.C. § 11001 "
    "et seq. and activities mandated therein.\n\nActs 1995, No. 634, § 2."
)


def test_ar_term_that_itself_contains_amendments_survives_the_guard():
    """THE SHARPEST RED -- the marker is not merely in the definition
    BODY, it is in the defined TERM's own quoted name: `'"Superfund
    Amendments and Reauthorization Act of 1986, Title III" refers to
    ...'`. Today `'Amendments'` fires on this block's own FIRST line
    (the one carrying the quoted term itself, before `_leading_quote_
    candidate` ever runs), at offset 15 -- `_trailing_notes_boundary`
    returns offset 0, trimming the block to nothing before a term or a
    definition can even be extracted from it. This is the clearest
    possible demonstration that "marker text appears somewhere in
    genuine content" -- not "generic vs specific marker" -- is the real
    failure mode: the term's own real, correct name is what triggers its
    own destruction. Once fixed: that line does not start with `'('` or
    `'Amendments'` itself (it starts with a quote mark), so it no longer
    counts as a trigger, and both the term AND its full real definition
    (including the trailing `"Acts 1995, No. 634, § 2."` citation
    fragment, which nothing else in the fix's scope trims -- acceptable:
    keeping a few extra citation chars is not the failure mode this gate
    exists to close, LOSING the entire real entry is) must be recovered."""
    row = _load_rows()[_AR_ACT_ID]
    text = row["text"].replace("\\n", "\n")
    candidates = extract_definitions_from_section(text, scope="law-wide")
    by_term = {c.terms[0]: c for c in candidates}

    assert len(candidates) == 5, (
        f"G13-1 landed -- this row has 5 real defined terms, and this count now "
        f"pins that ALL 5 survive, not merely that the Amendments-named term came "
        f"back by name. A count of 4 means the term-contains-the-marker "
        f"false-truncation drop this gate closed has regressed -- got "
        f"{len(candidates)}"
    )
    assert _AR_TERM in by_term, (
        f"{_AR_TERM!r} must be recovered as its own candidate -- got terms "
        f"{sorted(by_term)!r} (today dropped entirely because 'Amendments' -- "
        "part of the TERM's own real name -- fires on the block's first line)"
    )
    assert by_term[_AR_TERM].definition_text == _AR_EXPECTED_DEFINITION_TEXT, (
        f"expected the full real 135-char definition -- got "
        f"{len(by_term[_AR_TERM].definition_text)} chars: "
        f"{by_term[_AR_TERM].definition_text!r}"
    )


# --- Non-regression pin: USC_T51_C509_S50902, "United States" -- a --------
# --- GENUINE case that is ALREADY correct today and must stay so ----------

_FED_NOREG_ACT_ID = "USC_T51_C509_S50902"
_FED_NOREG_EXPECTED_TEXT = (
    "means the States of the United States, the District of Columbia, and "
    "the territories and possessions of the United States."
)


def test_fed_united_states_no_regression_genuine_pub_l_still_trims_correctly():
    """THE STOP-OVER-CORRECTING-THE-FIX GUARD (currently GREEN, must STAY
    green -- pins known-good behavior before AND after G13-1, mirroring
    `test_us_core_g3_guard_states_no_regression.py`'s own convention).
    This row's real trailing block is `"(Pub. L. 103-272, §1(e), ...)"` --
    a genuine, standalone citation-parenthetical starting immediately with
    `'('` at line-start. Today this ALREADY correctly shrinks the entry
    from 9,328 to 122 chars (verified: this assertion passes on
    unmodified shipped code right now). G13-1 must not perturb it -- the
    line starts with `'('`, so the new guard's own condition is satisfied
    and the trim fires exactly as it does today. If this assertion ever
    goes red once G13-1 lands, the fix over-corrected: it stopped
    trimming a genuine standalone citation block, not just the false
    mid-sentence cases this gate targets."""
    row = _load_rows()[_FED_NOREG_ACT_ID]
    text = row["text"].replace("\\n", "\n")
    candidates = extract_definitions_from_section(text, scope="law-wide")
    by_term = {c.terms[0]: c for c in candidates}

    assert "United States" in by_term, f"got terms {sorted(by_term)!r}"
    us = by_term["United States"]
    assert us.definition_text == _FED_NOREG_EXPECTED_TEXT, (
        f"'United States' real definition (9,328 raw chars -> already-correctly-"
        f"shrunk 122 chars TODAY) must stay byte-identical -- got "
        f"{len(us.definition_text)} chars: {us.definition_text!r}"
    )


# --- Non-regression pin: the EXISTING committed G3-main FED RED fixture ---
# --- (USC_T5_C34_S3401) must stay green, re-verified here for a -----------
# --- self-contained regression net on G13's OWN change surface ------------


def test_existing_fed_g3_main_red_fixture_still_reproduces_under_this_gates_change_surface():
    """Not a new defect -- re-verifies (this pass, against the SAME
    already-vendored fixture `g3_fed_unbounded_last_entry_row.json`, not
    a duplicate copy) that `USC_T5_C34_S3401`'s own already-committed RED
    (`test_us_core_g3_fed_unbounded_last_entry_red.py`) stays green under
    G13-1: its real trailing block is `"(Added Pub. L. 95-437, ...)"` --
    starts with `'('`, so the new guard's condition is satisfied and this
    fixture is completely unaffected either way. Included here (not only
    left to the other file) because G13-1 touches the exact same
    `_trailing_notes_boundary` function this fixture depends on, and this
    gate's own test file should carry a self-contained regression net for
    its own change surface, not rely solely on a different gate's file."""
    rows = json.loads(FED_RED_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    row = rows[0]
    assert row["act_id"] == "USC_T5_C34_S3401"

    text = row["text"].replace("\\n", "\n")
    candidates = extract_definitions_from_section(text, scope="law-wide")
    by_term = {c.terms[0]: c for c in candidates}

    assert "agency" in by_term, f"got {sorted(by_term)!r} -- unrelated regression"
    assert "part-time career employment" in by_term, f"got {sorted(by_term)!r}"
    ptce = by_term["part-time career employment"]
    assert len(ptce.definition_text) == 493, (
        f"must stay byte-identical to the already-committed RED's own pinned "
        f"value -- got {len(ptce.definition_text)} chars"
    )
    assert ptce.definition_text.endswith("temporary or intermittent basis.")
