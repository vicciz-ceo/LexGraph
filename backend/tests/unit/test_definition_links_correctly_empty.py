"""RED unit tests -- sprint 2026-08-04-defs-us-markers, planner pass 2,
priority 1 (gate U4, ruling U-R3).

Defines the REQUIRED contract for a new, not-yet-implemented module:

    backend/app/definition_links/correctly_empty.py

        from dataclasses import dataclass
        from typing import Literal

        CorrectlyEmptyReason = Literal["terminal_status", "cross_reference"]

        @dataclass(frozen=True)
        class CorrectlyEmptyResult:
            is_correctly_empty: bool
            reason: CorrectlyEmptyReason | None  # None iff is_correctly_empty is False

        def classify_correctly_empty(body_text: str) -> CorrectlyEmptyResult: ...

Gate U4 (the director's absolute zero-miss bar) requires every
Definitions-headed, zero-candidate section to be EITHER captured or
PROVEN correctly-empty. This module is the "proven correctly-empty" half
-- QA's independent, callable classifier, not a Developer's unverified
prose claim (ruling U-R3). It is a PURE function of `body_text` alone;
its caller is responsible for having already confirmed (a) the section's
own heading is a recognized Definitions heading (`is_definitions_heading`)
and (b) `extract_definitions_from_section` on this body already returned
zero candidates -- `classify_correctly_empty` does not re-check either
precondition and its result is meaningless if called outside that
context.

Classification is applied in priority order (first match wins):

  1. TERMINAL_STATUS -- the ENTIRE (whitespace-stripped) body is exactly
     one of `Repealed.` / `Expired.` / `Reserved.` / `Renumbered.` /
     `Omitted.` / `Vacant.` / `Recodified as ...` (optionally bracket-
     wrapped, optional trailing period, case-insensitive) -- the law
     itself says this section carries no operative text at all. Measured
     this pass (real DC data): 178/332 (53.6%) of DC's zero-candidate set
     is this class alone -- DC's single largest "miss" component, and
     entirely NOT a miss.

  2. CROSS_REFERENCE -- the ENTIRE (whitespace-stripped) body, after
     removing an optional trailing `History: ...` amendment-citation
     annotation (a real, further-non-operative tail -- see the WI rows
     below), is NOTHING BUT a single short sentence stating that the
     definitions governing this text live in ANOTHER citation (pattern:
     `(the )?definitions? (contained |set forth )?in <citation>
     (apply|shall apply|govern|are applicable)`, matched from the start).
     **The "entire body" requirement is load-bearing, not decorative --
     see the NEGATIVE tests below.**

  3. otherwise -- NOT correctly empty. A MISS: `is_correctly_empty=False`,
     `reason=None`.

## Why "entire body", not "starts with" (a correction to this sprint's
## own pass-1 log, found and proven this pass)

Pass 1's log described the cross-reference rule as matched "at the START
of the stripped body" -- with no requirement that the match consume the
rest of the body. Applying that literal rule to the FULL real corpus
(not just pass 1's WI/WY spot-checks) this pass found it is dangerously
over-broad: it misclassifies `STATE_WA_T47_C14_S020` -- wave 1's OWN
flagship WA test row, with 2 real captured terms -- as "correctly empty",
because its body opens "The definitions set forth in this section apply
throughout this chapter." (a SELF-referential preamble: the definitions
are right HERE) before its real content. Measured full-corpus: **727 of
WA's 734 naive-rule hits (99.0%) share this same self-referential shape,
each followed by real defining content** -- pass 1's reported "WA
734/1,778 (41.3%) cross-reference" figure was overwhelmingly wrong; the
corrected rate is **WA 4/1,778 (0.2%)**. Two real VA rows in this
fixture (46 and 7 genuine definitions respectively) prove the same
failure mode independently. This is exactly the danger ruling U-R3
warns about -- "not asserted by the Developer to explain away a residue"
-- caught here, before implementation, with real rows. Full corpus
numbers: sprint log `## P2`.

All rows below are REAL, vendored verbatim (byte-verified against the
source parquet this pass) into `us_markers_correctly_empty_rows.json`;
the wave-1 defect fixture is reused for its own negative rows (no new
vendoring needed for those). No test here reads the corpus snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"
CORRECTLY_EMPTY_FIXTURE = FIXTURES_DIR / "us_markers_correctly_empty_rows.json"
WAVE1_FIXTURE = FIXTURES_DIR / "us_markers_wave1_rows.json"


def _load(path: Path) -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(path.read_text(encoding="utf-8"))}


def _classify(body_text: str):
    # `app.definition_links.correctly_empty` does not exist yet -- this
    # import is EXPECTED to raise `ModuleNotFoundError` right now,
    # failing every test in this file individually at RUN time (not at
    # collection time -- deferred here on purpose so one missing module
    # never aborts collection of the rest of the suite). That per-test
    # failure IS this priority's proven-RED state (gate U4, ruling
    # U-R3): there is no behavior to call yet, only a contract to define
    # -- see this file's module docstring for the exact required module
    # path, dataclass shape, and function signature a Developer must
    # implement to turn this file green.
    from app.definition_links.correctly_empty import classify_correctly_empty

    return classify_correctly_empty(body_text)


# --- Class 1: terminal-status bodies -----------------------------------


@pytest.mark.parametrize(
    "act_id",
    [
        "STATE_DC_T47_C28_S47-2843",  # body: "Repealed."
        "STATE_DC_T42_C36_S42-3631",  # body: "Expired."
        "STATE_DC_T2_C3_S2-308.13",  # body: "Recodified as § 2-381.01 ."
        "STATE_DC_T33_C1_S33-112.03",  # body: "Reserved." -- see fixture README
        # caveat: this row's OWN heading is "[Reserved]", not itself
        # Definitions-shaped (verified across all 53 real state files --
        # no row combines a Reserved./Renumbered./Omitted./Vacant. body
        # with a Definitions-recognized heading anywhere in the corpus).
        # Vendored anyway: classify_correctly_empty is a pure function of
        # body_text, and this is REAL text proving the "Reserved." literal
        # shape genuinely exists in the corpus's terminal-status vocabulary.
    ],
)
def test_real_terminal_status_bodies_are_correctly_empty(act_id):
    rows = _load(CORRECTLY_EMPTY_FIXTURE)
    body = rows[act_id]["text"]
    result = _classify(body)
    assert result.is_correctly_empty is True, f"{act_id}: {body!r} must be correctly-empty"
    assert result.reason == "terminal_status", (
        f"{act_id}: expected reason='terminal_status', got {result.reason!r}"
    )


# --- Class 2: genuine cross-reference bodies ----------------------------


@pytest.mark.parametrize(
    "act_id",
    [
        "STATE_WI_C851_S851.002",  # "...applies to chs. 851 to 882." + History tail
        "STATE_WY_T99_C3_S99-3-1101",  # "The definitions in W.S. 99-3-101 apply..."
        "STATE_WA_T43_C99N_S010",  # "The definitions in RCW 36.102.010 apply..."
    ],
)
def test_real_genuine_cross_reference_bodies_are_correctly_empty(act_id):
    rows = _load(CORRECTLY_EMPTY_FIXTURE)
    body = rows[act_id]["text"]
    result = _classify(body)
    assert result.is_correctly_empty is True, f"{act_id}: {body!r} must be correctly-empty"
    assert result.reason == "cross_reference", (
        f"{act_id}: expected reason='cross_reference', got {result.reason!r}"
    )


# --- NEGATIVE class: the critical guard ---------------------------------
# "A classifier that says 'everything is fine' must fail these tests
# loudly" (director's brief for this pass). Each row here superficially
# resembles a cross-reference (opens with a "definitions ... apply/shall
# apply" citation-shaped sentence) but is a REAL, substantial miss.


def test_wave1_flagship_wa_row_is_not_correctly_empty_despite_self_referential_preamble():
    """`STATE_WA_T47_C14_S020` -- wave 1's OWN clean-rescue test row.
    2 real terms (Right-of-way, Airspace) sit immediately after a
    self-referential "The definitions set forth in this section apply
    throughout this chapter." preamble. A classifier that stops at
    "starts with a definitions-apply sentence" (pass 1's literal rule)
    would wrongly call this correctly-empty and silently erase a proven,
    real miss -- exactly the residue-hiding failure mode U-R3 exists to
    prevent."""
    rows = _load(CORRECTLY_EMPTY_FIXTURE)
    body = rows["STATE_WA_T47_C14_S020"]["text"]
    result = _classify(body)
    assert result.is_correctly_empty is False, (
        "this row has 2 real captured terms (see "
        "test_us_markers_wave1_inline_quote_fallback.py) -- must be a MISS, not "
        "correctly-empty"
    )
    assert result.reason is None


def test_va_self_referential_do_not_apply_row_with_46_real_definitions_is_not_correctly_empty():
    """`STATE_VA_T29.1_C7_A2.1_S29.1-733.2` -- real VA watercraft-titling
    Definitions section, 9,658 chars, 46 real quoted `"Term" means ...`
    definitions (Abandoned watercraft, Agreement, Barge, ... Watercraft,
    Written certificate of title). Body opens "The definitions in this
    section do not apply to any Virginia or federal law governing
    licensing..." -- a citation-shaped sentence containing the literal
    word "apply", immediately followed by substantial real content."""
    rows = _load(CORRECTLY_EMPTY_FIXTURE)
    body = rows["STATE_VA_T29.1_C7_A2.1_S29.1-733.2"]["text"]
    assert body.count('" means') >= 40, "sanity: this row must carry its 46 real definitions"
    result = _classify(body)
    assert result.is_correctly_empty is False, (
        "this row has 46 real quoted definitions -- must be a MISS, not correctly-empty"
    )
    assert result.reason is None


def test_va_real_other_citation_preamble_with_7_real_definitions_is_not_correctly_empty():
    """`STATE_VA_T58.1_SI_C17_A9_S58.1-1735` -- real VA rental-tax
    Definitions section, 3,726 chars, 7 real quoted definitions (Daily
    rental vehicle, Gross proceeds, Mobile office, Motor vehicle, Rental,
    Rental in the Commonwealth, Rentor). Body opens "The definitions in
    § 46.2-1408 shall apply, mutatis mutandis, to this article." -- names
    a REAL other citation (same surface shape as the genuine
    cross-reference rows above) but is followed by substantial operative
    content of its OWN, unlike the genuine cross-reference rows."""
    rows = _load(CORRECTLY_EMPTY_FIXTURE)
    body = rows["STATE_VA_T58.1_SI_C17_A9_S58.1-1735"]["text"]
    assert body.count('" means') >= 5, "sanity: this row must carry its 7 real definitions"
    result = _classify(body)
    assert result.is_correctly_empty is False, (
        "this row has 7 real quoted definitions -- must be a MISS, not correctly-empty "
        "(naming a real OTHER citation is not sufficient on its own -- the classifier "
        "must also confirm nothing operative follows it)"
    )
    assert result.reason is None


@pytest.mark.parametrize(
    "act_id",
    [
        "STATE_VA_T23.1_SI_C3_S23.1-300",
        "STATE_VA_T4.1_SII_C6_S4.1-600",
        "STATE_WA_T9A_C04_S110",
        "USC_T16_C65_S4503d",
        "USC_T15_C12_S431",
    ],
)
def test_wave1_defect_rows_are_not_correctly_empty(act_id):
    """Reuses wave 1's own fixture rows (no new vendoring) as further
    negative evidence: every one of these is a real, substantial,
    already-proven miss (see test_us_markers_wave1_inline_quote_fallback.py)
    -- none may be misclassified as correctly-empty."""
    rows = _load(WAVE1_FIXTURE)
    body = rows[act_id]["text"]
    result = _classify(body)
    assert result.is_correctly_empty is False, f"{act_id} is a real, substantial miss"
    assert result.reason is None
