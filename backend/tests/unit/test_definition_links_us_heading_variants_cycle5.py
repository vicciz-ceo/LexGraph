"""RED tests for cycle-5 items 10-13 (sprint 2026-08-04-defs-us-headings,
gate U4 -- the manager's post-QA-cycle-3 zero-miss gap classes, measured
independently by the manager against
`.../scratchpad/headings_mgr3_gap_rows.json`, exactly reproducing/exceeding
QA cycle 3's own counts). Every gap class below is a real, evidenced,
hand-verified drafting convention the shipped `us_heading_variants.py`
(cycle 4, D-DF) does not yet recognize.

**RED signal expected right now**: mixed by item, reported per test below
in each function's own docstring -- items 10/11 are `AssertionError` (the
already-shipped `matches_heading_variant_unconditional`/`matches_heading_
variant` simply return `False` today; the feature-absence is a missing
regex alternation, not a missing symbol); items 12/13 are `ImportError` on
four genuinely new, not-yet-written symbols (`matches_pointer_table_
heading`, `matches_defined_qualifier_heading`, `defines_qualifier_in_body`
-- `matches_defined_qualifier_heading`+`defines_qualifier_in_body` ship as
a THIRD gated `HeadingRule`, mirroring D-DF's exact two-field pattern).

## Item 10 -- R-VERB-extended `and` connector gap (45 rows / 19 states)

`_VERB_EXTENDED_RE`/`_VERB_EXTENDED_UNCONDITIONAL_RE`'s connector
whitelist is `for|as|term` (plus punctuation/dash) -- `and` is not in it,
despite being exactly the same defect class as the `for`/comma/period gaps
cycle 2 already fixed (H-R7/H-R9). Manager-measured 45 rows / 19 states,
manager-verified genuine (`Felony defined and classified.`, `Ice Cream
Defined and Standardized`, `As used in this section, "creditor process"
means...`). **Design: UNCONDITIONAL, NOT body-gated** -- unlike D-DF's
`for` alternation (which measured ~65% body-confirmed precision and was
gated), `and` was NOT flagged as a precision risk by either QA cycle 3 or
the manager's independent re-measurement; per the contract's own explicit
instruction, 14 of the 45 are Louisiana's templated
`"pollution defined and prohibited"` heading whose BODY never mentions
"pollution" at all (ledger L4) -- capturing the HEADING is still correct
and required under ruling H-R1, so this rule must NOT be gated on body
yield. Tests below assert directly on `matches_heading_variant_
unconditional` (the function actually registered with `body_confirms=
None`) for exactly this reason, including on a body-empty Louisiana row.

## Item 11 -- RI mojibake dash/quote normalization (10 genuine rows, all RI)

`\x80\x94` (mojibake em-dash), `\x80\x9c`/`\x80\x9d` (mojibake curly
quotes) are CP1252-artifact byte sequences standing in for a real
dash/curly-quote pair in Rhode Island's scrape -- e.g. `\x80\x9cBridge\x80
\x9d defined \x80\x94 Responsibility for structures.`. The mojibake dash
defeats R-VERB-extended's existing dash-connector alternative (`[–—]` /
`-{2,}` / whitespace-hyphen), which was written against REAL Unicode dash
characters, not these two-byte CP1252 artifacts. Behavior is pinned at the
`matches_heading_variant_unconditional`/`matches_heading_variant` level
(the SAME functions item 10 uses) -- however the Developer chooses to fix
this (widen the dash alternation to accept the literal byte sequence, or
normalize it away in a preprocessing pass), the observable behavior below
is what must hold.

**REQUIRED negative guard** (ledger L6): `STATE_RI_T34_C34-11_S34-11-37`
(`Indefinite references to "trustee".`, mojibake curly quotes around
`trustee`, no `defined` verb at all) carries the identical mojibake bytes
but derives its `defin` miss-pool membership from `Indefinite` -- the
already-documented morphology exclusion class, unrelated to this fix. It
must STAY False after normalization. **Honesty note on this test's RED
status**: manager-verified live (this Planner re-ran it against the
CURRENTLY SHIPPED module before writing this file) that this specific row
already evaluates `False` today, unchanged by cycle 5 -- so this is a
PRECISION PIN guarding against an over-broad fix, not a RED-for-feature-
absence in itself. Included per the contract's explicit "REQUIRED negative
guard" instruction regardless.

## Item 12 -- D-MT-E1 pointer-table headings (9 rows / 7 states)

`Other defined terms` / `Index of definitions [in code/act/chapter/
title]` -- a real, repeated drafting convention whose body is a
cross-reference TABLE mapping each term to the section that actually
defines it (e.g. `STATE_CO_T5_A1_P3_S5-1-303`: body `"Actuarial method"
section 5-1-301 (1) ... "Administrator" sections 5-1-301 (2) and 5-6-103
...`, dozens of entries). Manager count (exceeding QA cycle 3's 7/6):
**9 rows / 7 states** -- CO, CT, IA, ME, OK, SC (x3), WY. Neither existing
family-4 rule fires on any of the 9: R-MID's own preposition-exclusion
guard already correctly suppresses `"...Index of definitions in code"` (
`of`/`in` govern the token immediately before "definitions"/"code"), and
`"Other defined terms."`'s last tail token is `terms`, not `defined`, so
R-VERB-bare/extended never fire either -- a genuinely NEW heading shape,
not a connector-whitelist gap. **Design: UNCONDITIONAL** (no body gate) --
all 9 hand-verified as genuine cross-reference tables by QA cycle 3 (6/6
sampled) and this Planner (remaining 3 spot-checked below), with none of
D-DF's/item 13's precision-risk shape.

New symbol: `matches_pointer_table_heading(heading: str) -> bool`, folded
into `matches_heading_variant_unconditional`/`matches_heading_variant`'s
union (unconditional, `body_confirms=None` if shipped as its own
registered `HeadingRule`, or simply added to the existing union -- the
Developer's choice, not pinned here).

### Planner note (plan6) -- premise update for the item-12 negative pin

`test_pointer_table_heading_not_reachable_via_existing_rules`, as
originally written, asserted `matches_heading_variant_unconditional`/
`matches_heading_variant` themselves returned `False` for the CT/CO
pointer-table headings, to prove item 12 was closing a genuinely NEW gap
rather than something already reachable pre-cycle-5. That was correct and
necessary WHEN WRITTEN -- it was a snapshot taken deliberately against
"the CURRENTLY SHIPPED module, before this item's fix" (its own docstring's
words), i.e. against cycle 4, to justify that item 12 was warranted rather
than redundant with items 10/11.

Item 12 has since landed (this cycle) and, exactly as this module's own
docstring above specifies, folded `matches_pointer_table_heading` directly
into BOTH union functions' bodies (see `__init__.py`). The union functions
now correctly return `True` for these headings -- proven by
`test_pointer_table_heading_recognized_unconditionally` above, item 12's
own REQUIRED RED test, now green. The old pin's literal assertion (`False`
at the union level) therefore asserts the absence of a capability the
panel deliberately built, directly contradicting the sibling test on the
same two inputs. Flipping it to `True` would only duplicate that sibling
test.

What the pin was REALLY protecting -- that the pointer-table shape is not
reachable via R-MID's preposition-guarded tail-token check or via
R-VERB-bare/extended's `defined`-ending checks, i.e. that it is a
genuinely NEW heading shape requiring its own dedicated predicate
(R-POINTER) rather than an accidental side effect of an existing rule's
connector whitelist widening to swallow it -- is still true today and
still worth guarding. `test_pointer_table_heading_not_reachable_via_
existing_rules` is therefore RE-AUTHORED (not removed, not inverted) below
to assert that narrower, still-true property directly at the MECHANISM
level: it calls `rule_mid`, `rule_verb_bare`, `rule_verb_extended`, and
`rule_verb_extended_unconditional` individually (not the union) and pins
them at `False` for both headings, verified live against the shipped
cycle-5 module. This is strictly stronger than either the old pin or a
naive inversion: it pins WHICH mechanism does the capturing (R-POINTER
alone), so a future widening of R-MID or R-VERB-extended that accidentally
started matching these headings independently would be caught here, even
though the union-level result would stay `True` either way and give no
signal.

## Item 13 -- `defined (qualifier)` / `defined to [verb]` (7 rows)

A parenthetical or the connector word `to` immediately after `defined` is
not in R-VERB-extended's whitelist. **7 rows: KY(1), MO(4), PA(1,
repealed, harmless), VA(1, judgment call -- see below).** Two sub-shapes,
same underlying gap: `"[TERM] defined (qualifier)."` (MO x3, PA, VA) and
`"[TERM] defined to [verb]..."` (KY, MO 108.465). **Design: GATED**,
mirroring D-DF's exact two-field `HeadingRule` pattern -- unlike items
10-12, this shape carries a real, evidenced precision risk (the VA row,
see below), so it must NOT ship unconditional.

New symbols: `matches_defined_qualifier_heading(heading: str) -> bool`
(the heading-shape predicate, deliberately LOOSE -- it also matches the VA
row, on purpose, exactly as D-DF's `matches_defined_for_heading` matches
every `defined for` heading regardless of body) and `defines_qualifier_in_
body(body: str) -> bool` (the body-confirmation gate, doing the real
precision work). `defines_qualifier_in_body` is a DELIBERATE SUPERSET of
the existing, already-shipped `defines_in_body` (D-DF, cycle 4): same
quoted-term + lead-in-clause + bounded-gap mechanics, with the defining-
verb whitelist WIDENED to also accept `include(s)`/`shall (not )?
include(s)` -- MO's own drafting idiom (`the word "county" includes...`,
`"employee" shall not include...`) alongside the existing `means`/`shall
mean`/`is defined as`. This is a NEW predicate, not a widening of the
existing `defines_in_body` -- `defines_in_body` stays untouched (60
D-DF-confirmed rows are already pinned against it by
`test_definition_links_us_heading_variants_d_df.py`; widening its verb
whitelist would risk silently changing that already-shipped, already-QA'd
population).

### The VA judgment call -- `STATE_VA_T8.01_C14_A4_S8.01-397.1`

Heading: `Evidence of habit or routine practice; defined (Supreme Court
Rule 2:406 derived from this section)`. **Decision: NEGATIVE GUARD.**

The FULL real body (758 chars, fetched and byte-verified independently of
the manager's 400-char evidence snippet, which cuts off exactly before the
decisive sentence) is:

    A. Admissibility. Evidence of the habit of a person or of the routine
    practice of an organization, ... is relevant to prove that the conduct
    of the person or organization on a particular occasion was in
    conformity with the habit or routine practice. Evidence of prior
    conduct may be relevant to rebut evidence of habit or routine
    practice.

    B. Habit and routine practice defined. A "habit" is a person's regular
    response to repeated specific situations. A "routine practice" is a
    regular course of conduct of a group of persons or an organization in
    response to repeated specific situations.

    C. The provisions of this section are applicable only in civil
    proceedings.

Subsection B genuinely DOES define both terms named in the heading --
this is NOT a bare cross-reference. The honest tension: it uses an "is a"
COPULA construction (`A "habit" is a person's regular response...`), not
`means`/`mean`/`is defined as`/`includes` -- the exact "known, honestly-
stated limit" `defines_in_body`'s own docstring already disclaims
(`is a` is explicitly NOT pinned either direction there). Widening
`defines_qualifier_in_body`'s verb whitelist to bare `is a`/`is an` would
close this ONE row, but `"X" is a ...`/`"X" is an ...` is ordinary English
copula predication, not a specific legal drafting idiom the way `means`/
`shall mean`/`includes` are -- adding it as a general trigger risks a real,
unvalidated false-positive surface across the rest of the corpus that this
sprint has no time to measure (contrast with `include(s)`, validated
narrowly against exactly the 4 MO rows this item targets). Per H-R3's hard
zero-false-positive gate, the safer default under genuine uncertainty is
exclusion, not a broad new unvalidated trigger for one row. **This is
reported as a judgment call made under real ambiguity, not a clean
either-way case** -- see the Planner's report to the manager for the full
reasoning; if the manager/director prefer a VA-specific carve-out instead
of a negative guard, that is a one-line addition to the gate, not a design
change.

Fixtures (byte-identical to the real parquet, all 24 columns, verified via
an independent re-read comparing every column -- see the Planner's
report): `cycle5_defined_and_rows.json` (6), `cycle5_mojibake_rows.json`
(4), `cycle5_pointer_table_rows.json` (9), `cycle5_defined_qualifier_
rows.json` (7).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXDIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load(name: str) -> dict[str, dict]:
    rows = json.loads((FIXDIR / name).read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def _and_rows() -> dict[str, dict]:
    return _load("cycle5_defined_and_rows.json")


def _mojibake_rows() -> dict[str, dict]:
    return _load("cycle5_mojibake_rows.json")


def _pointer_rows() -> dict[str, dict]:
    return _load("cycle5_pointer_table_rows.json")


def _qualifier_rows() -> dict[str, dict]:
    return _load("cycle5_defined_qualifier_rows.json")


# === Item 10 -- `and` connector, UNCONDITIONAL ==============================


@pytest.mark.parametrize(
    "act_id,reason",
    [
        (
            "STATE_MI_C440_AAct-174-of-1962_S440.4952",
            'body: "As used in this section, \\"creditor process\\" means levy, '
            'attachment, garnishment..." -- manager-cited as explicitly genuine',
        ),
        (
            "STATE_IA_TXVI_C701_S701.7",
            "body: 'A public offense is a felony ... Felonies are class \"A\" "
            "felonies...' -- classification/definitional body, manager-cited genuine",
        ),
        (
            "STATE_KS_C79_A11_S79-1130",
            "body: '79-1130. Same; receipts factor defined and described. (a) "
            "General. The receipts factor is a fraction...' -- genuine substantive "
            "definition",
        ),
        (
            "STATE_ND_T29_C29-17_S29-17-33",
            "body: 'A challenge for cause is an objection to a particular juror "
            "and is either: 1. General... 2. Particular...' -- genuine definition",
        ),
        (
            "STATE_NV_Tpreliminary-chapter_C0_S0.040",
            'body: \'"physician" means a person who engages in the practice of '
            "medicine...' -- genuine self-definition",
        ),
    ],
)
def test_defined_and_connector_recognized_unconditionally(act_id, reason):
    from app.definition_links.rules.us_heading_variants import (
        matches_heading_variant,
        matches_heading_variant_unconditional,
    )

    row = _and_rows()[act_id]
    assert "defined and" in row["section_title"].lower()
    assert matches_heading_variant_unconditional(row["section_title"]) is True, (
        f"{row['section_title']!r}: {reason}"
    )
    assert matches_heading_variant(row["section_title"]) is True


def test_defined_and_connector_captures_louisiana_body_empty_row_h_r1():
    """H-R1: the heading must be captured even though this row's body NEVER
    mentions "pollution" (ledger L4, 14/45 of item 10's population) -- do
    NOT gate this rule on body yield. Body-empty is expected and correct,
    same accepted category as the pinned CO/NV/AK zero-yield hand-offs."""
    from app.definition_links.rules.us_heading_variants import (
        matches_heading_variant_unconditional,
    )

    row = _and_rows()["STATE_LA_Crevised-statutes_T38_S3009"]
    assert row["section_title"] == (
        "Constructions which would impede flow of water in watershed prohibited; "
        "pollution defined and prohibited; penalties fixed for violations"
    )
    assert "pollution" not in row["text"].lower(), (
        "precondition: this row's body must genuinely never mention the term, or "
        "this isn't testing H-R1's non-gating requirement"
    )
    assert matches_heading_variant_unconditional(row["section_title"]) is True, (
        "heading recognition (U1) is required regardless of body yield -- H-R1"
    )


# === Item 11 -- RI mojibake dash/quote normalization =========================


@pytest.mark.parametrize(
    "act_id,reason",
    [
        (
            "STATE_RI_T24_C24-8_S24-8-27",
            'body: "The word bridge as used in this chapter shall be a structure '
            'including supports..." -- genuine self-definition of "bridge"',
        ),
        (
            "STATE_RI_T44_C44-18_S44-18-15.2",
            'body: \'(a) As used in this section: (1) Remote seller means any '
            "seller...' -- genuine, QA cycle 3 hand-verified",
        ),
        (
            "STATE_RI_T5_C5-11_S5-11-1.1",
            'body: \'(a) For purposes of this chapter: (1) Door-to-door '
            "salespersons means persons who deliver goods...' -- genuine, and "
            "this heading ALSO exercises the mojibake `and`-joined multi-term list "
            "shape (\"Hawkers,\" \"peddlers,\" and \"door-to-door salespersons\")",
        ),
    ],
)
def test_ri_mojibake_dash_and_quotes_recognized(act_id, reason):
    from app.definition_links.rules.us_heading_variants import (
        matches_heading_variant,
        matches_heading_variant_unconditional,
    )

    row = _mojibake_rows()[act_id]
    assert "\x80\x94" in row["section_title"], (
        "precondition: this row must carry the real mojibake em-dash byte "
        "sequence, or this isn't testing the mojibake fix"
    )
    assert matches_heading_variant_unconditional(row["section_title"]) is True, (
        f"{row['section_title']!r}: {reason}"
    )
    assert matches_heading_variant(row["section_title"]) is True


def test_ri_mojibake_negative_guard_indefinite_references_to_trustee():
    """Ledger L6's required negative guard. `\\x80\\x9c`/`\\x80\\x9d` mojibake
    curly quotes surround "trustee", but this heading's `defin` miss-pool
    membership comes from "Indefinite" (morphology exclusion), not from any
    `defined`/`definition(s)` token -- no rule, mojibake-normalized or not,
    should ever fire here. Honesty note: manager-verified LIVE against the
    currently-shipped module (before this cycle's fix) that this row
    already evaluates False today -- this test is a PRECISION PIN against
    an over-broad fix, not a RED-for-feature-absence pin, included because
    the contract explicitly requires it."""
    from app.definition_links.rules.us_heading_variants import (
        matches_heading_variant,
        matches_heading_variant_unconditional,
    )

    row = _mojibake_rows()["STATE_RI_T34_C34-11_S34-11-37"]
    assert row["section_title"] == '§ 34-11-37. Indefinite references to \x80\x9ctrustee\x80\x9d.'
    assert "defined" not in row["section_title"].lower(), (
        "precondition: no 'defined' verb anywhere in this heading -- its miss-pool "
        "membership is purely the 'Indefinite' morphology false trigger"
    )
    assert matches_heading_variant_unconditional(row["section_title"]) is False
    assert matches_heading_variant(row["section_title"]) is False


# === Item 12 -- D-MT-E1 pointer-table headings, UNCONDITIONAL ================


@pytest.mark.parametrize(
    "act_id,reason",
    [
        (
            "STATE_CO_T5_A1_P3_S5-1-303",
            '"Index of definitions in code" -- body is a cross-reference table, '
            '\'"Actuarial method" section 5-1-301 (1) ... "Administrator" sections '
            "5-1-301 (2) and 5-6-103 ...' (dozens of entries)",
        ),
        (
            "STATE_CT_T36a_C664_S36a-3",
            '"Other defined terms." -- body: \'"Account". Sections 36a-155 and '
            "36a-365 . \"Additional proceeds\". Section 36a-746e . ...'",
        ),
        (
            "STATE_IA_TXIII_C537_S537.1303",
            '"Other defined terms." -- body: \'Other defined terms in this '
            'chapter and the sections in which they appear are: (1) "Closing '
            "costs\". Section 537.2501...'",
        ),
        (
            "STATE_ME_T9-A_C1_S1-303",
            '"Other defined terms" -- body: \'Other definitions appearing in '
            'this Act and the sections in which they appear are: "Computational '
            "period\" Section 2-510 ...'",
        ),
        (
            "STATE_OK_T14A_S14A-1-303",
            '"Index of definitions in act" -- body: \'Definitions in this title '
            'and the sections in which they appear are: "Actuarial method" - '
            "Section 1-301(1) ...' -- manager's own additional find beyond QA "
            "cycle 3's 7-row count",
        ),
        (
            "STATE_SC_T37_C3_S37-3-103",
            '"Index of definitions." -- body: \'The following definitions apply '
            'to this title and appear in this chapter as follows: "Consumer '
            'Loan"-Section 37-3-104 ...\'',
        ),
        (
            "STATE_SC_T37_C1_S37-1-303",
            '"Index of definitions in title." -- same SC pointer-table '
            "convention, a second chapter",
        ),
        (
            "STATE_SC_T37_C2_S37-2-103",
            '"Index of definitions in chapter." -- same SC pointer-table '
            "convention, a third chapter",
        ),
        (
            "STATE_WY_T40_C14_S40-14-142",
            '"Index of definitions" -- body: \'(a) Definitions in this act and '
            'the sections in which they appear are: (i) "Actuarial method"-- '
            "W.S. 40-14-140(a)(i) ...' -- manager's own additional find beyond "
            "QA cycle 3's 6-state count",
        ),
    ],
)
def test_pointer_table_heading_recognized_unconditionally(act_id, reason):
    from app.definition_links.rules.us_heading_variants import (
        matches_heading_variant,
        matches_heading_variant_unconditional,
        matches_pointer_table_heading,
    )

    row = _pointer_rows()[act_id]
    assert matches_pointer_table_heading(row["section_title"]) is True, (
        f"{row['section_title']!r}: {reason}"
    )
    assert matches_heading_variant_unconditional(row["section_title"]) is True
    assert matches_heading_variant(row["section_title"]) is True


def test_pointer_table_capture_is_via_dedicated_predicate_not_existing_rules():
    """RE-AUTHORED (plan6) from `test_pointer_table_heading_not_reachable_
    via_existing_rules` -- see this module's docstring, section "Planner
    note (plan6) -- premise update for the item-12 negative pin", for the
    full history of why the original union-level assertion (`matches_
    heading_variant_unconditional(...) is False`) went stale the moment
    item 12 landed and folded `matches_pointer_table_heading` into that
    same union: it now directly contradicts `test_pointer_table_heading_
    recognized_unconditionally` above on the identical two inputs, so it
    could not simply be flipped to `True` either -- that would only
    duplicate the positive test.

    What survives is the NARROWER, still-true, non-redundant claim: the
    pointer-table shape is captured SPECIFICALLY by R-POINTER
    (`matches_pointer_table_heading`), not by any accidental widening of
    R-MID's preposition-guarded tail-token check or R-VERB-bare/extended's
    `defined`-ending checks. Pinned here at the MECHANISM level, by calling
    those rule functions directly rather than the union, verified live
    against the shipped cycle-5 module (both return `False` for both
    headings today)."""
    from app.definition_links.rules.us_heading_variants import (
        rule_mid,
        rule_verb_bare,
        rule_verb_extended,
        rule_verb_extended_unconditional,
    )

    rows = _pointer_rows()
    other_defined_terms = rows["STATE_CT_T36a_C664_S36a-3"]["section_title"]
    index_of_definitions = rows["STATE_CO_T5_A1_P3_S5-1-303"]["section_title"]

    for heading in (other_defined_terms, index_of_definitions):
        # "Other defined terms." -- last tail token is "terms", not
        # "defined"; "Index of definitions in code" -- "definitions" IS a
        # mid tail token, but immediately preceded by "of" -- the SAME
        # preposition-exclusion guard that protects the D-HG 245-row
        # cluster suppresses it here too. Neither sub-family reaches
        # R-MID or R-VERB-bare/extended independently of R-POINTER.
        assert rule_mid(heading) is False, (
            f"{heading!r}: R-MID's preposition-guarded tail-token check must "
            "not independently fire on the pointer-table shape"
        )
        assert rule_verb_bare(heading) is False, (
            f"{heading!r}: last tail token is not exactly 'defined'"
        )
        assert rule_verb_extended(heading) is False, (
            f"{heading!r}: R-VERB-extended's connector whitelist must not "
            "independently fire on the pointer-table shape"
        )
        assert rule_verb_extended_unconditional(heading) is False, (
            f"{heading!r}: same, unconditional variant"
        )


# === Item 13 -- `defined (qualifier)` / `defined to [verb]`, GATED ==========


@pytest.mark.parametrize(
    "act_id,reason",
    [
        (
            "STATE_KY_TIX_C68_S68.002",
            '"...defined to apply to charter county governments" -- body: '
            '\'As used in this chapter... (1) "County" shall also mean a charter '
            "county government...' -- genuine, confirms via the existing `mean` "
            "verb (already in `defines_in_body`'s whitelist)",
        ),
        (
            "STATE_MO_C95_S95.551",
            '"Employee defined (St. Louis City)." -- body: \'The term '
            '"employee" shall not include any appointed or elected officers...\' '
            "-- genuine, confirms only via the WIDENED `include`-family verb",
        ),
        (
            "STATE_MO_C95_S95.465",
            '"Mayor and two houses of legislation defined (cities over '
            '100,000)." -- body: \'the word "mayor" shall include the chief '
            "magistrate...' -- genuine, `include`-family",
        ),
        (
            "STATE_MO_C108_S108.465",
            '"County defined to include certain cities." -- body: \'the word '
            '"county" includes the City of St. Louis...\' -- genuine, '
            "`include`-family, also the `defined to [verb]` heading sub-shape",
        ),
        (
            "STATE_MO_C50_S50.770",
            '"Supplies defined (second class and certain first class '
            'counties)." -- body: \'The word "supplies"... means materials, '
            "equipment...' -- genuine, confirms via the existing `means` verb",
        ),
    ],
)
def test_defined_qualifier_heading_with_confirming_body_is_captured(act_id, reason):
    from app.definition_links.rules.us_heading_variants import (
        defines_qualifier_in_body,
        matches_defined_qualifier_heading,
    )

    row = _qualifier_rows()[act_id]
    assert matches_defined_qualifier_heading(row["section_title"]) is True, (
        f"{row['section_title']!r}: heading is a 'defined (qualifier)'/'defined to "
        "[verb]' shape"
    )
    assert defines_qualifier_in_body(row["text"]) is True, reason
    assert (
        matches_defined_qualifier_heading(row["section_title"])
        and defines_qualifier_in_body(row["text"])
    ) is True


def test_defined_qualifier_heading_repealed_pa_row_is_harmless_non_capture():
    """PA's row matches the heading shape but its body is an empty repeal
    stub -- naturally fails body confirmation, exactly as the contract
    describes it ("1 repealed, harmless"). Not a negative-guard PRECISION
    concern (there is no content to falsely capture), just a documented
    non-capture."""
    from app.definition_links.rules.us_heading_variants import (
        defines_qualifier_in_body,
        matches_defined_qualifier_heading,
    )

    row = _qualifier_rows()["STATE_PA_T51_C71_S7101"]
    assert row["section_title"] == "Soldier defined (Repealed)."
    assert matches_defined_qualifier_heading(row["section_title"]) is True
    assert defines_qualifier_in_body(row["text"]) is False, (
        "body: '2020 Repeal. Section 7101 was repealed October 29, 2020...' -- no "
        "quoted term, no defining verb of any kind"
    )


def test_defined_qualifier_heading_va_habit_evidence_row_is_a_negative_guard():
    """The Planner's judgment call (see module docstring's 'The VA judgment
    call' section for the full reasoning and the real 758-char body text).
    Decision: NEGATIVE GUARD. The body's subsection B DOES define both
    named terms, but only via an 'is a' copula ('A "habit" is a person's
    regular response to repeated specific situations...'), which
    `defines_qualifier_in_body` deliberately does NOT recognize (same
    conservative choice `defines_in_body` already made for the identical
    shape, per its own docstring's 'Known, honestly-stated limits') --
    widening to bare 'is a'/'is an' would be a broad, unvalidated new
    trigger for the sake of one ambiguous row, a real precision risk under
    H-R3's hard gate. This is a genuinely close call, reported as such, not
    a clean exclusion."""
    from app.definition_links.rules.us_heading_variants import (
        defines_qualifier_in_body,
        matches_defined_qualifier_heading,
    )

    row = _qualifier_rows()["STATE_VA_T8.01_C14_A4_S8.01-397.1"]
    assert row["section_title"] == (
        "Evidence of habit or routine practice; defined (Supreme Court Rule 2:406 "
        "derived from this section)"
    )
    assert 'A "habit" is a person' in row["text"], (
        "precondition: the body's real definitional sentence must be present, or "
        "this test is not exercising the actual judgment call"
    )
    assert matches_defined_qualifier_heading(row["section_title"]) is True, (
        "the heading-shape predicate is deliberately LOOSE -- it matches this row "
        "on purpose, exactly as D-DF's matches_defined_for_heading matches every "
        "'defined for' heading regardless of body; precision is the body gate's job"
    )
    assert defines_qualifier_in_body(row["text"]) is False, (
        "body defines both terms via an 'is a' copula, not means/mean/is defined "
        "as/includes -- deliberately unrecognized, see module docstring"
    )
    assert (
        matches_defined_qualifier_heading(row["section_title"])
        and defines_qualifier_in_body(row["text"])
    ) is False


# === Decomposition coherence (D-DF's equivalence property, re-confirmed) ===


def test_matches_heading_variant_equals_unconditional_or_defined_for_still_holds_after_cycle5():
    """D-DF pinned `matches_heading_variant(h) == matches_heading_variant_
    unconditional(h) or matches_defined_for_heading(h)` for every heading
    (`test_definition_links_us_heading_variants_d_df.py`). Items 10/11/12/15
    do NOT change what this union MEANS -- they widen the SAME regexes
    `_rule_verb_extended`/`_rule_verb_extended_unconditional` (and add
    `matches_pointer_table_heading` into BOTH `matches_heading_variant` and
    `matches_heading_variant_unconditional`'s own bodies, item 12) IN
    LOCKSTEP, so the two-way decomposition must still hold exactly.
    **This is a real design constraint on the Developer's implementation,
    not just a test**: widening `_VERB_EXTENDED_UNCONDITIONAL_RE` without
    making the matching change to `_VERB_EXTENDED_RE` (or vice versa) would
    break this equivalence for every item-10/11/15 row. Item 13's new
    `matches_defined_qualifier_heading`/`defines_qualifier_in_body` pair is
    DELIBERATELY EXCLUDED from `matches_heading_variant`'s union: unlike
    `for` (which WAS already inside the original `_VERB_EXTENDED_RE`
    whitelist before D-DF split it out), the qualifier/to-verb shape was
    NEVER part of `matches_heading_variant`'s historical meaning at all --
    there is nothing to preserve, so it is a wholly new, separate
    predicate pair, checked independently above, not folded into this
    equivalence."""
    from app.definition_links.rules.us_heading_variants import (
        matches_defined_for_heading,
        matches_heading_variant,
        matches_heading_variant_unconditional,
    )

    headings: list[str] = []
    for loader in (_and_rows, _mojibake_rows, _pointer_rows):
        headings += [row["section_title"] for row in loader().values()]

    assert len(headings) >= 19, "sanity check: covers items 10/11/12's full new population"

    for heading in headings:
        full = matches_heading_variant(heading)
        decomposed = matches_heading_variant_unconditional(heading) or matches_defined_for_heading(
            heading
        )
        assert full == decomposed, (
            f"{heading!r}: the decomposition must still reproduce matches_heading_"
            "variant's behavior exactly after cycle 5's additions"
        )
