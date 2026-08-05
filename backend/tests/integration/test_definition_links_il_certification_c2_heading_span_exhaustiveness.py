"""D-CERT (IL track), sprint 2026-08-05-defs-il-certification, Round 2,
ruling M33-3 (panel manager).

C2's backbone assertion, applied to the SEPARATE heading population
(`c1_heading_denominator.py`, `backend/tests/fixtures/certification/
c1_heading_span_population.jsonl`) -- distinct from `test_definition_
links_il_certification_c2_span_exhaustiveness.py`'s own body-population
test, per this sprint's Level-1/Level-1b split (`clusters.py`'s own
module docstring).

## Why this test is expected GREEN, unlike its body-population sibling

Every row in the heading population is uniformly `production_captured=
False`, verified by exhaustive grep against the real package (no rule
anywhere reads `Article.heading` TEXT content -- only its own boolean
match against known heading PATTERNS). There is exactly one cluster,
`heading_quoted_span_unreached`, and it matches every row -- not because
this round declined to differentiate further, but because there is
genuinely nothing to differentiate between rows on yet (see `clusters.
cluster_heading_quoted_span_unreached`'s own docstring). A GREEN test
here is not a weaker gate than the RED body-population test; it is an
honest description of a smaller, uniform population, mechanically
checked the same way.

## What this test does NOT claim

It does NOT claim the `אכרזה זאת` residual is closed. Round 2 found
(while building this population) that `אכרזה זאת`'s own file produces
ZERO `Article` objects from `sections.parse_articles` at all -- there is
no `.heading` string for THIS population to even contain. See
`c1_heading_denominator.py`'s own `numberless_at_marker_diagnostic` and
`clusters.PROPOSED_CLUSTERS["numberless_at_marker_zero_article_files"]`
for that separate, more fundamental, NOT-yet-closed finding.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tests.certification import clusters

_MANIFEST_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "certification"
    / "c1_heading_span_population.jsonl"
)


def _load_rows() -> list[dict]:
    if not _MANIFEST_PATH.exists():
        pytest.fail(
            f"{_MANIFEST_PATH} is missing. This test reads a COMMITTED, "
            "vendored manifest -- it must never read the corpus itself. "
            "Regenerate it with: backend/.venv/bin/python "
            "backend/tests/certification/c1_heading_denominator.py"
        )
    rows: list[dict] = []
    with _MANIFEST_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def test_heading_manifest_is_the_real_whole_population_not_a_sample():
    """353 is `c1_heading_denominator.py`'s own measured, reproduced
    output -- an exact pin, matching the same discipline as the body
    population's own row-count pin."""
    rows = _load_rows()
    assert len(rows) == 353, (
        f"expected the full re-derived heading candidate-span population "
        f"(353 rows, c1_heading_denominator.py's own measured output); "
        f"got {len(rows)}. Re-run c1_heading_denominator.py and confirm "
        f"the new count deliberately before updating this pin."
    )


def test_c2_every_heading_span_carries_exactly_one_cluster_id():
    """The heading-population analogue of the body backbone test.
    Expected GREEN (see this module's own docstring for why that is not
    a weaker standard): every row matches exactly
    `heading_quoted_span_unreached`, zero unassigned, zero
    double-assigned."""
    rows = _load_rows()

    unassigned: list[dict] = []
    double_assigned: list[tuple[dict, list[str]]] = []

    for row in rows:
        assigned = clusters.assign_heading_clusters(row)
        if len(assigned) == 0:
            unassigned.append(row)
        elif len(assigned) > 1:
            double_assigned.append((row, assigned))

    failure_lines = []
    if unassigned:
        sample = unassigned[:5]
        failure_lines.append(
            f"{len(unassigned)}/{len(rows)} heading spans are UNASSIGNED. "
            "Sample: "
            + "; ".join(
                f"{r['file']} art.{r['article_number']} {r['term_text']!r}" for r in sample
            )
        )
    if double_assigned:
        sample = double_assigned[:5]
        failure_lines.append(
            f"{len(double_assigned)}/{len(rows)} heading spans are "
            "DOUBLE-ASSIGNED. Sample: "
            + "; ".join(
                f"{r['file']} art.{r['article_number']} {r['term_text']!r} -> {ids}"
                for r, ids in sample
            )
        )

    assert not failure_lines, "\n".join(failure_lines)


def test_akraza_zot_file_is_confirmed_absent_from_this_population():
    """Pins the Round-2 correction to ruling M33-3's own framing (see
    this module's docstring, "What this test does NOT claim"): the file
    genuinely named by the parent sprint's residual (5) produces ZERO
    rows here, because `sections.parse_articles` produces ZERO articles
    for it at all -- not because this scan somehow missed a real
    heading. A future fix to the underlying `sections.py` gap (see
    `clusters.PROPOSED_CLUSTERS["numberless_at_marker_zero_article_
    files"]`) would be expected to flip this test's own premise, at
    which point it (and this comment) should be revisited, not silently
    left green for the wrong reason."""
    rows = _load_rows()
    akraza_zot_file = (
        "אכרזה על ארגון יציג של זכאים לפי חוק משפחות חיילים שנספו במערכה "
        "(תגמולים ושיקום).wiki"
    )
    matches = [r for r in rows if r["file"] == akraza_zot_file]
    assert matches == [], (
        f"expected ZERO rows from {akraza_zot_file!r} in the heading "
        f"population (its own @-marker line produces zero Article "
        f"objects via sections.parse_articles, confirmed live); got "
        f"{matches!r}. If this now finds rows, sections.py's own article-"
        f"marker handling likely changed -- re-verify the "
        f"numberless_at_marker_diagnostic before treating this as a "
        f"simple update."
    )
