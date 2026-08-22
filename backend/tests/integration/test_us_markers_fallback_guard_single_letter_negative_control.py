"""RED + positive-control structural tests (sprint 2026-08-20-defs-boundary-
idioms, Planner micro-pass 4) for the ROUND-2 ADDENDUM (manager ruling
2026-08-23, contract Item 2, `2026-08-20-defs-boundary-idioms-scripts/
expansion_precision_2.md`) extension to `backend/app/definition_links/
us_profile.py::_is_implausible_fallback_capture` (the implausible-capture
filter applied inside `_merge_fallback_candidates`, itself always invoked by
`USProfile.extract_definitions_from_section`'s fallback-suppression guard
whenever `heading_was_derived=True`, since `f267644` -- see `test_us_markers_
fallback_guard_term_key_negative_control.py`'s own docstring for that
merge's history).

`expansion_precision_2.md` censused the FULL 27,568-item current-shipped
population (not a sample) for a bare single-letter fallback term (regex
`^[A-Za-z]$`) and found 19 instances across 4 jurisdictions (US-IA 16,
US-CA 1, US-OH 1, US-SC 1) -- every one individually verified against real
source text to be a false positive, splitting into two sub-mechanisms: a
lettered cross-reference citation (`paragraph "e"`, `subparagraph "b"`, 14/19,
all US-IA) mis-paired with a nearby, unrelated defining idiom, and a
classification-letter label (`class "B" violation`, an `"A"`-`"F"` grade,
an `"S" corporation`; 5/19) mis-paired with a distant, unrelated idiom -- the
same root "mis-paired quote" mechanism round 1 already found unclosable by
term-shape rules, but the single-letter subset IS closable by shape alone
because a real English defined term is never literally one bare letter
anywhere in this corpus (unlike a real multi-word or multi-character term,
which very much can be short). Zero genuine single-letter fallback terms
were found anywhere in the population (0/19). The director ruled (contract
Item 2, "ROUND-2 ADDENDUM"): extend the implausible-capture filter again --
reject a fallback term matching `^[A-Za-z]$`.

Per manager ruling M-R107, every fixture here is fully synthetic -- built
from unseen identifiers/citation letters never used elsewhere in the corpus
or this test suite, structurally shaped after the censused real FP rows
(a classification-letter label mis-paired with distant, unrelated prose) but
not keyed to any of their act_ids/row numbers/letters. Same engine-level
style as `test_us_markers_fallback_guard_term_key_negative_control.py`,
reusing its exact `_PROFILE`/`_terms` helper shape; ONE scenario type per
case here (not the term-key file's isolated/non-colliding split), because
unlike at that file's own time of writing, the merge (`f267644`) is ALREADY
live at this pass's `HEAD` -- `_merge_fallback_candidates` runs
unconditionally whenever `heading_was_derived=True`, regardless of whether
the primary engine found zero or some candidates, so there is only one
code path left to pin (verified empirically this pass: both an isolated-
primary and a non-colliding-primary row admit the bare single letter today,
identically -- both are pinned below for coverage of each row shape, not
because the code branches on it).

RED-for-cause (`test_red_*`): the merged guard's `_is_implausible_fallback_
capture` does not yet reject a bare single-letter term, so it IS admitted
today, live (verified this pass via direct-function replay, the same method
`expansion_precision.md`/`expansion_precision_2.md` and the prior micro-
passes used: calling the real, unmodified `extract_definitions_from_section`
with `heading_was_derived=True` and confirming the single-letter term is
present in its output). These assertions ("never admitted") therefore FAIL
today and must PASS once the ROUND-2 ADDENDUM's `^[A-Za-z]$` rule lands in
`_is_implausible_fallback_capture`.

Positive control (`test_positive_control_*`): a legitimate short-but-multi-
character term (`"AI"`, 2 characters) must remain admitted both today and
after the fix -- `^[A-Za-z]$` matches exactly one letter, never two, so this
guards against an over-broad implementation (e.g. a stray length threshold)
that would also reject short multi-character terms the ruling never asked
to close (`expansion_precision_2.md`'s own sample table lists a real 2-
character GENUINE term, `"PA"`, confirming legitimate short terms exist in
this corpus and must not be swept in)."""
from __future__ import annotations

from app.definition_links.profiles import get_profile

_PROFILE = get_profile("US-WA")  # has a registered EntrySplitterRule (family-3)

# --- Isolated-primary shape (primary engine finds zero candidates) --------

SINGLE_LETTER_TERM_ISOLATED = "B"
_TEXT_ISOLATED = (
    "Introductory text with no leading quote at all. "
    f'"{SINGLE_LETTER_TERM_ISOLATED}" includes a classification label '
    "mis-paired with distant, unrelated prose entirely, not a real definition."
)
_ISOLATED_DEF = "a classification label mis-paired with distant, unrelated prose entirely, not a real definition."

# --- Non-colliding-primary shape (primary engine finds a distinct term) ----

SINGLE_LETTER_TERM_NONCOLLIDING = "C"
_TEXT_NONCOLLIDING = (
    '"Wrenfeld" means a real, freestanding concept entirely on its own. '
    f'"{SINGLE_LETTER_TERM_NONCOLLIDING}" includes a classification label '
    "mis-paired with distant, unrelated prose entirely, not a real definition."
)
_NONCOLLIDING_DEF = "a classification label mis-paired with distant, unrelated prose entirely, not a real definition."

# --- Positive control: legitimate short multi-character term --------------

MULTI_CHAR_TERM = "AI"
_TEXT_CONTROL = (
    '"Wrenfeld" means a real, freestanding concept entirely on its own. '
    f'"{MULTI_CHAR_TERM}" includes a real multi-character acronym term that '
    "must stay admitted, not a bare single letter."
)
_CONTROL_DEF = "a real multi-character acronym term that must stay admitted, not a bare single letter."


def _primary_today(text: str):
    """`extract_definitions_from_section` called exactly as the real
    pipeline calls it on a `heading_was_derived` row -- i.e. through
    today's merged guard, BEFORE the ROUND-2 ADDENDUM's `^[A-Za-z]$` rule
    is added to `_is_implausible_fallback_capture`."""
    return _PROFILE.extract_definitions_from_section(text, scope="law-wide", heading_was_derived=True)


def _terms(candidates) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in candidates:
        for t in c.terms:
            out.setdefault(t, []).append(c.definition_text)
    return out


# --- Preconditions (guard against a vacuous RED) ---------------------------


def test_fixture_precondition_isolated_primary_is_empty():
    """Sanity for the isolated-primary RED below: the primary engine
    (independent of the guard, `heading_was_derived=False`) finds ZERO
    entries on this text -- proves the RED case is not vacuously passing
    because the row has some other, unrelated primary candidate."""
    raw_primary = _terms(
        _PROFILE.extract_definitions_from_section(_TEXT_ISOLATED, scope="law-wide", heading_was_derived=False)
    )
    assert raw_primary == {}, (
        f"sanity: the primary engine must find zero entries on this text "
        f"independent of the guard -- got {sorted(raw_primary)!r}"
    )


def test_fixture_precondition_noncolliding_primary_finds_exactly_wrenfeld():
    """Sanity for the non-colliding-primary RED below: the primary engine
    (independent of the guard) finds exactly 'Wrenfeld', a DISTINCT term
    from the single-letter one -- so per-term admission finds no collision
    at all for the single-letter term; only the extended filter can reject
    it."""
    raw_primary = _terms(
        _PROFILE.extract_definitions_from_section(_TEXT_NONCOLLIDING, scope="law-wide", heading_was_derived=False)
    )
    assert list(raw_primary) == ["Wrenfeld"], (
        f"sanity: primary engine must find exactly one, distinct entry -- got {sorted(raw_primary)!r}"
    )


# --- RED: today's merged guard admits the bare single letter, unfiltered ---


def test_red_isolated_single_letter_term_must_never_be_admitted():
    """RED-for-cause: on a row where the primary engine finds zero
    candidates (precondition above), today's merged guard admits the bare
    single-letter fallback term unfiltered -- `_is_implausible_fallback_
    capture` does not yet reject `^[A-Za-z]$`. Per the ROUND-2 ADDENDUM,
    it must NEVER be admitted -- this assertion fails today (verified this
    pass) and must pass once the rule lands."""
    primary_today = _terms(_primary_today(_TEXT_ISOLATED))
    assert SINGLE_LETTER_TERM_ISOLATED not in primary_today, (
        f"RED: today's merged guard admits this bare single-letter fallback "
        f"term unfiltered -- got {primary_today.get(SINGLE_LETTER_TERM_ISOLATED)!r}. "
        f"Once the ROUND-2 ADDENDUM's `^[A-Za-z]$` rule lands in "
        f"`_is_implausible_fallback_capture`, this term must be rejected."
    )


def test_red_noncolliding_single_letter_term_must_never_be_admitted():
    """RED-for-cause, non-colliding-primary shape -- same structure as the
    isolated RED above, but on a row where the primary engine already has
    a distinct entry ('Wrenfeld'); proves the filter itself does the work,
    not accidental term-collision protection (there is no collision here
    at all)."""
    primary_today = _terms(_primary_today(_TEXT_NONCOLLIDING))
    assert SINGLE_LETTER_TERM_NONCOLLIDING not in primary_today, (
        f"RED: today's merged guard admits this bare single-letter fallback "
        f"term unfiltered even alongside an unrelated, non-colliding primary "
        f"entry -- got {primary_today.get(SINGLE_LETTER_TERM_NONCOLLIDING)!r}. "
        f"Once the ROUND-2 ADDENDUM's `^[A-Za-z]$` rule lands, this term "
        f"must be rejected."
    )
    assert primary_today.get("Wrenfeld") == [
        'a real, freestanding concept entirely on its own. '
        f'"{SINGLE_LETTER_TERM_NONCOLLIDING}" includes a classification label '
        "mis-paired with distant, unrelated prose entirely, not a real definition."
    ], (
        f"'Wrenfeld' (the primary engine's own existing entry) must stay "
        f"unchanged -- got {primary_today.get('Wrenfeld')!r}"
    )


# --- Positive control: GREEN today, MUST STAY GREEN after the fix ---------


def test_positive_control_multi_char_short_term_still_admitted():
    """A legitimate short-but-multi-character term ('AI', 2 characters)
    must remain admitted both before and after the ROUND-2 ADDENDUM lands
    -- `^[A-Za-z]$` matches exactly one letter, never two. Guards against
    an over-broad implementation (e.g. a stray length threshold instead of
    the exact single-character shape) that would also sweep in short
    multi-character terms the ruling never asked to close (`expansion_
    precision_2.md`'s own sample includes a real 2-character GENUINE term,
    'PA')."""
    primary_today = _terms(_primary_today(_TEXT_CONTROL))
    assert primary_today.get(MULTI_CHAR_TERM) == [_CONTROL_DEF], (
        f"'{MULTI_CHAR_TERM}' must stay admitted both today and after the "
        f"ROUND-2 ADDENDUM's `^[A-Za-z]$` rule lands (it is 2 characters, "
        f"not a bare single letter) -- got {primary_today.get(MULTI_CHAR_TERM)!r}"
    )
    assert primary_today.get("Wrenfeld") == [
        'a real, freestanding concept entirely on its own. '
        f'"{MULTI_CHAR_TERM}" includes a real multi-character acronym term that '
        "must stay admitted, not a bare single letter."
    ], (
        f"'Wrenfeld' (the primary engine's own existing entry) must stay "
        f"unchanged -- got {primary_today.get('Wrenfeld')!r}"
    )
