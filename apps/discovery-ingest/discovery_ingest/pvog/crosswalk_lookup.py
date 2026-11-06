"""How a run gets the machine crosswalk: fetched once on first use, and kept for the rest of the run."""

from __future__ import annotations

from collections.abc import Callable

from discovery_ingest.pvog.category_mapping import MachineCrosswalk


class FetchedCrosswalk:
    """A crosswalk fetched on first use and kept for the rest of its run, so a run fetches it at most once."""

    def __init__(self, fetch: Callable[[], MachineCrosswalk]) -> None:
        """Keep the fetch; nothing is fetched until a harvest task asks for the crosswalk."""
        self._fetch = fetch
        self._held: MachineCrosswalk | None = None

    def get(self) -> MachineCrosswalk:
        """Return the held crosswalk, fetching it on the first call; a failed fetch raises and is not kept."""
        if self._held is None:
            self._held = self._fetch()
        return self._held
