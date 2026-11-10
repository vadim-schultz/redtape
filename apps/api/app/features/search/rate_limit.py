"""Rate limit of the public search: requests with ``q`` per client address, behind a known number of proxies."""

from __future__ import annotations

from litestar import Request
from litestar.middleware.rate_limit import RateLimitConfig, RateLimitMiddleware
from litestar.types import Receive, Scope, Send

from app.config import settings

UNKNOWN_PEER = "unknown"


def client_address(forwarded_for: str | None, peer: str, hops: int) -> str:
    """Return the client address: the ``X-Forwarded-For`` entry ``hops`` places from the right, else ``peer``.

    Each trusted proxy appends the address it saw, so only the rightmost entries are not client-controlled; a spoofed
    prefix the client sent lies further left. With ``hops`` 0, or without the header, the socket ``peer`` is the client.
    """
    entries = [entry.strip() for entry in (forwarded_for or "").split(",") if entry.strip()]
    if hops == 0 or not entries:
        return peer
    return entries[max(len(entries) - hops, 0)]


def _identifier(request: Request) -> str:
    peer = request.client.host if request.client else UNKNOWN_PEER
    return client_address(request.headers.get("x-forwarded-for"), peer, settings.trusted_proxy_hops)


def _is_search(request: Request) -> bool:
    return "q" in request.query_params


class LiveLimitMiddleware(RateLimitMiddleware):
    """Rate limit that reads the allowance from the settings on every request.

    Litestar builds a handler's middleware stack once per process, from a copy of the config, so a limit read in
    ``__init__`` could never be changed afterwards, not even by a test that builds a second app.
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Refresh the allowance, then limit the request as the parent does."""
        self.max_requests = settings.search_rate_limit_per_minute
        await super().__call__(scope, receive, send)


SEARCH_RATE_LIMIT = RateLimitConfig(
    rate_limit=("minute", settings.search_rate_limit_per_minute),
    identifier_for_request=_identifier,
    check_throttle_handler=_is_search,
    middleware_class=LiveLimitMiddleware,
)
