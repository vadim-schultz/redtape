"""The /snapshot request shape: existing fields untouched, plus the consent-tiering additions (chapter 1)."""

from __future__ import annotations

from discovery_ingest.browser.payloads import GOTO_OPTIONS, VIEWPORT, snapshot_body

URL = "https://portal.example/service/1"
USER_AGENT = "RedtapeBot/1.0 (+https://example.test/bot)"


def test_snapshot_body_includes_the_consent_hide_stylesheet() -> None:
    """snapshot_body · addStyleTag carries the OneTrust and a generic cookie-banner selector."""
    body = snapshot_body(URL, USER_AGENT, ["content", "screenshot"])

    style_tags = body["addStyleTag"]
    assert isinstance(style_tags, list) and len(style_tags) == 1
    css = style_tags[0]["content"]
    assert "#onetrust-banner-sdk" in css
    assert '[class*="cookie-banner" i]' in css


def test_snapshot_body_includes_the_accept_click_script() -> None:
    """snapshot_body · addScriptTag carries a known CMP accept-button id and a generic text-match fallback."""
    body = snapshot_body(URL, USER_AGENT, ["content", "screenshot"])

    script_tags = body["addScriptTag"]
    assert isinstance(script_tags, list) and len(script_tags) == 1
    script = script_tags[0]["content"]
    assert "onetrust-accept-btn-handler" in script
    assert "accept" in script.lower() and "agree" in script.lower()


def test_snapshot_body_keeps_the_existing_fields_unchanged() -> None:
    """snapshot_body · url, gotoOptions, userAgent, viewport, screenshotOptions and formats are untouched."""
    body = snapshot_body(URL, USER_AGENT, ["content", "screenshot"])

    assert body["url"] == URL
    assert body["gotoOptions"] == GOTO_OPTIONS
    assert body["userAgent"] == USER_AGENT
    assert body["viewport"] == VIEWPORT
    assert body["screenshotOptions"] == {"fullPage": True, "type": "jpeg", "quality": 80}
    assert body["formats"] == ["content", "screenshot"]


def test_snapshot_body_without_screenshot_format_adds_no_consent_fields() -> None:
    """snapshot_body · a content-only request is unchanged; consent tiering is for the screenshot path only."""
    body = snapshot_body(URL, USER_AGENT, ["content"])

    assert "addStyleTag" not in body and "addScriptTag" not in body
    assert body == {"url": URL, "gotoOptions": GOTO_OPTIONS, "userAgent": USER_AGENT, "formats": ["content"]}


def test_a_script_error_inside_the_page_does_not_fail_the_request() -> None:
    """addScriptTag · the injected script is wrapped in try/catch so a page-side throw cannot surface as an error."""
    body = snapshot_body(URL, USER_AGENT, ["content", "screenshot"])

    script = body["addScriptTag"][0]["content"]
    assert "try" in script and "catch" in script


def test_snapshot_body_without_consent_click_keeps_the_stylesheet_and_sends_no_accept_script() -> None:
    """snapshot_body · consent_click off (the fused render): tier 1 CSS stays, the tier-2 accept script is absent."""
    body = snapshot_body(URL, USER_AGENT, ["content", "screenshot"], consent_click=False)

    assert "addStyleTag" in body and "addScriptTag" not in body
