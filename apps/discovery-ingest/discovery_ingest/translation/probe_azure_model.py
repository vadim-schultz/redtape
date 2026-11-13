"""The Azure probe's report model: the JSON shape of one run, per locale and in total. The builder is in probe_azure_report."""

from __future__ import annotations

from pydantic import BaseModel

from discovery_ingest.translation.glossary import GlossaryMode


class RequestRow(BaseModel):
    """One answered request: the characters sent and the characters reported (null when the header was absent)."""

    sent: int
    metered: float | None


class LocaleRow(BaseModel):
    """What the probe learned about one target locale; ``measured`` is false when the probe ended before reaching it."""

    locale: str
    measured: bool
    units: int
    valid_units: int
    valid_share: float
    glossary_findings: int
    placeholder_failures: int
    token_units: int
    token_valid: int
    plural_units: int
    plural_valid: int
    billed_characters: float
    estimated_characters: int
    unmetered_requests: int
    requests: list[RequestRow]


class MarkupRow(BaseModel):
    """The HTML-tagged request: its characters with the tags, its visible characters, what was reported and the answer."""

    sent: int
    visible: int
    metered: float | None
    tags_billed: bool | None


class ThrottleRow(BaseModel):
    """The repeated calls: how many were answered, how many came back as 429, and each answer."""

    attempts: int
    answered: int
    throttled: int
    answers: list[str]


class AzureProbeReport(BaseModel):
    """The whole run: totals, the per-locale rows, the markup and throttle answers and the recommended glossary mode."""

    engine: str = "azure-translator"
    api_version: str
    units: int
    max_characters: float
    locales: list[LocaleRow]
    markup: MarkupRow | None
    throttle: ThrottleRow | None
    billed_characters: float
    estimated_characters: int
    recommended_glossary_mode: GlossaryMode
    stopped: str | None
