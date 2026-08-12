"""RED tests for cycle-5 item 15 (manager course-correction, mid-cycle,
delivered after independently classifying the FULL 1,224-row U4 residual
rather than sampling it -- U4 had already bounced three QA cycles on the
same signature: hand-read the residual, find a new mechanical gap class,
bounce). Evidence file (manager-authored, handed to this Planner, P-R9):
`.../scratchpad/headings_mgr3_class5_evidence.json` -- `candidate_captures`
(15 rows), `manager_judged_excluded` (4 rows, reasoned), `all_132_
unassigned` (full residual, not a sample).

## The design question, measured (not guessed) -- see the Planner's report
for the full recall/precision numbers on the real corpus

The manager identified THREE independent defeat mechanisms behind the 15
candidates, none fixed by item 10's `and` alone:

1. **Unwhitelisted WORD connector** -- `further`/`when`/`in case of`
   (bounded literal phrases, same closed-whitelist house style as the
   existing `for|as|term`/item 10's `and`).
2. **Trailing numeric/bracket scrape artifact** -- `defined 1`/`defined
   1]` (a footnote marker glued onto the heading by the scrape, defeating
   R-VERB-bare's exact-last-token check).
3. **Connector punctuation STRIPPED entirely by the corpus** (e.g. `Peace
   officer defined reserved peace officer included.` -- the dash that
   should sit between "defined" and "reserved" is simply GONE, not
   garbled) -- structurally UNFIXABLE by any whitelist, closed or not,
   because there is no token left to whitelist.

The manager asked this Planner to MEASURE, not assume, whether a targeted
whitelist extension (mechanism 1+2 only) or an "inversion" (anchor on
`[TERM] + defined`, suppress via negative guards, which WOULD also close
mechanism 3) holds precision on the real corpus, and to report the
numbers either way.

**Measured** (`scratchpad/plan5_item15_design_probe.py`/`_probe2.py`,
full 52-file corpus, `defin`-titled population, P-R10-sane -- reproduces
the pinned 2,014,611 total / 83,303 `defin`-titled / 22,228 baseline-miss
figures exactly before trusting the new ones):

- A first "Title-Case run precedes `defined`" inversion attempt
  MEASURABLY FAILS precision: among its 38 new-true rows on the live miss
  pool, it collides with the ALREADY-CORRECTLY-EXCLUDED pension `defined
  benefit`/`defined contribution` jargon class (ledger L6's 155-row
  morphology bucket) purely because a capitalized word (`Supplemental`,
  `Qualified`, `Limited`, `Electing`, `Administering`) happens to precede
  `defined` -- e.g. `38-952 Supplemental defined contribution plan;
  establishment; administration` (AZ), `161.615 Limited defined
  contribution plan -- Purpose...` (KY), `Qualified defined contribution
  plan for employees of not-for-profit employer` (MA), four separate OH
  `defined benefit or defined contribution plan` rows, two PA `Employer
  defined contributions` rows. This is exactly the "higher-FP-risk"
  outcome the manager warned inversion carries -- confirmed empirically,
  not by intuition. **Inversion is REJECTED.**
- A targeted WHITELIST EXTENSION (word connectors `further`/`when`/`in
  case of`, plus a LEFT-WORD-BOUNDARY-ANCHORED trailing bare-digit/
  unmatched-bracket strip -- `\\bdefined\\s+\\d+\\]?\\.?\\s*$`, critically
  requiring `\\b` before `defined` so `redefined` is NEVER matched; an
  earlier, unanchored attempt at this same probe falsely matched 4 real
  Nevada county-boundary `"...boundaries redefined 1969"` rows before the
  boundary was added -- caught and fixed by this same measurement, not
  shipped) captures **exactly 7 rows (6 unique headings)** on the full
  corpus, **zero new false positives** (the probe's search covers the
  ENTIRE `defin`-titled miss pool, not a sample -- this is an exhaustive
  precision check, not a spot check). **This design is ADOPTED.**
- Mechanism 3 (stripped connector) is NOT closed by either design --
  whitelist extension has nothing to whitelist, and inversion is
  rejected. **Reported as a named, honest residual below (item 15's own
  ledger addition), not silently dropped.**

## What item 15 captures (6 unique headings, 7 rows incl. one duplicate
act_id) -- UNCONDITIONAL (no body gate; same class as items 10/11, all
hand-verified genuine below)

Design: NO new public symbol -- same as items 10/11, this is a whitelist/
artifact-strip widening of the EXISTING `_VERB_EXTENDED_RE`/`_VERB_
EXTENDED_UNCONDITIONAL_RE` machinery, consumed via the already-registered
`matches_heading_variant_unconditional`/`matches_heading_variant`.

**RED signal**: `AssertionError` (the shipped functions already exist and
return `False` for every row below today -- feature-absence is a missing
regex alternation/strip, not a missing symbol, same as items 10/11).

## Named residual (item 15's own ledger addition, escalate rather than
silently drop -- see the Planner's report)

- `STATE_IA_TIV_C154_S154.1`, `STATE_IA_TVIII_C313_S313.2`,
  `STATE_IA_TXIV_C558_S558.1`, `STATE_IA_TXVI_C724_S724.2A` -- mechanism 3
  (stripped connector), structurally unwhitelistable. NOT asserted True
  anywhere in this file (would be a false claim); recorded as residual.
- `STATE_MI_C324_AAct-451-of-1994_S324.63501` (`Meanings of words and
  phrases defined in MCL 324.63502 and 324.63503.`) -- explicitly D-MT-E1
  pointer-definition territory per the manager's own evidence (points to
  TWO other sections' own definitions), a different capture mechanism
  than item 15's connector fix; routed, not built here.
- `STATE_NM_C3_A32_S3-32-3` (x2 act_id variants, `Addition to
  definitions`) -- a D-HG-guard FALSE NEGATIVE: `definitions` is the last
  tail token, preceded by the preposition `to`, correctly guarded per the
  D-HG ruling in general, but THIS row's real body genuinely defines a
  term (`"project" also means: A. any land and buildings...`). Relaxing
  the D-HG guard is explicitly forbidden by the director ("Do not relax
  the guard") -- this is the preamble panel's "genuine minority rescues
  via body-content rules" territory, not a heading-side fix here.

## Negative guards -- the four excluded shapes the manager named, each
with a REAL row (not synthesized)

1. Adjectival `defined <noun>` jargon -- `"Defined cost sharing"` (IN).
2. `all offenses/crimes/word defined by statute` constitutional-style
   provisions -- `All offenses defined by statute.` (AK).
3. `as defined in [some other section]` cross-reference -- `defined in
   s. 800.04` (FL).
4. `defined by rule`/`by statute` DELEGATION -- `"Undue hardship"--
   Defined by rule.` (WA) and `Word defined by statute always has same
   meaning` (ND, a second, differently-phrased instance of the same
   delegation shape).

Fixture (byte-identical to the real parquet, all 24 columns, independently
re-verified column-by-column -- see the Planner's report):
`cycle5_class5_connector_rows.json` (11 rows: 6 positive-shape headings +
5 negative guards).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "cycle5_class5_connector_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


# === Positive: 6 unique headings, UNCONDITIONAL ==============================


@pytest.mark.parametrize(
    "act_id,reason",
    [
        (
            "STATE_ID_T18_C1_S18-111A",
            '"18-111A FELONY DEFINED FURTHER." -- word connector `further`. Body: '
            "'Wherever the words felony... are used... the same shall be defined "
            "as a felony and shall be punishable...' -- genuine",
        ),
        (
            "STATE_ID_T18_C1_S18-111B",
            "same `further` connector shape, MISDEMEANOR sibling",
        ),
        (
            "STATE_MA_PI_TXV_C94_S187",
            "word connector `when`. Body: \"The term ''misbranded'' as used in "
            "this chapter shall apply to each drug...\" -- genuinely defines "
            '"misbranded"',
        ),
        (
            "STATE_NM_C29_A8_S29-8-2",
            'trailing bare-bracket scrape artifact (`defined 1]`, no matching '
            "open bracket). Body: 'As used in the Mutual Aid Act, \"public "
            "agency\" includes the federal government...' -- genuine",
        ),
        (
            "STATE_NY_ASCP_A19_S1901",
            "trailing bare-digit scrape artifact (`defined 1`, a stray footnote "
            'marker -- NY\'s own documented literal-`\\n` scrape-defect family). '
            'Heading unambiguously names two quoted terms ("disposition" and '
            '"fiduciary") followed by "defined"',
        ),
        (
            "STATE_SC_T16_C11_A1_S16-11-10",
            'the literal 3-word connector phrase `in case of` -- DISTINCT from '
            'the bare `defined in` cross-reference shape (guard #3 below), which '
            "stays excluded. Body: 'any house, outhouse, apartment, building... "
            "shall be deemed a dwelling house...' -- genuinely extends the "
            'meaning of "dwelling house" for burglary/arson purposes',
        ),
    ],
)
def test_class5_connector_and_artifact_shapes_recognized_unconditionally(act_id, reason):
    from app.definition_links.rules.us_heading_variants import (
        matches_heading_variant,
        matches_heading_variant_unconditional,
    )

    row = _load_rows()[act_id]
    assert matches_heading_variant_unconditional(row["section_title"]) is True, (
        f"{row['section_title']!r}: {reason}"
    )
    assert matches_heading_variant(row["section_title"]) is True


def test_class5_trailing_artifact_strip_does_not_match_redefined():
    """Regression guard for the exact bug this Planner's own measurement
    caught mid-probe: a trailing-artifact regex without a LEFT word
    boundary before `defined` also matches the substring inside
    `redefined`, producing real false positives on Nevada county-boundary
    rows (`"boundaries redefined 1969"` etc, geography, not definitions).
    `\\bdefined\\b` (not a bare `defined` lookbehind) is load-bearing."""
    from app.definition_links.rules.us_heading_variants import (
        matches_heading_variant_unconditional,
    )

    assert matches_heading_variant_unconditional(
        "Creation--1873; boundaries redefined 1969"
    ) is False, "'redefined 1969' must NOT be treated as 'defined 1969' with a stripped connector"


# === Negative guards -- the four excluded shapes, real rows ==================


@pytest.mark.parametrize(
    "act_id,shape,reason",
    [
        (
            "STATE_IN_T27_A1_C50_S27-1-50-2",
            "adjectival `defined <noun>` jargon",
            '"Defined cost sharing" -- `defined` is adjectival (modifies "cost '
            "sharing\"), not a participle describing this section's own subject "
            "being defined; body confirms this is a cost-sharing definition "
            "clause, but the class is `defined <noun>` jargon broadly (155-row "
            "pension/insurance bucket, ledger L6), correctly excluded",
        ),
        (
            "STATE_AK_T11_C11.81_S11.81.220",
            "all offenses/crimes/word defined by statute",
            '"All offenses defined by statute." -- a constitutional-style '
            "nullum-crimen-sine-lege provision, not itself a definitions "
            "section; body: 'No conduct constitutes an offense unless it is "
            "made an offense (1) by this title...'",
        ),
        (
            "STATE_FL_TXLVI_C800_S800.05",
            "as-defined-in cross-reference to another section",
            '"...for a felony defined in s. 800.04." -- `defined in` + a '
            "citation-shaped continuation is the cross-reference exclusion "
            "shape (same class as the already-pinned NY 'as defined in the "
            "United States internal revenue code' guard), NOT the genuine "
            "`in case of` idiom the SC positive row above uses",
        ),
        (
            "STATE_WA_T43_C41_S109",
            "defined-by-rule delegation",
            '"Undue hardship\"--Defined by rule." -- body: \'The director... '
            "shall by rule establish a definition of \"undue hardship\"...' -- "
            "the statute DELEGATES defining to a future rule, it does not "
            "itself define the term",
        ),
        (
            "STATE_ND_T1_C1-01_S1-01-09",
            "word-defined-by-statute delegation (second phrasing)",
            '"Word defined by statute always has same meaning" -- a choice-of-'
            "law/construction provision about OTHER statutes' definitions, not "
            "itself a definitions section",
        ),
    ],
)
def test_class5_negative_guards_stay_false(act_id, shape, reason):
    from app.definition_links.rules.us_heading_variants import (
        matches_heading_variant,
        matches_heading_variant_unconditional,
    )

    row = _load_rows()[act_id]
    assert matches_heading_variant_unconditional(row["section_title"]) is False, (
        f"[{shape}] {row['section_title']!r}: {reason}"
    )
    assert matches_heading_variant(row["section_title"]) is False
