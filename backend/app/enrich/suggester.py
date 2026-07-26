"""Offline heuristic suggester (Track B, item B2).

`suggest_assertions_from_spans` is a pure, offline, deterministic
function: no network calls, no randomness, no DB access -- given the same
spans it always returns the same candidates (`test_is_deterministic_
across_repeated_calls`). Authored span text is never rewritten: a matched
span's `quote_text` becomes the candidate `proposition` byte-exact, since
`app/enrich/pipeline.py::run_enrichment` is responsible for the
raw/sanitized split (mirroring `routers/assertions.py`), not this module.

`HeuristicEnricher` (item B3) is the real, built-in `Enricher`
(`app/enrich/base.py`) that wraps this pure function -- the default
`run_enrichment` uses when no `enricher=` is injected (ruling R4).
"""

from __future__ import annotations

import re
from typing import Any

# Ordered (pattern, assertion_type) pairs -- first match wins, so this
# order is itself part of the deterministic contract. Each pattern is a
# small, explainable keyword/phrase regex drawn from the controlled
# vocabulary in `app.services.validation.ALLOWED_ASSERTION_TYPES`. This is
# intentionally a rule set, not a model: R4 keeps anything probabilistic
# behind the optional, off-by-default pluggable `Enricher` interface,
# never in this built-in offline enricher.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"survives?\s+termination", re.IGNORECASE), "SURVIVES_TERMINATION"),
    (re.compile(r"creates?\s+an?\s+exception\s+to", re.IGNORECASE), "CREATES_EXCEPTION_TO"),
    (re.compile(r"conflicts?\s+with", re.IGNORECASE), "CONFLICTS_WITH"),
    (re.compile(r"\bmodifies\b|\bamends\b", re.IGNORECASE), "MODIFIES"),
    (re.compile(r"applies\s+to", re.IGNORECASE), "APPLIES_TO"),
    (re.compile(r"distinguishable\s+from", re.IGNORECASE), "DISTINGUISHABLE_FROM"),
    (re.compile(r"\bweakens\b", re.IGNORECASE), "WEAKENS"),
]


def suggest_assertions_from_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return candidate assertion proposals for `spans`.

    Each span is a `{"id": ..., "quote_text": ...}` mapping. A span whose
    `quote_text` matches none of the recognizable patterns above
    contributes no candidates at all -- this is a precision-first
    heuristic (`test_returns_no_candidates_for_a_span_with_no_recognizable_
    pattern`), not an attempt to classify every span.
    """
    candidates: list[dict[str, Any]] = []
    for span in spans:
        quote_text = span.get("quote_text") or ""
        for pattern, assertion_type in _PATTERNS:
            if pattern.search(quote_text):
                candidates.append(
                    {
                        "assertion_type": assertion_type,
                        # Verbatim: the heuristic recognizes authored text,
                        # it never rewrites it.
                        "proposition": quote_text,
                        "evidence_span_ids": [span["id"]],
                    }
                )
                break
    return candidates


class HeuristicEnricher:
    """The real, built-in, fully offline `Enricher` (ruling R4).

    Wraps `suggest_assertions_from_spans` to satisfy the `Enricher`
    protocol declared in `app/enrich/base.py`.
    """

    def suggest(self, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return suggest_assertions_from_spans(spans)
