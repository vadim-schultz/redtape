"""Offset/limit paging parameters shared by every list endpoint."""

from __future__ import annotations

from dataclasses import dataclass

from litestar.params import Parameter


@dataclass(frozen=True, slots=True)
class PageParams:
    """Validated offset/limit pair from the query string."""

    offset: int
    limit: int


def provide_page_params(
    offset: int = Parameter(query="offset", default=0, ge=0),
    limit: int = Parameter(query="limit", default=20, ge=1, le=100),
) -> PageParams:
    """Build `PageParams`; Litestar rejects out-of-range values with 400."""
    return PageParams(offset=offset, limit=limit)
