"""The small steps of llm_extract around the model call: read and clean the page, guard API calls, write the notes."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import TypeVar

from discovery_ingest.client import DiscoveryMachineApiError
from discovery_ingest.extract.clean import CleanPage, clean_page
from discovery_ingest.extract.decode import decode_html
from discovery_ingest.extract.llm.ground_state import Grounded
from discovery_ingest.schemas import TextExtractedQuery
from discovery_ingest.worker.browser_steps import Job, Settled, complete, refusal_for
from discovery_ingest.worker.settle import HTTP_NOT_FOUND, fail_permanently

MIN_TEXT_CHARS = 200
"""Cleaned text shorter than this is a shell or an error page: complete as ``no_content`` before spending a neuron."""
UNCHANGED = "unchanged"
"""The note of a page whose cleaned text a completed extraction already read: the model is not called."""
MAX_NOTE = 200
T = TypeVar("T")


def guarded(job: Job, call: Callable[[], T]) -> T:
    """Run a machine call; a refusal that is a limit stops the drain, any other refusal settles the task."""
    try:
        return call()
    except DiscoveryMachineApiError as err:
        raise refusal_for(job, err) from err


def read_page(job: Job, max_chars: int) -> CleanPage:
    """Download the task's snapshot, decode and clean it; settle the task when it is missing or has no text."""
    artifact_id = job.task.artifact_id
    if artifact_id is None:
        raise Settled(fail_permanently(job.client, job.task.id, "llm_extract task has no artifact_id"))
    content = guarded(job, lambda: job.client.artifacts.content(artifact_id))
    cleaned = clean_page(decode_html(content.data, content.content_type), job.task.target_url, max_chars=max_chars)
    if len(cleaned.text.strip()) < MIN_TEXT_CHARS:
        raise Settled(complete(job, "no_content"))
    return cleaned


def cleaned_text_hash(cleaned: CleanPage) -> str:
    """Return the SHA-256 of the cleaned page text; the raw bytes are never hashed, so markup nonces do not count."""
    return hashlib.sha256(cleaned.text.encode()).hexdigest()


def already_extracted(job: Job, text_hash: str) -> bool:
    """Whether a completed extraction of this page under the task's versions already read ``text_hash``.

    A task with no input key carries no versions, so nothing can match it and the model is always called. An API that
    does not serve the check yet (404, during a rollout) also means the model is called: the check only saves neurons.
    """
    input_key = job.task.input_key
    if input_key is None:
        return False
    query = TextExtractedQuery(
        catalogue_service_id=job.task.catalogue_service_id,
        target_url=job.task.target_url,
        input_key=input_key,
        text_hash=text_hash,
    )
    try:
        return job.client.tasks.text_extracted(query)
    except DiscoveryMachineApiError as err:
        return _unanswered_check(job, err)


def _unanswered_check(job: Job, err: DiscoveryMachineApiError) -> bool:
    """Read a refused check as "not extracted" when the route is missing, else settle the task as the refusal says."""
    if err.status_code == HTTP_NOT_FOUND:
        return False
    raise refusal_for(job, err) from err


def require_documents(job: Job, grounded: Grounded, text_hash: str) -> None:
    """Complete the task as ``login_wall`` or ``no_documents`` when grounding left nothing to post."""
    if grounded.documents:
        return
    note = "login_wall" if grounded.diagnostics.page_kind == "login_or_error" else "no_documents"
    raise Settled(complete(job, note, text_hash=text_hash))


def counts_note(grounded: Grounded, mentions: int, edges: int, unknown_codes: int) -> str:
    """Return ``docs=7 edges=5 dropped=2`` (plus ``unknown_codes=n`` when any), at most 200 characters."""
    dropped = sum(grounded.diagnostics.dropped.values())
    parts = [f"docs={mentions}", f"edges={edges}", f"dropped={dropped}"]
    unknown = unknown_codes + grounded.diagnostics.unknown_codes
    return " ".join(parts + ([f"unknown_codes={unknown}"] if unknown else []))[:MAX_NOTE]
