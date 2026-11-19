"""Decide whether a fetched page earns a render: its body changed, or its last finished render is older than the refresh age."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class RenderHistory:
    """When a page's last render finished; ``None`` when no render of the page has finished yet."""

    last_completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class RenderVerdict:
    """Whether to enqueue a render of a page, and the input key the render carries."""

    due: bool
    input_key: str | None = None


NO_RENDER = RenderVerdict(due=False)


def decide_render(
    *,
    previous_sha256: str | None,
    body_sha256: str,
    history: RenderHistory,
    now: datetime,
    max_age: timedelta,
) -> RenderVerdict:
    """Return the verdict for a fetched body: due when it changed, or when the last render is at least ``max_age`` old."""
    if not (_changed(previous_sha256, body_sha256) or _stale(history, now, max_age)):
        return NO_RENDER
    return RenderVerdict(due=True)


def _changed(previous_sha256: str | None, body_sha256: str) -> bool:
    """Return whether the body differs from the last stored one; a first body always differs."""
    return previous_sha256 != body_sha256


def _stale(history: RenderHistory, now: datetime, max_age: timedelta) -> bool:
    """Return whether no render has finished, or the last one finished at or before ``now - max_age``."""
    return history.last_completed_at is None or history.last_completed_at <= now - max_age
