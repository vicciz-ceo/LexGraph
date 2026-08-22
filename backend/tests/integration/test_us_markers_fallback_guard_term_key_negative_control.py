"""RED + negative-control structural tests (sprint 2026-08-20-defs-boundary-
idioms, Planner micro-pass 3) for the DIRECTOR RULING 2026-08-23 extension
to Item 2's implausible-capture filter (`backend/app/definition_links/
us_profile.py::USProfile.extract_definitions_from_section`'s fallback-
suppression guard, ~line 2551, and its narrow implausible-capture filter
described in `test_us_markers_fallback_guard_phantom_negative_control.py`).

The expansion-wave precision sample (`2026-08-20-defs-boundary-idioms-
scripts/expansion_precision.md`, commit `a9653f6`) found 5/100 sampled
new-wave terms were an outright "garbage term key" false positive: a
legislative-history Editorial-Notes amendment caption (containing the
literal substring `"Pub. L."` and/or matching `Subsec\\.\\s*\\(`, e.g. real
sample rows #11/#19/#26/#46/#49 -- `".. Pub. L. 101-37, section 7(a)(3), in
subpar. (F)..."`, `"Subsec. (q)(5) to (8). Pub. L. 105-276..."`) mis-paired
by the fallback's own quote-then-idiom scan as if it were a real
definiendum. The director ruled (contract Item 2, "DIRECTOR RULING
2026-08-23"): ship the expansion wave, but EXTEND the implausible-capture
rejection so a fallback term containing `"Pub. L."` or matching
`Subsec\\.\\s*\\(` is NEVER admitted by the merged guard -- measured on the
full 100-item sample as 5/5 caught, 0/95 collateral (a strict superset
refinement of the pre-existing `^\\d{4}[\\u2014\\u2013-]` filter, which
catches a DIFFERENT 4 phantom rows and does not overlap this shape at all:
none of the 5 garbage-term-key samples begin with a bare 4-digit year).

Per manager ruling M-R107, every fixture here is fully synthetic -- built
from unseen identifiers/citation numbers never used elsewhere in the corpus
or this test suite, structurally shaped after the sampler's real FP rows
but not keyed to any of their act_ids/row numbers/citation numbers. Same
engine-level style as the sibling `test_us_markers_fallback_guard_
structural_controls.py` (lighter than the persistence-altitude `..._
phantom_negative_control.py` real-row companion), reusing its exact
`_PROFILE`/`_primary`/`_terms` helper shape.

Two distinct scenarios are pinned per term-key shape (`Pub. L.` and
`Subsec.(`), because today's UN-FIXED guard behaves differently depending
on whether the primary engine already found something on the row:

- **RED-for-cause** (`test_red_*`): on a row where the primary engine finds
  ZERO candidates, today's guard (`if not candidates and heading_was_
  derived: candidates = _extract_inline_quoted_definitions(...)`)
  substitutes the ENTIRE raw fallback output UNFILTERED -- so a garbage
  term-key-shaped candidate IS admitted today, live, right now (not merely
  a future risk). These assertions (pinning "never admitted") therefore
  FAIL today and must PASS once Item 2's merge + the director's extended
  filter lands.
- **GREEN-and-staying-GREEN** (`test_negative_control_*`): on a row where
  the primary engine already finds a distinct, unrelated entry, today's
  guard suppresses the ENTIRE fallback call (the `if not candidates`
  branch is False), so the garbage term is absent today for an UNRELATED
  reason (total suppression, not the filter). Once Item 2's merge always
  runs the fallback, the garbage term becomes a live per-term admission
  candidate that does NOT collide with any primary term -- only the
  director's extended filter stops it. Proves the filter itself does the
  work, not accidental term-collision protection.

Both directions verified this pass via the same "direct-function replay"
method `expansion_precision.md` and the Planner's own footprint measurement
used (calling the real, unmodified `extract_definitions_from_section`
with `heading_was_derived=False` to get the primary engine's own raw
candidates, separately calling the real, unmodified `_extract_inline_
quoted_definitions` for the fallback's own raw candidates, then applying
Item 2's spec'd merge/filter, extended per the 2026-08-23 ruling, as a pure
function over both) -- see the Planner's completion report for the
proof-run output."""
from __future__ import annotations

from app.definition_links.profiles import get_profile
from app.definition_links.us_profile import _extract_inline_quoted_definitions

_PROFILE = get_profile("US-WA")  # has a registered EntrySplitterRule (family-3)

# --- Pub. L. shape -----------------------------------------------------

PUB_L_TERM_ISOLATED = "Pub. L. 203-77, redesignating prior provisions of this subchapter"
_TEXT_PUB_L_PRIMARY_EMPTY = (
    "Introductory text with no leading quote at all. "
    f'"{PUB_L_TERM_ISOLATED}" '
    "includes a phrase describing legislative history entirely, not a real definition."
)
_PUB_L_ISOLATED_DEF = "a phrase describing legislative history entirely, not a real definition."

PUB_L_TERM_NONCOLLIDING = "Pub. L. 203-77, amending prior definitions of this term"
_TEXT_PUB_L_PRIMARY_NONEMPTY = (
    '"Wrenfeld" means a real, freestanding concept entirely on its own. '
    f'"{PUB_L_TERM_NONCOLLIDING}" includes a stray capture that references '
    "legislative history, not a definition."
)
_PUB_L_NONCOLLIDING_DEF = "a stray capture that references legislative history, not a definition."

# --- Subsec.( shape ------------------------------------------------------

SUBSEC_TERM_ISOLATED = "Subsec. (a)(2). Some historical amendment note describing a prior redesignation"
_TEXT_SUBSEC_PRIMARY_EMPTY = (
    "Introductory text with no leading quote at all. "
    f'"{SUBSEC_TERM_ISOLATED}" '
    "includes a phrase describing legislative history entirely, not a real definition."
)
_SUBSEC_ISOLATED_DEF = "a phrase describing legislative history entirely, not a real definition."

SUBSEC_TERM_NONCOLLIDING = "Subsec. (b)(3). Some historical amendment note describing a prior redesignation"
_TEXT_SUBSEC_PRIMARY_NONEMPTY = (
    '"Halvex" means a real, freestanding concept entirely on its own. '
    f'"{SUBSEC_TERM_NONCOLLIDING}" includes a stray capture that looks like '
    "an amendment caption, not a definition."
)
_SUBSEC_NONCOLLIDING_DEF = "a stray capture that looks like an amendment caption, not a definition."


def _primary_today(text: str):
    """`extract_definitions_from_section` called exactly as the real
    pipeline calls it on a `heading_was_derived` row -- i.e. through
    TODAY'S un-fixed guard."""
    return _PROFILE.extract_definitions_from_section(text, scope="law-wide", heading_was_derived=True)


def _raw_primary_before_any_guard(text: str):
    """The primary engine's OWN candidates, independent of the
    `heading_was_derived` guard entirely (`heading_was_derived=False` never
    reaches the guard at all) -- used only for preconditions, to prove a
    given text's primary engine genuinely finds zero/one entries before any
    fallback substitution."""
    return _PROFILE.extract_definitions_from_section(text, scope="law-wide", heading_was_derived=False)


def _terms(candidates) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in candidates:
        for t in c.terms:
            out.setdefault(t, []).append(c.definition_text)
    return out


# --- Preconditions (guard against a vacuous RED/GREEN) ----------------------


def test_fixture_precondition_pub_l_primary_empty_scenario():
    """Sanity for the RED scenario: the primary engine (independent of the
    guard) finds ZERO entries on this text, and the fallback function
    itself DOES raw-capture the Pub.-L.-shaped term (unfiltered, unmodified
    by this item) -- so today's guard's `if not candidates` branch is True
    and substitutes this exact raw output."""
    assert _terms(_raw_primary_before_any_guard(_TEXT_PUB_L_PRIMARY_EMPTY)) == {}, (
        "sanity: the primary engine must find zero entries on this text "
        "independent of the guard"
    )
    fallback = _terms(_extract_inline_quoted_definitions(_TEXT_PUB_L_PRIMARY_EMPTY, scope="law-wide"))
    assert fallback.get(PUB_L_TERM_ISOLATED) == [_PUB_L_ISOLATED_DEF], (
        f"sanity: the fallback function itself must already raw-capture this "
        f"Pub.-L.-shaped term today -- got {fallback.get(PUB_L_TERM_ISOLATED)!r}"
    )


def test_fixture_precondition_subsec_primary_empty_scenario():
    """Sanity for the RED scenario, `Subsec.(` shape -- same structure as
    the Pub. L. precondition above."""
    assert _terms(_raw_primary_before_any_guard(_TEXT_SUBSEC_PRIMARY_EMPTY)) == {}, (
        "sanity: the primary engine must find zero entries on this text "
        "independent of the guard"
    )
    fallback = _terms(_extract_inline_quoted_definitions(_TEXT_SUBSEC_PRIMARY_EMPTY, scope="law-wide"))
    assert fallback.get(SUBSEC_TERM_ISOLATED) == [_SUBSEC_ISOLATED_DEF], (
        f"sanity: the fallback function itself must already raw-capture this "
        f"Subsec.(-shaped term today -- got {fallback.get(SUBSEC_TERM_ISOLATED)!r}"
    )


def test_fixture_precondition_pub_l_primary_nonempty_scenario():
    """Sanity for the GREEN-staying-GREEN scenario: the primary engine
    (independent of the guard) finds exactly 'Wrenfeld', a DISTINCT term
    from the Pub.-L.-shaped one -- so the guard's `if not candidates`
    branch is False today (total suppression), and per-term admission
    (once Item 2 lands) would find no collision at all for the Pub.-L.
    term -- only the extended filter can reject it."""
    raw_primary = _terms(_raw_primary_before_any_guard(_TEXT_PUB_L_PRIMARY_NONEMPTY))
    assert list(raw_primary) == ["Wrenfeld"], (
        f"sanity: primary engine must find exactly one, distinct entry -- got {sorted(raw_primary)!r}"
    )
    fallback = _terms(_extract_inline_quoted_definitions(_TEXT_PUB_L_PRIMARY_NONEMPTY, scope="law-wide"))
    assert fallback.get(PUB_L_TERM_NONCOLLIDING) == [_PUB_L_NONCOLLIDING_DEF], (
        f"sanity: the fallback function itself must already raw-capture this "
        f"non-colliding Pub.-L.-shaped term today -- got {fallback.get(PUB_L_TERM_NONCOLLIDING)!r}"
    )


def test_fixture_precondition_subsec_primary_nonempty_scenario():
    """Sanity for the GREEN-staying-GREEN scenario, `Subsec.(` shape --
    same structure as the Pub. L. precondition above."""
    raw_primary = _terms(_raw_primary_before_any_guard(_TEXT_SUBSEC_PRIMARY_NONEMPTY))
    assert list(raw_primary) == ["Halvex"], (
        f"sanity: primary engine must find exactly one, distinct entry -- got {sorted(raw_primary)!r}"
    )
    fallback = _terms(_extract_inline_quoted_definitions(_TEXT_SUBSEC_PRIMARY_NONEMPTY, scope="law-wide"))
    assert fallback.get(SUBSEC_TERM_NONCOLLIDING) == [_SUBSEC_NONCOLLIDING_DEF], (
        f"sanity: the fallback function itself must already raw-capture this "
        f"non-colliding Subsec.(-shaped term today -- got {fallback.get(SUBSEC_TERM_NONCOLLIDING)!r}"
    )


# --- RED: today's un-fixed guard admits the garbage term, unfiltered -------


def test_red_pub_l_shaped_term_must_never_be_admitted():
    """RED-for-cause: on this text the primary engine finds zero entries
    (precondition above), so today's guard substitutes the fallback's raw
    output UNFILTERED -- this Pub.-L.-shaped garbage term-key IS admitted
    today, live. Per the director's 2026-08-23 ruling extending the
    implausible-capture filter, it must NEVER be admitted -- this assertion
    fails today and must pass once Item 2's merge + extended filter land."""
    primary_today = _terms(_primary_today(_TEXT_PUB_L_PRIMARY_EMPTY))
    assert PUB_L_TERM_ISOLATED not in primary_today, (
        f"RED: today's un-fixed guard admits this Pub.-L.-shaped garbage "
        f"term-key unfiltered (the primary engine finds zero candidates on "
        f"this text) -- got {primary_today.get(PUB_L_TERM_ISOLATED)!r}. Once "
        f"Item 2's merge + the director's 2026-08-23 extended term-key "
        f"filter lands, this term must be rejected."
    )


def test_red_subsec_shaped_term_must_never_be_admitted():
    """RED-for-cause, `Subsec.(` shape -- same structure as the Pub. L.
    RED test above."""
    primary_today = _terms(_primary_today(_TEXT_SUBSEC_PRIMARY_EMPTY))
    assert SUBSEC_TERM_ISOLATED not in primary_today, (
        f"RED: today's un-fixed guard admits this Subsec.(-shaped garbage "
        f"term-key unfiltered (the primary engine finds zero candidates on "
        f"this text) -- got {primary_today.get(SUBSEC_TERM_ISOLATED)!r}. Once "
        f"Item 2's merge + the director's 2026-08-23 extended term-key "
        f"filter lands, this term must be rejected."
    )


# --- Negative controls: GREEN today, MUST STAY GREEN after the fix ---------


def test_negative_control_pub_l_shaped_term_never_becomes_a_persisted_term_even_without_a_collision():
    """GREEN today (coincidentally: the guard suppresses the ENTIRE
    fallback call since 'Wrenfeld' already makes the primary engine
    non-empty) and MUST STAY GREEN once Item 2's merge always runs the
    fallback: even though this Pub.-L.-shaped term does not collide with
    ANY primary term ('Wrenfeld'), the director's 2026-08-23 extended
    filter must still reject it before it is ever admitted."""
    primary_today = _terms(_primary_today(_TEXT_PUB_L_PRIMARY_NONEMPTY))
    assert PUB_L_TERM_NONCOLLIDING not in primary_today, (
        "the Pub.-L.-shaped term must not appear in extract_definitions_"
        "from_section's output today (guard currently suppresses the "
        "fallback entirely since 'Wrenfeld' is already non-empty) -- and "
        "per the director's 2026-08-23 extended filter it must STILL be "
        "absent once the merge lands, even though it collides with no "
        "primary term at all"
    )
    assert primary_today.get("Wrenfeld") == [
        'a real, freestanding concept entirely on its own. '
        f'"{PUB_L_TERM_NONCOLLIDING}" includes a stray capture that references '
        "legislative history, not a definition."
    ], (
        f"'Wrenfeld' (the primary engine's own existing entry) must stay "
        f"unchanged -- got {primary_today.get('Wrenfeld')!r}"
    )


def test_negative_control_subsec_shaped_term_never_becomes_a_persisted_term_even_without_a_collision():
    """GREEN today, MUST STAY GREEN after the fix, `Subsec.(` shape -- same
    structure as the Pub. L. negative control above."""
    primary_today = _terms(_primary_today(_TEXT_SUBSEC_PRIMARY_NONEMPTY))
    assert SUBSEC_TERM_NONCOLLIDING not in primary_today, (
        "the Subsec.(-shaped term must not appear in extract_definitions_"
        "from_section's output today (guard currently suppresses the "
        "fallback entirely since 'Halvex' is already non-empty) -- and "
        "per the director's 2026-08-23 extended filter it must STILL be "
        "absent once the merge lands, even though it collides with no "
        "primary term at all"
    )
    assert primary_today.get("Halvex") == [
        'a real, freestanding concept entirely on its own. '
        f'"{SUBSEC_TERM_NONCOLLIDING}" includes a stray capture that looks '
        "like an amendment caption, not a definition."
    ], (
        f"'Halvex' (the primary engine's own existing entry) must stay "
        f"unchanged -- got {primary_today.get('Halvex')!r}"
    )
