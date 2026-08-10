"""GREEN safety guards -- sprint 2026-08-10-green-the-suite, item #21
(Planner pass, citation-vs-marker discriminator design). These do NOT
target issue #21's 16 defects (those stay pinned RED in
`test_us_markers_c5guard_class_b_boundary_defects.py`); they pin CURRENT,
already-correct `extract_quote_anchored_entries` behavior at the same
direct-call level (per M35's normalization statement -- no jurisdiction
registration needed to observe the engine's own behavior truthfully) that
the discriminator fix is most likely to put at risk, because it sits on
the exact same `_DIGIT_MARKER_RE`/`_DIGIT_DOT_MARKER_RE`/
`_TRAILING_MARKER_CHAIN_RE` machinery the 16 RED tests need touched.

Each guard below documents WHY it is fragile, verified live by
prototyping candidate discriminator fixes and finding each one break a
DIFFERENT one of these rows before landing on a version that broke none
of them (see this sprint's own blast-radius spec for the corpus-wide
version of this measurement):

- UT `"Insolvent"` (explicit brief requirement): the paren-digit hard-stop
  that must fire for `"(5)"` even though `"Paid and delivered"` never
  becomes its own captured entry (its idiom, "does not include", is not
  recognized). A naive "skip digit-marker hard-stops broadly" fix
  regresses this immediately.
- ND top-level bare digit-dot entries (explicit brief requirement): the
  SAME `STATE_ND_T51_C51-19_S51-19-02` row that hosts 2 of the 16 RED
  defects (`Commissioner`/`Rule`, leaking "5. a."/"14. a.") also hosts
  clean, already-correct bare-digit-dot entries (`Advertisement`,
  `Franchisee`) a fortnight's fix must not disturb while extending the
  marker-chain-walk to cover the "N. a." shape.
- FL `"Article"` (found during prototyping, not requested): a digit-paren
  marker with NO nearby quote (`"(2)(a) It is unlawful:"`) that must
  STILL hard-stop -- proves a discriminator cannot simply require a quote
  near every digit marker (that breaks this row) OR simply tighten to
  "uppercase-at-a-sentence-boundary" without care (that part alone is
  safe here, but combined with other tightenings is easy to lose).
- AK `"department"` (found during prototyping, not requested): a
  SEMICOLON-separated TOP-LEVEL list (`"(1) \"commissioner\" means ...;
  (2) \"department\" means ...; (3) \"transportation\" ..."`) -- proves
  punctuation between successive digit markers (semicolon vs period)
  is NOT a reliable signal for "internal enumeration vs top-level
  entry" on its own: ND's internal lists AND AK's top-level entries both
  use semicolons between items. A fix that treats "semicolon before a
  digit marker" as an unconditional suppression signal regresses this
  row specifically.
- AL `"immediate family"` (found during a corpus-wide blast-radius scan,
  not a fixture at all -- `STATE_AL_T1_C21_S22-21-260`): a THIRD
  entry-opening shape beyond "quoted term" and "ordinary prose" --
  `"(1) ACQUISITION. Obtaining ..."`/`"(2) APPLICANT. Any person, ..."`
  labels each top-level entry with a short ALL-CAPS run instead of a
  quote. `"immediate family"` is a genuine quoted sub-definition
  embedded INSIDE entry (1)'s own body; a discriminator that only
  recognizes a quote (not also an ALL-CAPS label) as proof that item 1
  "opens a real entry" misclassifies this row's entire numbered list as
  internal content, suppresses every real digit-marker hard stop after
  it, and lets `"immediate family"` run off the end of the section
  unbounded -- which either truncates it to garbage or (if it exceeds
  `MAX_CLEAN_DEFINITION_LENGTH`) drops it outright."""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _entries(fname: str, act_id: str) -> dict[str, str]:
    rows = {r["act_id"]: r for r in json.loads((FIXTURES / fname).read_text(encoding="utf-8"))}
    return dict(extract_quote_anchored_entries(rows[act_id]["text"]))


def test_ut_insolvent_still_bounded_by_the_next_non_means_idiom_entry():
    """Direct engine-level pin of the case this module's own docstring
    names (`_DIGIT_MARKER_RE`/`_LETTER_MARKER_RE` entry): `"(5)"` must
    still hard-stop `"Insolvent"` even though `"Paid and delivered"`'s own
    idiom ("does not include") is not recognized and it never becomes its
    own `starts` entry. Complements the existing full-pipeline pin in
    `test_us_markers_wave1_auto_rescue_subcases.py` at the pure-function
    level the discriminator fix actually touches."""
    entries = _entries("us_markers_wave2_subcases_rows.json", "STATE_UT_T75B_S75B_1_301")
    insolvent = entries["Insolvent"]
    for forbidden in ("Paid and delivered", "Personal property"):
        assert forbidden not in insolvent, (
            f'"Insolvent" illegally swallowed {forbidden!r}: {insolvent!r}'
        )
    assert insolvent.rstrip().endswith("federal bankruptcy law."), (
        f"got {insolvent!r}"
    )


def test_nd_clean_top_level_digit_dot_entries_unaffected_by_the_same_rows_defects():
    """The SAME `STATE_ND_T51_C51-19_S51-19-02` row that hosts 2 of issue
    #21's 16 RED defects (`Commissioner`/`Rule`, both leaking a next-entry
    "N. a." marker chain) also hosts clean bare-digit-dot entries that
    must stay clean while the marker-chain-walk is extended to cover that
    shape."""
    entries = _entries("us_markers_c5guard_nd_rows.json", "STATE_ND_T51_C51-19_S51-19-02")
    advertisement = entries["Advertisement"]
    assert advertisement.rstrip().endswith(
        "published in connection with an offer or sale of a franchise."
    ), f"got {advertisement!r}"
    assert "2." not in advertisement[-10:], f"leaked next marker: {advertisement!r}"

    franchisee = entries["Franchisee"]
    assert franchisee.strip() == "a person to whom a franchise is granted.", (
        f"got {franchisee!r}"
    )


def test_fl_article_still_bounded_by_the_unquoted_subsection_2_marker():
    """`STATE_FL_TXXXIII_C540_S540.11`'s `"Article"` (the pinned GREEN
    case in `test_us_markers_unbounded_last_entry.py`): its digit-paren
    boundary, `"(2)(a) It is unlawful:"`, has NO quoted term anywhere
    nearby -- a discriminator that requires a quote near every digit
    marker to treat it as a hard stop regresses this row specifically."""
    entries = _entries(
        "us_markers_unbounded_last_entry_rows.json", "STATE_FL_TXXXIII_C540_S540.11"
    )
    article = entries["Article"]
    assert article.rstrip().endswith(
        "or any copy or reproduction which duplicates, in whole or in part, the original."
    ), f"'Article' swallowed subsection (2): {article[-120:]!r}"
    assert "unlawful" not in article, f"'Article' swallowed subsection (2): {article!r}"


def test_ak_semicolon_joined_top_level_entries_stay_correctly_bounded():
    """`STATE_AK_T44_C44.42_S44.42.900` (mojibake-repaired inline, mirroring
    `us_markers_mojibake.py`'s own `_repair_ak`): its top-level list uses
    SEMICOLONS between `"(1)"`/`"(2)"`/`"(3)"`, the SAME punctuation ND's
    internal enumerations use between THEIR items -- proving punctuation
    alone cannot be the discriminator signal. `"commissioner"` and
    `"department"` must each close at their own real boundary, not run
    into the next entry."""
    rows = {
        r["act_id"]: r["text"]
        for r in json.loads(
            (FIXTURES / "us_markers_wave2_subcases_rows.json").read_text(encoding="utf-8")
        )
    }
    text = rows["STATE_AK_T44_C44.42_S44.42.900"].replace("\x93", '"').replace("\x94", '"')
    entries = dict(extract_quote_anchored_entries(text))

    commissioner = entries["commissioner"]
    assert commissioner.strip().rstrip(";") == (
        "the commissioner of transportation and public facilities"
    ), f"got {commissioner!r}"

    department = entries["department"]
    assert department.strip().rstrip(";") == (
        "the Department of Transportation and Public Facilities"
    ), f"got {department!r}"
    assert "transportation" not in department.lower().replace(
        "department of transportation and public facilities", ""
    ), f"'department' swallowed the next entry: {department!r}"


def test_al_all_caps_labeled_entries_still_bound_a_nested_quoted_sub_definition():
    """`STATE_AL_T1_C21_S22-21-260` (pulled live from the pinned corpus,
    not a hand-authored fixture -- see this module's own docstring): the
    row's own top-level list is labeled `"(1) ACQUISITION."`,
    `"(2) APPLICANT."`, ..., `"(14) STATE HEALTH PLANNING AND DEVELOPMENT
    AGENCY (SHPDA)."` -- ALL-CAPS labels, never quotes. `"immediate
    family"` is a genuine quoted `"shall mean"` sub-definition embedded
    inside entry (1)'s own body and must close at its own real boundary,
    not run into `"(2) APPLICANT."` and beyond."""
    entries = _entries("us_markers_c5guard_al_allcaps_rows.json", "STATE_AL_T1_C21_S22-21-260")
    immediate_family = entries["immediate family"]
    assert immediate_family.rstrip().endswith(
        "as such degrees are computed according to law."
    ), f"got {immediate_family!r}"
    assert "APPLICANT" not in immediate_family, (
        f"'immediate family' swallowed the next ALL-CAPS entry: {immediate_family!r}"
    )
    assert len(immediate_family) < 300, (
        f"'immediate family' ran unbounded past its own ~178-char definition "
        f"({len(immediate_family)} chars): {immediate_family[-60:]!r}"
    )
