"""PVOG ``personalMatters`` leaf code to domain-axis hint, for the citizen leaves that are domain-shaped
rather than situation-shaped.

A first pass over the 24 citizen-branch leaves ``situation-tag-activation`` chapter 3's
``PERSONAL_MATTER_TO_SITUATION`` leaves unmapped, recovering a ``domain_codes`` hint for the 14 that cut
across situations the way a domain does — taxes, identity documents, legal/consumer process, disaster
aid, continuing education, and childcare. Spot-checked and approved as-is by a human
(``situation-tag-hierarchy/gaps-and-decisions.md`` P3, 2026-11-02) — this chapter's own Step 0.

The remaining 10 unmapped citizen leaves (civic engagement, hobbies, travel, environment) have no clean
analogue among the 13 existing domains and stay unmapped, same as today.
"""

from __future__ import annotations

PERSONAL_MATTER_TO_DOMAIN: dict[str, list[str]] = {
    "1060100": ["taxes-finance"],
    "1060200": ["taxes-finance"],
    "1060300": ["taxes-finance"],
    "1060800": ["taxes-finance"],
    "1070100": ["identity-civil-status"],
    "1070200": ["identity-civil-status"],
    "1150100": ["law-justice"],
    "1150200": ["law-justice"],
    "1150300": ["law-justice"],
    "1150400": ["law-justice"],
    "1160100": ["social-benefits"],
    "1160200": ["social-benefits"],
    "1040100": ["education"],
    "1020200": ["family-children"],
}

PERSONAL_MATTER_DOMAIN_CLARITY: dict[str, float] = {code: 0.8 for code in PERSONAL_MATTER_TO_DOMAIN}
"""A flat 0.8 for all 14 — lower than the situation axis's reviewed 0.95, reflecting that this table is a
first pass pending Step 0 at the time it was written, not a mapping judgment already signed off like
``PERSONAL_MATTER_CLARITY``'s source table.
"""
