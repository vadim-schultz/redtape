"""Run lifecycle routes: open a run record for a drain and close it with its report."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from discovery_ingest.client.http_client import MachineHttpClient
from discovery_ingest.schemas import RunFinishRequest, RunStage, RunStartResponse


class RunsAPI:
    """Open and close run records."""

    def __init__(self, http: MachineHttpClient) -> None:
        """Keep the shared HTTP client."""
        self._http = http

    def start(self, kind: Literal["worker_drain"] = "worker_drain", stage: RunStage = "worker_drain") -> UUID:
        """Open a run record of ``kind`` for ``stage`` and return its id."""
        return self._http.request_model(RunStartResponse, "POST", "/runs", json={"kind": kind, "stage": stage}).id

    def finish(self, run_id: UUID, body: RunFinishRequest) -> None:
        """Close ``run_id`` with its report."""
        self._http.request("POST", f"/runs/{run_id}/finish", json=body.model_dump(mode="json"))
