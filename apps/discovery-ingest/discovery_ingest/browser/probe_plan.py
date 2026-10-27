"""Which Cloudflare calls the probe makes: every variant once per page, the contract call for error urls."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

from discovery_ingest.browser.endpoints import Endpoint
from discovery_ingest.browser.payloads import Body, content_body, screenshot_body, snapshot_body

INLINE_TARGET = "(inline html)"
ECHO_HTML = "<html><body><script>document.body.textContent = navigator.userAgent</script></body></html>"
BodyBuilder = Callable[[str, str], Body]


@dataclass(frozen=True, slots=True)
class ProbeCall:
    """One request: its variant name, endpoint, target url and body; ``expect`` is text the result must echo."""

    variant: str
    endpoint: Endpoint
    target: str
    body: Body
    expect: str | None = None


_PAGE_VARIANTS: dict[str, tuple[Endpoint, BodyBuilder]] = {
    "content": ("content", lambda url, ua: content_body(url, ua)),
    "content-lean": ("content", lambda url, ua: content_body(url, ua, lean=True)),
    "snapshot-md": ("snapshot", lambda url, ua: snapshot_body(url, ua, ["content", "markdown"])),
    "screenshot-jpeg": ("screenshot", lambda url, ua: screenshot_body(url, ua, "jpeg")),
    "screenshot-png": ("screenshot", lambda url, ua: screenshot_body(url, ua, "png")),
    "snapshot-shot": ("snapshot", lambda url, ua: snapshot_body(url, ua, ["content", "screenshot"])),
}
VARIANTS: tuple[str, ...] = ("ua-echo", *_PAGE_VARIANTS)


def _echo_call(user_agent: str) -> ProbeCall:
    body: Body = {"html": ECHO_HTML, "userAgent": user_agent}
    return ProbeCall("ua-echo", "content", INLINE_TARGET, body, expect=user_agent)


def _page_call(variant: str, url: str, user_agent: str) -> ProbeCall:
    endpoint, build = _PAGE_VARIANTS[variant]
    return ProbeCall(variant, endpoint, url, build(url, user_agent))


def _targets(variant: str, pages: Sequence[str], errors: Sequence[str]) -> Sequence[str]:
    return (*pages, *errors) if variant == "content" else pages


def _calls(
    variants: Sequence[str], pages: Sequence[str], errors: Sequence[str], user_agent: str
) -> Iterator[ProbeCall]:
    for variant in variants:
        if variant == "ua-echo":
            yield _echo_call(user_agent)
            continue
        for url in _targets(variant, pages, errors):
            yield _page_call(variant, url, user_agent)


def probe_plan(
    pages: Sequence[str], errors: Sequence[str], *, user_agent: str, variants: Sequence[str] | None
) -> list[ProbeCall]:
    """Return the calls in a fixed order: the cheap userAgent echo first, then each variant over the pages."""
    unknown = [name for name in variants or () if name not in VARIANTS]
    if unknown:
        raise ValueError(f"unknown variant {', '.join(unknown)}; expected {', '.join(VARIANTS)}")
    chosen = [name for name in VARIANTS if variants is None or name in variants]
    return list(_calls(chosen, pages, errors, user_agent))
