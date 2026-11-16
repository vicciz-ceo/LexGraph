"""Normalize `users.email` and make it unique, ignoring letter case.

Before 2026-11-16 emails were stored as typed (POST /users stripped
surrounding spaces, bootstrap stored them verbatim) and duplicates were
checked by exact comparison with no database constraint, so
`Ada@Firm.example` and `ada@firm.example` could become two accounts, and
two concurrent creations could even store the same address twice
(findings api:24, ui:25). The app now normalizes emails (stripped,
lowercased) on write and lookup, and the unique index `ix_users_email`
backs its duplicate check.

`upgrade(engine)`:

- rewrites every stored email that is not normalized, unless another
  account's email normalizes to the same address;
- reports each group of accounts whose emails are equal once normalized
  (case variants, or exact duplicates left by the old race) as a WARNING
  on this module's logger, naming every account id and stored email, and
  changes none of them: which account keeps the address is an operator's
  decision (docs/RUNBOOK.md, "Upgrading: case-insensitive emails");
- creates the unique index once no such group remains.

Until the duplicates are resolved the app keeps working: lookups match
every account of a group and answer 409 rather than guess.

Idempotent, per the migration convention (`MIGRATION_ID` + `upgrade`):

- fresh `Base.metadata.create_all()` database: the model already declares
  the index -> nothing to do, returns False;
- older database: normalizes, then creates the index -> True;
- older database with shared addresses: normalizes the others (True if
  any changed), reports the groups, leaves the index for a later run;
  re-running reports them again and returns False until they are
  resolved, then creates the index (True);
- already-migrated database: False.

No row is deleted or merged.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

MIGRATION_ID = "20261116_users_email_unique"

_INDEX = "ix_users_email"

logger = logging.getLogger(__name__)


def normalize_email(email: str) -> str:
    """Frozen copy of `app.routers.users.normalize_email` (a test pins
    that they agree), so this migration keeps meaning what it meant."""
    return email.strip().lower()


def upgrade(engine: Engine) -> bool:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        # Nothing to upgrade: create_all() builds the current schema.
        return False
    if any(index["name"] == _INDEX for index in inspector.get_indexes("users")):
        return False

    changed = False
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, email FROM users")).all()
        groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for user_id, email in rows:
            groups[normalize_email(email)].append((user_id, email))

        for address, accounts in groups.items():
            if len(accounts) == 1 and accounts[0][1] != address:
                conn.execute(
                    text("UPDATE users SET email = :email WHERE id = :id"),
                    {"email": address, "id": accounts[0][0]},
                )
                changed = True

        shared = {address: accounts for address, accounts in groups.items() if len(accounts) > 1}
        if not shared:
            conn.execute(text(f"CREATE UNIQUE INDEX {_INDEX} ON users (email)"))
            return True

    details = "; ".join(
        f"{address}: " + ", ".join(f"{user_id} ({email!r})" for user_id, email in sorted(accounts))
        for address, accounts in sorted(shared.items())
    )
    logger.warning(
        "%d email address(es) are shared by more than one user account once letter case "
        "and surrounding spaces are ignored. Those accounts were left unchanged and the "
        "unique email index was not created yet. Give each account its own address, then "
        "run this migration again (docs/RUNBOOK.md, 'Upgrading: case-insensitive emails'). "
        "Shared: %s",
        len(shared),
        details,
    )
    return changed
