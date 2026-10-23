"""Size-capped reading of a streamed HTTP response."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from discovery_ingest.worker.outcome import FetchAbort, FetchFailure


@dataclass(frozen=True, slots=True)
class Reply:
    """Status, headers and capped body of one HTTP response."""

    status_code: int
    headers: httpx.Headers
    body: bytes


def read_reply(response: httpx.Response, *, max_bytes: int) -> Reply:
    """Read ``response`` until it ends or passes ``max_bytes``; abort and drop the body when it does."""
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > max_bytes:
            raise FetchAbort(
                f"response exceeds {max_bytes} bytes", FetchFailure.TOO_LARGE, http_status=response.status_code
            )
        chunks.append(chunk)
    return Reply(response.status_code, response.headers, b"".join(chunks))
