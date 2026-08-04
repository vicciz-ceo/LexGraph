"""QA cycle-4 findings (sprint 2026-08-04-defs-us-pr, gate P4 zero-miss
sweep + gate P2 "outside canonical sections"). Independent QA verification
of the panel's cycle-3 handoff surfaced these as NEW misses the panel had
not seen -- none were named in the contract's `## Bucket D final split
(cycle 3)` table or the cycle-3 Developer/Manager corpus self-checks.

Per the sprint's role separation, QA does not fix `pr_profile.py` -- these
are RED tests pinning the gap for a Planner/Developer cycle-4 item, plus
one documentation-completeness pin (a residue-shaped row missing from the
contract's 7-row table). QA-authored, tests/fixtures only.

Six real rows, `pr_sample_rows_qa_cycle4.json`, byte-compared against the
live parquet immediately before commit -- see fixtures README.

## Findings, one test each

1. **`extract_local_definitions` misses the majority of its own target
   signal.** Full-corpus sweep (both `A los fines de este Artículo` and
   `Para propósitos de este Artículo`, 42 real corpus rows total) found only
   8/42 (19%) actually captured -- the function only recognizes ONE narrow
   shape (a quoted term immediately after the trigger phrase + optional
   comma). Two real, distinct unhandled shapes pinned here:
   `STATE_PR_LEY_20_2017_ART4_14` (`"se define "X" como..."` -- the quoted
   term follows `se define`, not the trigger phrase directly) and
   `STATE_PR_LEY_1_1966_ART8` (`"el término mayoría significará..."` --
   an UNQUOTED term, a shape the function has no pattern for at all).
2. **`A los efectos de este Artículo` -- a full THIRD synonymous
   scope-trigger phrase, measured in the Planner's own cycle-1 survey table
   (13 corpus-wide rows) -- is not in `_LOCAL_TRIGGER_RE`'s alternation at
   all.** 0/13 real corpus rows captured; `STATE_PR_LEY_77_1957_ART9_400`
   is a clean, unambiguous miss (`la frase "Comisión no devengada"
   significa...`, the SAME quoted+bare-idiom shape `extract_definitions_
   from_section` already handles for canonical sections).
3. **The unquoted-term dash separator never received cycle-2's ASCII-hyphen
   widening.** `_QUOTED_TERM_DASH_RE` accepts a plain ASCII hyphen (added
   cycle 2, comment: "cycle 1 only accepted the typographic dash"), but the
   UNQUOTED sibling `_UNQUOTED_TERM_DASH_RE` still only accepts `[–—]` --
   confirmed live: swapping ONLY the ASCII hyphen for an en-dash in
   `STATE_PR_LEY_209_2016_ART2`'s real text (no other change) flips it from
   0 to 2 correct candidates.
4. **`quiere decir` -- an idiom the Planner's OWN cycle-1 survey measured
   as real (7 corpus-wide / 3 canonical rows) -- was never added to either
   idiom alternation.** `STATE_PR_LEY_82_1964_ART3` has 3 real
   `"X" quiere decir Y` entries in one canonical section, all zero-yield.
5. **The cycle-3 marker-precondition gate on
   `extract_heading_anchored_definition` (`if _ENTRY_MARKER_RE.search
   (body): return []`) is over-broad, confirmed on a 4th real row beyond
   ruling M-R9's tension.** `STATE_PR_CIVIL_ART1267` (heading `"Vicio
   redhibitorio; definición"`) opens with a clean, unconditioned defining
   sentence ("Es vicio redhibitorio el defecto oculto...") but the SAME
   body also contains an incidental `(a)/(b)/(c)` examples sub-list --
   structurally identical to the `STATE_PR_LEY_77_1957_ART9_040` shape
   `extract_definitions_from_section`'s OWN dispatch fix already protects
   (cycle 2), but `extract_heading_anchored_definition`'s guard is a blunt
   any-marker-anywhere check, not a lead-in-based one, so it still returns
   `[]` here. Unlike M-R7's 3 rows (genuine conditions/subsection labels),
   this row is not a condition -- QA's lean (see the sprint log) is that
   this is a recall win, not a repeat of the M-R7 violation, and this test
   is left `xfail` (not a hard RED) since fixing gate 3 is a Developer/
   Planner judgment call on the right narrower condition, not something QA
   prescribes the mechanism for.

None of these six change the panel's own confirmed numbers (94.8% combined,
0 false positives, 633/635 headings) -- they are additive misses the
existing corpus self-checks did not individually surface because they
either fall outside the 633 canonical rows entirely (findings 1/2) or were
absorbed into the "33 still zero, out of this cycle's scope" aggregate
without row-level diagnosis (findings 3/4/5).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.pr_profile import (
    extract_definitions_from_section,
    extract_heading_anchored_definition,
    extract_local_definitions,
    is_definitions_heading,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "pr_sample_rows_qa_cycle4.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


# --- Finding 1: extract_local_definitions misses non-quoted-immediate shapes


def test_local_definitions_misses_a_se_define_como_lead_in(pr_rows):
    """`STATE_PR_LEY_20_2017_ART4_14`: 'Para propósitos de este Artículo,
    se define "toque de queda" como una orden decretada...' -- a real,
    unambiguous article-scoped definition. Currently captured: 0."""
    row = pr_rows["STATE_PR_LEY_20_2017_ART4_14"]
    assert 'se define' in row["text"]
    candidates = extract_local_definitions(row["text"])
    matching = [c for c in candidates if "toque de queda" in c.terms]
    assert len(matching) == 1, (
        "extract_local_definitions should capture the quoted term following "
        "'se define X como' -- currently returns "
        f"{candidates!r}"
    )


def test_local_definitions_misses_an_unquoted_term(pr_rows):
    """`STATE_PR_LEY_1_1966_ART8`: 'A los fines de este Artículo, el
    término mayoría significará la mitad más uno de los miembros
    presentes.' -- an UNQUOTED local-scope definition (5 near-identical
    rows share this exact shape across the University of PR law:
    ART6/8/9/10/11, all currently zero-yield). Currently captured: 0."""
    row = pr_rows["STATE_PR_LEY_1_1966_ART8"]
    candidates = extract_local_definitions(row["text"])
    matching = [c for c in candidates if "mayoría" in c.terms]
    assert len(matching) == 1, (
        "extract_local_definitions has no pattern at all for an UNQUOTED "
        f"term -- currently returns {candidates!r}"
    )


# --- Finding 2: "A los efectos de este Artículo" trigger entirely absent


def test_local_definitions_never_tries_the_efectos_trigger_variant(pr_rows):
    """`STATE_PR_LEY_77_1957_ART9_400`: 'A los efectos de este Artículo,
    la frase "Comisión no devengada" significa la comisión que se ha
    adelantado...' -- `_LOCAL_TRIGGER_RE` only recognizes 'A los fines de
    este Artículo'/'Para propósitos de este Artículo', never 'A los
    efectos de este Artículo' (13 real corpus-wide rows, per the Planner's
    own cycle-1 survey table -- 0/13 captured today)."""
    row = pr_rows["STATE_PR_LEY_77_1957_ART9_400"]
    assert "A los efectos de este Artículo" in row["text"]
    candidates = extract_local_definitions(row["text"])
    matching = [c for c in candidates if "Comisión no devengada" in c.terms]
    assert len(matching) == 1, (
        "'A los efectos de este Artículo' is not in _LOCAL_TRIGGER_RE's "
        f"alternation at all -- currently returns {candidates!r}"
    )


# --- Finding 3: unquoted-dash pattern never got the ASCII-hyphen widening


def test_unquoted_dash_separator_rejects_a_real_ascii_hyphen(pr_rows):
    """`STATE_PR_LEY_209_2016_ART2`: 'a) Documento acreditativo -
    significará el documento escrito...' uses a plain ASCII hyphen
    (U+002D) between the unquoted term and its idiom, exactly the
    character `_QUOTED_TERM_DASH_RE` was widened to accept in cycle 2 --
    `_UNQUOTED_TERM_DASH_RE` never received the same fix. Currently
    captured: 0 of 2 real entries in this row."""
    row = pr_rows["STATE_PR_LEY_209_2016_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    terms = {t for c in candidates for t in c.terms}
    assert "Documento acreditativo" in terms, (
        "_UNQUOTED_TERM_DASH_RE only accepts en/em dash [–—], not the real "
        f"corpus's ASCII hyphen -- currently returns {candidates!r}"
    )
    assert "Establecimiento comercial" in terms


# --- Finding 4: "quiere decir" idiom never implemented


def test_quiere_decir_idiom_is_not_recognized(pr_rows):
    """`STATE_PR_LEY_82_1964_ART3`: three real entries use `"X" quiere
    decir Y` (`"corporación" quiere decir Corporación de Renovación
    Urbana...`, etc.) -- `quiere decir` was measured as a real idiom in
    the Planner's own cycle-1 survey (7 corpus-wide / 3 canonical rows)
    but was never added to `_DEFINING_IDIOM_ALTERNATION` or
    `_QUOTED_DEFINING_IDIOM_ALTERNATION`. Currently captured: 0 of 3."""
    row = pr_rows["STATE_PR_LEY_82_1964_ART3"]
    assert row["text"].count("quiere decir") >= 3
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    terms = {t for c in candidates for t in c.terms}
    assert "corporación" in terms, (
        "'quiere decir' is absent from every idiom alternation in "
        f"pr_profile.py -- currently returns {candidates!r}"
    )


# --- Finding 5: marker-precondition gate over-suppression (M-R9 adjacent) ---


@pytest.mark.xfail(
    reason=(
        "QA finding, cycle-4 candidate, NOT a prescribed fix: "
        "extract_heading_anchored_definition's cycle-3 marker-precondition "
        "gate ('if _ENTRY_MARKER_RE.search(body): return []') correctly "
        "protects ruling M-R7's 3 genuine-condition rows, but is blunt "
        "enough to also suppress this row, which is NOT a condition -- a "
        "clean, unconditioned defining sentence followed by an incidental "
        "examples sub-list, the same shape extract_definitions_from_"
        "section's own cycle-2 dispatch fix already protects for "
        "STATE_PR_LEY_77_1957_ART9_040. QA's lean (sprint log): recall "
        "win, narrow the gate to check only whether the CORROBORATING "
        "SENTENCE itself is marker-free, not the whole body. Left xfail, "
        "not RED, because the exact narrower condition is a Developer/"
        "Planner design choice this test does not prescribe."
    ),
    strict=True,
)
def test_heading_anchored_definition_captures_vicio_redhibitorio_despite_an_incidental_sublist(
    pr_rows,
):
    row = pr_rows["STATE_PR_CIVIL_ART1267"]
    assert is_definitions_heading(row["section_title"])
    candidates = extract_heading_anchored_definition(
        row["section_title"], row["text"], scope="law-wide"
    )
    matching = [c for c in candidates if "Vicio redhibitorio" in c.terms]
    assert len(matching) == 1
