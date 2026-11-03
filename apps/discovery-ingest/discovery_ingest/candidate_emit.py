"""Select staged candidates and report what emitting them creates; no HTTP details live here."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.emit_models import MAX_EMIT_CANDIDATES, EmitItem, EmitPreview

DEFAULT_EMIT_LIMIT = 10
NOTHING_SELECTED = ["no candidates selected"]


@dataclass(frozen=True, slots=True)
class EmitSelection:
    """Which candidates to emit: the named ids, or the most mentioned staged ones."""

    ids: tuple[UUID, ...]
    min_mentions: int
    limit: int

    def validate(self) -> None:
        """Raise ``ValueError`` for a limit outside 1-50 or more named ids than the limit."""
        if not 1 <= self.limit <= MAX_EMIT_CANDIDATES:
            raise ValueError(f"--limit must be between 1 and {MAX_EMIT_CANDIDATES}")
        if len(self.ids) > self.limit:
            raise ValueError(
                f"{len(self.ids)} ids exceed --limit {self.limit}; raise it to at most {MAX_EMIT_CANDIDATES}"
            )


def select_candidate_ids(client: DiscoveryIngestClient, selection: EmitSelection) -> list[UUID]:
    """Return the named ids, or the staged candidates with enough mentions, most mentioned first."""
    if selection.ids:
        return list(selection.ids)
    page = client.candidates.list_staged(min_mentions=selection.min_mentions, limit=selection.limit)
    return [item.id for item in page.items]


def _preview_line(preview: EmitPreview) -> str:
    if preview.skip_reason is None:
        return f"would create {preview.candidate_id}"
    return f"skipped {preview.candidate_id} {preview.skip_reason}"


def _emit_line(item: EmitItem) -> str:
    if item.skip_reason is not None:
        return f"skipped {item.candidate_id} {item.skip_reason}"
    outcome = "replayed" if item.replayed else "created"
    return f"{outcome} {item.candidate_id} {item.suggestion_id}"


def preview_report(client: DiscoveryIngestClient, selection: EmitSelection) -> list[str]:
    """Preview every selected candidate through the read-only route and describe the result."""
    ids = select_candidate_ids(client, selection)
    if not ids:
        return NOTHING_SELECTED
    previews = [client.candidates.preview_emit(candidate_id) for candidate_id in ids]
    skipped = sum(preview.skip_reason is not None for preview in previews)
    summary = f"dry run: would create {len(previews) - skipped}, skipped {skipped}"
    return [summary, *(_preview_line(preview) for preview in previews)]


def emit_report(client: DiscoveryIngestClient, selection: EmitSelection) -> list[str]:
    """Emit every selected candidate in one call and describe the result."""
    ids = select_candidate_ids(client, selection)
    if not ids:
        return NOTHING_SELECTED
    response = client.candidates.emit(ids)
    counts = f"created {response.created_count}, replayed {response.replayed_count}, skipped {response.skipped_count}"
    return [counts, *(_emit_line(item) for item in response.items)]
