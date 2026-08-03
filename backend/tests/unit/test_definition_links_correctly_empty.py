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

## Bounce cycle: a real defect in the SHIPPED module, found by the
## manager's adversarial full-corpus sweep (ruling U-R7)

After the Developer implemented `correctly_empty.py` against this file's
original 15 tests (all green), the manager ran the classifier over every
Definitions-headed, zero-candidate section in the REAL, FULL corpus (all
53 jurisdiction files -- 34,241 such sections). 228 (0.67%) are called
correctly-empty by the shipped module; of those, **exactly 4, all WA, are
WRONG** -- each carries substantial real definitional content (2-12
`"Term" means ...` entries apiece). Every other jurisdiction's verdicts
are clean; the module IS strongly miss-biased overall (the bias ruling
U-R3 demands) -- this is a narrow, specific regex defect, not a
systemic one, and the fix (owned by the Developer, not this file) must
not overcorrect into never returning `cross_reference` at all, or gate
U4 becomes unfalsifiable in the other direction.

**Root cause, diagnosed by reading the shipped regex** (`_CROSS_REFERENCE_
RE`'s citation group, `[^\n]+?`, is lazy but otherwise unrestricted, and
the trailing-clause group tolerates any non-period character freely) --
confirmed by the fact that **all 4 real offending rows have ZERO newline
characters** (single-line bodies, unlike the genuine cross-reference rows
above, which are short single sentences with nothing to swallow). Two
distinct exploitable shapes, both present among the 4 real rows:

  (a) The body OPENS with a self-referential "The definitions in this
      section apply..." preamble, contains real definitions, and
      (coincidentally, or via an unrelated-content data-artifact --
      see the test docstrings below) CLOSES with a second, later
      occurrence of `apply`/`govern`/`are applicable`. Because there is
      no `\n` to stop it, `[^\n]+?` backtracks straight through the real
      content to reach that second occurrence, and `fullmatch` succeeds.
  (b) The body has only the ONE self-referential trigger, but its real
      entries are separated by SEMICOLONS, not periods -- the trailing-
      clause group's `[^.\n]` branch swallows semicolons, quotes, digits,
      and parens without complaint, so the match succeeds even with only
      one trigger occurrence, all the way to the body's own final period.

A fix that only special-cases "reject if the trigger phrase appears
twice" would close shape (a) but NOT shape (b) -- this is why the general
guard test below is required, not just the 4 named-row tests: it
recombines REAL content (with real, varied punctuation) with a genuine
trailing cross-reference sentence PROGRAMMATICALLY, at test-run time, so
it cannot be satisfied by a fix tuned to the 4 exact byte-strings above.
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


# --- BOUNCE CYCLE: the manager's adversarial full-corpus sweep found ----
# 4 real, false "correctly_empty" verdicts in the SHIPPED module (ruling
# U-R7). See this file's module docstring ("Bounce cycle" section) for
# the root-cause diagnosis (single-line bodies defeat the `[^\n]`
# newline boundary the shipped regex relies on, two distinct ways).


@pytest.mark.parametrize(
    "act_id, min_means_count",
    [
        # (a) opens self-referential, real content, closes on a SECOND
        # real "apply"/"applicable" occurrence later in the same line.
        ("STATE_WA_T82_C23A_S010", 7),  # Petroleum product, Possession, Control, ...
        # (a) variant: the row's OWN text field concatenates a SECOND,
        # unrelated section's content (a real, non-injected vaquill
        # data-artifact, not this test's concern) whose own trailing
        # "...are applicable to a disability insurance producer." is what
        # the regex latches onto -- proves the defect doesn't even need a
        # genuinely-matching second citation, just the bare trigger words.
        ("STATE_WA_T18_C44_S011", 11),  # Committee, Department, Designated escrow officer, ...
        # (a) variant: same unrelated-content-concatenation artifact,
        # closes on "...do not apply with respect to..." (negated, like
        # pass 1's VA "do not apply" false positive -- the regex does not
        # parse negation, it only looks for the bare word "apply").
        ("STATE_WA_T70A_C30_S010", 12),  # Approved shellfish tag or label, Commercial quantity, ...
        # (b) ONLY the self-referential trigger occurs -- real entries are
        # semicolon-separated with no internal periods, so the shipped
        # regex's permissive `[^.\n]` trailing-clause class swallows all
        # of it without ever needing a second trigger occurrence.
        ("STATE_WA_T70_C28_S008", 2),  # Department, Secretary, Tuberculosis control
    ],
)
def test_real_wa_false_positive_rows_are_not_correctly_empty(act_id, min_means_count):
    """The 4 real rows the manager's full-corpus sweep found misclassified
    by the shipped module (34,241 zero-candidate sections corpus-wide, 228
    called correctly-empty, exactly these 4 wrong -- all WA, all the same
    class of newline-dependent regex defect). Each genuinely opens with a
    self-referential "The definitions in this section apply..." preamble
    -- textbook cross-reference SHAPE -- but carries substantial real
    defining content that the classifier must not discard."""
    rows = _load(CORRECTLY_EMPTY_FIXTURE)
    body = rows[act_id]["text"]
    assert body.count('" means') >= min_means_count, (
        f"sanity: {act_id} must carry its real definitions"
    )
    assert "\n" not in body, (
        f"sanity: {act_id} must be the real single-line body this defect depends on"
    )
    result = _classify(body)
    assert result.is_correctly_empty is False, (
        f"{act_id} has {body.count('\" means')}+ real quoted definitions -- must be a MISS, "
        "not correctly-empty, regardless of its self-referential opening"
    )
    assert result.reason is None


def _real_content_prefix(body: str, cut_marker: str) -> str:
    """Return everything in `body` up to (excluding) the first occurrence
    of `cut_marker`, trailing-whitespace-stripped. Used only to drop a
    row's OWN trailing content (its accidental second trigger, or a
    concatenated-unrelated-section artifact) before recombining the row's
    genuine leading real content with a DIFFERENT row's genuine
    cross-reference sentence below -- both halves are REAL vendored text,
    the recombination happens at test-run time, not vendored as if it
    were itself one real row."""
    return body[: body.index(cut_marker)].rstrip()


def test_general_guard_real_content_before_any_genuine_cross_reference_suffix_is_never_correctly_empty():
    """The general form of the bounce-cycle defect (see module docstring):
    ANY body carrying real, substantial defining content before a
    trailing genuine cross-reference sentence must classify as a MISS --
    not merely the 4 exact byte-strings above. Each case below
    recombines a REAL leading fragment (self-referential opening + real
    definitions, sliced from one of the 4 rows above, its own accidental
    trailing content dropped) with a DIFFERENT row's REAL, independently-
    verified genuine cross-reference sentence, at test-run time. A fix
    tuned only to recognize the 4 named rows above (e.g. by hard-coding
    their exact text, or by only checking "does the trigger phrase occur
    exactly once") would still fail these -- proving the fix is general,
    not a memorized lookup table. All 4 combinations below are confirmed
    to reproduce the SAME false-positive against the currently shipped
    module (not merely a hypothetical)."""
    rows = _load(CORRECTLY_EMPTY_FIXTURE)

    t82_prefix = _real_content_prefix(
        rows["STATE_WA_T82_C23A_S010"]["text"], " (6) Except for terms defined"
    )
    t18_prefix = _real_content_prefix(rows["STATE_WA_T18_C44_S011"]["text"], "(1) Insurance producer")
    t70a_prefix = _real_content_prefix(
        rows["STATE_WA_T70A_C30_S010"]["text"], "(1) Pursuant to the federal clean air act"
    )
    t70c28_full = rows["STATE_WA_T70_C28_S008"]["text"]  # no accidental trailing content to drop

    wi_crossref = rows["STATE_WI_C851_S851.002"]["text"]
    wy_crossref = rows["STATE_WY_T99_C3_S99-3-1101"]["text"]
    wa_genuine_crossref = rows["STATE_WA_T43_C99N_S010"]["text"]

    combos = {
        "t82_real_content + WY_genuine_crossref": t82_prefix + " " + wy_crossref,
        "t18_real_content + WA_genuine_crossref": t18_prefix + " " + wa_genuine_crossref,
        "t70a_real_content + WI_genuine_crossref_with_history_tail": t70a_prefix + " " + wi_crossref,
        "t70c28_real_content + WY_genuine_crossref": t70c28_full + " " + wy_crossref,
    }

    for name, body in combos.items():
        result = _classify(body)
        assert result.is_correctly_empty is False, (
            f"{name}: a REAL defining-content prefix followed by a REAL genuine "
            f"cross-reference sentence must be a MISS, not correctly-empty -- got "
            f"{result!r} for body ending {body[-120:]!r}"
        )
        assert result.reason is None


def test_genuine_cross_reference_class_is_not_disabled_by_the_fix():
    """Guard against overcorrection (director's explicit instruction on
    this bounce cycle): a fix that makes `cross_reference` NEVER fire
    again would also make gate U4 unfalsifiable -- these 4 already-green
    positives (see `test_real_genuine_cross_reference_bodies_are_correctly_
    empty` above) must stay green. This is a regression guard, not new
    evidence -- restated here so a future regex change that trades the
    false-positive problem for a false-negative one fails loudly in THIS
    file, next to the defect it must not overcorrect."""
    rows = _load(CORRECTLY_EMPTY_FIXTURE)
    for act_id in ("STATE_WI_C851_S851.002", "STATE_WY_T99_C3_S99-3-1101", "STATE_WA_T43_C99N_S010"):
        body = rows[act_id]["text"]
        result = _classify(body)
        assert result.is_correctly_empty is True, (
            f"{act_id}: must remain correctly-empty -- the fix must not disable this class"
        )
        assert result.reason == "cross_reference"
