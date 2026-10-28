"""Refuse a browser drain before it claims anything: Cloudflare settings and artifact storage must be ready."""

from __future__ import annotations

from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.browser.client import CloudflareBrowserClient
from discovery_ingest.config import BrowserSettings
from discovery_ingest.worker.storage_guard import storage_problem

EXIT_MISSING_SETTINGS = 2
EXIT_STORAGE_NOT_READY = 1


class BrowserSetupError(Exception):
    """The drain must not start; ``exit_code`` is the command's exit status and the message says why."""

    def __init__(self, message: str, exit_code: int) -> None:
        """Keep the process ``exit_code`` beside the message."""
        super().__init__(message)
        self.exit_code = exit_code


def prepare_browser(
    settings: BrowserSettings, user_agent: str, client: DiscoveryMachineClient
) -> CloudflareBrowserClient:
    """Return the Cloudflare client, or raise :class:`BrowserSetupError` when a browser kind cannot be drained."""
    missing = settings.missing_credentials()
    if missing:
        raise BrowserSetupError(
            f"browser kinds need these environment variables: {', '.join(missing)}", EXIT_MISSING_SETTINGS
        )
    problem = storage_problem(client, "a render has nowhere to go")
    if problem is not None:
        raise BrowserSetupError(problem, EXIT_STORAGE_NOT_READY)
    return CloudflareBrowserClient(settings, user_agent=user_agent)
