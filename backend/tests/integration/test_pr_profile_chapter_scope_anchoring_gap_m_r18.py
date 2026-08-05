r"""Planner (M-R18, sprint 2026-08-04-defs-us-pr) -- an INCIDENTAL finding
from the exhaustive chapter-scope sweep, deliberately kept OUT of
`test_pr_profile_chapter_scope_vocabulary_m_r18.py`.

## Not a vocabulary gap -- a first-sentence ANCHORING gap

`STATE_PR_LEY_77_1957_ART23_010` (heading "Artículo 23.010. Título corto;
definiciones") opens:

    "Este Capítulo se conocerá como la 'Ley de Seguro de Préstamos
    Hipotecarios' y podrá citarse como tal. Para los fines de este
    capítulo: (1) Seguro de préstamos hipotecarios. -- Significa..."

The SECOND sentence contains "Para los fines de este capítulo" -- already
one of the fully-recognized trigger phrases, no new vocabulary needed. But
`detect_pr_chapter_scope` anchors on the body's FIRST sentence only (the
M-D3 erratum's own deliberate anchor, chosen cycle-9 specifically to reach
PAST a bare subsection label like `"(a) Para los fines..."` -- see
`pr_profile.py`'s own module comment above `_PR_CHAPTER_SCOPE_TRIGGER_RE`).
Here the first sentence is a genuine, complete short-title clause ("This
Chapter shall be known as...") that happens to contain the SAME unit word
("Este Capítulo") as its own subject -- pushing the real scope-setting
sentence to position 2. `determine_scope` returns `"law-wide"`, live,
today; the row's own drafting intent is `"chapter"`.

This is the SAME character of defect as the two prior misses (a phrase the
mechanism does not reach), but the mechanism at fault is the ANCHOR
(which sentence to look in), not the TRIGGER ALTERNATION (which phrases to
recognize within it) -- fixing this needs different code (e.g. trying
sentence 2 when sentence 1 has no trigger AND is itself a short-title/
citation clause, or scanning up to the first entry-marker instead of just
one sentence) than fixing the vocabulary does. Folding it into "the closed
vocabulary" would misrepresent what closes it, so it is named here,
separately, on its own evidence -- 1 canonical row, corpus-wide prevalence
not further chased (out of this bounded pass's scope; flagged, not
guessed). Recorded on the residual ledger for the manager to rule on
disposition (fix now vs. defer).

## Fixture

`pr_sample_rows_cycle12.json` (shared with the vocabulary-closure file) --
`STATE_PR_LEY_77_1957_ART23_010`, byte-verified sha256-identical against a
fresh, independent read of the pinned snapshot
(`301000fc3465374ee0f23c3c6953a8a861e95cad`).
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def test_get_profile_us_pr_misses_a_genuine_trigger_pushed_to_the_second_sentence_by_a_short_title_clause_live():
    """RED today: the genuine "Para los fines de este capítulo" trigger in
    `STATE_PR_LEY_77_1957_ART23_010`'s SECOND sentence is invisible to the
    first-sentence anchor because the FIRST sentence is a real, complete
    short-title clause that itself mentions "Este Capítulo". Proven on the
    live path (`get_profile("US-PR").determine_scope`), not the bare
    function."""
    rows = json.loads((FIXTURES / "pr_sample_rows_cycle12.json").read_text(encoding="utf-8"))
    row = next(r for r in rows if r["act_id"] == "STATE_PR_LEY_77_1957_ART23_010")

    from app.definition_links.profiles import get_profile
    from app.definition_links import pr_profile

    body = row["text"]
    first_sentence = pr_profile._sentence_containing(body, 0)
    assert "Para los fines de este capítulo" not in first_sentence, (
        "fixture sanity check: the genuine trigger must NOT be in the first "
        "sentence, or this test does not prove an anchoring gap at all -- "
        f"first sentence was: {first_sentence!r}"
    )
    assert "para los fines de este capítulo" in body.lower(), (
        "fixture sanity check: the genuine trigger must actually be present "
        "somewhere in the body, or this test proves nothing"
    )

    profile = get_profile("US-PR")
    assert profile.determine_scope(body) == "chapter", (
        "the row's own second sentence declares chapter scope in an already-"
        "recognized phrase; the first-sentence anchor is missing it -- an "
        "anchoring gap, not a vocabulary one (see this file's module "
        "docstring)"
    )
