"""Failed discovery tasks name their class on the wire: robots, not_found and transient are named, the rest permanent."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable

import httpx
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.worker.outcome import FetchFailure, FetchOutcome, classified, failure_outcome
from discovery_ingest.worker.settle import fail_from_api_error, fail_from_outcome, fail_permanently, fail_with
from pydantic import SecretStr

API_BASE = "https://redtape.test"
TASK_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _client(status: int = 200) -> tuple[DiscoveryIngestClient, list[dict[str, object]]]:
    """A client whose every answer is ``status``; the JSON body of each request is recorded."""
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(status, json={"id": str(TASK_ID), "status": "failed", "last_error": "x"})

    return DiscoveryIngestClient(
        API_BASE, SecretStr("test-machine-key"), transport=httpx.MockTransport(handler)
    ), bodies


def _status_outcome(status: int) -> FetchOutcome:
    return classified(
        FetchOutcome(http_status=status, content_type=None, byte_length=None, error_message=f"HTTP {status}")
    )


def _sent_class(settle: Callable[[DiscoveryIngestClient], object]) -> object:
    client, bodies = _client()
    settle(client)
    (body,) = bodies
    return body.get("failure_class")


def test_a_robots_block_is_sent_as_robots_and_a_not_found_page_as_not_found() -> None:
    """task failure · happy: a robots.txt disallow names robots, a 404 names not_found, and neither is retried."""
    robots = failure_outcome("robots.txt disallows", FetchFailure.ROBOTS_DISALLOWED)
    assert _sent_class(lambda client: fail_from_outcome(client, TASK_ID, robots)) == "robots"
    assert _sent_class(lambda client: fail_from_outcome(client, TASK_ID, _status_outcome(404))) == "not_found"


def test_a_timeout_or_a_server_error_is_sent_as_transient_and_retried() -> None:
    """task failure · happy: a timeout and a 503 name transient and ask the API to retry."""
    timeout = classified(failure_outcome("timed out", FetchFailure.TIMEOUT))
    client, bodies = _client()
    fail_from_outcome(client, TASK_ID, timeout)
    assert bodies[-1] == {"error": "timed out", "retryable": True, "failure_class": "transient"}

    client, bodies = _client()
    fail_from_api_error(client, TASK_ID, DiscoveryMachineApiError(503, "unavailable"))
    assert bodies[-1] == {"error": "unavailable", "retryable": True, "failure_class": "transient"}


def test_a_blocked_fetch_is_sent_as_permanent_and_never_as_transient() -> None:
    """task failure · negative: a blocked or unsupported fetch is not retried and is never named transient."""
    blocked = classified(failure_outcome("host is not public", FetchFailure.BLOCKED))
    assert _sent_class(lambda client: fail_from_outcome(client, TASK_ID, blocked)) == "permanent"
    assert _sent_class(lambda client: fail_permanently(client, TASK_ID, "no artifact")) == "permanent"


def test_a_client_error_from_the_api_is_permanent() -> None:
    """task failure · negative: a 4xx refusal of a task is permanent, so the API does not requeue it as transient."""
    client, bodies = _client()
    fail_from_api_error(client, TASK_ID, DiscoveryMachineApiError(422, "bad input"))
    assert bodies[-1]["failure_class"] == "permanent"
    assert bodies[-1]["retryable"] is False


def test_a_retryable_settle_names_transient_for_the_requeue() -> None:
    """task failure · happy: a retryable settle that names no outcome class is sent as transient."""
    client, bodies = _client()
    fail_with(client, TASK_ID, "boom", retryable=True)
    assert bodies[-1]["failure_class"] == "transient"


def test_a_fail_without_a_class_keeps_the_old_body_shape() -> None:
    """task failure · negative: a caller that names no class sends no failure_class key, so the API stores none."""
    client, bodies = _client()
    client.tasks.fail(TASK_ID, error="boom")
    assert bodies[-1] == {"error": "boom", "retryable": False}


def test_a_completion_sends_the_text_hash_only_when_it_has_one() -> None:
    """task completion · happy: the cleaned-text hash rides with the completion; without one the body is unchanged."""
    text_hash = "ab" * 32
    client, bodies = _client()
    client.tasks.complete(TASK_ID, note="docs=2 edges=1 dropped=0", text_hash=text_hash)
    assert bodies[-1] == {"note": "docs=2 edges=1 dropped=0", "text_hash": text_hash}

    client, bodies = _client()
    client.tasks.complete(TASK_ID, note="login_wall")
    assert bodies[-1] == {"note": "login_wall"}
