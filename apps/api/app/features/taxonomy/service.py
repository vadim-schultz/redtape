from __future__ import annotations

from collections.abc import Iterable, Sequence
from uuid import UUID

from app.features.taxonomy.repository import TaxonomyRepository, TermModel
from app.i18n_resolution import pick_i18n
from app.models.taxonomy import Domain, LifeSituation
from app.schema.taxonomy.read import TermRead


class TaxonomyCodeError(ValueError):
    """Raised when a term code does not exist."""


class TaxonomyService:
    """Locale-resolved taxonomy reads and code → id resolution for other features."""

    def __init__(self, repository: TaxonomyRepository) -> None:
        self._repo = repository

    def list_domains(self, *, locale: str, enabled_locales: set[str]) -> list[TermRead]:
        return self._list(Domain, locale, enabled_locales)

    def list_situations(self, *, locale: str, enabled_locales: set[str]) -> list[TermRead]:
        return self._list(LifeSituation, locale, enabled_locales)

    def resolve_domain_ids(self, codes: Sequence[str]) -> list[UUID]:
        return self._resolve(Domain, codes)

    def resolve_situation_ids(self, codes: Sequence[str]) -> list[UUID]:
        return self._resolve(LifeSituation, codes)

    def to_term_read(self, term: Domain | LifeSituation, *, locale: str, enabled_locales: Iterable[str]) -> TermRead:
        enabled = set(enabled_locales)
        return TermRead(
            code=term.code,
            name=pick_i18n(term.name_i18n, locale=locale, enabled=enabled),
            description=pick_i18n(term.description_i18n, locale=locale, enabled=enabled),
            icon=term.icon,
        )

    def _list(self, model: TermModel, locale: str, enabled_locales: Iterable[str]) -> list[TermRead]:
        terms = self._repo.list_terms(model)
        return [self.to_term_read(term, locale=locale, enabled_locales=enabled_locales) for term in terms]

    def _resolve(self, model: TermModel, codes: Sequence[str]) -> list[UUID]:
        ids = self._repo.ids_for_codes(model, codes)
        unknown = sorted(set(codes) - ids.keys())
        if unknown:
            raise TaxonomyCodeError(f"Unknown {model.__tablename__} code(s): {', '.join(unknown)}")
        return [ids[code] for code in codes]
