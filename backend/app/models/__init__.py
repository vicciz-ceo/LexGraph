"""ORM model package (sprint 2026-07-25-collaborative-assertions, item F1).

Registers the 13 SQLAlchemy model classes described in the sprint log's
"Data model reference" against `app.db.Base`. Importing this package (see
`app/main.py::create_app()`) is sufficient to register every mapped
class's table with `Base.metadata` so that `Base.metadata.create_all()`
(called by `tests/conftest.py`'s `app` fixture) creates the real tables
that `seed_*` raw-SQL helpers and future routers/services expect.

No routes or service logic live here — schema only, per item F1's scope.
"""

from __future__ import annotations

from app.models.assertion import Assertion
from app.models.assertion_comment import AssertionComment
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_rating import AssertionRating
from app.models.assertion_revision import AssertionRevision
from app.models.audit_event import AuditEvent
from app.models.document import Document
from app.models.matter import Matter
from app.models.matter_role import MatterRole
from app.models.organization import Organization
from app.models.repository import Repository
from app.models.source_span import SourceSpan
from app.models.user import User

__all__ = [
    "Assertion",
    "AssertionComment",
    "AssertionEvidence",
    "AssertionRating",
    "AssertionRevision",
    "AuditEvent",
    "Document",
    "Matter",
    "MatterRole",
    "Organization",
    "Repository",
    "SourceSpan",
    "User",
]
