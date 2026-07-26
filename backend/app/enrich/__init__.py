"""Offline enrichment package (sprint 2026-07-26-local-first-platform,
Track B).

Suggests draft assertions from documents/spans already stored in the local
DB -- document acquisition/scraping is out of scope this sprint (ruling
R7). Everything in this package is fully offline (ruling R4; enforced by
`backend/tests/unit/test_no_network_dependencies.py`): no `httpx`,
`requests`, `urllib.request`, `aiohttp`, or `socket` imports anywhere in
this package, now or later.

- `base.py` -- the pluggable `Enricher` protocol (item B3).
- `suggester.py` -- the pure heuristic function and the real, built-in
  `HeuristicEnricher` (item B2).
- `pipeline.py` -- `run_enrichment(...)`, which writes real
  `Assertion`/`AssertionRevision`/`AssertionEvidence` rows (item B2).
- `cli.py` -- `python -m app.enrich.cli --matter-id <id>` (item B1).
"""

from __future__ import annotations
