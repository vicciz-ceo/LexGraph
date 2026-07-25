"""Repository ORM model (sprint 2026-07-25-collaborative-assertions, item F1).

`repositories(id, organization_id, name)` per the sprint log's Data model
reference. Schema only — no business logic.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
