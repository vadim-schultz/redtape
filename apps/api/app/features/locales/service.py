"""Map locale and translation rows to their read models."""

from __future__ import annotations

from app.features.locales.repository import LocalesRepository
from app.models.locale import SupportedLocale
from app.schema.locale.read import LocaleRead, TranslationBundle
from app.shared.locale import DEFAULT_LOCALE


class LocalesService:
    """Read-only locale listing and translation bundles."""

    def __init__(self, repository: LocalesRepository) -> None:
        """Bind the service to the locales repository."""
        self._repo = repository

    def list_enabled(self) -> list[LocaleRead]:
        """Every enabled locale, sorted by code, with completeness computed from ``ui_translation``."""
        counts = self._repo.key_counts_by_locale(DEFAULT_LOCALE)
        return [_read_with_completeness(row, counts) for row in self._repo.list_enabled()]

    def translations_for(self, code: str) -> TranslationBundle:
        """Return the full UI translation bundle for `code`; empty when there are no rows."""
        rows = self._repo.translations_for(code)
        return TranslationBundle(locale=code, translations=dict(rows))


def _completeness_pct(counts: dict[str, int], code: str) -> float:
    """Return the share of the source locale's keys that ``code`` has, rounded to one decimal; 0 without a source."""
    total = counts.get(DEFAULT_LOCALE, 0)
    return round(100.0 * counts.get(code, 0) / total, 1) if total else 0.0


def _read_with_completeness(row: SupportedLocale, counts: dict[str, int]) -> LocaleRead:
    """Map a locale row to its read model, replacing the stored completeness with the computed one."""
    read = LocaleRead.model_validate(row)
    return read.model_copy(update={"completeness_pct": _completeness_pct(counts, row.code)})
