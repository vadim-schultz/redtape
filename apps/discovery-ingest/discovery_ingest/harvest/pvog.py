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
from discovery_ingest.pvog.situation_mapping import PERSONAL_MATTER_TO_SITUATION

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


def _situation_codes(raw_payload: dict[str, object]) -> list[str] | None:
    """Return the mapped situation codes for the stashed Lebenslage code, or ``None`` if unmapped.

    Reads ``raw_payload["_personal_matter_code"]`` (stashed by
    :func:`discovery_ingest.pvog.client.map_pvog_record`) through
    :data:`PERSONAL_MATTER_TO_SITUATION` — the table's full list for a mapped (clean or ambiguous)
    code, unchanged for a bundled leaf.
    """
    code = raw_payload.get("_personal_matter_code")
    if not isinstance(code, str):
        return None
    return PERSONAL_MATTER_TO_SITUATION.get(code)


def _draft(
    module: Module,
    selector: ModuleSelector,
    item: Found,
    locale: str,
    situation_codes: list[str] | None,
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
    )


def _module_drafts(module: Module, locale: str, situation_codes: list[str] | None) -> list[MentionDraft]:
    selector = MODULE_SELECTORS[module.code]
    found = dict.fromkeys(item for item in selector.strategy(module) if not is_noise(item.title))
    return [_draft(module, selector, item, locale, situation_codes) for item in found]


def harvest_pvog_payload(raw_payload: dict[str, object]) -> list[MentionDraft]:
    """Return the document mentions in ``raw_payload.details``, in module and document order."""
    locale = _locale(raw_payload)
    situation_codes = _situation_codes(raw_payload)
    return [
        draft for module in selected_modules(raw_payload) for draft in _module_drafts(module, locale, situation_codes)
    ]
