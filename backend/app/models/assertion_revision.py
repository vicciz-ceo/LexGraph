"""AssertionRevision ORM model (sprint 2026-07-25-collaborative-assertions,
item F1).

Exact field list per spec §3 (ASSERTION REVISION HISTORY). Nullability
mirrors Assertion: `object_entity_type`/`object_entity_id` may be null for
standalone propositions; `jurisdiction`/`effective_from`/`effective_to`
are optional; `revision_reason` is an optional free-text reason for the
edit. Schema only — no business logic (revision creation is B1 work).

`(assertion_id, revision_number)` is unique (audit finding api:0): two
concurrent edits based on the same revision used to store two rows with
the same number, after which every read of that assertion -- and the whole
matter list -- failed with `MultipleResultsFound`. Existing databases get
the index from `app.migrations.m20261116_assertion_revision_number_unique`.
Importing this module also registers the "every assertion has a revision
row for its current number" session hook (`app.models.assertion_invariants`).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.db_types import UtcDateTime

#: Shared with the migration that adds the index to existing databases.
REVISION_NUMBER_UNIQUE_INDEX = "uq_assertion_revisions_assertion_id_revision_number"


class AssertionRevision(Base):
    __tablename__ = "assertion_revisions"
    __table_args__ = (
        Index(REVISION_NUMBER_UNIQUE_INDEX, "assertion_id", "revision_number", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assertion_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assertions.id"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    proposition: Mapped[str] = mapped_column(Text, nullable=False)
    # Track A, item A1 (issue #2, gate G1): the author's exact submitted
    # bytes, stored alongside the (possibly lossy, browser-faithful)
    # sanitized `proposition` column above. Nullable at the schema level
    # only to accommodate rows backfilled by the standalone migration in
    # `app.migrations.add_raw_text_columns`; every write path in this app
    # populates it unconditionally (see routers/assertions.py).
    proposition_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    assertion_type: Mapped[str] = mapped_column(String(255), nullable=False)

    subject_entity_type: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    object_entity_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    object_entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    jurisdiction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    revision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Review authoring:5: the exact reason an editor submitted; `revision_reason`
    # holds its sanitized text (as `proposition_raw` / `proposition`). Null for
    # reasons the system writes ("initial creation") and for revisions saved
    # before migration 20261116_revision_reason_raw.
    revision_reason_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)


# Registered here, next to the model whose rows it guarantees, so that any
# process able to write assertions has it: importing any `app.models.*`
# module runs `app/models/__init__.py`, which imports this one.
from app.models import assertion_invariants as _assertion_invariants  # noqa: E402,F401
