"""In-app notification ORM models (spec §15; audit findings pipeline:9, ui:7).

`notifications` replaces the per-process list that `app.state.
notification_store` used to hold. One row is one notice for one
recipient, so every API worker, a restarted server and the out-of-process
agent CLI/MCP server all read and write the same feed. Read state lives
on the row (`read_at`, NULL = unread).

`payload` is a small JSON object of references and event facts
(`assertion_id`, `matter_id`, status transition, revision number, ...).
It never holds document text, comment bodies or other confidential
content; the readable context (current proposition, matter name, actor
name) is joined in when a feed is read, and only while the recipient is
still a member of the matter (see `app.notifications`).

`notification_preferences` stores a user's explicit choice per event
type. A missing row means the default in `app.notifications.
DEFAULT_PREFERENCES` (every event on, except per-rating notices, which
spec §15 says must be off by default).

Instants use the shared `app.db_types.UtcDateTime`: SQLite has no
timezone-aware storage, so a plain `DateTime(timezone=True)` comes back
naive and would be serialized without an offset (findings api:15 / ui:3).
Its DDL is the one `DateTime(timezone=True)` emits, as the migration's
snapshot expects.

Created on existing databases by migration
`app.migrations.m20261116_durable_notifications`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.db_types import UtcDateTime


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_created", "recipient_user_id", "created_at"),
        Index("ix_notifications_recipient_read", "recipient_user_id", "read_at"),
        Index("ix_notifications_assertion", "assertion_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    matter_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("matters.id"), nullable=True)
    assertion_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assertions.id"), nullable=True
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "event_type", name="uq_notification_preferences_user_event"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
