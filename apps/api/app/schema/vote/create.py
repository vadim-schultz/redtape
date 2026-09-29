"""Request schema for casting a vote."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class VoteCreate(BaseModel):
    """`PUT /api/v1/suggestions/{id}/vote` body."""

    model_config = ConfigDict(extra="forbid")

    value: Literal[1, -1]
