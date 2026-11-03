"""Run the Step 0 probe: the same cleaned page through each model, one throttled call at a time."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.extract.clean import CleanPage, clean_page
from discovery_ingest.extract.llm.client import ChatMessage
from discovery_ingest.extract.llm.payloads import chat_body, run_body
from discovery_ingest.extract.llm.probe_calls import ProbeClient, RawCall
from discovery_ingest.extract.llm.probe_cost import cost_row, neurons_of
from discovery_ingest.extract.llm.probe_envelope import chat_envelope_row, envelope_row, usage_row
from discovery_ingest.extract.llm.probe_errors import acceptance_row, quota_row, refusal, violation_row
from discovery_ingest.extract.llm.probe_outcome import cleaner_row, quality_row
from discovery_ingest.extract.llm.probe_report import ProbeReport, ProbeRow
from discovery_ingest.extract.llm.probe_taxonomy import PROBE_TAXONOMY
from discovery_ingest.extract.llm.prompt import build_messages
from discovery_ingest.extract.llm.schema import build_json_schema
from discovery_ingest.extract.llm.schema_prep import prepare_schema
from discovery_ingest.llm_settings import LlmSettings

__all__ = ["ProbeReport", "run_probe"]

PROBE_URL = "https://probe.invalid/page"
VIOLATION_MAX_TOKENS = 16
VIOLATION_MESSAGES: list[ChatMessage] = [{"role": "user", "content": "Extract the documents this page asks for."}]


@dataclass(frozen=True, slots=True)
class ModelCalls:
    """The calls made for one model: native, OpenAI-compatible and the deliberately truncated one (when sent)."""

    native: RawCall
    chat: RawCall | None
    short: RawCall | None

    def all(self) -> list[RawCall]:
        """The calls that were made."""
        return [call for call in (self.native, self.chat, self.short) if call is not None]


def _call_model(model: str, client: ProbeClient, page: CleanPage, settings: LlmSettings) -> ModelCalls:
    messages, schema = build_messages(page, PROBE_TAXONOMY), prepare_schema(build_json_schema(PROBE_TAXONOMY))
    native = client.post("run", run_body(messages, schema, settings.llm_max_tokens), model)
    if refusal(native):
        return ModelCalls(native, None, None)
    chat = client.post("chat", chat_body(model, messages, schema, settings.llm_max_tokens), model)
    short = client.post("run", run_body(VIOLATION_MESSAGES, schema, VIOLATION_MAX_TOKENS), model) if native.ok else None
    return ModelCalls(native, chat, short)


def _rows(model: str, calls: ModelCalls, page: CleanPage) -> list[ProbeRow]:
    return [
        acceptance_row(model, calls.native),
        envelope_row(model, calls.native),
        chat_envelope_row(model, calls.chat),
        usage_row(model, calls.native, calls.chat),
        violation_row(model, calls.short),
        cost_row(model, calls.native),
        quality_row(model, calls.native, page, PROBE_TAXONOMY),
        quota_row(model, calls.all()),
    ]


def _probe_model(model: str, client: ProbeClient, page: CleanPage, settings: LlmSettings, report: ProbeReport) -> None:
    calls = _call_model(model, client, page, settings)
    report.rows += _rows(model, calls, page)
    report.neurons_spent += sum(neurons_of(model, call) for call in calls.all())
    report.stopped = next((why for call in calls.all() if (why := refusal(call))), None)
    report.refused = report.stopped is not None


def run_probe(
    settings: LlmSettings,
    models: Sequence[str],
    html: str,
    *,
    http: httpx.Client,
    throttle: Throttle,
    max_neurons: float,
) -> ProbeReport:
    """Probe each model with the cleaned ``html``; stop at a rejected token, the daily quota or ``max_neurons``."""
    client, report = ProbeClient(settings, http, throttle), ProbeReport()
    page = clean_page(html, PROBE_URL, max_chars=settings.llm_input_chars)
    for model in models:
        if report.neurons_spent >= max_neurons:
            report.stopped = f"neuron cap of {max_neurons:g} reached before {model}"
            break
        _probe_model(model, client, page, settings, report)
        if report.refused:
            return report
    report.rows.append(cleaner_row(page, client.markdown(html)))
    return report
