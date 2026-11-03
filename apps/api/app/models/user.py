"""ORM model for application users and their roles."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Uuid, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserRole(enum.StrEnum):
    """Access level granted to an app_user row."""

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


ROLE_RANK: dict[UserRole, int] = {UserRole.USER: 0, UserRole.MODERATOR: 1, UserRole.ADMIN: 2}


class AppUser(Base):
    """A Supabase-authenticated identity, keyed by its Supabase `sub`."""

    __tablename__ = "app_user"
    __table_args__ = (Index("uq_app_user_email_lower", text("lower(email)"), unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            name="user_role",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=UserRole.USER,
        server_default=text("'user'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
