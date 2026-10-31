"""Tiered, best-effort cookie/consent banner handling for the screenshot path only (chapter 1).

Tier 1 (CSS hide) and tier 2 (accept-click script) are fields sent on the existing ``/snapshot``
request; tier 3 (detect-and-flag) reads the DOM the same call already returns. See
``.plans/candidate-view-polish/00-architecture.md`` section 3 and D1-D3 in ``gaps-and-decisions.md``.
"""

from __future__ import annotations

from selectolax.lexbor import LexborHTMLParser, LexborNode

from discovery_ingest.extract.clean_dom import WIDGET_NAME

CONSENT_HIDE_CSS = """
#onetrust-banner-sdk,
#onetrust-consent-sdk,
#CybotCookiebotDialog,
#qc-cmp2-container,
#didomi-host,
.osano-cm-window,
[class*="cookie-banner" i],
[id*="cookie-consent" i],
[aria-label*="cookie" i] {
  display: none !important;
}
"""
"""Tier 1 — a starting CMP list (OneTrust, Cookiebot, Quantcast/Didomi, Osano, D2) plus generic
cookie-banner attribute patterns; always hidden, whether or not tier 2's click fires."""

CONSENT_ACCEPT_SCRIPT = """
(async () => {
  try {
    const ids = [
      "onetrust-accept-btn-handler",
      "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
      "didomi-notice-agree-button",
    ];
    let clicked = false;
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) {
        el.click();
        clicked = true;
        break;
      }
    }
    if (!clicked) {
      const pattern = /accept|agree|allow|consent|akzeptieren|zustimmen|erlauben|einverstanden/i;
      const candidates = Array.from(document.querySelectorAll("button, a"));
      const match = candidates.find((el) => pattern.test(el.textContent || ""));
      if (match) {
        match.click();
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 300));
  } catch (e) {
    // Best effort only: a page-side failure here must never surface as a request error.
  }
})();
"""
"""Tier 2 — a known "accept all" button id for the same CMPs as tier 1, else a generic
English/German text match on buttons and links; a short settle wait follows any click so a
closing animation finishes before the screenshot. Wrapped in try/catch: best effort, never raises."""

_ATTRIBUTE_SELECTOR = "[id], [class]"
_CONSENT_TERMS = ("cookie", "consent")


def has_leftover_consent_widget(html: str) -> bool:
    """Return whether ``html`` still shows a cookie/consent widget after tiers 1-2 (tier 3, D3: log only).

    Narrows ``clean_dom.WIDGET_NAME`` (``cookie|consent|search|breadcrumb``) to just the
    cookie/consent terms, so an unrelated search or breadcrumb node never trips this flag.
    """
    tree = LexborHTMLParser(html)
    return any(_is_consent_widget(node) for node in tree.css(_ATTRIBUTE_SELECTOR))


def _is_consent_widget(node: LexborNode) -> bool:
    name = f"{node.attributes.get('id') or ''} {node.attributes.get('class') or ''}".lower()
    return WIDGET_NAME.search(name) is not None and any(term in name for term in _CONSENT_TERMS)
