"""Cycle-4 Planner tests, item 24 -- the page-break scrape-footer artifact
in `extract_definitions_from_section`'s SHARED scan path (sprint
2026-08-04-defs-us-pr, gates P4/P5).

Cycle 3 discovered the real page-break footer artifact (`"Rev. <date>
www.ogp.pr.gov Página N de M "<Law Title>"[ de <year>] [Ley N-YYYY, según
enmendada]"`, 370 corpus-wide rows) and stripped it -- but ONLY inside
`extract_heading_anchored_definition` (item 13), never in `extract_
definitions_from_section`'s own per-block scan, which every canonical
Definiciones section (600+ rows) still runs through. The developer's own
cycle-3 note judged this an acceptable risk because "every cycle-3
ordinary-workload test row's FIRST relevant quote occurs before any
footer text" -- true for THOSE rows, but not a corpus-wide guarantee.

This cycle's own P-R7-compliant sweep (independent of any existing test)
found **208 canonical rows** where a quoted-title footer sits BETWEEN two
real entry markers (not merely after the last one) -- and, live-checked
directly rather than assumed, at least one of them is ALREADY corrupted
by it TODAY: `STATE_PR_LEY_240_2002_ART3` (a real row never used in any
prior test) produces a candidate whose TERM is a mangled prose fragment
("Tiene un diagnóstico con una condición visual de deterioro
progresivo") and whose `definition_text` is literally the footer
boilerplate itself ("Rev. 15 de abril de 2024 www.ogp.pr.gov Página 2 de
5 ..."). This is a confirmed, live, real-corpus bug -- not a
hypothetical -- caught by re-running the discipline the module's own
comments recommend ("run the fix over the full corpus, don't trust the
pinned tests alone") rather than trusting the developer's own risk
assessment.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.pr_profile import extract_definitions_from_section

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows_cycle4.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


def test_footer_boilerplate_does_not_become_a_fabricated_candidate(pr_rows):
    """`STATE_PR_LEY_240_2002_ART3`: a real footer sits between two
    marker entries. No candidate's `definition_text` may contain the
    footer's own literal boilerplate marker (`www.ogp.pr.gov`), and no
    candidate's term may be the mangled prose fragment currently produced
    (`"Tiene un diagnóstico..."` -- not a real defined term in this
    law)."""
    row = pr_rows["STATE_PR_LEY_240_2002_ART3"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    for c in candidates:
        assert "www.ogp.pr.gov" not in c.definition_text, (
            f"footer boilerplate leaked into a candidate's definition_text: {c!r}"
        )
    all_terms = {t for c in candidates for t in c.terms}
    assert "Tiene un diagnóstico con una condición visual de deterioro progresivo" not in all_terms


def test_the_five_real_terms_are_still_correctly_captured(pr_rows):
    """Floor proof that fixing the footer leak must not cost the 5
    genuinely correct terms this row's extraction already gets right
    today (a regression guard for whatever fix lands, not new RED for
    these 5)."""
    row = pr_rows["STATE_PR_LEY_240_2002_ART3"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {t for c in candidates for t in c.terms}
    expected = {
        "Estudiante ciego",
        "Braille",
        "Programa de Educación Individualizado",
        "Materiales educativos",
        "Secretario",
    }
    assert expected <= all_terms
