"""How a run gets the machine crosswalk: fetched once on first use, and handed to a validation as its context."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from pydantic import ValidationInfo

from discovery_ingest.pvog.category_mapping import MachineCrosswalk


class CrosswalkLookup(Protocol):
    """Gives the machine crosswalk when a validation first needs it: a crosswalk that is held, or one fetched on demand."""

    def get(self) -> MachineCrosswalk:
        """Return the crosswalk, fetching it if it is not yet held."""
        ...


LegacyContext = ValidationInfo[CrosswalkLookup | None]
"""The validation context of a payload that carries legacy fields: the lookup that translates them, or none."""


def crosswalk_from(info: LegacyContext) -> MachineCrosswalk:
    """Return the crosswalk a validation was given as context; legacy fields cannot be translated without it."""
    if info.context is None:
        raise ValueError("legacy domain or situation fields need the machine crosswalk as validation context")
    return info.context.get()


class FetchedCrosswalk:
    """A crosswalk fetched on first use and kept for the rest of its run, so a run fetches it at most once."""

    def __init__(self, fetch: Callable[[], MachineCrosswalk]) -> None:
        """Keep the fetch; nothing is fetched until a validation or a harvest task asks for the crosswalk."""
        self._fetch = fetch
        self._held: MachineCrosswalk | None = None

    def get(self) -> MachineCrosswalk:
        """Return the held crosswalk, fetching it on the first call; a failed fetch raises and is not kept."""
        if self._held is None:
            self._held = self._fetch()
        return self._held
