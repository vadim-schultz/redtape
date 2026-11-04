"""Refuse an llm_extract drain before it claims anything: credentials, model, ledger, storage and vocabulary must be ready."""

from __future__ import annotations

from contextlib import ExitStack

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.config import IngestSettings
from discovery_ingest.extract.llm.meter import RESOURCE
from discovery_ingest.extract.llm.prices import known_models
from discovery_ingest.extract.llm.taxonomy import Taxonomy
from discovery_ingest.operations.models import build_model_client
from discovery_ingest.worker.llm_enqueue import LlmEnqueuer
from discovery_ingest.worker.llm_runtime import LlmResources
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.storage_guard import storage_problem

EXIT_MISSING_SETTINGS = 2
EXIT_NOT_READY = 1


class LlmSetupError(Exception):
    """The drain must not start; ``exit_code`` is the command's exit status and the message says why."""

    def __init__(self, message: str, exit_code: int) -> None:
        """Keep the process ``exit_code`` beside the message."""
        super().__init__(message)
        self.exit_code = exit_code


def _check_settings(settings: IngestSettings) -> str:
    """Return the model id, or raise when a Workers AI variable, the model or its price is missing."""
    missing = settings.missing_ai_credentials()
    if missing:
        raise LlmSetupError(
            f"llm_extract needs these environment variables: {', '.join(missing)}", EXIT_MISSING_SETTINGS
        )
    if not settings.llm_model:
        raise LlmSetupError(
            "llm_extract needs the environment variable LLM_MODEL (a Workers AI model id)", EXIT_MISSING_SETTINGS
        )
    if settings.llm_model not in known_models():
        raise LlmSetupError(
            f"LLM_MODEL {settings.llm_model} has no neuron price; known: {', '.join(known_models())}",
            EXIT_MISSING_SETTINGS,
        )
    return settings.llm_model


def _check_ledger(client: DiscoveryIngestClient) -> None:
    if BudgetGuard(client.budget).remaining(RESOURCE).ledger_unavailable:
        raise LlmSetupError(
            "cannot read the neuron budget ledger (GET /machine/budgets); llm_extract will not spend without it",
            EXIT_NOT_READY,
        )


def _check_storage(client: DiscoveryIngestClient) -> None:
    problem = storage_problem(client, "an extraction has no snapshots to read")
    if problem is not None:
        raise LlmSetupError(problem, EXIT_NOT_READY)


def _taxonomy(client: DiscoveryIngestClient) -> Taxonomy:
    try:
        return client.candidates.taxonomy()
    except DiscoveryMachineApiError as err:
        raise LlmSetupError(f"cannot read the taxonomy (GET /machine/taxonomy): {err}", EXIT_NOT_READY) from err


def prepare_llm(settings: IngestSettings, client: DiscoveryIngestClient, stack: ExitStack) -> LlmResources:
    """Return the model resources, or raise :class:`LlmSetupError` when ``llm_extract`` cannot be drained.

    The model's HTTP client is entered into ``stack``, so its owner closes it on every exit path.
    """
    model = _check_settings(settings)
    _check_ledger(client)
    _check_storage(client)
    taxonomy = _taxonomy(client)
    model_client = build_model_client(settings, model, stack)
    return LlmResources(model_client, taxonomy, model, settings.llm_max_tokens, settings.llm_input_chars)


def prepare_llm_enqueue(
    settings: IngestSettings, client: DiscoveryIngestClient, policy: DrainPolicy
) -> LlmEnqueuer | None:
    """Return the ``llm_extract`` enqueue hook, or ``None`` when ``LLM_ENQUEUE`` is off or no page is rendered.

    Raise :class:`LlmSetupError` when the switch is on for a render drain and ``LLM_MODEL`` is not set, because the
    task key is derived from the model.
    """
    if not settings.llm_enqueue or "render_page" not in policy.kinds:
        return None
    if not settings.llm_model:
        raise LlmSetupError(
            "LLM_ENQUEUE needs the environment variable LLM_MODEL (it keys the task)", EXIT_MISSING_SETTINGS
        )
    return LlmEnqueuer(client, settings.llm_model)
