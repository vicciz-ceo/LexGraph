"""Sprint 2026-08-23-defs-debt-31, Item 1 -- structural controls (M-R107:
novel, unseen identifiers, never a real term/jurisdiction/section key)
complementing this file's sibling real-row reproductions
(`test_us_markers_defs_debt_31_bleed_trim_real_rows_red.py`). Each control
here isolates ONE population the fix must reach, per gate 1's explicit
"every population the change can reach is enumerated and measured, not
just the wave" instruction (standing single-letter lesson):

1. a candidate reached ONLY through the fallback (bare `includes`, never
   `_TIGHT_IDIOM_RE`-recognized) -- proves the fix is not accidentally
   scoped to primary-engine-adjacent rows;
2. the ORIGINAL zero-primary-candidate population (the pre-dates-the-wave
   shape: primary finds NOTHING at all on this row, not just "this one
   term") -- this fallback pre-dates the wave; the whole fallback
   population counts, not only wave-additions;
3. a body with ZERO newline characters (one physical line) -- 9 real
   jurisdictions (NH/SC/PR/NY/UT/OH/IL/WA/NJ) have effectively no
   newlines in their raw text; a trim mechanism that silently depends on
   `\\n`-delimited paragraph/marker structure would silently no-op there;
4. a positive control: a fallback entry immediately followed by its own
   real next quoted+idiom sibling must keep its FULL text -- the fix must
   not become a new, over-eager truncation defect.

All bodies call `USProfile.extract_definitions_from_section` directly with
`heading_was_derived=True`, the exact call shape
`USProfile.extract_definitions_from_section` (us_profile.py ~2619-2620)
uses when it invokes `_merge_fallback_candidates` -- matching the existing
`test_us_markers_fallback_guard_single_letter_negative_control.py`
convention (same helper shape, same profile access pattern)."""
from __future__ import annotations

from app.definition_links.profiles import get_profile

_PROFILE_OH = get_profile("US-OH")
_PROFILE_NJ = get_profile("US-NJ")  # one of the 9 effectively-no-newline jurisdictions


def _terms(candidates) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in candidates:
        for t in c.terms:
            out[t] = c.definition_text
    return out


# --- 1: fallback-only candidate (bare "includes", never primary-recognized) -

TEXT_FALLBACK_ONLY_BLEED = (
    "Introductory prose with no leading quote at all. "
    '"Wrenfeld apparatus" includes a self-contained diagnostic unit used for '
    "calibration testing. "
    "2. Renewal procedures for unrelated apparatus proceed as follows: "
    "(a) An operator must submit updated documentation; "
    "(b) The certifying board reviews the submission within thirty days."
)


def test_fixture_precondition_fallback_only_bleed_has_zero_primary_candidates():
    """Sanity: the primary engine (independent of the fallback merge) finds
    ZERO entries here -- bare `includes` is not `_TIGHT_IDIOM_RE`-recognized
    -- so the RED test below is not vacuously passing via the primary path."""
    primary = _terms(
        _PROFILE_OH.extract_definitions_from_section(
            TEXT_FALLBACK_ONLY_BLEED, scope="law-wide", heading_was_derived=False
        )
    )
    assert primary == {}, f"sanity: primary engine must find zero entries, got {sorted(primary)!r}"


def test_red_fallback_only_candidate_bleed_is_trimmed():
    """A candidate reachable ONLY through `_extract_inline_quoted_
    definitions` (bare `includes`) must still be TRIMMED at its own true
    end, not bleed into the unrelated numbered renewal-procedure
    subsection -- proves the fix reaches fallback-sourced candidates
    generally, not just ones a primary-engine sibling happens to bound."""
    merged = _terms(
        _PROFILE_OH.extract_definitions_from_section(
            TEXT_FALLBACK_ONLY_BLEED, scope="law-wide", heading_was_derived=True
        )
    )
    assert merged.get("Wrenfeld apparatus") == (
        "a self-contained diagnostic unit used for calibration testing."
    ), f"got {merged.get('Wrenfeld apparatus')!r}"


# --- 2: original zero-primary-candidate population (pre-dates the wave) ----

TEXT_ZERO_PRIMARY_ROW_BLEED = (
    "Introductory prose with no leading quote at all, and no other "
    'recognizable entry anywhere on this row. "Halvorsen credential" '
    "includes a certification issued to a qualifying applicant under this "
    "subchapter. "
    "2. Renewal procedures for unrelated credentials proceed as follows: "
    "(a) An applicant must submit updated documentation; "
    "(b) The issuing authority reviews the submission within thirty days."
)


def test_fixture_precondition_zero_primary_row_has_zero_primary_candidates():
    """Sanity for the population this control targets: the ENTIRE row (not
    just this one term) has zero primary-engine candidates -- the exact
    'if not candidates' shape that pre-dates the wave (the 130-loss-
    recovery population's own shape, per the prior sprint's investigation),
    distinct from a row where the primary engine already found something
    else. Bare `includes` (unlike `means`/`shall include`) is never
    `_TIGHT_IDIOM_RE`-recognized by ANY jurisdiction's primary path,
    including OH's own EntrySplitterRule (which itself calls
    `extract_quote_anchored_entries` unconditionally, independent of
    `heading_was_derived`) -- verified here, not assumed."""
    primary = _terms(
        _PROFILE_OH.extract_definitions_from_section(
            TEXT_ZERO_PRIMARY_ROW_BLEED, scope="law-wide", heading_was_derived=False
        )
    )
    assert primary == {}, f"sanity: whole-row primary candidates must be zero, got {sorted(primary)!r}"


def test_red_zero_primary_candidate_population_bleed_is_trimmed():
    """Same shape as gate 1's 'whole fallback population counts, not just
    the wave' instruction: a row where the primary engine found NOTHING at
    all (the original always-ran-unfiltered guard population) must still
    get TRIM-not-DROP treatment for its own bleed, exactly like a
    wave-population row does."""
    merged = _terms(
        _PROFILE_OH.extract_definitions_from_section(
            TEXT_ZERO_PRIMARY_ROW_BLEED, scope="law-wide", heading_was_derived=True
        )
    )
    assert merged.get("Halvorsen credential") == (
        "a certification issued to a qualifying applicant under this subchapter."
    ), f"got {merged.get('Halvorsen credential')!r}"


# --- 3: zero-newline body (one physical line; 9 real jurisdictions) --------

TEXT_NO_NEWLINE_BLEED = (
    'Introductory prose with no leading quote at all. "Thornquist '
    "accreditation\" includes a status granted to an institution meeting "
    "the applicable standards. 2. Renewal procedures for unrelated "
    "accreditations proceed as follows: (a) An institution must submit "
    "updated documentation; (b) The accrediting board reviews the "
    "submission within thirty days."
)
assert "\n" not in TEXT_NO_NEWLINE_BLEED, "this control's whole point is a single physical line"


def test_red_no_newline_body_bleed_is_trimmed_without_relying_on_newlines():
    """Same bleed shape as control 1/2 above, but with ZERO `\\n`
    characters anywhere in the body -- NH/SC/PR/NY/UT/OH/IL/WA/NJ have
    effectively no newlines in their real raw text (known trap, this
    sprint's contract), so a trim mechanism that silently keys off
    paragraph/line boundaries would no-op for those 9 jurisdictions. This
    control proves the fix trims correctly on a single-physical-line body
    too, using US-NJ (one of the 9)."""
    merged = _terms(
        _PROFILE_NJ.extract_definitions_from_section(
            TEXT_NO_NEWLINE_BLEED, scope="law-wide", heading_was_derived=True
        )
    )
    assert merged.get("Thornquist accreditation") == (
        "a status granted to an institution meeting the applicable standards."
    ), f"got {merged.get('Thornquist accreditation')!r}"


# --- 4: positive control -- a legitimately long, correctly-bounded entry ---
# must NOT be shortened by an over-eager trim heuristic.

TEXT_LEGITIMATE_LONG_ENTRY = (
    'Introductory prose with no leading quote at all. "Kestrelbourne '
    'notice" includes a written communication delivered under this '
    "subchapter that includes the recipient's name, the date of delivery, "
    "and a statement of the recipient's right to respond within thirty "
    'days. "Marrowfield notice" includes a separate written communication '
    "used for a different, unrelated purpose."
)


def test_positive_control_legitimately_bounded_entry_is_not_over_trimmed():
    """A fallback entry immediately followed by its OWN real next
    quoted+idiom sibling ('Marrowfield notice') is already correctly
    bounded by that sibling's quote -- the fix must leave this exact,
    already-correct boundary alone. Regression guard against a future trim
    heuristic that clips too early (e.g. on the embedded comma-separated
    clauses); GREEN today and must stay GREEN after the fix lands."""
    merged = _terms(
        _PROFILE_OH.extract_definitions_from_section(
            TEXT_LEGITIMATE_LONG_ENTRY, scope="law-wide", heading_was_derived=True
        )
    )
    assert merged.get("Kestrelbourne notice") == (
        "a written communication delivered under this subchapter that "
        "includes the recipient's name, the date of delivery, and a "
        "statement of the recipient's right to respond within thirty days."
    ), f"got {merged.get('Kestrelbourne notice')!r}"
    assert merged.get("Marrowfield notice") == (
        "a separate written communication used for a different, unrelated purpose."
    ), f"got {merged.get('Marrowfield notice')!r}"
