"""Dependency that exposes the validated list query to a handler."""

from __future__ import annotations

from litestar import Request
from litestar.di import Provide

from app.shared.list_query.model import ListQuery, ListQuerySpec
from app.shared.list_query.parse import parse_list_query


def provide_list_query(spec: ListQuerySpec) -> Provide:
    """Return a dependency that validates the request's query string against ``spec``."""

    def provide(request: Request) -> ListQuery:
        return parse_list_query(request.query_params, spec)

    return Provide(provide, sync_to_thread=False)
