"""The Azure probe's data: the plan of a run, what each case measured, and the result the report is built from."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from discovery_ingest.translation.adapters.azure_translator_http import AzureConnection
from discovery_ingest.translation.azure_settings import load_azure_translator_settings
from discovery_ingest.translation.repair import Checked
from discovery_ingest.translation.units import TranslationUnit

ANSWERED: Final = "answered"
"""The answer of a throttle attempt that the service answered; any other answer is the error it returned."""


@dataclass(frozen=True, slots=True)
class Exchange:
    """One request the service answered: the characters sent and the characters it reported (``None``: no header)."""

    sent: int
    metered: float | None


@dataclass(frozen=True, slots=True)
class AzureProbePlan:
    """The plan of one probe run.

    It holds the reviewed units, the locales (at least one), the most characters the run may bill, the connection and
    the pacing of the calls.
    """

    units: tuple[TranslationUnit, ...]
    locales: tuple[str, ...]
    max_characters: float
    connection: AzureConnection
    min_interval_seconds: float


@dataclass(frozen=True, slots=True)
class LocaleRun:
    """The checked units of each locale case, and the requests the locale sent."""

    checked: dict[str, list[Checked]]
    exchanges: tuple[Exchange, ...]


@dataclass(frozen=True, slots=True)
class MarkupRun:
    """One HTML-tagged request: the characters sent with the tags, the visible characters and what was reported."""

    sent: int
    visible: int
    metered: float | None


@dataclass(frozen=True, slots=True)
class ThrottleRun:
    """The repeated calls at the minimum interval, each with its answer: ``ANSWERED`` or the error the service returned."""

    attempts: int
    answers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AzureProbeResult:
    """Everything the cases measured; ``stopped`` says why the probe ended early (else ``None``)."""

    locales: dict[str, LocaleRun]
    markup: MarkupRun | None
    throttle: ThrottleRun | None
    exchanges: tuple[Exchange, ...]
    stopped: str | None


def connection_from_settings() -> AzureConnection:
    """Return the connection the environment names; raise :class:`ValueError` naming any credential variable that is unset."""
    settings = load_azure_translator_settings()
    key, region = settings.credentials()
    return AzureConnection(settings.azure_translator_endpoint, settings.azure_translator_api_version, key, region)
