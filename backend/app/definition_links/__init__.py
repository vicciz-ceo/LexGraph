"""Deterministic definition-linking package (sprint 2026-07-29-definition-links).

Connects articles within a law via the definitions the law contains, and
connects laws to each other when a definition is derived from another law
(director mandate). Wholly deterministic: stdlib + existing repo
dependencies only -- no LLM/ML/network calls anywhere in this package (a
regression test enforces this: `tests/unit/test_definition_links_no_network_
dependencies.py`).

Stages (see `docs/sprint/sprints/2026-07-29-definition-links-review.md`'s
"Deterministic definition-linking design" for the full algorithm spec):

- Stage 0 (`normalize.py`): text normalization + wikilink stripping.
- Stage 1 (`sections.py`): locate articles and definitions sections.
- Stage 2 (`extract.py`): extract (term, definition) pairs.
- Stage 3 (`matcher.py`): build the article -> definition link index.
- Stage 4 (`derivation.py`): detect cross-law derivation.
- Stage 5 (`guards.py`): false-positive guards + bidi-degraded-text guard.
- Ingestion (`ingest.py`): article-aware wiki-format ingestion (ruling M4).
- Orchestration (`pipeline.py`): persistence pipeline (rulings M2/M5/M7).
- Surface (`cli.py`): `python -m app.definition_links.cli` (ruling M6).
"""

from __future__ import annotations
