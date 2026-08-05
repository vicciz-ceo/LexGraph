r"""Planner (M-R18, sprint 2026-08-04-defs-us-pr) -- closes the CHAPTER-scope
trigger vocabulary by exhaustive corpus measurement, per ruling M-R18
("stop discovering trigger shapes one at a time").

## Method (full derivation in the panel log's M-R18 Planner entry)

Swept the real `us_pr_statutes.parquet` (HF snapshot
`301000fc3465374ee0f23c3c6953a8a861e95cad`) for every `este/esta` +
unit-word occurrence (Capítulo, Artículo, Ley, Código, Título, Subtítulo,
Sección), completely independent of `_PR_CHAPTER_SCOPE_TRIGGER_RE` (P-R7 --
the sweep does not seed from the mechanism it measures), then restricted to
the 633 canonical (Definiciones-heading) rows' TRUE first sentence (the
real `pr_profile._sentence_containing(body, 0)`, not an approximation) --
the population that can actually change `determine_scope`'s chapter-vs-
law-wide verdict.

**Capítulo: 31 canonical first-sentence hits.** 21 already resolve
`"chapter"`. Of the remaining 10: **6 are the already-ruled 5th shape**
(`"Para/A fines/efectos de este Capítulo"`, no `"los"` -- QA cycle-11's own
finding, independently reproduced by this from-scratch sweep, exact same 6
act_ids: `STATE_PR_LEY_20_2017_ART2_03/_ART3_03/_ART4_03/_ART5_03`,
`STATE_PR_LEY_77_1957_ART32_020/_ART53_020`). The other 4 are NOT vocabulary
gaps (verified by hand-reading full body text, not just the matched
substring):

  - `STATE_PR_LEY_77_1957_ART23_010` -- genuine trigger present, but in the
    body's SECOND sentence (first sentence is a short-title clause). An
    ANCHORING gap, not a vocabulary one -- see
    `test_pr_profile_chapter_scope_anchoring_gap_m_r18.py`, tracked
    separately per the manager's own escalation discipline.
  - `STATE_PR_RENTAS_SEC2041_03` -- "...deducciones... establecidas en el
    Subcapítulo 2 de este Capítulo" -- a cross-reference to an internal
    subdivision, not a scope declaration.
  - `STATE_PR_LEY_77_1957_ART36_010` -- "...de acuerdo con este capítulo"
    is the tail of a TERM's own definition clause, not a section preamble.
  - `STATE_PR_MUNICIPAL_ART7_100` -- "A los efectos de los Artículos 7.100
    a 7.103 de este Capítulo" scopes to 4 specific articles, narrower than
    the whole chapter; forcing it into `"chapter"` would over-broaden.
    Single occurrence, excluded, named on the residual ledger.

The `"según/como se usa(n)/emplea(n) en este Capítulo"` family (7 rows,
e.g. `STATE_PR_LEY_77_1957_ART39_050`) is verified ALREADY correctly
resolved -- it ends in the literal substring "en este Capítulo", which the
existing unanchored third regex branch (`En\s+este\s+Capítulo`) already
catches. Not a gap.

**Ley (324 hits) and Código (20 hits): EXCLUDED, deliberately.** Both
overwhelmingly genuine ("a los fines/efectos de esta Ley/este Código"), but
their semantic scope (the whole document) already equals `determine_scope`'s
own DEFAULT ("law-wide") -- adding a trigger for them would be vacuous by
construction, not a closed gap. Verified 0 mis-scopes either way.

**Artículo (7 hits) and Sección (4 hits) in the canonical/chapter context:
EXCLUDED.** All are either mid-body cross-references to a subsection of the
CURRENT canonical article/section (e.g. "según se define en el inciso (b)
de este Artículo") or tautological self-reference ("el significado
adjudicado en esta Sección" = defined right here) -- neither changes
chapter-vs-law-wide, and canonical sections never self-scope to `"local"`
by design (0/635, already established). No gap.

**Título (2 hits) and Subtítulo (11 hits, revealing Subcapítulo, 6 more
hits): a genuine finding with NO home in the current 2-way contract --
ESCALATED to the manager, not force-fit here.** See the panel log's M-R18
Planner entry and the sprint contract's residual ledger. Both are the SAME
grammatical family as the Capítulo trigger ("para/a (los) fines/efectos/
propósitos de este X"), unambiguously genuine (e.g.
`STATE_PR_RENTAS_SEC3010_01`: "A los efectos de este Subtítulo, los
siguientes términos tendrán el significado..."), but `determine_scope`'s
contract is documented as strictly 2-way (chapter/law-wide) and Título/
Subtítulo are a real intermediate granularity the data cannot even express
today (the parquet's own `chapter` column is uniform per code for every PR
law except Código Civil -- verified -- so even the ALREADY-SHIPPED
`"chapter"` kind is behaviorally degenerate to `"law-wide"` for its entire
current 21-row population). Escalated as a genuine recall/precision
trade-off (D-Q1), not guessed at here.

## Fixtures

`pr_sample_rows_cycle12.json` -- 2 REAL rows (all original parquet columns,
byte-verified sha256-identical against a fresh, independent read of the
pinned snapshot), the 2 already-known-and-ruled 5th-shape rows.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load(name: str) -> dict[str, dict]:
    rows = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows_cycle12():
    return _load("pr_sample_rows_cycle12.json")


def test_get_profile_us_pr_resolves_chapter_for_para_fines_no_los_live(pr_rows_cycle12):
    """`STATE_PR_LEY_20_2017_ART2_03` opens "Para fines de este Capítulo:
    ..." -- no "los". Currently mis-scoped `"law-wide"` (confirmed live);
    the closed vocabulary requires `"chapter"`. One of the 6 canonical rows
    behind the already-ruled 5th-shape fix (QA cycle-11), independently
    reproduced by this cycle's own from-scratch sweep."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle12["STATE_PR_LEY_20_2017_ART2_03"]
    profile = get_profile("US-PR")

    assert profile.determine_scope(row["text"]) == "chapter"


def test_get_profile_us_pr_resolves_chapter_for_para_efectos_no_los_live(pr_rows_cycle12):
    """`STATE_PR_LEY_77_1957_ART32_020` opens "Para efectos de este
    Capítulo, se considerará..." -- no "los". Same 5th-shape gap, the
    "efectos" (rather than "fines") variant, independently reproduced."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle12["STATE_PR_LEY_77_1957_ART32_020"]
    profile = get_profile("US-PR")

    assert profile.determine_scope(row["text"]) == "chapter"


@pytest.mark.parametrize(
    "trigger_phrase",
    [
        # the 2 corpus-confirmed no-"los" variants (Para + fines/efectos)
        "Para fines de este Capítulo",
        "Para efectos de este Capítulo",
        # the symmetric no-"los" variants with "A" instead of "Para" --
        # not yet observed in the 633-row canonical population, but the
        # SAME grammatical mechanism (P-R7: close the CLASS, not just the
        # instances on file) -- the existing regex already treats "A" and
        # "Para" as interchangeable WITH "los"; the fix (making "los"
        # optional) is prefix-agnostic, so both must be proven.
        "A fines de este Capítulo",
        "A efectos de este Capítulo",
    ],
)
def test_each_no_los_chapter_scope_trigger_variant_is_recognized_live(trigger_phrase):
    """Synthetic body, mirroring `test_each_named_chapter_scope_trigger_
    variant_is_recognized_live`'s own established convention for isolated
    mechanism proofs (cycle-9). Closes the full 2(prep)x2(noun) no-"los"
    combination space, not just the 2 corpus-attested rows above."""
    from app.definition_links.profiles import get_profile

    body = f'{trigger_phrase}, "Término" significa una definición de prueba.'
    profile = get_profile("US-PR")

    assert profile.determine_scope(body) == "chapter"
