"""Backfill revision 1 of assertions stored without one (audit findings
api:1, pipeline:2, pipeline:3, ui:4).

Until `app.models.assertion_invariants` enforced "every assertion has a
revision row for its current number", the definition-links pass stored
accepted `system_generated` assertions with `current_revision_number = 1`
and no revision row or audit event, so rating them 404s and the first edit
loses the generated text. Re-running the pass does not repair existing rows
(its idempotency key skips them), so this migration does, once:

* every assertion whose current number is 1 and that has no revision 1 gets
  revision 1 built from its own fields. Such an assertion was never edited
  (an edit always writes revision 2), so these ARE its original fields;
  `proposition_raw` takes the stored proposition, the best raw value left.
* if that assertion has no `assertion_created` audit event, one is added:
  dated at the assertion's creation, by its author, naming the new revision,
  with `new_value` NULL (the status at creation was not recorded) and
  `correlation_id` "migration:<MIGRATION_ID>" so it reads as reconstructed.

Rows whose current number is above 1 but whose current revision is missing
cannot be reconstructed and are only counted in a warning. Definition-link
rows edited before this fix have revision 2 but no revision 1; their
original text is gone and they are left as they are. Raw SQL against a
plain `Engine`, independent of the current ORM models.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

MIGRATION_ID = "20261116_backfill_initial_assertion_revisions"
CORRELATION_ID = f"migration:{MIGRATION_ID}"

_MIRRORED = (
    "proposition", "assertion_type", "subject_entity_type", "subject_entity_id",
    "object_entity_type", "object_entity_id", "jurisdiction", "effective_from", "effective_to",
)
_MISSING_CURRENT = (
    "NOT EXISTS (SELECT 1 FROM assertion_revisions r WHERE r.assertion_id = a.id "
    "AND r.revision_number = a.current_revision_number)"
)

logger = logging.getLogger(__name__)


def _reason(origin: str | None) -> str:
    return f"initial creation ({(origin or 'unknown').replace('_', '-')}, backfilled)"


def upgrade(engine: Engine) -> bool:
    """Insert the missing revision 1 rows. True if it changed anything."""
    inspector = inspect(engine)
    if not (inspector.has_table("assertions") and inspector.has_table("assertion_revisions")):
        return False
    revision_columns = {column["name"] for column in inspector.get_columns("assertion_revisions")}
    has_raw = "proposition_raw" in revision_columns
    audited = inspector.has_table("audit_events")

    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT a.id, a.repository_id, a.matter_id, a.author_user_id, a.created_at, a.origin, "
            + ", ".join(f"a.{column}" for column in _MIRRORED)
            + f" FROM assertions a WHERE a.current_revision_number = 1 AND {_MISSING_CURRENT}"
            + " ORDER BY a.created_at, a.id"
        )).mappings().all()
        unrecoverable = conn.execute(text(
            f"SELECT COUNT(*) FROM assertions a WHERE a.current_revision_number <> 1 AND {_MISSING_CURRENT}"
        )).scalar_one()

        insert_columns = ["id", "assertion_id", "revision_number", *_MIRRORED,
                          *(["proposition_raw"] if has_raw else []),
                          "revision_reason", "edited_by_user_id", "created_at"]
        insert_revision = text(
            f"INSERT INTO assertion_revisions ({', '.join(insert_columns)}) "
            f"VALUES ({', '.join(':' + column for column in insert_columns)})"
        )
        insert_event = text(
            "INSERT INTO audit_events (id, actor_user_id, event_type, timestamp, repository_id, "
            "matter_id, assertion_id, assertion_revision_id, previous_value, new_value, correlation_id) "
            "SELECT :id, :actor, 'assertion_created', :timestamp, :repository_id, :matter_id, "
            ":assertion_id, :revision_id, NULL, NULL, :correlation_id WHERE NOT EXISTS ("
            "SELECT 1 FROM audit_events e WHERE e.assertion_id = :assertion_id "
            "AND e.event_type = 'assertion_created')"
        )
        for row in rows:
            revision_id = str(uuid.uuid4())
            values = {column: row[column] for column in _MIRRORED}
            values.update(id=revision_id, assertion_id=row["id"], revision_number=1,
                          revision_reason=_reason(row["origin"]),
                          edited_by_user_id=row["author_user_id"], created_at=row["created_at"])
            if has_raw:
                values["proposition_raw"] = row["proposition"]
            conn.execute(insert_revision, values)
            if audited:
                conn.execute(insert_event, {
                    "id": str(uuid.uuid4()), "actor": row["author_user_id"],
                    "timestamp": row["created_at"], "repository_id": row["repository_id"],
                    "matter_id": row["matter_id"], "assertion_id": row["id"],
                    "revision_id": revision_id, "correlation_id": CORRELATION_ID,
                })

    if rows:
        logger.warning("backfilled revision 1 for %d assertion(s) stored without one", len(rows))
    if unrecoverable:
        logger.warning("%d assertion(s) have no row for their current revision number above 1; "
                       "left unchanged (their history cannot be reconstructed)", unrecoverable)
    return bool(rows)
