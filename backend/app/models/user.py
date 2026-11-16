"""User ORM model (sprint 2026-07-25-collaborative-assertions, item F1).

`users(id, email, display_name, sign_in_token_hash)`. Schema only — no
business logic (auth/permissions are B3/B4 service work against
`app.auth`/`app.services.permissions`).

`id` is a public reference (rosters, author/reviewer ids). The sign-in
credential is a separate secret token; only its sha256 hex digest is
stored, in `sign_in_token_hash` (unique, indexed; NULL = no credential).
See `app.auth` and the `m20261116_sign_in_tokens` migration, which adds
this column to databases created before it existed.

`email` is stored normalized (stripped, lowercased; see
`app.routers.users.normalize_email`) and is unique (index
`ix_users_email`), so uniqueness is case-insensitive. The
`m20261116_users_email_unique` migration normalizes older databases and
adds the index once no two accounts share an address.
"""

from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sign_in_token_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
