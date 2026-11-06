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
from discovery_ingest.pvog.category_mapping import MachineCrosswalk, PvogCategoryEvidence
from discovery_ingest.pvog.models import PvogSourcePath

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
    """The canonical evidence one PVOG path carries onto every drafted mention."""

    category_codes: list[str] | None
    category_confidence: float | None
    leaf_code: str | None
    source_path: PvogSourcePath | None
    mapping_version: str | None

    @classmethod
    def from_payload(cls, raw_payload: dict[str, object], crosswalk: MachineCrosswalk) -> LeafHints:
        """Read the stashed PVOG path and map it through the crosswalk the harvest was given."""
        code = _leaf_code(raw_payload)
        source_path = _source_path(raw_payload)
        if source_path is None:
            return cls(None, None, code, None, None)
        evidence = crosswalk.evidence_for_path(source_path)
        return cls(*_evidence_fields(evidence), code or source_path.leaf_code, source_path, crosswalk.artifact_version)


def _source_path(raw_payload: dict[str, object]) -> PvogSourcePath | None:
    """Parse the captured PVOG path without turning malformed source data into a category."""
    raw_path = raw_payload.get("_pvog_source_path")
    if not isinstance(raw_path, dict):
        return None
    try:
        path = PvogSourcePath.model_validate(raw_path)
    except ValueError:
        return None
    leaf_code = _leaf_code(raw_payload)
    return path if leaf_code in {None, path.leaf_code} else None


def _evidence_fields(evidence: PvogCategoryEvidence | None) -> tuple[list[str] | None, float | None]:
    """Return mention fields for mapped evidence, or empty category fields for source-only paths."""
    if evidence is None:
        return None, None
    return list(evidence.category_codes), evidence.confidence


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
            category_codes=self._hints.category_codes,
            direct_category_confidence=self._hints.category_confidence,
            pvog_leaf_code=self._hints.leaf_code,
            pvog_source_path=self._hints.source_path,
            pvog_mapping_version=self._hints.mapping_version,
        )


def harvest_pvog_payload(raw_payload: dict[str, object], crosswalk: MachineCrosswalk) -> list[MentionDraft]:
    """Return the document mentions in ``raw_payload.details``, in module and document order, mapped through ``crosswalk``."""
    drafter = PvogDrafter(_locale(raw_payload), LeafHints.from_payload(raw_payload, crosswalk))
    return [draft for module in selected_modules(raw_payload) for draft in drafter.module_drafts(module)]
