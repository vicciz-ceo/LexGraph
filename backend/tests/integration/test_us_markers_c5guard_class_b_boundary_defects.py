"""RED tests -- sprint 2026-08-04-defs-us-markers, phase-3 Planner, item 2 of
the M35/U-R17 work order. Pins the "class B" population: genuine terms
devC's US-NJ/MI/ND/NY/OK registration newly surfaces whose CAPTURED TEXT is
defective (as opposed to the class-A stale-pin population re-authored in the
5 `test_us_markers_c5guard_*.py` files, and the vacated class-C spurious
theory, U-R16). Per M34's merge sequencing, devC merges only after this file
and the c5guard re-pins land; these tests stay RED and are routed to
core-follow-on-3 (`## M33`) -- this panel does not fix them and does not
extend any local guard toward a citation-vs-marker discriminator (explicitly
forbidden, `## M33`).

**Entry point / normalization statement, one line per M35's mandatory
requirement, stated once here since it is identical for every test below**:
every test calls `extract_quote_anchored_entries` DIRECTLY on each row's raw
fixture `text` -- the exact, unmodified function devC's one-line
`_JURISDICTIONS` widening wires into the live pipeline for these
jurisdictions (verified: `git diff` of devC's branch touches ONLY that
tuple, zero lines in `us_markers_boundary.py`). Ingest normalization
(`ingest_us_statutes.py:237`, `text.replace("\\\\n", "\\n")`, the M14/I8 fix)
is confirmed a NO-OP on every row used below -- checked directly, none of
these NJ/ND/OK rows contain the literal backslash-n artifact that made
Task 3's colon-idiom NY REDs invalid (`## M35`, U-R11 recurrence). Calling
the engine directly here is therefore behaviourally identical to what the
live pipeline will do once devC's tuple lands; no jurisdiction registration
is needed to observe this defect truthfully.

**The FINAL, CLOSED class-B list is 15 of the 75 extra terms** (`## M37`):
QA's mechanical sweep (7 stated criteria) flagged 18, read all 18 against
raw source, and the manager independently re-derived 5 of the 18 -- weighting
false positives -- before accepting the list. `Offer` (ND) was withdrawn (it
was an existing baseline pin, not one of the 75 extras); `retailer` (NY) was
accepted-cleared as a "cosmetic residue class" (a trailing `"; and"` list
connector, no content lost). This file pins all 15, plus ONE additional term
this Planner independently found and verified beyond the closed list (see
the final test below) -- reported per M37's own invitation: "If you find a
sixteenth, say so. The set is closed on current evidence, not by decree."

**Sorted by mechanism, not symptom, 14 of the 15 are ONE defect** (`## M37`):
the parenthesised/bare-number-vs-marker ambiguity that `## M33` scoped to
CORE as the core-follow-on-3 anchor (the same ambiguity as this panel's own
U-R12). Mid-citation truncations are a citation's internal number misread as
a boundary; "stops after sub-item (1)" is the source's own "(2)" misread as
a next-entry marker; the `"5. a."`/`"12. a."`/`"14. a."` leaks are bare
digit-dot markers; `gallon` is the `"(1)"` inside `means one (1) United
States standard gallon`. Per M35's own instruction, each test below pins the
OBSERVABLE defect (the specific wrong captured text, verified against raw
source) -- NOT a theory of the marker-vs-citation mechanism -- so a correct
future fix (wherever core lands it) satisfies these tests regardless of its
internal shape.

**Criterion blind spot, carried forward from `## M37` so it is not lost**:
these defects were found by content-loss/truncation heuristics, which catch
large and medium losses but NOT single-token losses. `facility`'s missing
`means ` prefix and its lost trailing `" 3"` (off `...c. 34, p. 97, s. 3.`)
are both sub-threshold on every mechanical criterion and were found only by
hand-reading the raw row. A future automated re-run of this sweep will not
re-find them."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _entries(fname: str, act_id: str) -> dict[str, str]:
    rows = {r["act_id"]: r for r in json.loads((FIXTURES / fname).read_text(encoding="utf-8"))}
    return dict(extract_quote_anchored_entries(rows[act_id]["text"]))


# --- NJ (STATE_NJ_T58_C22_S22-3) ---------------------------------------


def test_nj_facility_missing_means_prefix_and_truncated_citation_tail():
    """Raw source: `... "Water supply facility" or "facility" means and
    refers to the real property ... L.1958, c. 34, p. 97, s. 3.` -- 'facility'
    is a genuine second alias (U-R16 vacated the spurious theory), defined in
    the SAME sentence as 'Water supply facility'. Two independent, both
    sub-threshold-on-mechanical-criteria defects on this one capture: (1) its
    own `means ` prefix is dropped (starts `'and refers to...'` instead of
    `'means and refers to...'`); (2) its citation tail loses the trailing
    digit (ends `'...s.'` instead of `'...s. 3.'`)."""
    entries = _entries("us_markers_c5guard_nj_rows.json", "STATE_NJ_T58_C22_S22-3")
    text = entries["facility"]
    assert text.startswith("means "), (
        f"'facility' definition_text is missing its own 'means ' prefix: {text[:60]!r}"
    )
    assert text.rstrip().endswith("s. 3."), (
        f"'facility' definition_text lost the trailing citation digit "
        f"(should end '...s. 3.'): {text[-30:]!r}"
    )


# --- NJ (STATE_NJ_T12A_C2_S2-104 / S2-105) ------------------------------


def test_nj_between_merchants_citation_tail_truncated():
    """Raw source ends `... L.1961, c. 120, s. 2-104.` -- captured text ends
    `'...s. 2-'`, losing the final `104.`"""
    entries = _entries("us_markers_c5guard_nj_rows.json", "STATE_NJ_T12A_C2_S2-104")
    text = entries["Between merchants"]
    assert text.rstrip().endswith("s. 2-104."), f"citation tail truncated: {text[-20:]!r}"


def test_nj_commercial_unit_citation_tail_truncated():
    """Raw source ends `... L.1961, c. 120, s. 2-105.` -- captured text ends
    `'...s. 2-'`, losing the final `105.`"""
    entries = _entries("us_markers_c5guard_nj_rows.json", "STATE_NJ_T12A_C2_S2-105")
    text = entries["Commercial unit"]
    assert text.rstrip().endswith("s. 2-105."), f"citation tail truncated: {text[-20:]!r}"


# --- OK (STATE_OK_T68_S68-701) ------------------------------------------


def test_ok_gallon_parenthesized_number_misread_as_next_entry_marker():
    """Raw source: `(g) The term "gallon" means one (1) United States
    standard\\n\\ngallon at a temperature of sixty (60) degrees Fahrenheit.`
    -- the `(1)` inside the definition's own text is misread as a next-entry
    marker; captured text is truncated to the 3-char stub `'one'`
    (M24's original finding, independently reproduced here)."""
    entries = _entries("us_markers_c5guard_ok_rows.json", "STATE_OK_T68_S68-701")
    text = entries["gallon"]
    assert "United States standard" in text and "gallon at a temperature" in text, (
        f"'gallon' definition_text is truncated to a stub, losing the real "
        f"definition ('means one (1) United States standard gallon at a "
        f"temperature of sixty (60) degrees Fahrenheit.'): {text!r}"
    )


# --- ND (STATE_ND_T57_C57-39.2_S57-39.2-01) ------------------------------


def test_nd_bundled_transaction_stops_after_first_sub_item():
    """Raw source's `"Bundled transaction"` entry continues past sub-item
    `(1)` into `(2) A product provided free of charge with the required
    purchase of another product...` and `(3) Items included in the
    definition of gross receipts.`, plus a further lettered `b.` clause.
    Captured text stops at the end of `(1)`, losing all of it."""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T57_C57-39.2_S57-39.2-01")
    text = entries["Bundled transaction"]
    assert "provided free of charge" in text, (
        f"'Bundled transaction' definition_text stops after sub-item (1), "
        f"losing (2) ('...provided free of charge with the required "
        f"purchase...') and (3): {text[-80:]!r}"
    )


def test_nd_farm_machinery_repair_parts_leaks_next_entry_marker_chain():
    """Raw source's own sentence is complete and ends cleanly: `... do not
    include tires, fluid, gas, grease,\\n\\nlubricant, wax, or paint.` The
    NEXT entry's own `12. a. "Gross receipts" ...` marker chain leaks onto
    the end of this capture instead of stopping at the real period."""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T57_C57-39.2_S57-39.2-01")
    text = entries["Farm machinery repair parts"]
    assert "12. a." not in text, (
        f"'Farm machinery repair parts' definition_text illegally leaks the "
        f"next entry's own '12. a.' marker chain: {text[-30:]!r}"
    )
    assert text.rstrip().endswith("or paint."), f"got {text[-30:]!r}"


def test_nd_gross_receipts_stops_after_first_sub_item():
    """Raw source's `"Gross receipts"` entry continues past `(1)` into
    `(2) The cost of materials used, labor or service costs, ...`,
    `(3)`, `(4) Delivery charges; and`, `(5) Credit for any trade-in ...`,
    plus a further lettered `b.` clause. Captured text stops at the end of
    `(1)`, losing all of it."""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T57_C57-39.2_S57-39.2-01")
    text = entries["Gross receipts"]
    assert "materials used, labor or service costs" in text, (
        f"'Gross receipts' definition_text stops after sub-item (1), losing "
        f"(2)-(5) and part b.: {text[-80:]!r}"
    )


def test_nd_sale_at_retail_citation_tail_truncated():
    """Raw source ends `... as provided in section 57-39.2-12.` -- captured
    text ends `'...57-39.2-'`, losing the final `12.`"""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T57_C57-39.2_S57-39.2-01")
    text = entries["sale at retail"]
    assert text.rstrip().endswith("57-39.2-12."), f"citation tail truncated: {text[-20:]!r}"


# --- ND (STATE_ND_T57_C57-02_S57-02-01) ----------------------------------


def test_nd_agricultural_property_stops_after_first_sub_item():
    """Raw source's `"Agricultural property"` entry continues past `1. a.`'s
    own `(1)` into `(2) Property platted on or after March 30, 1981, is not
    agricultural property\\n\\nwhen any four of the following conditions
    exist:` plus lettered sub-items `(a)`-`(e)`. Captured text stops at the
    end of `(1)` -- which happens to end in a grammatically complete
    sentence, so this is the "premature but not obviously truncated" shape
    `## M37` flags as a mechanical-criterion blind spot: no dangling
    citation or missing punctuation signals it, only comparison to raw
    source does."""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T57_C57-02_S57-02-01")
    text = entries["Agricultural property"]
    assert "Property platted on or after March 30, 1981" in text, (
        f"'Agricultural property' definition_text stops after sub-item (1), "
        f"losing (2) and its (a)-(e) sub-items: {text[-80:]!r}"
    )


def test_nd_air_carrier_transportation_property_citation_tail_truncated():
    """Raw source ends `... pursuant to chapters 57-06 and 57-32.` --
    captured text ends `'...57-06 and 57-'`, losing the final `32.`"""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T57_C57-02_S57-02-01")
    text = entries["Air carrier transportation property"]
    assert text.rstrip().endswith("57-06 and 57-32."), f"citation tail truncated: {text[-30:]!r}"


def test_nd_centrally_assessed_property_citation_tail_truncated():
    """Raw source ends `... under chapters 57-05, 57-06, and 57-32.` --
    captured text ends `'...57-06, and 57-'`, losing the final `32.`"""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T57_C57-02_S57-02-01")
    text = entries["Centrally assessed property"]
    assert text.rstrip().endswith("57-06, and 57-32."), f"citation tail truncated: {text[-30:]!r}"


def test_nd_commercial_property_list_cut_mid_enumeration():
    """Raw source ends `... classes of property defined in subsections 1, 4,
    10, 12, 13, and 14.` -- captured text ends `'...12, 13, and'`, dropping
    the list's final member and its terminal period entirely."""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T57_C57-02_S57-02-01")
    text = entries["Commercial property"]
    assert text.rstrip().endswith("12, 13, and 14."), f"list cut mid-enumeration: {text[-30:]!r}"


# --- ND (STATE_ND_T51_C51-19_S51-19-02) -----------------------------------


def test_nd_commissioner_leaks_next_entry_marker_chain():
    """Raw source's own sentence is complete: `4. "Commissioner" means the
    insurance commissioner.` The NEXT entry's own `5. a. "Franchise" ...`
    marker chain leaks onto the end of this capture instead of stopping at
    the real period."""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T51_C51-19_S51-19-02")
    text = entries["Commissioner"]
    assert "5. a." not in text, (
        f"'Commissioner' definition_text illegally leaks the next entry's "
        f"own '5. a.' marker chain: {text!r}"
    )
    assert text.rstrip().endswith("the insurance commissioner."), f"got {text!r}"


def test_nd_franchise_loses_clauses_2_and_3():
    """Raw source's `"Franchise"` entry is one sentence spanning three
    clauses joined by `by which:` -- `(1) A franchisee is granted the right
    to engage ...`, `(2) The operation of the franchisee's business ... is
    substantially associated with the franchisor's trademark, service mark
    ...`, and `(3) The franchisee is required to pay, directly or
    indirectly, a franchise fee.` Captured text stops at the end of `(1)`,
    losing clauses (2) and (3) of its own 3-part definition."""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T51_C51-19_S51-19-02")
    text = entries["Franchise"]
    assert "trademark, service mark" in text, (
        f"'Franchise' definition_text is missing clause (2) ('...substantially "
        f"associated with the franchisor's trademark, service mark...'): {text!r}"
    )
    assert "required to pay, directly or indirectly, a franchise fee" in text, (
        f"'Franchise' definition_text is missing clause (3) ('...required to "
        f"pay, directly or indirectly, a franchise fee.'): {text!r}"
    )


def test_nd_rule_leaks_next_entry_marker_chain():
    """Raw source's own sentence is complete: `13. "Rule" means any
    published regulation or standard of general application issued by the
    commissioner.` The NEXT entry's own `14. a. (1) "Sale" ...` marker chain
    leaks onto the end of this capture instead of stopping at the real
    period."""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T51_C51-19_S51-19-02")
    text = entries["Rule"]
    assert "14. a." not in text, (
        f"'Rule' definition_text illegally leaks the next entry's own "
        f"'14. a.' marker chain: {text!r}"
    )
    assert text.rstrip().endswith("the commissioner."), f"got {text!r}"


# --- Beyond the closed 15: this Planner's own additional finding ---------


def test_nd_nonprimary_residential_property_citation_tail_lost_entirely():
    """NOT on M37's closed 15-item list -- an independent finding by this
    Planner, verified against raw source and reported per M37's own
    invitation ("If you find a sixteenth, say so"). Raw source ends `...
    not included in the class of property defined in subsection 12.` --
    captured text ends `'...defined in subsection'`, losing the citation
    number AND the terminal period entirely (not merely truncated -- fully
    absent). Same mechanism family as the other ND citation-tail losses in
    this row (`Air carrier transportation property`, `Centrally assessed
    property`, `Commercial property`), verified via the identical direct
    `extract_quote_anchored_entries` call as the rest of this file."""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T57_C57-02_S57-02-01")
    text = entries["Nonprimary residential property"]
    assert text.rstrip().endswith("defined in subsection 12."), (
        f"'Nonprimary residential property' definition_text lost its citation "
        f"tail entirely: {text[-40:]!r}"
    )
