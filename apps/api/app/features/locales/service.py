"""Map locale and translation rows to their read models."""

from __future__ import annotations

from app.features.locales.repository import LocalesRepository
from app.schema.locale.read import LocaleRead, TranslationBundle


class LocalesService:
    """Read-only locale listing and translation bundles."""

    def __init__(self, repository: LocalesRepository) -> None:
        """Bind the service to the locales repository."""
        self._repo = repository

    def list_enabled(self) -> list[LocaleRead]:
        """Every enabled locale, sorted by code."""
        return [LocaleRead.model_validate(row) for row in self._repo.list_enabled()]

    def translations_for(self, code: str) -> TranslationBundle:
        """Return the full UI translation bundle for `code`; empty when there are no rows."""
        rows = self._repo.translations_for(code)
        return TranslationBundle(locale=code, translations=dict(rows))
