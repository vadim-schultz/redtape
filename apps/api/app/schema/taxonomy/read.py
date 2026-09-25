"""Pydantic models for the taxonomy API (read-only)."""

from __future__ import annotations

from pydantic import BaseModel


class TermRead(BaseModel):
    """A locale-resolved domain or life situation."""

    code: str
    name: str
    description: str
    icon: str | None
