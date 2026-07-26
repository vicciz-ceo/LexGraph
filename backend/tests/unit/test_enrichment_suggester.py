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
