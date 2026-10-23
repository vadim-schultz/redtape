"""Per-host robots.txt rules, fetched once per process."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from discovery_ingest.config import BOT_PRODUCT_TOKEN
from discovery_ingest.worker.outcome import FetchOutcome

RobotsFetch = Callable[[str], FetchOutcome]


class RobotsUnavailableError(Exception):
    """A host's robots.txt could not be read, so its pages must be skipped this run."""


def _origin(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}"


def _unavailable(outcome: FetchOutcome) -> bool:
    status = outcome.http_status
    return outcome.error_message is not None or status is None or not (200 <= status < 500)


def _parse(outcome: FetchOutcome) -> RobotFileParser:
    """Build rules from a robots.txt outcome; a client error means everything is allowed."""
    if _unavailable(outcome):
        raise RobotsUnavailableError(f"robots.txt unavailable ({outcome.error_message or outcome.http_status})")
    lines = (outcome.body or b"").decode("utf-8", errors="replace").splitlines()
    rules = RobotFileParser()
    rules.parse(lines if outcome.body is not None else [])
    return rules


class RobotsCache:
    """Answer ``allowed(url)`` from robots.txt rules cached per origin."""

    def __init__(self, fetch: RobotsFetch, *, agent: str = BOT_PRODUCT_TOKEN) -> None:
        self._fetch = fetch
        self._agent = agent
        self._rules: dict[str, RobotFileParser | RobotsUnavailableError] = {}

    def allowed(self, url: str) -> bool:
        """Return whether ``url`` may be fetched; raise when the host's robots.txt is unavailable."""
        rules = self._rules_for(_origin(url))
        if isinstance(rules, RobotsUnavailableError):
            raise RobotsUnavailableError(*rules.args)
        return rules.can_fetch(self._agent, url)

    def _rules_for(self, origin: str) -> RobotFileParser | RobotsUnavailableError:
        if origin not in self._rules:
            self._rules[origin] = self._load(origin)
        return self._rules[origin]

    def _load(self, origin: str) -> RobotFileParser | RobotsUnavailableError:
        try:
            return _parse(self._fetch(f"{origin}/robots.txt"))
        except RobotsUnavailableError as err:
            return err
