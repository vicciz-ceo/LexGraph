"""User ORM model (sprint 2026-07-25-collaborative-assertions, item F1).

`users(id, email, display_name)` per the sprint log's Data model
reference. Schema only — no business logic (auth/permissions are B3/B4
service work against `app.auth`/`app.services.permissions`).
"""

from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
