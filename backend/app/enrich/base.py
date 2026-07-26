"""Pluggable enricher interface (Track B, item B3; ruling R4).

R4: "heuristic/rule-based suggester in core (fully offline); LLM enrichers
behind a pluggable interface, optional and off by default -- preserves the
no-cloud guarantee." `Enricher` is that pluggable interface, and the ONE
declared boundary seam in this sprint's live-path testing policy: the
built-in `HeuristicEnricher` (`app/enrich/suggester.py`) is real and fully
offline, but a future off-by-default LLM-backed enricher -- or a test
double satisfying this same shape -- can be swapped into
`app/enrich/pipeline.py::run_enrichment` via its `enricher=` parameter
without touching the pipeline itself.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Enricher(Protocol):
    """Anything with a `suggest(spans) -> candidates` method.

    `spans`: a list of `{"id": str, "quote_text": str}` mappings (the
    shape `app/enrich/pipeline.py` builds from real `SourceSpan` rows).

    Returns: a list of candidate mappings, each shaped at least
    `{"assertion_type": str, "proposition": str, "evidence_span_ids": list[str]}`
    -- the shape `suggest_assertions_from_spans` in `app/enrich/suggester.py`
    produces, and that `run_enrichment` consumes regardless of which
    `Enricher` produced it.
    """

    def suggest(self, spans: list[dict[str, Any]]) -> list[dict[str, Any]]: ...
