"""Harvest document mentions from the xZufi modules stored in a PVOG catalogue payload.

Rules (bump ``EXTRACTOR_VERSION`` and the API's ``PVOG_HARVESTER_VERSION`` on any change):

* only filled modules named in ``MODULE_SELECTORS`` count;
* text modules yield their list items, or line-separated paragraphs when they have none; a nested
  list yields its leaf items only, because the parent item merely labels its children;
* form modules yield one item per link: the link title, with the link URI as ``official_url``;
* every fragment passes the single noise predicate in :mod:`discovery_ingest.harvest.noise`.
"""

from __future__ import annotations

from discovery_ingest.harvest.modules import MODULE_SELECTORS, Found, Module, ModuleSelector, selected_modules
from discovery_ingest.harvest.noise import is_noise
from discovery_ingest.harvest.text import plain_text
from discovery_ingest.mentions import MentionDraft
from discovery_ingest.pvog.domain_mapping import PERSONAL_MATTER_DOMAIN_CLARITY, PERSONAL_MATTER_TO_DOMAIN
from discovery_ingest.pvog.situation_mapping import PERSONAL_MATTER_CLARITY, PERSONAL_MATTER_TO_SITUATION

EXTRACTOR = "pvog-payload"
EXTRACTOR_VERSION = "1"
DEFAULT_LOCALE = "de"
MAX_EXCERPT = 500
EXCERPT_LEAD = 100


def _locale(raw_payload: dict[str, object]) -> str:
    code = raw_payload.get("languageCode")
    if not isinstance(code, str) or not code.strip():
        return DEFAULT_LOCALE
    return code.strip().replace("_", "-").split("-")[0].lower()


def _excerpt(module: Module, title: str) -> str:
    text = plain_text(module.text or "")
    start = max(0, text.find(title) - EXCERPT_LEAD) if len(text) > MAX_EXCERPT else 0
    return text[start : start + MAX_EXCERPT] or title


def _leaf_code(raw_payload: dict[str, object]) -> str | None:
    """Return the stashed Lebenslage code itself, or ``None`` when the payload has none.

    Reads ``raw_payload["_personal_matter_code"]`` (stashed by
    :func:`discovery_ingest.pvog.client.map_pvog_record`) — exposed under its own name since it is no
    longer only an internal stash feeding :func:`_situation_codes`; it is now a value other code
    (:class:`MentionDraft`'s own ``pvog_leaf_code``) reads directly.
    """
    code = raw_payload.get("_personal_matter_code")
    return code if isinstance(code, str) else None


def _situation_codes(raw_payload: dict[str, object]) -> list[str] | None:
    """Return the mapped situation codes for the stashed Lebenslage code, or ``None`` if unmapped.

    Reads the leaf code through :data:`PERSONAL_MATTER_TO_SITUATION` — the table's full list for a
    mapped (clean or ambiguous) code, unchanged for a bundled leaf.
    """
    code = _leaf_code(raw_payload)
    if code is None:
        return None
    return PERSONAL_MATTER_TO_SITUATION.get(code)


def _situation_confidence(raw_payload: dict[str, object]) -> float | None:
    """Return the leaf's mapping-clarity weight, or ``None`` when it is not situation-mapped."""
    code = _leaf_code(raw_payload)
    if code is None:
        return None
    return PERSONAL_MATTER_CLARITY.get(code)


def _domain_codes(raw_payload: dict[str, object]) -> list[str] | None:
    """Return the recovered domain-axis hint for the stashed leaf code, or ``None`` if unmapped."""
    code = _leaf_code(raw_payload)
    if code is None:
        return None
    return PERSONAL_MATTER_TO_DOMAIN.get(code)


def _domain_confidence(raw_payload: dict[str, object]) -> float | None:
    """Return the leaf's flat domain-hint clarity weight, or ``None`` when it has no domain hint."""
    code = _leaf_code(raw_payload)
    if code is None:
        return None
    return PERSONAL_MATTER_DOMAIN_CLARITY.get(code)


def _draft(
    module: Module,
    selector: ModuleSelector,
    item: Found,
    locale: str,
    *,
    situation_codes: list[str] | None,
    situation_confidence: float | None,
    domain_codes: list[str] | None,
    domain_confidence: float | None,
    leaf_code: str | None,
) -> MentionDraft:
    return MentionDraft(
        title_i18n={locale: item.title},
        role=selector.role,
        excerpt=_excerpt(module, item.title),
        source_field=f"details[code={module.code}]",
        extractor=EXTRACTOR,
        extractor_version=EXTRACTOR_VERSION,
        official_url=item.official_url,
        situation_codes=situation_codes,
        direct_situation_confidence=situation_confidence,
        domain_codes=domain_codes,
        direct_domain_confidence=domain_confidence,
        pvog_leaf_code=leaf_code,
    )


def _module_drafts(
    module: Module,
    locale: str,
    *,
    situation_codes: list[str] | None,
    situation_confidence: float | None,
    domain_codes: list[str] | None,
    domain_confidence: float | None,
    leaf_code: str | None,
) -> list[MentionDraft]:
    selector = MODULE_SELECTORS[module.code]
    found = dict.fromkeys(item for item in selector.strategy(module) if not is_noise(item.title))
    return [
        _draft(
            module,
            selector,
            item,
            locale,
            situation_codes=situation_codes,
            situation_confidence=situation_confidence,
            domain_codes=domain_codes,
            domain_confidence=domain_confidence,
            leaf_code=leaf_code,
        )
        for item in found
    ]


def harvest_pvog_payload(raw_payload: dict[str, object]) -> list[MentionDraft]:
    """Return the document mentions in ``raw_payload.details``, in module and document order."""
    locale = _locale(raw_payload)
    return [
        draft
        for module in selected_modules(raw_payload)
        for draft in _module_drafts(
            module,
            locale,
            situation_codes=_situation_codes(raw_payload),
            situation_confidence=_situation_confidence(raw_payload),
            domain_codes=_domain_codes(raw_payload),
            domain_confidence=_domain_confidence(raw_payload),
            leaf_code=_leaf_code(raw_payload),
        )
    ]
