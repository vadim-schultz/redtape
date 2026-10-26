"""Postgres-backed discovery staging enums."""

from __future__ import annotations

import enum


def enum_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    """Return member values for SQLAlchemy native enums."""

    return [member.value for member in enum_cls]


class DiscoverySource(enum.StrEnum):
    """Which government or manual feed produced a catalogue row."""

    GOVDATA = "govdata"
    PVOG = "pvog"
    FIM = "fim"
    LEIKA = "leika"
    MANUAL = "manual"


class DiscoveryTaskStatus(enum.StrEnum):
    """Lifecycle of a queued fetch or enrich task."""

    PENDING = "pending"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscoveryTaskKind(enum.StrEnum):
    """What kind of work a discovery task performs."""

    FETCH_URL = "fetch_url"
    ENRICH_METADATA = "enrich_metadata"
    HARVEST_PAYLOAD = "harvest_payload"
    EXTRACT_PAGE = "extract_page"
    CAPTURE_SCREENSHOT = "capture_screenshot"
    RENDER_PAGE = "render_page"


LEGACY_TASK_KINDS: tuple[DiscoveryTaskKind, ...] = (
    DiscoveryTaskKind.FETCH_URL,
    DiscoveryTaskKind.ENRICH_METADATA,
)
"""Kinds every worker handles; the default when a claim names no ``kinds``."""


class DiscoveryClaimKind(enum.StrEnum):
    """Staging claim shape before emit to suggestions."""

    NEW_DOCUMENT = "new_document"
    NEW_REQUIREMENT = "new_requirement"
    METADATA = "metadata"


class DiscoveryEventType(enum.StrEnum):
    """Append-only lineage event labels."""

    CATALOGUE_UPSERTED = "catalogue_upserted"
    TASK_ENQUEUED = "task_enqueued"
    TASK_CLAIMED = "task_claimed"
    FETCH_LOGGED = "fetch_logged"
    CLAIM_RECORDED = "claim_recorded"
    EMIT_ATTEMPTED = "emit_attempted"
    TASK_RELEASED = "task_released"


class DiscoveryRunKind(enum.StrEnum):
    """Which operational job a run record describes."""

    WORKER_DRAIN = "worker_drain"


class DiscoveryRunStatus(enum.StrEnum):
    """Lifecycle of an operational run."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DiscoveryCandidateStatus(enum.StrEnum):
    """Lifecycle of a document candidate."""

    STAGED = "staged"
    EMITTED = "emitted"


class DiscoveryMentionRole(enum.StrEnum):
    """How a procedure relates to a mentioned document."""

    REQUIRED = "required"
    FORM = "form"


class DiscoveryArtifactKind(enum.StrEnum):
    """What an object-store artifact holds."""

    HTML_SNAPSHOT = "html_snapshot"
    SCREENSHOT = "screenshot"
