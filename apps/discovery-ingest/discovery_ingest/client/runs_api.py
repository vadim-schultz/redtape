"""Run lifecycle routes: open a worker-drain run record and close it with its report."""

from __future__ import annotations

from uuid import UUID

from discovery_ingest.client.http_client import MachineHttpClient
from discovery_ingest.schemas import RunFinishRequest, RunStartResponse


class RunsAPI:
    """Open and close run records."""

    def __init__(self, http: MachineHttpClient) -> None:
        """Keep the shared HTTP client."""
        self._http = http

    def start(self) -> UUID:
        """Open a ``worker_drain`` run record and return its id."""
        return self._http.request_model(RunStartResponse, "POST", "/runs", json={"kind": "worker_drain"}).id

    def finish(self, run_id: UUID, body: RunFinishRequest) -> None:
        """Close ``run_id`` with its report."""
        self._http.request("POST", f"/runs/{run_id}/finish", json=body.model_dump(mode="json"))
