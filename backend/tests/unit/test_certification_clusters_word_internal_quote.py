"""D-CERT (IL track), sprint 2026-08-05-defs-il-certification, Round 2,
ruling M33-2 (panel manager, `2026-08-05-defs-il-certification-log.md`).

**Why this file exists, per the ruling's own explicit instruction:** "the
refinement must carry its own committed unit test pinning the `ו"`
conjunction case." Round 1 found (and reported, not applied) a measured
2.3% false-positive rate in cluster 1's contract-specified predicate
(`clusters.is_word_internal_quote`): a quote immediately preceded by a
bare, standalone vav conjunction ("ו", "and") is the OPENING delimiter of
a second term in a `"term1" ו"term2"` list, never a word-internal
abbreviation marker, even though both its immediate neighbors are Hebrew
letters -- the predicate's own literal trigger condition. The panel
manager independently re-verified this on `"רכב" ו"דרך"` before ruling it
APPLIED, not merely reported. This file pins that positive case AND its
negative controls (a vav that is genuinely part of a longer word, where
the ORIGINAL word-internal classification must still hold) as plain
unit-level assertions on strings -- no corpus, no fixture, no pipeline
call. This is deliberately the SMALL, fast, exhaustive-by-inspection
complement to the corpus-scale manifest: the manifest shows the
predicate's AGGREGATE effect (2,096 corrections across 1,004 real
files); this file shows the predicate is CORRECT on the minimal case
that motivated the change, byte for byte, independent of the corpus.
"""

from __future__ import annotations

from tests.certification import clusters


def test_original_word_internal_case_is_unaffected_by_the_refinement():
    """`תשע"א` (a real corpus abbreviation shape, e.g. the Hebrew year
    תשע"א) -- the quote's neighbors are 'ע' and 'א', neither of which is
    'ו'. Must remain word-internal exactly as cluster 1's original,
    unrefined predicate already classified it -- the refinement changes
    ONE specific shape, not the general rule."""
    assert clusters.is_word_internal_quote("ע", "א") is True
    assert clusters.is_word_internal_quote("ע", "א", char_before_prev="ש") is True


def test_standalone_vav_conjunction_opener_is_now_eligible_not_word_internal():
    '''THE case this refinement exists for. `"רכב" ו"דרך"` -- two real,
    distinct terms ("car", "road") joined by a bare vav conjunction with
    no space before the second quote. The second quote's own neighbors:
    prev_char='ו' (the conjunction itself), next_char='ד' (first letter
    of "דרך"), char_before_prev=' ' (the space between "רכב" and "ו" --
    the vav is a standalone one-letter word, not part of a longer word).
    Verified independently by the panel manager against this exact
    string before ruling M33-2 -- this test pins the same case, not a
    paraphrase of it.'''
    line = '"רכב" ו"דרך"'
    quote_positions = [i for i, ch in enumerate(line) if ch == '"']
    # 4 quotes total: close-"רכב" open/close-"דרך" pairs plus the
    # opening quote of "רכב" itself -- the THIRD one (index 2) is the
    # opening delimiter of "דרך", the one this refinement is about.
    assert len(quote_positions) == 4
    opener_index = quote_positions[2]
    prev_char = line[opener_index - 1]
    next_char = line[opener_index + 1]
    char_before_prev = line[opener_index - 2]
    # Sanity-check the harvested characters actually match the
    # docstring's own claim, so a future edit to `line` cannot silently
    # make this test assert something else.
    assert (prev_char, next_char, char_before_prev) == ("ו", "ד", " ")

    assert clusters.is_word_internal_quote(prev_char, next_char, char_before_prev) is False


def test_standalone_vav_at_start_of_text_is_also_eligible():
    """`char_before_prev=""` (start-of-body/line, no character at all
    before the vav) must be treated the same as whitespace -- a lone `ו`
    at the very start of a scanned span is still a standalone
    conjunction, not evidence of a longer word continuing leftward off
    the edge of what this predicate can see."""
    assert clusters.is_word_internal_quote("ו", "ד", char_before_prev="") is False
    # The default (no third argument at all) must match the explicit ""
    # case -- callers that cannot supply three characters of context
    # still get the safe, standalone-vav-assuming behavior.
    assert clusters.is_word_internal_quote("ו", "ד") is False


def test_vav_that_is_part_of_a_longer_word_stays_word_internal_negative_control():
    """The refinement must NOT over-correct: a vav immediately preceded
    by ANOTHER Hebrew letter (i.e. the vav is the last letter of a
    longer word, not a one-letter conjunction standing alone) is still a
    genuine word-internal context, and the quote after it must still be
    classified word-internal exactly as cluster 1's original predicate
    would. This is the negative control the ruling's own text implies
    ("a stated-falsifiable predicate... measurably false is worse than
    no template at all" cuts both ways -- an over-corrected predicate
    that stops disposing real abbreviations would be a new, different
    false-positive class)."""
    assert clusters.is_word_internal_quote("ו", "ד", char_before_prev="ב") is True
    assert clusters.is_word_internal_quote("ו", "ד", char_before_prev="א") is True


def test_base_hebrew_letter_gate_still_applies_first():
    """The vav-conjunction refinement only ever NARROWS the original
    predicate (moves some cases from True to False); it must never WIDEN
    it. A quote with a non-Hebrew-letter neighbor stays False regardless
    of the vav logic, exactly as before the refinement."""
    assert clusters.is_word_internal_quote("ו", " ") is False
    assert clusters.is_word_internal_quote(" ", "ד") is False
    assert clusters.is_word_internal_quote("a", "b") is False
    assert clusters.is_word_internal_quote("", "") is False


def test_predicate_is_total_and_returns_a_plain_bool():
    """Backbone-test precondition (see `test_definition_links_il_
    certification_c2_span_exhaustiveness.py`'s own Level-0 totality
    test): the refined predicate must still return an unambiguous `bool`
    for every combination it can be called with, never raise, never
    return `None`/truthy-non-bool."""
    sample_chars = ["", " ", "\n", '"', "-", "ו", "א", "ת", "ד", "0", "a"]
    for prev in sample_chars:
        for next_ in sample_chars:
            for before in sample_chars:
                result = clusters.is_word_internal_quote(prev, next_, before)
                assert isinstance(result, bool), (prev, next_, before, result)
