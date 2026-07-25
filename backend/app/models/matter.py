"""Matter ORM model (sprint 2026-07-25-collaborative-assertions, item F1).

`matters(id, repository_id, name)` per the sprint log's Data model
reference. Schema only — no business logic.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Matter(Base):
    __tablename__ = "matters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
