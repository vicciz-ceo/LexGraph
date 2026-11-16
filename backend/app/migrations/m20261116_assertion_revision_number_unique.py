"""Unique `(assertion_id, revision_number)` on `assertion_revisions`
(audit finding api:0).

Two concurrent edits based on the same revision used to store two rows with
one revision number; every later read of that assertion -- and the whole
matter list, review queue and knowledge base -- then failed with
`MultipleResultsFound`. The model declares the unique index now (fresh
databases get it from `Base.metadata.create_all()`); this migration adds it
to existing databases.

Duplicate numbers already stored are renumbered first, never deleted, in a
deterministic order:

* rows of an affected assertion are ordered by `(revision_number,
  created_at, id)`, except that inside the group holding the assertion's
  current number, the row whose content matches the assertion's current
  fields (the edit that committed last; on a tie, the newest) goes last;
* a row keeps its number unless that would repeat or go below the previous
  row's, in which case it takes the previous number + 1;
* the assertion's `current_revision_number` follows its current row.

Rows keep their ids, so ratings (`assertion_revision_id`) and audit events
stay attached to the revision they were recorded against. Every move is
logged as a warning. Raw SQL against a plain `Engine`, independent of the
current ORM models (same convention as `add_raw_text_columns`).
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine

MIGRATION_ID = "20261116_assertion_revision_number_unique"
INDEX_NAME = "uq_assertion_revisions_assertion_id_revision_number"
_COLUMNS = ("assertion_id", "revision_number")
_CONTENT = (
    "proposition", "assertion_type", "subject_entity_type", "subject_entity_id",
    "object_entity_type", "object_entity_id", "jurisdiction", "effective_from", "effective_to",
)

logger = logging.getLogger(__name__)


def _has_unique_revision_numbers(engine: Engine) -> bool:
    inspector = inspect(engine)
    for index in inspector.get_indexes("assertion_revisions"):
        if index.get("unique") and tuple(index["column_names"]) == _COLUMNS:
            return True
    return any(
        tuple(constraint["column_names"]) == _COLUMNS
        for constraint in inspector.get_unique_constraints("assertion_revisions")
    )


def _sort_key(value) -> str:
    return "" if value is None else str(value)


def _current_row_id(revisions, assertion) -> str | None:
    if assertion is None:
        return None
    group = [r for r in revisions if r["revision_number"] == assertion["current_revision_number"]]
    matching = [r for r in group if all(r[field] == assertion[field] for field in _CONTENT)]
    pool = matching or group
    if not pool:
        return None
    return max(pool, key=lambda r: (_sort_key(r["created_at"]), r["id"]))["id"]


def renumber_duplicate_revisions(conn: Connection) -> list[tuple[str, str, int, int]]:
    """Give every revision of an assertion a distinct number (see module
    docstring). Returns `(assertion_id, revision_id, old, new)` per moved row."""
    affected = conn.execute(text(
        "SELECT DISTINCT assertion_id FROM assertion_revisions "
        "GROUP BY assertion_id, revision_number HAVING COUNT(*) > 1"
    )).scalars().all()
    columns = ", ".join(_CONTENT)
    moved: list[tuple[str, str, int, int]] = []
    for assertion_id in sorted(affected):
        revisions = conn.execute(text(
            f"SELECT id, revision_number, created_at, {columns} FROM assertion_revisions "
            "WHERE assertion_id = :assertion_id"
        ), {"assertion_id": assertion_id}).mappings().all()
        assertion = conn.execute(text(
            f"SELECT current_revision_number, {columns} FROM assertions WHERE id = :assertion_id"
        ), {"assertion_id": assertion_id}).mappings().first()
        current_id = _current_row_id(revisions, assertion)
        ordered = sorted(revisions, key=lambda r: (
            r["revision_number"], r["id"] == current_id, _sort_key(r["created_at"]), r["id"],
        ))
        previous = 0
        new_current = None
        for row in ordered:
            number = max(row["revision_number"], previous + 1)
            if number != row["revision_number"]:
                conn.execute(text("UPDATE assertion_revisions SET revision_number = :number WHERE id = :id"),
                             {"number": number, "id": row["id"]})
                moved.append((assertion_id, row["id"], row["revision_number"], number))
            if row["id"] == current_id:
                new_current = number
            previous = number
        if new_current is not None and new_current != assertion["current_revision_number"]:
            conn.execute(text("UPDATE assertions SET current_revision_number = :number WHERE id = :id"),
                         {"number": new_current, "id": assertion_id})
    return moved


def upgrade(engine: Engine) -> bool:
    """Renumber duplicates and create the unique index. True if it changed anything."""
    if not inspect(engine).has_table("assertion_revisions") or _has_unique_revision_numbers(engine):
        return False
    with engine.begin() as conn:
        moved = renumber_duplicate_revisions(conn)
        conn.execute(text(
            f"CREATE UNIQUE INDEX {INDEX_NAME} ON assertion_revisions (assertion_id, revision_number)"
        ))
    for assertion_id, revision_id, old, new in moved:
        logger.warning("assertion %s: revision row %s renumbered %d -> %d (duplicate revision number)",
                       assertion_id, revision_id, old, new)
    return True
