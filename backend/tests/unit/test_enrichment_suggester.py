"""Track B, item B2 — offline heuristic suggester, pure-function unit tests
(gate G6).

`app.enrich.suggester` does not exist yet -- ModuleNotFoundError is the
expected RED signal. `suggest_assertions_from_spans` is a pure, offline,
deterministic function: no network, no randomness, no DB access -- given
the same spans it always returns the same candidates.
"""

from __future__ import annotations


def test_suggests_survives_termination_from_a_recognizable_span():
    from app.enrich.suggester import suggest_assertions_from_spans

    spans = [
        {
            "id": "span-1",
            "quote_text": "This obligation shall survive termination of this Agreement.",
        }
    ]
    candidates = suggest_assertions_from_spans(spans)

    assert len(candidates) >= 1
    candidate = candidates[0]
    assert candidate["assertion_type"] == "SURVIVES_TERMINATION"
    assert candidate["evidence_span_ids"] == ["span-1"]
    # Authored text preserved byte-exact in the candidate proposition (or a
    # direct quote of it) -- never rewritten by the heuristic.
    assert "survive termination" in candidate["proposition"]


def test_returns_no_candidates_for_a_span_with_no_recognizable_pattern():
    from app.enrich.suggester import suggest_assertions_from_spans

    spans = [{"id": "span-2", "quote_text": "The sky is blue today."}]
    candidates = suggest_assertions_from_spans(spans)
    assert candidates == []


def test_is_deterministic_across_repeated_calls():
    from app.enrich.suggester import suggest_assertions_from_spans

    spans = [
        {
            "id": "span-3",
            "quote_text": "This obligation shall survive termination of this Agreement.",
        }
    ]
    first = suggest_assertions_from_spans(spans)
    second = suggest_assertions_from_spans(spans)
    assert first == second


# --- What a long span proposes (audit finding pipeline:11) -------------------
# An ingested statute section is one span; suggesting all of it gave drafts
# of tens of thousands of characters. A span up to MAX_PROPOSITION_LENGTH is
# still suggested whole and byte-exact; from a longer one the candidate
# quotes the sentence that matched, or its clause, verbatim.


def _only_candidate(quote_text: str) -> dict:
    from app.enrich.suggester import suggest_assertions_from_spans

    (candidate,) = suggest_assertions_from_spans([{"id": "span", "quote_text": quote_text}])
    return candidate


def test_a_short_span_is_suggested_whole_and_byte_exact():
    from app.enrich.suggester import MAX_PROPOSITION_LENGTH

    quote = "  Sec. 4. The parties agree. This clause applies to all affiliates.  "
    padded = quote + " " * (MAX_PROPOSITION_LENGTH - len(quote))

    assert _only_candidate(quote)["proposition"] == quote
    assert _only_candidate(padded)["proposition"] == padded


def test_a_long_span_proposes_the_sentence_that_matched():
    filler = "The definitions in this chapter govern its construction. " * 30
    quote = filler + "Sec. 5 applies to every franchisee in the U.S. as of 2026. " + filler

    candidate = _only_candidate(quote)

    assert candidate["assertion_type"] == "APPLIES_TO"
    assert candidate["proposition"] == "Sec. 5 applies to every franchisee in the U.S. as of 2026."
    assert candidate["evidence_span_ids"] == ["span"]


def test_a_long_sentence_is_narrowed_to_its_clause():
    items = "; ".join(f"({i}) a loan of type {i} described in this division" for i in range(40))
    quote = ("(C) No limitation based on capital applies to loans of the following types: " + items + ". "
             + "Other text follows here. " * 10)

    proposition = _only_candidate(quote)["proposition"]

    assert proposition == "(C) No limitation based on capital applies to loans of the following types:"


def test_a_match_that_cannot_be_quoted_within_the_limit_is_not_suggested():
    from app.enrich.suggester import MAX_PROPOSITION_LENGTH, suggest_assertions_from_spans

    unbroken = "word " * (MAX_PROPOSITION_LENGTH // 5) + "applies to " + "word " * (MAX_PROPOSITION_LENGTH // 5)

    assert len(unbroken) > MAX_PROPOSITION_LENGTH
    assert suggest_assertions_from_spans([{"id": "span", "quote_text": unbroken}]) == []
