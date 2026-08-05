r"""Cycle-9 Planner (M-R15 step 2, P1 canonical wiring — item 31).

`pr_profile.is_definitions_heading` has existed as a tested pure function
since cycle 1 and has NEVER been registered. This is the registration
proof: a `HeadingRule(jurisdiction_codes=("US-PR",), matches=pr_profile.
is_definitions_heading)` in a NEW rule module (`rules/us_pr_headings.py`,
Developer's to write, mirroring `rules/us_pr_citations.py`'s "wraps an
existing extractor verbatim" shape) makes `USProfile.is_definitions_
heading` — reached ONLY through `get_profile("US-PR")`, never a direct
`pr_profile` call — return `True` for a real Spanish Definiciones heading.

## Precision measurement (own, fresh corpus check — not inherited)

Own script against the real `us_pr_statutes.parquet` (23,636 rows), ground
truth built independently of `is_definitions_heading`'s own machinery (raw
`defini(on|ones)` stem substring anywhere in `section_title`, case-
insensitive — the SAME denominator construction cycle-1's survey used):

    ground truth (raw stem in section_title):      635
    pr_profile.is_definitions_heading fires on:     633
    English baseline fires on (Spanish corpus):       0
    TRUE POSITIVES:  633       FALSE POSITIVES:  0
    FALSE NEGATIVES:   2 (both CORRECT Table-of-Contents rejections,
                           STATE_PR_LEY_165_2020_ART1_2 / _51_2020_ART1_2 —
                           "Definiciones" appears only as a cross-referenced
                           chapter entry inside a TOC dump, not as this
                           row's OWN heading)

    PRECISION = 633/633 = 100.00%      RECALL = 633/635 = 99.69%

100.00% precision is comfortably above the ~90% floor the headings panel's
D-DF ruling needed `body_confirms` to reach (that panel's BARE rule
measured 86-89%). **No `body_confirms` is used for this `HeadingRule`** —
data-backed, not inherited: at 100% precision there is no false-positive
rate for a body-side gate to rescue, and `body_confirms` can only ever
REJECT a heading match (never rescue a miss), so adding one here would be
pure downside (further recall loss on the 2 already-explained TOC misses'
siblings, if any existed) for zero precision gain. Measured fresh this
cycle (`/private/tmp/.../scratchpad/pr_p1_heading_precision.py`) — supersedes
inheriting the headings panel's own D-DF answer for a structurally
different corpus.
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
def pr_rows_cycle1():
    return _load("pr_sample_rows.json")


@pytest.fixture()
def de_rows():
    return _load("de_sample_rows.json")


def test_get_profile_us_pr_recognizes_the_mandate_example_row_heading_live(pr_rows_cycle1):
    """`STATE_PR_LEY_249_2003_ART3` is the sprint contract's own named
    example row (`## Mandate`). Real heading `"Artículo 3. Definiciones"`,
    real body — no synthetic text anywhere in this assertion."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle1["STATE_PR_LEY_249_2003_ART3"]
    profile = get_profile("US-PR")

    assert profile.is_definitions_heading(row["section_title"], row["text"]) is True, (
        "get_profile('US-PR').is_definitions_heading must recognize the mandate's own "
        f"example row — got False for {row['section_title']!r}"
    )


def test_get_profile_us_pr_recognizes_a_compound_colon_suffixed_heading_live(pr_rows_cycle1):
    """`STATE_PR_LEY_77_1957_ART30_020`'s real heading is `"Artículo
    30.020. Definiciones:"` (trailing colon, compound section-number
    form) — a different shape than the bare-plural cycle-1 example,
    proving the live path isn't accidentally overfit to one heading
    shape."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle1["STATE_PR_LEY_77_1957_ART30_020"]
    profile = get_profile("US-PR")

    assert profile.is_definitions_heading(row["section_title"], row["text"]) is True


def test_get_profile_us_pr_correctly_rejects_the_table_of_contents_heading_live(pr_rows_cycle1):
    """`STATE_PR_LEY_165_2020_ART1_2` is a real Table-of-Contents dump
    whose `section_title` MENTIONS "Definiciones" only as a cross-
    referenced chapter entry (`"...Artículo 1.4 Definiciones Ar[tículo
    1.5...]"`), never as this row's OWN heading — one of the two measured
    false negatives above, and the CORRECT answer, not a miss. A live-path
    negative guard, not just a direct-function one (cycle-1's
    `test_pr_profile_headings.py` already pins this at the `PRProfile`-
    direct-call level; this re-proves it through the real registry-backed
    `get_profile` seam, where a careless `HeadingRule` could regress it)."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle1["STATE_PR_LEY_165_2020_ART1_2"]
    profile = get_profile("US-PR")

    assert profile.is_definitions_heading(row["section_title"], row["text"]) is False


def test_registering_us_pr_heading_rule_does_not_change_a_real_english_state_row_live(de_rows):
    """P5 (M-R4) two-sided proof, heading half: a REAL English-state row
    (`STATE_DE_T5_C7_SVIII_S796`, working-baseline state) fed through
    `get_profile("US-PR").is_definitions_heading` — the SAME registered PR
    `HeadingRule`, but on genuine English text — must produce the exact
    SAME answer baseline alone would, proving the Spanish stem-match rule
    never fires on English prose. `is_definitions_heading` baseline
    already returns True for a literal "Definitions" heading, so this
    checks BOTH the section's real (True) heading AND a real body
    fragment as a non-heading negative control."""
    from app.definition_links.profiles import get_profile
    from app.definition_links.us_profile import is_definitions_heading as us_baseline_is_def_heading

    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    pr_profile_obj = get_profile("US-PR")

    baseline_heading = us_baseline_is_def_heading(row["section_title"])
    live_heading = pr_profile_obj.is_definitions_heading(row["section_title"], row["text"])
    assert live_heading == baseline_heading, (
        "get_profile('US-PR').is_definitions_heading on a real English heading must equal "
        f"baseline's own answer exactly — baseline={baseline_heading!r} live={live_heading!r}"
    )

    # Negative control: an ordinary (non-heading) English body fragment.
    baseline_body_as_heading = us_baseline_is_def_heading(row["text"][:80])
    live_body_as_heading = pr_profile_obj.is_definitions_heading(row["text"][:80], row["text"])
    assert live_body_as_heading == baseline_body_as_heading == False
