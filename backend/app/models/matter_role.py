"""MatterRole ORM model (sprint 2026-07-25-collaborative-assertions, item F1).

`matter_roles(id, user_id, matter_id, role)` per the sprint log's Data
model reference — role in viewer/contributor/reviewer/admin;
unique(user_id, matter_id). Schema only — permission evaluation is B4's
`app.services.permissions` work.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

VALID_ROLES = ("viewer", "contributor", "reviewer", "admin")


class MatterRole(Base):
    __tablename__ = "matter_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "matter_id", name="uq_matter_roles_user_matter"),
        CheckConstraint(
            "role IN ('viewer', 'contributor', 'reviewer', 'admin')",
            name="ck_matter_roles_role_valid",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    matter_id: Mapped[str] = mapped_column(String(36), ForeignKey("matters.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
