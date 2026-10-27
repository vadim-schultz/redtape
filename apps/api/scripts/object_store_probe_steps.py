"""Individual probe steps for :mod:`scripts.object_store_probe`: one function per check, each returning detail text."""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from urllib.parse import urlparse

from app.shared.object_store import S3ObjectStore

PAYLOAD = b"<html><body>object store probe</body></html>"
CONTENT_TYPE = "text/html"
DOWNLOAD_NAME = "probe-snapshot.html"


@dataclass(frozen=True)
class HttpReply:
    """Status, headers and body of one plain HTTP GET."""

    status: int
    headers: Mapping[str, str]
    body: bytes


HttpGet = Callable[[str], HttpReply]


@dataclass(frozen=True)
class ProbeRow:
    """Outcome of one probe step."""

    step: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class ProbeContext:
    """What every step needs: the store, the HTTP getter and the unique key."""

    store: S3ObjectStore
    http_get: HttpGet
    prefix: str

    @property
    def key(self) -> str:
        """Return the object key used by every step."""
        return f"{self.prefix}object.html"


class ProbeCheckError(Exception):
    """A step's expectation was not met."""


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise ProbeCheckError(message)


def urllib_get(url: str) -> HttpReply:
    """Fetch ``url`` with the standard library, returning HTTP errors as replies."""
    try:
        with urllib.request.urlopen(url, timeout=15) as response:  # presigned https URL
            return HttpReply(response.status, dict(response.headers), response.read())
    except urllib.error.HTTPError as error:
        return HttpReply(error.code, dict(error.headers), error.read())


def _header(reply: HttpReply, name: str) -> str:
    lowered = {key.lower(): value for key, value in reply.headers.items()}
    return lowered.get(name.lower(), "")


def _check_put(ctx: ProbeContext) -> str:
    ctx.store.put(ctx.key, PAYLOAD, CONTENT_TYPE)
    return f"{len(PAYLOAD)} bytes"


def _check_exists(ctx: ProbeContext) -> str:
    _expect(ctx.store.exists(ctx.key), "HEAD did not find the object")
    return "HEAD found it"


def _check_get(ctx: ProbeContext) -> str:
    _expect(ctx.store.get(ctx.key) == PAYLOAD, "downloaded bytes differ")
    return "bytes round-trip"


def _check_presigned_get(ctx: ProbeContext) -> str:
    url = ctx.store.presigned_get_url(ctx.key)
    reply = ctx.http_get(url)
    _expect(reply.status == 200, f"unauthenticated GET answered {reply.status}")
    _expect(reply.body == PAYLOAD, "presigned GET returned different bytes")
    return f"200 from {urlparse(url).netloc}"


def _check_presigned_download(ctx: ProbeContext) -> str:
    reply = ctx.http_get(ctx.store.presigned_get_url(ctx.key, download_name=DOWNLOAD_NAME))
    disposition = _header(reply, "content-disposition")
    _expect(reply.status == 200, f"unauthenticated GET answered {reply.status}")
    _expect("attachment" in disposition and DOWNLOAD_NAME in disposition, f"Content-Disposition was {disposition!r}")
    return disposition


def _check_delete(ctx: ProbeContext) -> str:
    ctx.store.delete(ctx.key)
    return "deleted"


def _check_exists_after_delete(ctx: ProbeContext) -> str:
    _expect(not ctx.store.exists(ctx.key), "object still exists after delete")
    return "HEAD reports it gone"


def _check_no_leftovers(ctx: ProbeContext) -> str:
    with suppress(Exception):
        ctx.store.delete(ctx.key)
    leftover = ctx.store.count_prefix(ctx.prefix)
    _expect(leftover == 0, f"{leftover} object(s) left under {ctx.prefix}")
    return "0 objects left"


STEPS: tuple[tuple[str, Callable[[ProbeContext], str]], ...] = (
    ("put", _check_put),
    ("exists", _check_exists),
    ("get", _check_get),
    ("presigned_get", _check_presigned_get),
    ("presigned_download", _check_presigned_download),
    ("delete", _check_delete),
    ("exists_after_delete", _check_exists_after_delete),
    ("leftover_objects", _check_no_leftovers),
)


def run_step(name: str, check: Callable[[ProbeContext], str], ctx: ProbeContext) -> ProbeRow:
    """Run one check and turn an exception into a failing row."""
    try:
        return ProbeRow(name, True, check(ctx))
    except Exception as error:
        return ProbeRow(name, False, f"{type(error).__name__}: {error}")
