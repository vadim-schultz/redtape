"""Response schema for casting a vote; the tally-bearing `SuggestionRead` is chapter 4's job."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class VoteRead(BaseModel):
    """`PUT /api/v1/suggestions/{id}/vote` response body."""

    model_config = ConfigDict(from_attributes=False)

    ok: Literal[True] = True
    value: int
