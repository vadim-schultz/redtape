"""The result types of validation: a validator's signature and the finding a failed check produces."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

Check = Callable[[str, str], str | None]
"""A validator: ``(source, translated)`` to a description of the problem, or ``None`` when the text is fine."""


@dataclass(frozen=True, slots=True)
class Finding:
    """A broken promise: the ``check`` that found it, the ``field`` it was found in and a ``detail``."""

    check: str
    field: Literal["title", "description", "text"]
    detail: str
