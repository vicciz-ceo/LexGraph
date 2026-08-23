"""Sprint 2026-08-23-defs-debt-31, Item 3 (issue #31 debt class 3 --
"mis-paired-quote FP class"). Gate 3 is explicit: "evidence before code...
ship a fix only if an executed run proves zero genuine anchor losses...
otherwise return adjudicated evidence + a recommendation... not a forced-
code item." A no-code, written-adjudication outcome is a LEGITIMATE PASS
for this item -- by design, this file contains NO test asserting a
required extraction-code behavior, and therefore NO RED test.

**Why no RED test (deliberate, not an oversight)**: two independent prior
passes (`expansion_precision.md` Task 3/Filter leverage;
`expansion_precision_2.md` Task 2's new-FP-shape section) already
established, from real sampled/censused corpus data, that mis-paired
quotes (a real quoted phrase -- proper noun, program/report title, sign
text, cross-reference parenthetical, or classification label -- wrongly
paired with a defining idiom belonging to distant, unrelated prose) are
NOT separable from genuine same-shape terms by any term-key or payload-
shape signal: `Crime Stoppers` (FALSE POSITIVE) vs `Pilot Program`
(GENUINE) are the identical 2-word Title-Case shape; `apprenticeship`
(FALSE POSITIVE) vs `anyone`/`agency`/`community` (GENUINE) are the
identical ordinary-lowercase-word shape. Writing a test that asserts
"today's code mis-pairs this" as a passing/protected state would be
exactly the forbidden pattern ("never assert the pre-fix broken state in
a test the Developer cannot edit") -- if a fix IS found, that assertion
would need to flip, and only the Planner may edit tests. Writing a test
that asserts "this must be fixed" would foreclose the equally legitimate
adjudicated-recommendation outcome gate 3 names. Same precedent already
shipped in this exact codebase: `test_us_markers_fx7_ceiling_known_closed_
scope.py`'s own docstring: "there is no RED test in this file" -- GREEN
structural proof of WHY a hypothesized fix's premise does not hold, not a
target.

**What this file DOES pin (safe under any outcome)**: a pure, code-free
lexical fact about the SIGNAL SPACE a term-key/payload-shape rule would
have to work from -- the genuine and mis-paired exemplars below are
IDENTICAL by every shape signal this codebase's own filters already use
(word count, case pattern, character-class profile, length). This can
never flip red regardless of what the Developer ships (it calls no
production code at all), and it is the concrete, reproducible version of
why gate 3's "provable" bar is real, not rhetorical.

**Seam note (widened this sprint, not the prior one)**: the prior sprint's
gate 7 explicitly forbade touching `_extract_inline_quoted_definitions`'s
own internals; THIS sprint's gate 8 explicitly NAMES that same function as
an expected seam (needed for Item 1's trim fix). A positional/span-
tracking fix for mis-paired quotes -- previously ruled out only because
that seam was closed -- is not pre-foreclosed here; gate 3's "fix only if
provable" leaves it open. This file does not assume either way."""
from __future__ import annotations

import re

# --- M-R107 structural fixtures: novel identifiers, matched by shape ------
# Modeled on the evidence's own matched pairs, restated with unseen terms.

GENUINE_TERM = "Larkspur Guild"  # 2-word Title-Case phrase, genuinely defined
MISPAIRED_TERM = "Hollowmere Trust"  # 2-word Title-Case phrase, NOT itself defined

GENUINE_LOWERCASE_TERM = "waylay"  # ordinary lowercase word, genuinely defined
MISPAIRED_LOWERCASE_TERM = "forswear"  # ordinary lowercase word, NOT itself defined


def _shape_signature(term: str) -> tuple:
    """The same class of signal this codebase's own zero-collateral filters
    already use (`_FALLBACK_STOPWORD_TERMS`: an exact closed word list;
    `_FALLBACK_CAPTION_YEAR_RE`: a leading-digit shape;
    `Pub. L.`/`Subsec.\\(`: literal substrings; the single-letter
    `^[A-Za-z]$` rule: character count) -- word count and per-word
    capitalization pattern, never the term's own semantic content,
    definition-text content, or position in the source text. Deliberately
    NOT exact character length -- none of this codebase's existing filters
    key on that, and two same-shape English phrases are not expected to be
    byte-length-identical."""
    words = term.split()
    return (
        len(words),
        tuple(w[:1].isupper() for w in words),
        bool(re.fullmatch(r"[A-Za-z ]+", term)),
    )


def test_title_case_genuine_and_mispaired_terms_are_shape_identical():
    """`Larkspur Guild` (genuine) and `Hollowmere Trust` (mis-paired) are
    the SAME shape by every signal a term-key/payload rule could use --
    reproducing, with novel identifiers, the real evidence's own matched
    pair (`Crime Stoppers` FALSE POSITIVE vs `Pilot Program` GENUINE,
    `expansion_precision.md`). No rule keyed to this signal space can
    admit one and reject the other."""
    assert _shape_signature(GENUINE_TERM) == _shape_signature(MISPAIRED_TERM), (
        f"the genuine and mis-paired exemplars must be shape-identical for "
        f"this to be evidence of anything -- got "
        f"{_shape_signature(GENUINE_TERM)!r} vs {_shape_signature(MISPAIRED_TERM)!r}"
    )


def test_lowercase_genuine_and_mispaired_terms_are_shape_identical():
    """`waylay` (genuine) and `forswear` (mis-paired) are the same
    ordinary-lowercase-word shape -- reproducing the real evidence's
    `apprenticeship` (FALSE POSITIVE) vs `anyone`/`agency`/`community`
    (GENUINE) matched set with novel identifiers."""
    assert _shape_signature(GENUINE_LOWERCASE_TERM) == _shape_signature(MISPAIRED_LOWERCASE_TERM), (
        f"got {_shape_signature(GENUINE_LOWERCASE_TERM)!r} vs "
        f"{_shape_signature(MISPAIRED_LOWERCASE_TERM)!r}"
    )


def test_existing_shipped_shape_filters_do_not_discriminate_the_mispaired_shape():
    """The filters this codebase ALREADY ships
    (`us_profile._is_implausible_fallback_capture`: bare-stopword,
    4-digit-year-caption, `Pub. L.`, `Subsec.\\(`) are every one of them a
    term-key/payload SHAPE rule -- none inspects position. Direct proof
    they do not fire on either exemplar here (imported, not
    re-implemented): a rule of this family cannot be the mechanism that
    closes this defect class, which is exactly gate 3's own "evidence
    before code" premise, not an assumption."""
    from app.definition_links.us_profile import _is_implausible_fallback_capture
    from app.definition_links.extract import DefinitionCandidate

    for term in (GENUINE_TERM, MISPAIRED_TERM, GENUINE_LOWERCASE_TERM, MISPAIRED_LOWERCASE_TERM):
        candidate = DefinitionCandidate(terms=(term,), definition_text="placeholder text.", scope="law-wide")
        assert not _is_implausible_fallback_capture(candidate), (
            f"{term!r} must not be caught by any EXISTING shape filter -- "
            f"if it were, it would not be evidence for this item's own "
            f"'no shape rule can discriminate this class' finding"
        )
