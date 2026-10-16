"""Stable fingerprints for discovery claim deduplication."""

from __future__ import annotations

import hashlib
import json

from app.models.discovery import DiscoveryClaimKind


def claim_payload_fingerprint(kind: DiscoveryClaimKind, payload: dict[str, object]) -> str:
    """Return a stable hash for ``(kind, payload)`` uniqueness."""

    canonical = json.dumps(
        {"kind": kind.value, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
