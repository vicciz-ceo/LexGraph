"""RED tests pinning director ruling D-DF (sprint 2026-08-04-defs-us-headings,
dev cycle 4) under the `body_confirms` design program ruling P-R8 accepted
as-is: an additive optional field on `HeadingRule`
(`body_confirms: Callable[[str], bool] | None = None`), consumed at the
dispatch site as `matches(heading) and (body_confirms is None or
body_confirms(body))`.

**Background** — `defined for` is ALREADY SHIPPED (`a0419a4`) as one
alternation of the closed connector whitelist `for|as|term` inside
`_VERB_EXTENDED_RE` (`us_heading_variants.py:169`). Two independent human
reads (QA 37/43 ≈ 86%, Developer 31/35 ≈ 88.6%) plus the manager's own
full-population mechanical scan (72/110 = 65.5% with a detectable
self-definition marker, 7 cross-reference-only, 31 neither) all landed
below every other shipped rule's ~90%+ precision floor. D-DF: capture
`defined for` ONLY when the body ALSO carries a self-definition marker.
This is a change to shipped behavior, not a new capture.

**RED signal expected right now**: `ImportError` on the three new symbols
this file requires (`matches_heading_variant_unconditional`,
`matches_defined_for_heading`, `defines_in_body`) — none exist in the
shipped module yet. This is genuinely blocked on TWO things landing, in
order: (1) core ships `HeadingRule.body_confirms` in
`rules/registry.py` (core scope item 4, program ruling P-R8): (2) the
Developer implements the design below in `us_heading_variants.py`. Correct
red-before-green order — do not weaken any assertion below to go green
early.

## Design decision this file locks the Developer to

**The module must register exactly TWO `HeadingRule`s, not one**, in this
exact order:

1. `HeadingRule(jurisdiction_codes=("US-*",), matches=matches_heading_
   variant_unconditional)` — `body_confirms` left at its default (`None`).
   `matches_heading_variant_unconditional` is the union of R-SEC, R-MID,
   R-VERB-bare, R-VERB-extended **minus the `for` connector alternation**,
   R-TRUNC, R-MISSPELL — i.e. today's `_VERB_EXTENDED_RE` with `for`
   removed from its `for|as|term` whitelist (leaving `as`/`term` and every
   punctuation/dash form untouched).
2. `HeadingRule(jurisdiction_codes=("US-*",), matches=matches_defined_for_
   heading, body_confirms=defines_in_body)` — `matches_defined_for_heading`
   is a NARROW predicate, true iff `defined` is immediately followed by the
   literal connector word `for` (exactly the alternation split out of rule
   1). `defines_in_body` is the D-DF marker predicate (spec below).

**Why not one rule with `body_confirms` attached?** The module currently
registers exactly ONE `HeadingRule` whose `matches` is the whole-module
union `matches_heading_variant`. Attaching `body_confirms` to that single
rule would gate ALL ~20,307 recognized headings on body content, not just
the 110 `defined for` rows — a catastrophic over-application of D-DF
(rejected). The two-rule split confines the gate to exactly the 110-row
population the ruling is about.

**Why registration ORDER matters (unconditional first, gated second) and
why rule 2's `matches` must be NARROW, not the full union:**
`HeadingRule` is documented (`registry.py`, predating `body_confirms`) as a
"first-positive-wins" detection kind. Two dispatch semantics are
consistent with that phrase for a list of same-kind rules: (A) evaluate
every registered rule's `matches(h) and (body_confirms is None or
body_confirms(body))` and return True if ANY is True (a plain OR); or (B)
iterate in registration order and, for the FIRST rule whose `.matches(h)`
alone is True, return THAT rule's conjunction immediately, without trying
any further rule even if the conjunction is False. This module cannot
control which of (A)/(B) core implements. Under (A) the design below is
correct regardless of order or rule-2 narrowness. Under (B) it is ALSO
correct, but only because (i) the unconditional rule is tried first, so
any heading that is genuinely a definitions heading for an UNRELATED
reason (e.g. also matches R-MID) is captured before rule 2 is ever
consulted, and (ii) rule 2's `matches` is narrow (isolated to the `for`
shape alone) rather than the full union, so it can never itself be the
"first matching rule" for a heading that rule 1 would also unconditionally
capture. Registering gated-before-unconditional, or giving rule 2 the full
`matches_heading_variant` as its `matches`, would both be unsafe under
semantics (B) (a real, if rare, false-suppression risk) — this is a
deliberate design constraint, not a stylistic preference.

**`matches_heading_variant` keeps its current public meaning, unchanged**
(full union, INCLUDING the `for` alternation, exactly as today) — this is
a deliberate decision, not an oversight. 19 existing unit tests + 8
composed end-to-end tests depend on it (verified: none of them exercise
the `for` shape — grep for "defined for" across `backend/tests/` returns
zero hits before this file existed — so no existing test's behavior
changes). It stops being what gets registered directly, but remains a
correct, useful "is this heading a family-4 shape at all" predicate
(heading-only, matching what U6's 94.7% recall figure measures) distinct
from "does this heading's ROW get captured in production" (which, for the
`defined for` subset, now also depends on the body). It must equal
`matches_heading_variant_unconditional(h) or matches_defined_for_heading(h)`
for every heading — pinned below.

## `defines_in_body` predicate spec (pin the BEHAVIOR below, not a regex —
the Developer is free to implement this any way that reproduces every
pinned input/output pair)

True iff the body contains a quoted term (straight or curly, single or
double quotes) followed -- directly, or after a short intervening
"as used in ...,"/"for the purposes of ...,"-style lead-in clause and/or a
comma -- by the defining verb `means`/`mean` or the phrase `is defined as`.
Deliberately conservative, same spirit as the manager's own full-population
scan (72/110 self-definition, 7 cross-reference-only, 31 neither): a body
that only CROSS-REFERENCES another section's definition (`has the meaning
ascribed to it in NRS 459.7024`, `has the same meaning as that term is
defined in section 19-2.5-102`) must NOT count -- that is precisely the
self-definition/cross-reference distinction D-DF is about.

**Known, honestly-stated limits** (do not silently over-claim recall):
- Misses defining verbs other than `means`/`mean`/`is defined as`, e.g.
  `includes`, `shall include`, `refers to`, `is a` -- NOT pinned either
  direction below (no test asserts a verdict for e.g. "labor includes
  work performed..."); a real implementation may reasonably go either way
  and that is acceptable, not a violation of this spec.
- The federal COVID shape (`USC_T15_C122_S9801`), where the defining verb
  sits past a dash and a numbered sub-clause (`the term "X"— (1) means`),
  is deliberately NOT pinned either direction -- that row is used ONLY to
  prove the `term` connector word stays unconditional (it never reaches
  `defines_in_body` in production either, since rule 1 has
  `body_confirms=None`).
- Only straight/curly DOUBLE quotes are represented in the pinned fixture
  rows; single-quote forms are untested here.

Fixture: `backend/tests/fixtures/us_statutes/d_df_defined_for_rows.json`
(7 real rows) plus reuse of `us_heading_variants_rows.json`'s existing
`STATE_CO_T22_A33_P1_S22-33-106.3` / `STATE_NV_T58_C706_S706.074` /
`STATE_AL_T25_C9_S25-9-276` rows. See the fixture README's
`d_df_defined_for_rows.json` section for full provenance and the live
rule-isolation check (each `for`-shape heading below is captured, in the
shipped pre-D-DF code, SOLELY via `_rule_verb_extended` -- every other
rule and baseline `is_definitions_heading` are `False` -- so gating the
`for` alternation cleanly isolates this fix from every other rule).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

D_DF_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "d_df_defined_for_rows.json"
)
MAIN_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_heading_variants_rows.json"
)


def _load(path: Path) -> dict[str, dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def _ddf_rows() -> dict[str, dict]:
    return _load(D_DF_FIXTURE_PATH)


def _main_rows() -> dict[str, dict]:
    return _load(MAIN_FIXTURE_PATH)


# --- 1. Positive: body DOES confirm -> captured -------------------------


def test_defined_for_heading_with_self_definition_body_is_captured():
    from app.definition_links.rules.us_heading_variants import (
        defines_in_body,
        matches_defined_for_heading,
    )

    row = _ddf_rows()["STATE_KY_TXVIII_C214_S214.280"]
    assert row["section_title"] == '214.280 "Mattress" defined for KRS 214.290 to 214.310'

    assert matches_defined_for_heading(row["section_title"]) is True, (
        "the heading itself is a 'defined for' shape"
    )
    assert defines_in_body(row["text"]) is True, (
        "body: 'As used in KRS 214.290 to 214.310, \"mattress\" means ...' -- a clean "
        "local self-definition marker"
    )
    # The published P-R8 dispatch semantics, hand-composed (body_confirms is
    # never None for this rule, so this reduces to the conjunction below).
    assert (matches_defined_for_heading(row["section_title"]) and defines_in_body(row["text"])) is True


# --- 2. Negative: body does NOT confirm -> NOT captured (the whole point) -


@pytest.mark.parametrize(
    "act_id,reason",
    [
        (
            "STATE_CT_T45a_C802c_S45a-502",
            "full body is 'Annotation to former section 45-96a: Cited. 168 C. 144.' -- a "
            "bare case-citation stub, zero defining content of any kind (also, "
            "incidentally, the already-documented CT 'text column omits subsection (a)' "
            "data-quality gap -- doesn't change the correctness of not capturing this "
            "row: whatever body text production actually has carries no marker)",
        ),
        (
            "STATE_AL_T43_C8_S43-8-230",
            "body is a construction-of-terms RULE about half-bloods/adoptees/children-"
            "born-out-of-wedlock in class-gift terminology -- it never itself defines "
            "any single quoted term",
        ),
    ],
)
def test_defined_for_heading_without_self_definition_body_is_not_captured(act_id, reason):
    from app.definition_links.rules.us_heading_variants import (
        defines_in_body,
        matches_defined_for_heading,
    )

    row = _ddf_rows()[act_id]
    assert matches_defined_for_heading(row["section_title"]) is True, (
        "precondition: heading must be a genuine 'defined for' shape, or this isn't "
        "testing what it claims to"
    )
    assert defines_in_body(row["text"]) is False, reason
    assert (matches_defined_for_heading(row["section_title"]) and defines_in_body(row["text"])) is False


# --- 3. Blast-radius guard: sibling connectors + punctuation stay UNCONDITIONAL -


@pytest.mark.parametrize(
    "act_id,label",
    [
        ("STATE_ID_T18_C58_S18-5817", "as"),
        ("USC_T15_C122_S9801", "term"),
        ("STATE_NJ_T58_C16A_S16A-102", "comma"),
        ("STATE_CT_T31_C567_S31-232l", "period"),
    ],
)
def test_sibling_connector_and_punctuation_forms_stay_unconditional(act_id, label):
    from app.definition_links.rules.us_heading_variants import (
        matches_defined_for_heading,
        matches_heading_variant_unconditional,
    )

    row = _ddf_rows()[act_id]
    assert matches_heading_variant_unconditional(row["section_title"]) is True, (
        f"the {label!r} form must stay unconditional (body_confirms=None) -- D-DF "
        "touches ONLY the 'for' connector alternation, nothing else in "
        "_VERB_EXTENDED_RE"
    )
    assert matches_defined_for_heading(row["section_title"]) is False, (
        f"a {label!r}-form heading must NOT also be classified as the 'for' shape -- "
        "the two rules' matches predicates must not overlap"
    )


def test_existing_semicolon_form_stays_unconditional():
    """Reuses the existing real AL row already vendored in
    us_heading_variants_rows.json -- no re-vendoring needed."""
    from app.definition_links.rules.us_heading_variants import (
        matches_defined_for_heading,
        matches_heading_variant_unconditional,
    )

    row = _main_rows()["STATE_AL_T25_C9_S25-9-276"]
    assert matches_heading_variant_unconditional(row["section_title"]) is True
    assert matches_defined_for_heading(row["section_title"]) is False


def test_unconditional_rule_ignores_missing_body_marker_colorado_and_nevada():
    """The other direction of the blast-radius guard: prove the unconditional
    rule captures these headings WITHOUT ever needing a body marker -- both
    real bodies carry only a CROSS-REFERENCE ('has the meaning ascribed to
    ...'/'has the same meaning as ... is defined in ...'), which
    `defines_in_body` must NOT count as a self-definition, yet the heading
    is (and must remain) captured regardless, because body_confirms=None
    for this rule."""
    from app.definition_links.rules.us_heading_variants import (
        defines_in_body,
        matches_heading_variant_unconditional,
    )

    co = _main_rows()["STATE_CO_T22_A33_P1_S22-33-106.3"]
    assert matches_heading_variant_unconditional(co["section_title"]) is True
    assert defines_in_body(co["text"]) is False, (
        "'\"physical custodian\" has the same meaning as that term is defined in "
        "section 19-2.5-102' is a CROSS-REFERENCE, not a self-definition"
    )

    nv = _main_rows()["STATE_NV_T58_C706_S706.074"]
    assert matches_heading_variant_unconditional(nv["section_title"]) is True
    assert defines_in_body(nv["text"]) is False, (
        "'\"Hazardous material\" has the meaning ascribed to it in NRS 459.7024.' is "
        "also cross-reference-only"
    )


# --- 4. defines_in_body: direct predicate pinning on additional real shapes -


def test_defines_in_body_recognizes_additional_real_self_definition_shapes():
    from app.definition_links.rules.us_heading_variants import defines_in_body

    nj = _ddf_rows()["STATE_NJ_T58_C16A_S16A-102"]
    assert defines_in_body(nj["text"]) is True, (
        "'As used in this section \"emergency supplies\" means, but is not limited "
        "to:' -- comma directly after 'means'"
    )

    ct_period = _ddf_rows()["STATE_CT_T31_C567_S31-232l"]
    assert defines_in_body(ct_period["text"]) is True, (
        "'(c)(1) For purposes of this section, \"suitable work\" means any work...' "
        "-- the marker sits well past an earlier, unrelated (b) cross-reference to a "
        "different section; the predicate must scan the FULL body, not a short prefix"
    )

    id_row = _ddf_rows()["STATE_ID_T18_C58_S18-5817"]
    assert defines_in_body(id_row["text"]) is True, (
        "'\"Abandon\" means leaving unattended and uninclosed...' -- straight-quote "
        "term directly before 'means'"
    )


# --- 5. matches_heading_variant keeps its full, unchanged, decomposed meaning -


def test_matches_heading_variant_equals_unconditional_or_defined_for_everywhere():
    """Pins that the widely-depended-on `matches_heading_variant` symbol is
    UNCHANGED behavior -- a deliberate decision, not an oversight (see
    module docstring). Checked across every heading this sprint's fixtures
    already carry an opinion about: the 16 rows in
    us_heading_variants_rows.json (10 positive + 6 negative), the 2 dossier
    synthetic negatives, and all 7 of this file's own rows."""
    from app.definition_links.rules.us_heading_variants import (
        matches_defined_for_heading,
        matches_heading_variant,
        matches_heading_variant_unconditional,
    )

    headings = [row["section_title"] for row in _main_rows().values()]
    headings += [row["section_title"] for row in _ddf_rows().values()]
    headings += ["Repeal of definitions", "Terms as defined in section 5"]

    assert len(headings) >= 25, "sanity check: this should cover a broad real population"

    for heading in headings:
        full = matches_heading_variant(heading)
        decomposed = matches_heading_variant_unconditional(heading) or matches_defined_for_heading(heading)
        assert full == decomposed, (
            f"{heading!r}: matches_heading_variant must equal "
            "matches_heading_variant_unconditional(h) or matches_defined_for_heading(h) "
            "-- the decomposition must reproduce today's shipped full-union behavior "
            "exactly, with zero drift"
        )
