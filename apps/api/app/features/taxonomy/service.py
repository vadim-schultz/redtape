from __future__ import annotations

from collections.abc import Iterable, Sequence
from uuid import UUID

from app.features.taxonomy.repository import TaxonomyRepository, TermModel
from app.i18n_resolution import pick_i18n
from app.models.taxonomy import Domain, LifeSituation, LifeSituationGroup
from app.schema.taxonomy.read import (
    AxisCount,
    LifeSituationGroupedRead,
    MatrixCell,
    MatrixResponse,
    TermRead,
    VocabularyResponse,
    VocabularyTerm,
)
from app.shared.locale import ResolvedLocale


class TaxonomyCodeError(ValueError):
    """Raised when a term code does not exist."""


class TaxonomyService:
    """Locale-resolved taxonomy reads and code → id resolution for other features."""

    def __init__(self, repository: TaxonomyRepository) -> None:
        self._repo = repository

    def list_domains(self, *, locale: ResolvedLocale) -> list[TermRead]:
        return self._list(Domain, locale)

    def list_situations(self, *, locale: ResolvedLocale) -> list[TermRead]:
        return self._list(LifeSituation, locale)

    def list_situation_groups(self, *, locale: ResolvedLocale) -> list[TermRead]:
        return self._list(LifeSituationGroup, locale)

    def list_situations_with_group(self, *, locale: ResolvedLocale) -> list[LifeSituationGroupedRead]:
        """Every situation, locale-resolved, carrying its group's stable ``code``."""
        rows = self._repo.list_situations_with_group()
        return [
            LifeSituationGroupedRead(
                **self.to_term_read(situation, locale=locale).model_dump(),
                group_code=group_code,
            )
            for situation, group_code in rows
        ]

    def resolve_domain_ids(self, codes: Sequence[str]) -> list[UUID]:
        return self._resolve(Domain, codes)

    def resolve_situation_ids(self, codes: Sequence[str]) -> list[UUID]:
        return self._resolve(LifeSituation, codes)

    def vocabulary(self) -> VocabularyResponse:
        """Return both vocabularies in sort order with every stored translation."""
        return VocabularyResponse(
            domains=self._terms(Domain),
            situations=self._terms(LifeSituation),
        )

    def known_domain_codes(self, codes: Iterable[str]) -> set[str]:
        """Return the subset of ``codes`` that is a domain code."""
        return set(self._repo.ids_for_codes(Domain, codes))

    def known_situation_codes(self, codes: Iterable[str]) -> set[str]:
        """Return the subset of ``codes`` that is a life-situation code."""
        return set(self._repo.ids_for_codes(LifeSituation, codes))

    def get_matrix(self, document_ids: Sequence[UUID]) -> MatrixResponse:
        """Matrix over the given in-scope documents; `total` is their number, tagged or not."""
        return MatrixResponse(
            total=len(document_ids),
            cells=[MatrixCell(domain=d, situation=s, count=n) for d, s, n in self._repo.matrix_counts(document_ids)],
            situations=[AxisCount(code=c, count=n) for c, n in self._repo.situation_counts(document_ids)],
            domains=[AxisCount(code=c, count=n) for c, n in self._repo.domain_counts(document_ids)],
        )

    def to_term_read(self, term: Domain | LifeSituation | LifeSituationGroup, *, locale: ResolvedLocale) -> TermRead:
        return TermRead(
            code=term.code,
            name=pick_i18n(term.name_i18n, locale),
            description=pick_i18n(term.description_i18n, locale),
            icon=term.icon,
        )

    def _terms(self, model: TermModel) -> list[VocabularyTerm]:
        return [
            VocabularyTerm(code=t.code, name_i18n=t.name_i18n, description_i18n=t.description_i18n)
            for t in self._repo.list_terms(model)
        ]

    def _list(self, model: TermModel, locale: ResolvedLocale) -> list[TermRead]:
        terms = self._repo.list_terms(model)
        return [self.to_term_read(term, locale=locale) for term in terms]

    def _resolve(self, model: TermModel, codes: Sequence[str]) -> list[UUID]:
        ids = self._repo.ids_for_codes(model, codes)
        unknown = sorted(set(codes) - ids.keys())
        if unknown:
            raise TaxonomyCodeError(f"Unknown {model.__tablename__} code(s): {', '.join(unknown)}")
        return [ids[code] for code in codes]
