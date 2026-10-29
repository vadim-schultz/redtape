"""Compose the after_snapshot actions of a render drain."""

from __future__ import annotations

from discovery_ingest.artifacts import ArtifactRead
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.render import AfterSnapshot


def chain(*hooks: AfterSnapshot | None) -> AfterSnapshot:
    """Return one hook that runs each given hook in order; ``None`` entries are skipped."""
    active = [hook for hook in hooks if hook is not None]

    def run(task: ClaimedTask, artifact: ArtifactRead) -> None:
        for hook in active:
            hook(task, artifact)

    return run
