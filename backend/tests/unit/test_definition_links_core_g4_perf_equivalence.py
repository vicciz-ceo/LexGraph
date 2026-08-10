"""Gate-1 equivalence guard -- sprint 2026-08-10-core-g4-discriminator-perf.

Gate 1 is the sprint's dominant constraint: whatever the Developer does to
bound G4's citation/cross-reference discriminator lookback
(`_citation_or_xref_context`, `_is_citation_or_xref_context`,
`us_profile.py:1488-1530`), `resolve_unit_path` and
`_is_citation_or_xref_context` must return EXACTLY what they return today,
for every input. A faster wrong answer is a sprint failure, and this is the
test that catches it.

**P-R11 compliance.** The baseline this test asserts against
(`../fixtures/us_statutes/core_g4_perf_equivalence_baseline.json`) is NOT
hand-authored. It was produced by literally running the CURRENT (unbounded-
lookback) code in this module against `_build_cases()` below and dumping the
real return values -- see `_regenerate_baseline` at the bottom. To
regenerate after an intentional, reviewed behavior change: `python -m
tests.unit.test_definition_links_core_g4_perf_equivalence` from `backend/`
with `PYTHONPATH=.:..` (or run the equivalent module invocation), then
review the JSON diff before committing.

**M-R107 compliance.** Every body below is synthetic prose built from
generic filler and the SAME closed vocabulary/citation shapes
`_citation_or_xref_context` itself is defined over (see its module comment,
us_profile.py:1394-1439) -- no corpus row IDs, hashes, section numbers,
terms, dates, titles, or exact sentences are depended on. This is a
CHARACTERIZATION test: it does not assert what the "correct" answer is for
any of these bodies (existing G2/G4/I9/I11 correctness tests already own
that), only that the current output is stable across the Developer's speed
change.

**Coverage.** The seven bodies below each combine several
`_citation_or_xref_context` branches (structural word, full-U.S.C.,
`Section N`, lone `§ N`, bare state code), the newline exception's positive
and negative sides, the chain-connector continuation rule, and the G2
ladder-selection-deferral path (an unclassifiable leading token) -- so a
lookback-window change that alters behavior on any one of them trips this
test. For each body this test pins TWO things: (1) `_is_citation_or_xref_
context`'s own boolean verdict for EVERY marker token `_iter_us_unit_marker_
tokens` finds in the body (exhaustive, not cherry-picked), and (2)
`resolve_unit_path`'s returned path at several char offsets (end of each
body, plus just after a few interior anchors).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links import us_profile
from app.definition_links.profiles import get_profile
from app.definition_links.sections import Article

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "core_g4_perf_equivalence_baseline.json"
)


def _build_cases() -> dict[str, dict]:
    """Deterministic synthetic bodies + the char offsets to probe. Pure
    inputs only -- no expected VALUES live here; see the module docstring.
    """
    return {
        "digit_ladder_with_rejections": {
            "text": (
                "1. General provisions apply as stated in Section 100.5 of "
                "this chapter.\n"
                "(a) A citation under subsection (1) of this part does not "
                "reopen an entry.\n"
                "(b) Related matters continue under (i) a first item and "
                "(ii) a second item.\n"
                "(2) A new top-level entry begins here, unaffected by the "
                "section citation above.\n"
            ),
            "anchors": ["a first item", "a second item", "begins here"],
        },
        "lower_alpha_ladder_full_usc_citation": {
            "text": (
                "(a) Introductory clause referencing 47 U.S.C. § 522(13) "
                "for definitions.\n"
                "(b) A second clause opens (1) a first sub-item and (2) a "
                "second sub-item.\n"
                "(c) A closing clause returns to the top level.\n"
            ),
            "anchors": ["a first sub-item", "second sub-item", "top level"],
        },
        "upper_alpha_ladder_bare_state_code": {
            "text": (
                "(A) Opening clause citing ABCDE 123.4(b) as an external "
                "reference.\n"
                "(B) A second clause opens (1) one sub-item.\n"
            ),
            "anchors": ["external reference", "one sub-item"],
        },
        "chain_continuation_or_connector": {
            "text": (
                "(A) Baseline clause.\n"
                "(B) A citation reads subsection (1)(a) or (1)(b) of this "
                "section without reopening any entry.\n"
                "(C) A fresh top-level clause follows.\n"
            ),
            "anchors": ["without reopening any entry", "clause follows"],
        },
        "newline_exception_positive_and_negative": {
            "text": (
                "Section 32\n\n(F) Township clause opens a genuine "
                "top-level entry.\n"
                "Section 112\n(1965), a citation continuation that stays "
                "rejected.\n"
                "(G) A further genuine clause follows.\n"
            ),
            "anchors": ["top-level entry", "stays rejected", "clause follows"],
        },
        "lone_section_and_ladder_deferral": {
            "text": (
                "(NEW) A revisor annotation that cannot open any ladder.\n"
                "1. The first genuine digit-outermost entry follows.\n"
                "§ 900(a) is a lone-section citation just before a real "
                "clause.\n"
                "(a) A genuine sub-item follows the citation above.\n"
            ),
            "anchors": ["entry follows", "before a real clause", "citation above"],
        },
        "structural_word_forward_and_backward_context": {
            "text": (
                "(a) Paragraph (b) of this subsection controls when both "
                "conflict.\n"
                "(b) The controlling clause is defined here as (1) primary "
                "and (2) secondary.\n"
            ),
            "anchors": ["controls when both conflict", "primary", "secondary"],
        },
    }


def _article(text: str) -> Article:
    return Article(number="1", heading="Definitions", body=text, chapter="1")


def _compute(cases: dict[str, dict]) -> dict[str, dict]:
    profile = get_profile("US-FED")
    result: dict[str, dict] = {}
    for name, case in cases.items():
        text = case["text"]
        article = _article(text)

        token_verdicts = []
        for start, end, token in us_profile._iter_us_unit_marker_tokens(text):
            marker_form = "parenthesized" if text[start] == "(" else "period"
            verdict = us_profile._is_citation_or_xref_context(
                text, start, end, marker_form
            )
            token_verdicts.append(
                {"start": start, "end": end, "token": token, "rejected": verdict}
            )

        offsets = {"end_of_body": len(text)}
        for anchor in case["anchors"]:
            assert anchor in text, f"{name!r} fixture drifted -- anchor {anchor!r} missing"
            offsets[anchor] = text.index(anchor) + len(anchor)

        paths = {}
        for label, offset in offsets.items():
            path = profile.resolve_unit_path(article, char_offset=offset)
            paths[label] = [{"kind": step.kind, "value": step.value} for step in path]

        result[name] = {"token_verdicts": token_verdicts, "paths": paths}
    return result


def test_is_citation_or_xref_context_and_resolve_unit_path_match_the_pinned_baseline():
    cases = _build_cases()
    actual = _compute(cases)
    baseline = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert set(actual) == set(baseline), (
        f"case set drifted: actual={sorted(actual)} baseline={sorted(baseline)}"
    )
    for name in baseline:
        assert actual[name] == baseline[name], (
            f"GATE 1 VIOLATION in case {name!r}: output changed. "
            f"actual={actual[name]!r} baseline={baseline[name]!r}"
        )


def _regenerate_baseline() -> None:  # pragma: no cover -- manual maintenance path
    cases = _build_cases()
    computed = _compute(cases)
    FIXTURE.write_text(
        json.dumps(computed, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {FIXTURE}")


if __name__ == "__main__":  # pragma: no cover
    _regenerate_baseline()
