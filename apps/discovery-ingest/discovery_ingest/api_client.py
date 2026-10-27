"""HTTP client for discovery machine routes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

import httpx

from discovery_ingest.artifacts import ArtifactContent, ArtifactRead, ArtifactStatus, ArtifactUpload, StoredArtifact
from discovery_ingest.batch_dedup import dedupe_batch_items
from discovery_ingest.budget_models import BudgetReservation, BudgetResource, BudgetRow, BudgetSnapshot
from discovery_ingest.emit_models import CandidatePage, EmitPreview, EmitRequest, EmitResponse
from discovery_ingest.mentions import MentionItem, MentionsRequest, MentionsResponse
from discovery_ingest.schemas import (
    CatalogueBatchItem,
    CatalogueBatchRequest,
    CatalogueMachineRead,
    ClaimAppendRequest,
    ClaimAppendResponse,
    DiscoveryTaskKind,
    EntityUpsertRequest,
    EntityUpsertResponse,
    FetchLogAppendRequest,
    RunFinishRequest,
    RunStartResponse,
    TaskClaimRequest,
    TaskClaimResponse,
    TaskEnqueueRequest,
    TaskEnqueueResponse,
    TaskSummary,
)

HTTP_INSUFFICIENT_STORAGE = 507
DATABASE_LIMIT_DETAIL = "database_soft_limit"
HTTP_CONFLICT = 409
HTTP_CREATED = 201


class DiscoveryMachineApiError(Exception):
    """Machine API returned a non-success status."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"discovery machine API {status_code}: {detail}")

    @property
    def is_database_limit(self) -> bool:
        """Whether the API refused a write because the database is above its soft limit (stop, do not fail)."""
        return self.status_code == HTTP_INSUFFICIENT_STORAGE and DATABASE_LIMIT_DETAIL in self.detail


class DiscoveryMachineClient:
    """Post catalogue batch upserts with ``X-API-Key``."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def post_catalogue_batches(self, items: Sequence[CatalogueBatchItem], *, batch_size: int = 50) -> None:
        """Upsert items in chunks of at most ``batch_size``."""
        if batch_size < 1 or batch_size > 50:
            raise ValueError("batch_size must be between 1 and 50")
        deduped = dedupe_batch_items(items)
        chunk: list[CatalogueBatchItem] = []
        for item in deduped:
            chunk.append(item)
            if len(chunk) >= batch_size:
                self._post_batch(chunk)
                chunk = []
        if chunk:
            self._post_batch(chunk)

    def _post_batch(self, items: list[CatalogueBatchItem]) -> None:
        body = CatalogueBatchRequest(items=items)
        url = f"{self._base_url}/api/v1/discovery/machine/catalogue/batch"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(
                url,
                json=body.model_dump(mode="json"),
                headers={"X-API-Key": self._api_key},
            )
        if response.status_code >= 400:
            detail = response.text
            raise DiscoveryMachineApiError(response.status_code, detail)

    def get_catalogue(self, catalogue_id: UUID) -> CatalogueMachineRead:
        """Load minimal catalogue row for enrich workers."""
        url = f"{self._base_url}/api/v1/discovery/machine/catalogue/{catalogue_id}"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.get(url, headers={"X-API-Key": self._api_key})
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return CatalogueMachineRead.model_validate(response.json())

    def post_entity(self, body: EntityUpsertRequest) -> EntityUpsertResponse:
        """Upsert a discovery entity under a catalogue row."""
        url = f"{self._base_url}/api/v1/discovery/machine/entities"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(
                url,
                json=body.model_dump(mode="json"),
                headers={"X-API-Key": self._api_key},
            )
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return EntityUpsertResponse.model_validate(response.json())

    def post_claim(self, body: ClaimAppendRequest) -> ClaimAppendResponse:
        """Append a discovery claim on an entity."""
        url = f"{self._base_url}/api/v1/discovery/machine/claims"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(
                url,
                json=body.model_dump(mode="json"),
                headers={"X-API-Key": self._api_key},
            )
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return ClaimAppendResponse.model_validate(response.json())

    def post_mentions(self, items: Sequence[MentionItem]) -> MentionsResponse:
        """Record up to 100 document mentions in one transaction."""
        body = MentionsRequest(items=list(items))
        url = f"{self._base_url}/api/v1/discovery/machine/candidates/mentions"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(url, json=body.model_dump(mode="json"), headers={"X-API-Key": self._api_key})
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return MentionsResponse.model_validate(response.json())

    def list_staged_candidates(self, *, min_mentions: int, limit: int) -> CandidatePage:
        """Return up to ``limit`` staged candidates with at least ``min_mentions`` mentions, most mentioned first."""
        url = f"{self._base_url}/api/v1/discovery/machine/candidates/"
        params: dict[str, str | int] = {"status": "staged", "min_mentions": min_mentions, "limit": limit}
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.get(url, params=params, headers={"X-API-Key": self._api_key})
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return CandidatePage.model_validate(response.json())

    def preview_candidate_emit(self, candidate_id: UUID) -> EmitPreview:
        """Return what emitting ``candidate_id`` would create; the route never writes."""
        url = f"{self._base_url}/api/v1/discovery/machine/candidates/{candidate_id}/emit-preview"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.get(url, headers={"X-API-Key": self._api_key})
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return EmitPreview.model_validate(response.json())

    def emit_candidates(self, candidate_ids: Sequence[UUID]) -> EmitResponse:
        """Emit up to 50 candidates as pending suggestions; replays and duplicates are reported, not raised."""
        body = EmitRequest(candidate_ids=list(candidate_ids))
        url = f"{self._base_url}/api/v1/discovery/machine/candidates/emit"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(url, json=body.model_dump(mode="json"), headers={"X-API-Key": self._api_key})
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return EmitResponse.model_validate(response.json())

    def claim_tasks(self, *, limit: int, kinds: Sequence[DiscoveryTaskKind]) -> TaskClaimResponse:
        """Claim pending discovery tasks of ``kinds`` for this API key."""
        body = TaskClaimRequest(limit=limit, kinds=list(kinds))
        url = f"{self._base_url}/api/v1/discovery/machine/tasks/claim"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(
                url,
                json=body.model_dump(mode="json"),
                headers={"X-API-Key": self._api_key},
            )
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return TaskClaimResponse.model_validate(response.json())

    def get_task_summary(self, *, kinds: Sequence[DiscoveryTaskKind]) -> TaskSummary:
        """Return queue counts for ``kinds`` without leasing anything."""
        url = f"{self._base_url}/api/v1/discovery/machine/tasks/summary"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.get(url, params={"kinds": list(kinds)}, headers={"X-API-Key": self._api_key})
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return TaskSummary.model_validate(response.json())

    def enqueue_task(self, body: TaskEnqueueRequest) -> TaskEnqueueResponse:
        """Enqueue a follow-up task; an equivalent existing task is returned instead."""
        url = f"{self._base_url}/api/v1/discovery/machine/tasks"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(
                url,
                json=body.model_dump(mode="json"),
                headers={"X-API-Key": self._api_key},
            )
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return TaskEnqueueResponse.model_validate(response.json())

    def start_run(self) -> UUID:
        """Open a ``worker_drain`` run record and return its id."""
        url = f"{self._base_url}/api/v1/discovery/machine/runs"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(url, json={"kind": "worker_drain"}, headers={"X-API-Key": self._api_key})
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return RunStartResponse.model_validate(response.json()).id

    def finish_run(self, run_id: UUID, body: RunFinishRequest) -> None:
        """Close ``run_id`` with its report."""
        url = f"{self._base_url}/api/v1/discovery/machine/runs/{run_id}/finish"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(url, json=body.model_dump(mode="json"), headers={"X-API-Key": self._api_key})
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)

    def append_fetch(self, task_id: UUID, body: FetchLogAppendRequest) -> None:
        """Append a fetch log row for a claimed task."""
        url = f"{self._base_url}/api/v1/discovery/machine/tasks/{task_id}/fetches"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(
                url,
                json=body.model_dump(mode="json"),
                headers={"X-API-Key": self._api_key},
            )
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)

    def complete_task(self, task_id: UUID, *, note: str | None = None) -> None:
        """Mark a claimed task completed; ``note`` says why nothing was produced (for example ``login_wall``)."""
        body = {"note": note} if note is not None else None
        self._call("POST", f"/tasks/{task_id}/complete", json=body)

    def release_task(self, task_id: UUID, reason: str, *, not_before: datetime | None = None) -> None:
        """Hand a claimed task back to ``pending`` without consuming an attempt (a limit stopped the work)."""
        body = {"reason": reason, **({"not_before": not_before.isoformat()} if not_before else {})}
        self._call("POST", f"/tasks/{task_id}/release", json=body)

    def upload_artifact(self, task_id: UUID, upload: ArtifactUpload) -> StoredArtifact:
        """Store a snapshot or screenshot for a claimed task; 201 created it, 200 matched identical stored bytes."""
        fields = {"kind": upload.kind, "source_url": upload.source_url, "fetched_at": upload.fetched_at.isoformat()}
        if upload.final_url:
            fields["final_url"] = upload.final_url
        files = {"file": (f"{upload.kind}", upload.data, upload.content_type)}
        response = self._call("POST", f"/tasks/{task_id}/artifacts", data=fields, files=files)
        return StoredArtifact(ArtifactRead.model_validate(response.json()), response.status_code == HTTP_CREATED)

    def get_artifact_status(self) -> ArtifactStatus:
        """Report whether storage is configured, with bytes used against the cap."""
        return ArtifactStatus.model_validate(self._call("GET", "/artifacts/status").json())

    def get_artifact_content(self, artifact_id: UUID) -> ArtifactContent:
        """Download the stored bytes of ``artifact_id``; 404 means unknown or missing object, 503 an unset store."""
        response = self._call("GET", f"/artifacts/{artifact_id}/content")
        return ArtifactContent(response.content, response.headers.get("content-type"))

    def fail_task(self, task_id: UUID, *, error: str, retryable: bool = False) -> None:
        """Fail a claimed task with ``error``; the API re-pends it when ``retryable`` and attempts remain."""
        url = f"{self._base_url}/api/v1/discovery/machine/tasks/{task_id}/fail"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.post(
                url,
                json={"error": error, "retryable": retryable},
                headers={"X-API-Key": self._api_key},
            )
        if response.status_code >= 400:
            raise DiscoveryMachineApiError(response.status_code, response.text)

    def get_budgets(self) -> BudgetSnapshot:
        """Return every budget resource in its current period."""
        return BudgetSnapshot.model_validate(self._budget_call("GET", "").json())

    def reserve_budget(self, resource: BudgetResource, amount: float) -> BudgetReservation:
        """Reserve ``amount`` of ``resource``; a denial (409) is an answer, not an error."""
        response = self._budget_call("POST", f"/{resource}/reserve", {"amount": amount}, allow=(HTTP_CONFLICT,))
        return BudgetReservation.model_validate(response.json())

    def adjust_budget(self, resource: BudgetResource, delta: float) -> BudgetRow:
        """Apply a signed correction to ``resource`` once its real cost is known."""
        return BudgetRow.model_validate(self._budget_call("POST", f"/{resource}/adjust", {"delta": delta}).json())

    def exhaust_budget(self, resource: BudgetResource) -> BudgetRow:
        """Mark ``resource`` exhausted for the rest of its period."""
        return BudgetRow.model_validate(self._budget_call("POST", f"/{resource}/exhaust").json())

    def _budget_call(
        self, method: str, suffix: str, body: dict[str, float] | None = None, *, allow: tuple[int, ...] = ()
    ) -> httpx.Response:
        return self._call(method, f"/budgets{suffix}", json=body, allow=allow)

    def _call(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, str | float] | None = None,
        data: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        allow: tuple[int, ...] = (),
    ) -> httpx.Response:
        url = f"{self._base_url}/api/v1/discovery/machine{path}"
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            response = client.request(
                method, url, json=json, data=data, files=files, headers={"X-API-Key": self._api_key}
            )
        if response.status_code >= 400 and response.status_code not in allow:
            raise DiscoveryMachineApiError(response.status_code, response.text)
        return response


def _post_catalogue_batches(
    base_url: str,
    api_key: str,
    items: Sequence[CatalogueBatchItem],
    *,
    batch_size: int = 50,
) -> None:
    """Upsert catalogue items via the discovery machine API."""
    client = DiscoveryMachineClient(base_url, api_key)
    client.post_catalogue_batches(items, batch_size=batch_size)
