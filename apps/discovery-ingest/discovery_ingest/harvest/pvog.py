"""Harvest document mentions from the xZufi modules stored in a PVOG catalogue payload.

Rules (bump ``EXTRACTOR_VERSION`` and the API's ``PVOG_HARVESTER_VERSION`` on any change):

* only filled modules named in ``MODULE_SELECTORS`` count;
* text modules yield their list items, or line-separated paragraphs when they have none; a nested
  list yields its leaf items only, because the parent item merely labels its children;
* form modules yield one item per link: the link title, with the link URI as ``official_url``;
* every fragment passes the single noise predicate in :mod:`discovery_ingest.harvest.noise`.
"""

from __future__ import annotations

from dataclasses import dataclass

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
    :func:`discovery_ingest.pvog.client.map_pvog_record`).
    """
    code = raw_payload.get("_personal_matter_code")
    return code if isinstance(code, str) else None


@dataclass(frozen=True, slots=True)
class LeafHints:
    """The mapping hints one PVOG Lebenslage leaf carries onto every mention drafted from its payload."""

    situation_codes: list[str] | None
    situation_confidence: float | None
    domain_codes: list[str] | None
    domain_confidence: float | None
    leaf_code: str | None

    @classmethod
    def from_payload(cls, raw_payload: dict[str, object]) -> LeafHints:
        """Read the stashed leaf code once and consult the four mapping tables for it; no code means no hints."""
        code = _leaf_code(raw_payload)
        if code is None:
            return cls(None, None, None, None, None)
        return cls(
            situation_codes=PERSONAL_MATTER_TO_SITUATION.get(code),
            situation_confidence=PERSONAL_MATTER_CLARITY.get(code),
            domain_codes=PERSONAL_MATTER_TO_DOMAIN.get(code),
            domain_confidence=PERSONAL_MATTER_DOMAIN_CLARITY.get(code),
            leaf_code=code,
        )


class PvogDrafter:
    """Draft the mentions of one payload's modules, each carrying the same leaf hints."""

    def __init__(self, locale: str, hints: LeafHints) -> None:
        """Keep the payload locale and the leaf hints every draft carries."""
        self._locale = locale
        self._hints = hints

    def module_drafts(self, module: Module) -> list[MentionDraft]:
        """Return the drafts of one selected module, one per distinct non-noise fragment, in document order."""
        selector = MODULE_SELECTORS[module.code]
        found = dict.fromkeys(item for item in selector.strategy(module) if not is_noise(item.title))
        return [self._draft(module, selector, item) for item in found]

    def _draft(self, module: Module, selector: ModuleSelector, item: Found) -> MentionDraft:
        return MentionDraft(
            title_i18n={self._locale: item.title},
            role=selector.role,
            excerpt=_excerpt(module, item.title),
            source_field=f"details[code={module.code}]",
            extractor=EXTRACTOR,
            extractor_version=EXTRACTOR_VERSION,
            official_url=item.official_url,
            situation_codes=self._hints.situation_codes,
            direct_situation_confidence=self._hints.situation_confidence,
            domain_codes=self._hints.domain_codes,
            direct_domain_confidence=self._hints.domain_confidence,
            pvog_leaf_code=self._hints.leaf_code,
        )


def harvest_pvog_payload(raw_payload: dict[str, object]) -> list[MentionDraft]:
    """Return the document mentions in ``raw_payload.details``, in module and document order."""
    drafter = PvogDrafter(_locale(raw_payload), LeafHints.from_payload(raw_payload))
    return [draft for module in selected_modules(raw_payload) for draft in drafter.module_drafts(module)]
