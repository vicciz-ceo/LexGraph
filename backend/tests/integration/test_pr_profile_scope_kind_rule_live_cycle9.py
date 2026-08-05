r"""Cycle-9 Planner (M-R15 step 2, P1 canonical wiring — item 32, gate P3's
chapter half). `ScopeKindRule(jurisdiction_codes=("US-PR",), detect=...)`
makes `USProfile.determine_scope` — reached ONLY through `get_profile(
"US-PR")` — return `"chapter"` for a canonical Definiciones section whose
own opening declares a chapter-wide restriction (`"A los fines de este
Capítulo"` / `"A los efectos de este Capítulo"` / `"En este Capítulo"` and
siblings), never overriding baseline (which never fires on Spanish text).

## Supersedes `test_pr_profile_scope_cycle4.py` IN SUBSTANCE, not in file

That file's 6 REDs (held since cycle 4) all call `PRProfile(code=
"US-PR").determine_scope(...)` DIRECTLY. Confirmed this cycle: `PRProfile`
(`pr_profile.py`) has NO `determine_scope` method at all (`hasattr`
checked directly) and is NEVER instantiated anywhere in `backend/app/`
outside its own module (`grep -rn "PRProfile" backend/app/` outside
`pr_profile.py` → nothing) — the seam question was settled AGAINST the
`PRProfile` proposal (contract `## Coordination`: "PR ships as `USProfile`-
hosted rule modules"). `_REGISTRY["US-PR"]` is a `USProfile` instance;
`PRProfile` is a dead, unregistered class, a leftover of the ORIGINALLY-
PROPOSED (and rejected) distinct-profile-class seam option.

**Those 6 tests do NOT become satisfiable by a registered `ScopeKindRule`
as written** — no `ScopeKindRule` can make a method exist on a class that
is never returned by `get_profile` and never consults the registry. Per
role separation ("do not edit an existing test to fit"), that file is left
byte-untouched; it will remain permanently RED via `AttributeError` unless
a future ruling explicitly retires or rehomes it. The SUBSTANCE of what it
asserts — 4 distinct scope-trigger behaviors — DOES become satisfiable,
retargeted at the real `get_profile("US-PR")` path below.

## Scope: PR's own measured chapter-scope convention (M-D3 erratum)

PR bodies have ZERO newlines corpus-wide (cycle-1 survey, reconfirmed:
0/633 canonical rows contain `"\n"`) — so English/IL's `body_text.
splitlines()[0]` "first line" anchoring convention is a SILENT NO-OP for
PR (one "line" == the whole body), not merely inapplicable. Measured
(own script, `pr_p1_scope_measure*.py`, three anchoring strategies
compared against the real corpus): anchoring on the body's first SENTENCE
(`.`/`!`/`?` boundary — `pr_profile._SENTENCE_END_RE`'s own existing
convention, already used elsewhere in that module) is the anchor that
gets this right; "text before the first `_ENTRY_MARKER_RE` marker" is
NOT — it mis-treats a bare subsection-style label like `"(a) Para los
fines de este Capítulo..."` as if `(a)` were entry marker #1, returning
an EMPTY lead-in and missing the trigger (confirmed: 3 real canonical
rows share this exact shape, `STATE_PR_INCENTIVOS_SEC6070_55` vendored
below as the fixture proof).

Measured chapter-scope population (first-sentence anchored, own script,
verified precision — every one of the 21 hits hand-checked: the matched
trigger phrase sits BEFORE the body's real declarative preamble ends, in
18/21 cases literally at char offset 0): **21/633 canonical rows**
resolve to `"chapter"` — NOT the cycle-1 survey's 7 (that survey checked
only 2 of the phrases named in this item's brief, and did not anchor to
prevent the whole-body over-match a bare substring search produces: an
unanchored "En este Capítulo" search matches 28 canonical rows, but 7 of
those are the phrase appearing deep in unrelated body prose — e.g.
`STATE_PR_LEY_77_1957_ART9_040` at char 1253/1305, ~96% through the body
— never a scope declaration at all; see the negative-guard test below).
Full per-phrase counts, the anchoring comparison, and the 21-row list are
in the panel log's cycle-9 Planner entry.
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
def pr_rows_cycle2():
    return _load("pr_sample_rows_cycle2.json")


@pytest.fixture()
def pr_rows_cycle9():
    return _load("pr_sample_rows_cycle9.json")


@pytest.fixture()
def de_rows():
    return _load("de_sample_rows.json")


def test_get_profile_us_pr_determines_chapter_scope_on_the_real_fixture_row_live(pr_rows_cycle1):
    """`STATE_PR_LEY_77_1957_ART30_020` opens verbatim with "A los fines
    de este Capítulo, ..." at char offset 0 — the clean, unambiguous case
    (this is the SAME real row cycle-4's held test #1 used a SYNTHETIC
    paraphrase of; here it is the real body, byte-verified)."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle1["STATE_PR_LEY_77_1957_ART30_020"]
    profile = get_profile("US-PR")

    assert profile.determine_scope(row["text"]) == "chapter"


def test_get_profile_us_pr_determines_chapter_scope_when_a_subsection_label_prefixes_the_trigger_sentence_live(
    pr_rows_cycle9,
):
    """`STATE_PR_INCENTIVOS_SEC6070_55` opens `"(a) Para los fines de
    este Capítulo los siguientes términos..."` — the bare `(a)` label
    would be misread as entry marker #1 by a lead-in-before-first-marker
    anchor (returning an empty lead-in and MISSING this trigger); a
    first-sentence anchor correctly reaches past it. This is the test
    that forces the right anchoring choice — it is RED under the wrong
    design even though the phrase IS present in the body."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle9["STATE_PR_INCENTIVOS_SEC6070_55"]
    profile = get_profile("US-PR")

    assert profile.determine_scope(row["text"]) == "chapter"


def test_get_profile_us_pr_defaults_to_law_wide_on_the_mandate_example_row_live(pr_rows_cycle1):
    """`STATE_PR_LEY_249_2003_ART3` opens "Para propósitos de esta Ley,
    ..." — a LAW-scope idiom, not a chapter one. Must default to
    `"law-wide"`, never `"chapter"` or `"local"` (canonical sections never
    self-scope to `"local"` — that granularity is `extract_local_scope_
    definitions`'s domain, item 26, confirmed 0/635 in the cycle-1
    survey)."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle1["STATE_PR_LEY_249_2003_ART3"]
    profile = get_profile("US-PR")

    assert profile.determine_scope(row["text"]) == "law-wide"


def test_get_profile_us_pr_does_not_over_trigger_on_a_deep_body_mention_live(pr_rows_cycle2):
    """`STATE_PR_LEY_77_1957_ART9_040`'s body contains the literal
    substring "En este Capítulo" — but at char offset 1253 of a 1305-char
    body (~96% through it, inside an unrelated closing sentence: "...
    obtener una licencia como tal.", nowhere near "en este Capítulo para
    obtener..."), never as the section's own opening scope declaration.
    A `ScopeKindRule` that greps the WHOLE body (rather than anchoring to
    the opening) would wrongly return `"chapter"` here — this is the
    negative-guard proof that it does not. A test that WOULD FAIL under
    the naive "search anywhere in body" design measured and rejected this
    cycle (28 canonical hits unanchored vs. 21 anchored — this exact row
    is one of the 7-row difference)."""
    from app.definition_links.profiles import get_profile

    row = pr_rows_cycle2["STATE_PR_LEY_77_1957_ART9_040"]
    assert "en este Capítulo" in row["text"] or "En este Capítulo" in row["text"], (
        "fixture sanity check: this row must actually contain the substring "
        "being guarded against, or the negative guard proves nothing"
    )
    profile = get_profile("US-PR")

    assert profile.determine_scope(row["text"]) == "law-wide"


@pytest.mark.parametrize(
    "trigger_phrase",
    [
        "A los fines de este Capítulo",
        "A los efectos de este Capítulo",
        "En este Capítulo",
    ],
)
def test_each_named_chapter_scope_trigger_variant_is_recognized_live(trigger_phrase):
    """Same 3 phrases cycle-4's held test #3 named, retargeted at the live
    path. Synthetic body (no real corpus row needed to prove a
    well-defined positive for an isolated trigger phrase — matches this
    codebase's own convention for mechanism-proof tests, e.g. `test_pr_
    profile_article_scope_live_cycle5.py`'s module docstring)."""
    from app.definition_links.profiles import get_profile

    body = f'{trigger_phrase}, "Término" significa una definición de prueba.'
    profile = get_profile("US-PR")

    assert profile.determine_scope(body) == "chapter"


def test_article_scope_phrase_never_yields_local_or_chapter_live():
    """Same substance as cycle-4's held test #4: "A los fines de este
    Artículo" (article-scope) must never make `determine_scope` return
    `"local"` — reconfirmed this cycle, 0/633 canonical rows use it as
    their own opening scope-setter (own script)."""
    from app.definition_links.profiles import get_profile

    body = 'A los fines de este Artículo, "vehículo" incluye motocicletas.'
    profile = get_profile("US-PR")

    result = profile.determine_scope(body)
    assert result not in ("local", "chapter"), (
        f"an ARTICLE-scope trigger must not be read as chapter-or-narrower — got {result!r}"
    )


def test_registering_us_pr_scope_kind_rule_does_not_change_a_real_english_state_row_live(de_rows):
    """P5 (M-R4) two-sided proof, scope half: a REAL English-state row
    fed through `get_profile("US-PR").determine_scope` must equal
    baseline's own answer exactly."""
    from app.definition_links.profiles import get_profile
    from app.definition_links.us_profile import determine_scope as us_baseline_determine_scope

    row = de_rows["STATE_DE_T5_C7_SVIII_S796"]
    profile = get_profile("US-PR")

    baseline = us_baseline_determine_scope(row["text"])
    live = profile.determine_scope(row["text"])
    assert live == baseline, (
        f"get_profile('US-PR').determine_scope on real English text must equal baseline "
        f"exactly — baseline={baseline!r} live={live!r}"
    )
