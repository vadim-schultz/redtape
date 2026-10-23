"""Shared stub for the machine run-lifecycle routes."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import httpx

RUN_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def run_response(request: httpx.Request, finishes: list[dict[str, object]] | None = None) -> httpx.Response | None:
    """Answer start/finish run requests, or return ``None`` for other URLs."""
    url = str(request.url)
    started = datetime.now(UTC).isoformat()
    if url.endswith("/machine/runs"):
        body = {"id": str(RUN_ID), "kind": "worker_drain", "status": "running", "started_at": started}
        return httpx.Response(201, json=body)
    if url.endswith(f"/machine/runs/{RUN_ID}/finish"):
        payload = json.loads(request.content.decode())
        if finishes is not None:
            finishes.append(payload)
        body = {"id": str(RUN_ID), "kind": "worker_drain", "status": payload["status"], "started_at": started}
        return httpx.Response(200, json=body)
    return None
