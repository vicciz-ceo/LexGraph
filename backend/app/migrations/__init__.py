"""Hand-rolled reversible schema migrations (no Alembic — sprint
2026-07-26-local-first-platform, Track A, item A1).

Each migration module in this package exposes `upgrade(engine)` and
`downgrade(engine)` functions operating on a plain SQLAlchemy `Engine`
(raw DDL via `sqlalchemy.text`), so they can be run standalone against a
local SQLite file without any migration-framework dependency, matching
this project's local-first, zero-cloud-dependency posture.
"""

from __future__ import annotations
