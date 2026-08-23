"""Structural tests (sprint 2026-08-20-defs-boundary-idioms, Planner
micro-pass 5) for `backend/app/definition_links/us_profile.py::_is_
implausible_fallback_capture` (the implausible-capture filter applied
inside `_merge_fallback_candidates`, itself always invoked by `USProfile.
extract_definitions_from_section`'s fallback-suppression guard whenever
`heading_was_derived=True`, since `f267644` -- see `test_us_markers_
fallback_guard_term_key_negative_control.py`'s own docstring for that
merge's history).

**REVERSED by director ruling 2026-08-23** (contract
`docs/sprint/sprints/2026-08-20-defs-boundary-idioms.md`, Item 2, the
"REVERSED by director ruling 2026-08-23" block; log doc
`docs/sprint/sprints/2026-08-20-defs-boundary-idioms-log.md`, "Director
ruling: revert single-letter rule, certify, ship (2026-08-23, manager)").
Micro-pass 4's `^[A-Za-z]$` fallback-term rejection rule (commit `877c970`)
was found by the Developer's finish pass to reach a THIRD, previously
unmeasured population -- 19 bare single-letter fallback captures already
present, byte-identical, in BOTH baseline and pre-fix-current (invisible to
every prior delta/census, which only ever looked at pure-added anchors). A
spot check of that population confirmed at least one is NOT a phantom:
`STATE_NV_T43_C484B_S484B.307`, term `"X"` -- `"...A red "X" symbol means a
driver facing the signal must not enter or drive in any lane over which the
red signal is shown."` -- a real, well-formed `"TERM" means DEFINITION`
clause where the single letter IS the actual, correct definiendum (a
standard traffic lane-control symbol). Rejecting it deletes a genuine
pre-existing definition, contradicting both Acceptance Gate 3 ("ZERO
genuine anchor losses") and the ROUND-2 ADDENDUM's own premise ("a real
English defined term is never literally one bare letter... in this
corpus"). Ruling: REVERT `877c970`; the 19 wave phantoms this rule WOULD
have correctly caught ship instead as enumerated named tracked debt
(preamble-sprint precedent for phantom debt); the `cc51c49` combined
measurement (zero genuine losses) stands certified under P-R11 once the
tree is byte-identical to it again.

**This pass (Planner micro-pass 5) retires the two now-obsolete RED pins**
that asserted the reversed rule's rejection behavior
(`test_red_isolated_single_letter_term_must_never_be_admitted`,
`test_red_noncolliding_single_letter_term_must_never_be_admitted` --
removed) and re-points the file to pin the RULED (post-revert) behavior
instead: a bare single-letter fallback term -- isolated or alongside a
non-colliding primary entry -- must be ADMITTED by the merged guard, not
rejected. This is deliberate, not a coverage gap: admitting single-letter
fallback terms is exactly what protects the genuine NV "X" anchor above: A
future, smarter rule (reject a single-letter fallback term only when it
lacks an ADJACENT defining verb -- i.e. distinguish `"X" means ...` from a
distant, unrelated `"e" ... shall include ...` mis-pairing by proximity/
idiom-adjacency rather than by character-count shape alone) may be designed
in a later sprint, with its own evidence; it is explicitly OUT of scope
here.

**Current-state note (read before trusting a green/red run in isolation):**
at this pass's `HEAD`, commit `877c970` (the `^[A-Za-z]$` rejection rule)
is still an ancestor -- the Developer's revert has NOT landed yet. So the
re-pointed "is admitted" assertions below are **RED-for-cause right now**
(the still-live rule rejects the single-letter term) and are proven, this
pass, to turn **GREEN under a monkeypatched simulation of the reverted
code** (`_FALLBACK_SINGLE_LETTER_TERM_RE` replaced with a pattern that
never matches, the same "simulate the fix, run the real unmodified
pipeline" method every prior pass in this sprint used for its own
consistency proof). Both sides are stated together deliberately: this file
pins the RULED end-state, not today's still-live code, and will read GREEN
in the normal suite run only once the Developer's revert commit lands.

Per manager ruling M-R107, every fixture here is fully synthetic -- built
from unseen identifiers/citation letters never used elsewhere in the corpus
or this test suite, structurally shaped after the censused real FP rows
(a classification-letter label mis-paired with distant, unrelated prose)
but not keyed to any of their act_ids/row numbers/letters. Same
engine-level style as `test_us_markers_fallback_guard_term_key_negative_
control.py`, reusing its exact `_PROFILE`/`_terms` helper shape; ONE
scenario type per case here (not the term-key file's isolated/non-colliding
split as a behavioral fork), because the merge (`f267644`) runs
unconditionally whenever `heading_was_derived=True`, regardless of whether
the primary engine found zero or some candidates -- both row shapes are
pinned for coverage of each shape, not because the code branches on it."""
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
    today's merged guard, AS IT STANDS AT THIS PASS'S `HEAD` (the
    `877c970` single-letter rejection rule still present, pending the
    Developer's revert)."""
    return _PROFILE.extract_definitions_from_section(text, scope="law-wide", heading_was_derived=True)


def _terms(candidates) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in candidates:
        for t in c.terms:
            out.setdefault(t, []).append(c.definition_text)
    return out


# --- Preconditions (guard against a vacuous RED) ---------------------------


def test_fixture_precondition_isolated_primary_is_empty():
    """Sanity for the isolated-primary test below: the primary engine
    (independent of the guard, `heading_was_derived=False`) finds ZERO
    entries on this text -- proves that test is not vacuously passing
    because the row has some other, unrelated primary candidate."""
    raw_primary = _terms(
        _PROFILE.extract_definitions_from_section(_TEXT_ISOLATED, scope="law-wide", heading_was_derived=False)
    )
    assert raw_primary == {}, (
        f"sanity: the primary engine must find zero entries on this text "
        f"independent of the guard -- got {sorted(raw_primary)!r}"
    )


def test_fixture_precondition_noncolliding_primary_finds_exactly_wrenfeld():
    """Sanity for the non-colliding-primary test below: the primary engine
    (independent of the guard) finds exactly 'Wrenfeld', a DISTINCT term
    from the single-letter one -- so per-term admission finds no collision
    at all for the single-letter term; whether it is admitted or rejected
    is decided entirely by the implausible-capture filter, not collision."""
    raw_primary = _terms(
        _PROFILE.extract_definitions_from_section(_TEXT_NONCOLLIDING, scope="law-wide", heading_was_derived=False)
    )
    assert list(raw_primary) == ["Wrenfeld"], (
        f"sanity: primary engine must find exactly one, distinct entry -- got {sorted(raw_primary)!r}"
    )


# --- RED-until-revert: pin the RULED (post-revert) admission behavior -----


def test_red_isolated_single_letter_term_is_admitted():
    """RED-until-revert (director ruling 2026-08-23, see module docstring):
    pins the RULED behavior -- a bare single-letter fallback term, on a row
    where the primary engine finds zero candidates (precondition above),
    must be ADMITTED by the merged guard, not rejected. This is what
    protects the genuine NV "X" anchor (`STATE_NV_T43_C484B_S484B.307`)
    from deletion.

    At this pass's `HEAD`, `877c970` (the `^[A-Za-z]$` rejection rule) is
    still present -- `_is_implausible_fallback_capture` still rejects this
    term, so this assertion FAILS today (RED-for-cause, verified this
    pass). It must PASS once the Developer reverts `877c970`; verified this
    pass GREEN under a monkeypatched simulation of the reverted code (see
    log doc "Planner micro-pass 5" for the proof run)."""
    primary_today = _terms(_primary_today(_TEXT_ISOLATED))
    assert primary_today.get(SINGLE_LETTER_TERM_ISOLATED) == [_ISOLATED_DEF], (
        f"RED-until-revert: a bare single-letter fallback term must be ADMITTED "
        f"by the merged guard (the ROUND-2 `^[A-Za-z]$` rule was reversed -- it "
        f"deleted the genuine NV 'X' anchor) -- got "
        f"{primary_today.get(SINGLE_LETTER_TERM_ISOLATED)!r}. This stays RED "
        f"until the Developer reverts `877c970`."
    )


def test_red_noncolliding_single_letter_term_is_admitted():
    """RED-until-revert, non-colliding-primary shape -- same structure as
    the isolated case above, but on a row where the primary engine already
    has a distinct entry ('Wrenfeld'); proves admission is decided by the
    filter itself, not by an accidental absence of collision.

    Same current-state note as above: RED-for-cause at this pass's `HEAD`
    (`877c970` still present); verified this pass GREEN under a
    monkeypatched simulation of the reverted code."""
    primary_today = _terms(_primary_today(_TEXT_NONCOLLIDING))
    assert primary_today.get(SINGLE_LETTER_TERM_NONCOLLIDING) == [_NONCOLLIDING_DEF], (
        f"RED-until-revert: a bare single-letter fallback term must be ADMITTED "
        f"by the merged guard even alongside an unrelated, non-colliding primary "
        f"entry -- got {primary_today.get(SINGLE_LETTER_TERM_NONCOLLIDING)!r}. "
        f"This stays RED until the Developer reverts `877c970`."
    )
    assert primary_today.get("Wrenfeld") == [
        'a real, freestanding concept entirely on its own. '
        f'"{SINGLE_LETTER_TERM_NONCOLLIDING}" includes a classification label '
        "mis-paired with distant, unrelated prose entirely, not a real definition."
    ], (
        f"'Wrenfeld' (the primary engine's own existing entry) must stay "
        f"unchanged -- got {primary_today.get('Wrenfeld')!r}"
    )


# --- Positive control: GREEN today, MUST STAY GREEN after the revert ------


def test_positive_control_multi_char_short_term_still_admitted():
    """A legitimate short-but-multi-character term ('AI', 2 characters)
    must remain admitted both today and after the Developer's revert --
    it was never reached by the reversed `^[A-Za-z]$` rule (which matches
    exactly one letter, never two) and there is no other rule that would
    touch it. Kept unchanged this pass (director/Planner brief: "the 'AI'
    control stays") as a stable regression pin across the revert, guarding
    against any future implementation (single-letter or otherwise) that
    would over-broadly sweep in short multi-character terms
    (`expansion_precision_2.md`'s own sample includes a real 2-character
    GENUINE term, 'PA')."""
    primary_today = _terms(_primary_today(_TEXT_CONTROL))
    assert primary_today.get(MULTI_CHAR_TERM) == [_CONTROL_DEF], (
        f"'{MULTI_CHAR_TERM}' must stay admitted both today and after the "
        f"Developer's revert (it is 2 characters, not a bare single letter) "
        f"-- got {primary_today.get(MULTI_CHAR_TERM)!r}"
    )
    assert primary_today.get("Wrenfeld") == [
        'a real, freestanding concept entirely on its own. '
        f'"{MULTI_CHAR_TERM}" includes a real multi-character acronym term that '
        "must stay admitted, not a bare single letter."
    ], (
        f"'Wrenfeld' (the primary engine's own existing entry) must stay "
        f"unchanged -- got {primary_today.get('Wrenfeld')!r}"
    )
