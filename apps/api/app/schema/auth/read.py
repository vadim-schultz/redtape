"""Pydantic models for the auth API."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserRead(BaseModel):
    """The authenticated user's public profile."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str | None
    role: UserRole
