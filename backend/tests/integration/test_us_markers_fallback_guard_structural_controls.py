"""RED + negative-control structural tests (sprint 2026-08-20-defs-
boundary-idioms, pass 2 amendment, Item 2) for the fallback-suppression
guard fix in `backend/app/definition_links/us_profile.py::USProfile.
extract_definitions_from_section` (~line 2551).

Per manager ruling M-R107: every fixture here is fully synthetic, built
from unseen identifiers (never used elsewhere in the corpus or this test
suite) -- no jurisdiction, term, section number, date, or title is keyed
on for the RECOVERY mechanism. The real-row recovery is covered separately
by `test_us_markers_fallback_guard_recovery.py` (FED 12889/WA 717/OH 3296/
NY 1978) and the phantom-shape negative control by the real-row
`test_us_markers_fallback_guard_phantom_negative_control.py` (FED 4978).

Engine-level (`USProfile.extract_definitions_from_section`, not full
persistence) -- lighter than the persistence-altitude companions, same
style as `test_us_markers_boundary_idioms_structural_controls.py`."""
from __future__ import annotations

from app.definition_links.profiles import get_profile
from app.definition_links.us_profile import _extract_inline_quoted_definitions

_PROFILE = get_profile("US-WA")  # has a registered EntrySplitterRule (family-3)


def _primary(text: str):
    return _PROFILE.extract_definitions_from_section(text, scope="law-wide", heading_was_derived=True)


def _terms(candidates) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in candidates:
        for t in c.terms:
            out.setdefault(t, []).append(c.definition_text)
    return out


# --- RED: positive recovery, per-term merge --------------------------------


def test_fixture_precondition_primary_finds_exactly_zorbenex_and_fallback_also_finds_quixtor():
    """Sanity/precondition, not the RED itself: proves the exact shape this
    test depends on, so the RED below cannot go vacuous. Today, the
    primary engine finds exactly ONE entry ('Zorbenex' -- swallowing the
    rest of the text since it does not recognize bare 'includes' as a
    boundary); the fallback (unmodified by this item) independently finds
    BOTH 'Zorbenex' (cleanly bounded) and 'Quixtor'."""
    text = '"Zorbenex" means a first concept. "Quixtor" includes a second concept entirely.'

    primary_today = _terms(_primary(text))
    assert list(primary_today) == ["Zorbenex"], (
        f"sanity: primary engine must find exactly one entry today, got {sorted(primary_today)!r}"
    )

    fallback = _terms(_extract_inline_quoted_definitions(text, scope="law-wide"))
    assert fallback.get("Quixtor") == ["a second concept entirely."], (
        f"sanity: the fallback function itself must already find 'Quixtor' "
        f"today (unmodified by this item) -- got {fallback.get('Quixtor')!r}"
    )


def test_red_fallback_only_term_is_admitted_alongside_an_existing_primary_entry():
    """Today: the primary engine finds exactly ONE entry ('Zorbenex'), so
    `if not candidates` is False and the fallback never runs at all --
    'Quixtor' (only reachable through the broader fallback, which DOES
    recognize bare 'includes') is silently absent from
    `extract_definitions_from_section`'s own output. Once Item 2 merges the
    fallback's own per-term-novel candidates, 'Quixtor' must be recovered
    WITHOUT disturbing 'Zorbenex' (still present, unchanged)."""
    text = '"Zorbenex" means a first concept. "Quixtor" includes a second concept entirely.'

    primary = _terms(_primary(text))
    assert "Quixtor" in primary, (
        "RED: 'Quixtor' is missing entirely from extract_definitions_from_"
        "section's own output -- once Item 2's guard-site fix merges the "
        f"fallback's own per-term-novel candidates it must be admitted. Got "
        f"terms: {sorted(primary)!r}"
    )
    assert primary["Quixtor"] == ["a second concept entirely."], (
        f"'Quixtor' recovered but with the wrong text: {primary['Quixtor']!r}"
    )
    assert "Zorbenex" in primary and primary["Zorbenex"] == [
        'a first concept. "Quixtor" includes a second concept entirely.'
    ], (
        f"'Zorbenex' (the primary engine's own existing entry) must stay "
        f"unchanged -- got {primary.get('Zorbenex')!r}"
    )


# --- Negative controls: GREEN today, MUST STAY GREEN after Item 2's fix ----


def test_negative_control_stray_preposition_never_becomes_a_persisted_term():
    """A synthetic body reproducing the SAME general shape investigation.md
    classifies as a phantom mis-capture (a bare common English function
    word quoted immediately before a defining idiom): the fallback
    function DOES find it as a raw candidate (verified directly below,
    unmodified by this item) -- Item 2's spec'd implausible-capture filter
    must reject it before it is ever admitted. GREEN today (primary
    already has an entry, so the fallback never runs at all); MUST STAY
    GREEN after Item 2's merge lands."""
    text = (
        '"Wrenfeld" means a real, freestanding concept entirely on its own. '
        '"for" includes an unrelated stray capture that should never become a term.'
    )

    fallback = _terms(_extract_inline_quoted_definitions(text, scope="law-wide"))
    assert fallback.get("for") == [
        "an unrelated stray capture that should never become a term."
    ], (
        f"sanity: the fallback function itself must already raw-capture 'for' "
        f"today (unmodified by this item) -- got {fallback.get('for')!r}"
    )

    primary_today = _terms(_primary(text))
    assert "for" not in primary_today, (
        "'for' must not appear in extract_definitions_from_section's output "
        "today (guard currently suppresses the fallback entirely since "
        "'Wrenfeld' is already non-empty) -- and per Item 2's spec'd "
        "implausible-capture filter, it must STILL be absent once the merge "
        "lands, even though the fallback alone would otherwise surface it"
    )


def test_negative_control_amendment_caption_shape_never_becomes_a_persisted_term():
    """Same shape, for the OTHER phantom class investigation.md names: a
    quoted span beginning with a 4-digit year immediately followed by an
    em/en dash or hyphen -- the legislative-history amendment-caption
    shape. GREEN today; MUST STAY GREEN after Item 2's fix."""
    text = (
        '"Halvex" means a real, freestanding concept entirely on its own. '
        '"1999—Subsec. (a). Some citation note" includes another stray '
        "capture that looks like an amendment caption, not a definition."
    )
    caption_term = "1999—Subsec. (a). Some citation note"

    fallback = _terms(_extract_inline_quoted_definitions(text, scope="law-wide"))
    assert fallback.get(caption_term) == [
        "another stray capture that looks like an amendment caption, not a definition."
    ], f"sanity: the fallback function itself must already raw-capture this caption shape today -- got {fallback.get(caption_term)!r}"

    primary_today = _terms(_primary(text))
    assert caption_term not in primary_today, (
        f"the amendment-caption-shaped term must not appear in "
        f"extract_definitions_from_section's output today, and per Item 2's "
        f"spec'd implausible-capture filter must STILL be absent once the "
        f"merge lands"
    )
