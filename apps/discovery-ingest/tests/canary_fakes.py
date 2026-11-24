"""Fakes for the fused-render canary: a scripted browser whose renders and fused snapshots are recorded HTML."""

from __future__ import annotations

from discovery_ingest.browser.port import RenderedPage, ScreenshotImage

JPEG = b"\xff\xd8\xff" + b"0" * 8


def page(text: str = "") -> str:
    """Return a recorded-style page whose main region holds one paragraph of ``text``."""
    return f'<html lang="de"><body><main><h1>Leistung</h1><p>{text}</p></main></body></html>'


class FakeCanaryBrowser:
    """Serves each URL's /content renders in order and its fused snapshot DOM; records the consent flag of each fused call."""

    def __init__(self, *, renders: dict[str, list[str]], fused: dict[str, str], ms: int = 2000) -> None:
        self._renders = {url: list(htmls) for url, htmls in renders.items()}
        self._fused = fused
        self._ms = ms
        self.consent_clicks: list[bool] = []

    def render(self, url: str) -> RenderedPage:
        """Return the next scripted DOM of ``url`` at the fake's browser cost."""
        return RenderedPage(self._renders[url].pop(0), self._ms, 200, url)

    def screenshot(self, url: str, *, consent_click: bool = True) -> ScreenshotImage:
        """Return the fused DOM of ``url`` with a small JPEG, and record ``consent_click``."""
        self.consent_clicks.append(consent_click)
        return ScreenshotImage(JPEG, "image/jpeg", self._ms, self._fused[url], 200, url)
