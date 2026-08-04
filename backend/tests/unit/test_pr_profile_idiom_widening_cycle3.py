"""RED tests for the `se refiere a` / `se referirá a` idiom-gap re-triage --
sprint 2026-08-04-defs-us-pr, cycle 3, gates P1/P4.

## Why this file exists

The cycle-2 Developer deliberately did NOT widen `_DEFINING_IDIOM_
ALTERNATION` (`significará|significa|será|es`) to include `se refiere a`/
`se referirá a`, flagging it explicitly as a residual-risk follow-up (see
`docs/sprint/sprints/2026-08-04-defs-us-pr-log.md`, cycle-2 Developer
entry, "Design choices / residual risk on the record": "widening the
idiom alternation used by the bare-idiom patterns has a wider blast
radius... than I was willing to take unilaterally against a corpus-wide
check I could only run once at the end"). The manager's own bucket-D
split (`scratchpad/mgr_bucketD_split.py`) then mis-labelled several rows
using this idiom as "anchor-less residue" (bucket D) when they are
actually ordinary idiom gaps, per this cycle's director-mandated
re-triage.

## Corpus-wide survey (this cycle, `se refiere a` / `se referirá a` /
sibling idioms)

| Idiom | Corpus-wide rows | Canonical-section rows | Among CURRENT zero-yield rows |
|---|---|---|---|
| `se refiere a` | 180 | 85 | 3 |
| `se referirá(n) a` | 22 | 9 | 2 |
| `se entenderá(n)` (not already-handled `...por`) | 646 | 52 | 4 |
| `se considera(rá) como` | 303 | 30 | 5 |

**Verdict**: `se refiere a`/`se referirá a` are real, safe defining
idioms when used the SAME way `significa`/`será`/`es` already are --
immediately after a QUOTED term, inside an already-detected canonical
Definiciones section. `se considera como` is a real sibling idiom too
(found via re-triaging `STATE_PR_LEY_155_1937_SEC1`, see
`test_pr_profile_extraction_cycle3.py`) -- flagged as a further follow-up
idiom, not fixed this cycle (only 1 of its 5 zero-yield rows is diagnosed
here; the other 4 need their own per-row diagnosis before a blanket
widening is safe, per this file's own precision finding below).

## THE RECALL-VS-FALSE-POSITIVE FINDING (why this needs a scoped fix, not
a blanket regex edit)

A blind widening of `_DEFINING_IDIOM_ALTERNATION` to include `se refiere
a`/`se referirá a` EVERYWHERE it's referenced is UNSAFE. Simulated
live against the real corpus (scratchpad `planner_c3_survey.py`/
`planner_c3_survey2.py`, never committed): widening the alternation used
by the per-BLOCK quoted patterns (`_QUOTED_TERM_COMMA_IDIOM_RE`,
`_QUOTED_TERM_BARE_IDIOM_RE`) is safe -- those patterns only ever fire on
a block that already STARTS with a quote character, so a widened idiom
word cannot suddenly start matching unrelated unquoted prose. But
widening the SAME alternation as used by the DISPATCH-FALLBACK check
(`_UNQUOTED_BARE_IDIOM_TERM_RE`, which decides whether a MARKED body's
lead-in text before its first marker is itself a single bare-copulative
definition) is NOT safe: `STATE_PR_LEY_214_2004_ART2`'s real body OPENS
with a gender-neutrality boilerplate disclaimer, `"Todo término utilizado
en esta Ley para referirse a una persona o puesto se refiere a ambos
géneros, y los siguientes términos..."` -- widened to recognize `se
refiere a` as a bare idiom, THIS disclaimer itself satisfies the
dispatch-fallback shape (capital-letter-anchored short "term" + idiom
word), wrongly swallowing the entire 26-real-term marked list into ONE
fabricated "term" candidate (verified live: 26 correct terms -> 1
fabricated term). This is exactly the collision class the Developer's own
docstring already warns about for the English-preamble case (`"As used in
this subchapter:"`) -- the SAME structural risk, a different real
trigger phrase.

`test_widening_must_not_swallow_a_markers_lead_in_disclaimer_into_one_
fabricated_term` below is the regression guard pinning this: it is
NOT currently RED (the unfixed code correctly extracts all 26 real terms
today, since it has no `se refiere a` recognition at all yet) -- it is a
GREEN guard from day one, in the same spirit as
`test_clause_splitting_widening_does_not_create_new_false_positives` in
`test_pr_profile_headings_cycle2.py`: a fence around the Developer's
planned fix, proving the widening this file's OTHER test demands must be
scoped to the per-block quoted patterns only, never the dispatch
fallback.

Fixture data: REAL rows, `backend/tests/fixtures/us_statutes/
pr_sample_rows_cycle3.json`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.pr_profile import extract_definitions_from_section

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "pr_sample_rows_cycle3.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


# --- RED: the safe widening (quoted-block idiom only) ------------------------


def test_se_refiere_a_quoted_term_comma_idiom_is_captured(pr_rows):
    """`STATE_PR_LEY_66_2011_ART3`: `a. "Práctica basada en evidencia" se
    refiere a prácticas...` / `b. "Administración" se refiere a la
    Administración de Instituciones Juveniles.` -- both entries are
    marked, quoted-term blocks using `se refiere a` as their ONLY idiom
    signal (no colon/dash). Fully solved by widening the QUOTED-block
    idiom alternation alone (no dispatch-fallback involvement -- this
    row's own body has real `a.`/`b.` markers, so its lead-in before the
    first marker is empty)."""
    row = pr_rows["STATE_PR_LEY_66_2011_ART3"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    assert "Práctica basada en evidencia" in all_terms
    assert "Administración" in all_terms
    practica = next(c for c in candidates if c.terms == ("Práctica basada en evidencia",))
    assert "prácticas que han sido documentadas" in practica.definition_text


# --- GREEN from day one: the precision regression guard ---------------------


def test_widening_must_not_swallow_a_markers_lead_in_disclaimer_into_one_fabricated_term(
    pr_rows,
):
    """`STATE_PR_LEY_214_2004_ART2`: opens with a gender-neutrality
    disclaimer (`"Todo término utilizado en esta Ley para referirse a una
    persona o puesto se refiere a ambos géneros..."`) BEFORE its real
    marked entry list of 26+ distinct defined terms (`"Bono o Bonos"`,
    `"Fideicomiso"`, `"Departamento"`, etc.). A widening of the idiom set
    that reaches the DISPATCH-FALLBACK lead-in check would wrongly treat
    this disclaimer itself as a single bare-copulative definition,
    discarding every real marked entry. This must NEVER regress -- all of
    the real terms must survive, and the disclaimer sentence itself must
    NOT become a fabricated term."""
    row = pr_rows["STATE_PR_LEY_214_2004_ART2"]
    assert row["text"].startswith("Todo término utilizado en esta Ley")  # sanity
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    assert len(candidates) >= 20, (
        f"widening regression: only {len(candidates)} candidates survived "
        f"(expected >=20 real marked entries); terms={all_terms}"
    )
    assert "Fideicomiso" in all_terms
    assert "Departamento" in all_terms
    # the disclaimer itself must never become a fabricated "term"
    for term in all_terms:
        assert "se refiere a ambos géneros" not in term
        assert len(term) < 80, f"suspiciously long fabricated-looking term: {term!r}"
