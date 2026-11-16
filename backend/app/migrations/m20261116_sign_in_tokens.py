"""Add `users.sign_in_token_hash` and keep existing sign-ins working.

Before this migration the bearer token WAS the user id (old ruling R3).
Sign-in now uses a separate secret token whose sha256 hex digest is stored
in a new unique, indexed column (see `app.auth`). To avoid locking anyone
out, every account that exists when the column is added gets
hash = sha256(its user id): the old credential keeps working. That legacy
credential is public (every matter member can see user ids), so it is
flagged at startup and in the admin console and should be rotated
(`python -m app.rotate_sign_in_token`, or Admin -> User accounts).

Idempotent, per the migration convention (`MIGRATION_ID` + `upgrade`):

- fresh `Base.metadata.create_all()` database: column and index already
  exist -> nothing to do, returns False;
- pre-upgrade database: adds the column, backfills legacy hashes, then
  creates the unique index -> True;
- already-migrated database: False.

SQLite commits `ALTER TABLE ... ADD COLUMN` immediately, so the unique
index is created last and doubles as the completion marker: if a previous
run stopped after adding the column, the next run still backfills the
accounts that have no hash. Once the index exists, a NULL hash is left
alone: it means "no sign-in credential", never "use the public id".
No data is deleted.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.auth import hash_sign_in_token

MIGRATION_ID = "20261116_sign_in_tokens"

_COLUMN = "sign_in_token_hash"
_INDEX = "ix_users_sign_in_token_hash"


def upgrade(engine: Engine) -> bool:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        # Nothing to upgrade: create_all() builds the current schema.
        return False

    changed = False
    columns = {column["name"] for column in inspector.get_columns("users")}
    if _COLUMN not in columns:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE users ADD COLUMN {_COLUMN} VARCHAR(64)"))
        changed = True

    indexes = {index["name"] for index in inspect(engine).get_indexes("users")}
    if _INDEX in indexes:
        return changed

    with engine.begin() as conn:
        pending = conn.execute(text(f"SELECT id FROM users WHERE {_COLUMN} IS NULL")).all()
        for (user_id,) in pending:
            conn.execute(
                text(f"UPDATE users SET {_COLUMN} = :token_hash WHERE id = :id"),
                {"token_hash": hash_sign_in_token(user_id), "id": user_id},
            )
        conn.execute(text(f"CREATE UNIQUE INDEX {_INDEX} ON users ({_COLUMN})"))
    return True
