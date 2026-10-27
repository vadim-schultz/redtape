"""Request bodies for the quick actions, shared by the client and the probe so the probe tests what the worker sends."""

from __future__ import annotations

from pydantic import JsonValue

Body = dict[str, JsonValue]
GOTO_OPTIONS: dict[str, JsonValue] = {"waitUntil": "networkidle2", "timeout": 30000}
LEAN_RESOURCE_TYPES: list[JsonValue] = ["image", "font", "media"]
VIEWPORT: dict[str, JsonValue] = {"width": 1280, "height": 800}
JPEG_QUALITY = 80


def content_body(url: str, user_agent: str, *, lean: bool = False) -> Body:
    """Return the ``/content`` body; ``lean`` also rejects images, fonts and media."""
    body: Body = {"url": url, "gotoOptions": GOTO_OPTIONS, "userAgent": user_agent}
    if lean:
        body["rejectResourceTypes"] = LEAN_RESOURCE_TYPES
    return body


def snapshot_body(url: str, user_agent: str, formats: list[JsonValue]) -> Body:
    """Return the ``/snapshot`` body for ``formats``; a screenshot is a full-page JPEG."""
    body: Body = {"url": url, "gotoOptions": GOTO_OPTIONS, "userAgent": user_agent, "formats": formats}
    if "screenshot" in formats:
        body.update(viewport=VIEWPORT, screenshotOptions=_screenshot_options("jpeg"))
    return body


def screenshot_body(url: str, user_agent: str, image_type: str) -> Body:
    """Return the ``/screenshot`` body: full page at the worker viewport, JPEG at quality 80 or PNG."""
    return {
        "url": url,
        "gotoOptions": GOTO_OPTIONS,
        "userAgent": user_agent,
        "viewport": VIEWPORT,
        "screenshotOptions": _screenshot_options(image_type),
    }


def _screenshot_options(image_type: str) -> dict[str, JsonValue]:
    options: dict[str, JsonValue] = {"fullPage": True, "type": image_type}
    if image_type == "jpeg":
        options["quality"] = JPEG_QUALITY
    return options
