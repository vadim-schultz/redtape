"""The result types of validation: a validator's signature and the finding a failed check produces."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

Check = Callable[[str, str], str | None]
"""A validator: ``(source, translated)`` to a description of the problem, or ``None`` when the text is fine."""


@dataclass(frozen=True, slots=True)
class Finding:
    """A broken promise: the ``check`` that found it, the ``field`` it was found in and a ``detail``.

    An ``advisory`` finding is recorded and counted, but the unit it belongs to still passes.
    """

    check: str
    field: Literal["title", "description", "text"]
    detail: str
    advisory: bool = False


def blocks(findings: Iterable[Finding]) -> bool:
    """Return whether any of ``findings`` fails its unit: every finding that is not advisory."""
    return any(not finding.advisory for finding in findings)
