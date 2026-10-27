"""Read the browser time a response reports in ``X-Browser-Ms-Used``."""

from __future__ import annotations

import math


def parse_ms_used(raw: str | None) -> int | None:
    """Return the header as whole milliseconds (fractions round up), or ``None`` when absent or unreadable."""
    try:
        value = float(raw) if raw is not None else math.nan
    except ValueError:
        return None
    return math.ceil(value) if math.isfinite(value) and value >= 0 else None
