"""Scheme and address guard: the fetcher only talks to public http(s) hosts."""

from __future__ import annotations

import ipaddress
import socket
from typing import Protocol
from urllib.parse import urlparse

from discovery_ingest.worker.outcome import FetchAbort, FetchFailure

ALLOWED_SCHEMES = frozenset({"http", "https"})


class HostResolver(Protocol):
    """Resolve a host name to the IP addresses a connection could use."""

    def resolve(self, host: str) -> list[str]:
        """Return every address of ``host``; raise ``OSError`` when it does not resolve."""
        ...


class SystemResolver:
    """Resolve hosts through the operating system."""

    def resolve(self, host: str) -> list[str]:
        """Return every address of ``host``; raise ``OSError`` when it does not resolve."""
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        return sorted({str(info[4][0]) for info in infos})


def is_public_address(address: str) -> bool:
    """Return whether ``address`` is a globally routable unicast IP address."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast and not ip.is_reserved


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _addresses_of(host: str, resolver: HostResolver) -> list[str]:
    if _is_ip_literal(host):
        return [host]
    try:
        return resolver.resolve(host)
    except OSError as err:
        raise FetchAbort(f"cannot resolve host {host}: {err}", FetchFailure.CONNECTION) from err


def validate_destination(url: str, resolver: HostResolver) -> None:
    """Abort unless ``url`` is http(s) and every address of its host is public."""
    parts = urlparse(url)
    if parts.scheme not in ALLOWED_SCHEMES:
        raise FetchAbort(f"unsupported scheme {parts.scheme or '(none)'!r}", FetchFailure.BLOCKED)
    host = parts.hostname or ""
    if not all(is_public_address(address) for address in _addresses_of(host, resolver)):
        raise FetchAbort(f"host {host} resolves to a non-public address", FetchFailure.BLOCKED)
