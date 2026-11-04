"""Canonical taxonomy reads, filter resolution, and legacy compatibility adapters."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from app.features.taxonomy.compatibility import LegacyTaxonomyAdapter
from app.features.taxonomy.repository import TaxonomyRepository, TermModel
from app.i18n_resolution import pick_i18n
from app.models.taxonomy import Category, Domain, LifeSituation, LifeSituationGroup
from app.schema.taxonomy.read import (
    AxisCount,
    CategoryNodeRead,
    CategoryTagRead,
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


@dataclass(frozen=True, slots=True)
class CategoryFilter:
    """Resolved canonical codes plus explicit legacy inputs for one list query."""

    codes: tuple[str, ...] = ()
    legacy_domain_codes: tuple[str, ...] = ()
    legacy_situation_codes: tuple[str, ...] = ()
    domain_category_codes: tuple[str, ...] = ()
    situation_category_codes: tuple[str, ...] = ()
    category_domain_codes: tuple[str, ...] = ()
    category_situation_codes: tuple[str, ...] = ()


class TaxonomyService:
    """Resolve canonical taxonomy reads and compatibility filters for other features."""

    def __init__(self, repository: TaxonomyRepository) -> None:
        """Bind the service to its taxonomy repository."""
        self._repo = repository
        self._compatibility = LegacyTaxonomyAdapter()

    def list_domains(self, *, locale: ResolvedLocale) -> list[TermRead]:
        """List the domain terms in the requested locale."""
        return self._list(Domain, locale)

    def list_situations(self, *, locale: ResolvedLocale) -> list[TermRead]:
        """List the life-situation terms in the requested locale."""
        return self._list(LifeSituation, locale)

    def list_situation_groups(self, *, locale: ResolvedLocale) -> list[TermRead]:
        """List the life-situation group terms in the requested locale."""
        return self._list(LifeSituationGroup, locale)

    def list_categories(self, *, locale: ResolvedLocale) -> list[CategoryNodeRead]:
        """Return the active category tree with localized names and descriptions."""
        rows = self._repo.list_categories()
        by_parent: dict[UUID | None, list[Category]] = defaultdict(list)
        by_id = {row.id: row for row in rows}
        for row in rows:
            if row.parent_id is None or row.parent_id in by_id:
                by_parent[row.parent_id].append(row)
        return [self._category_node(row, by_parent, locale) for row in by_parent[None]]

    def category_names(self, *, locale: ResolvedLocale) -> dict[str, str]:
        """Return localized names for every active canonical category."""
        return {category.code: pick_i18n(category.name_i18n, locale) for category in self._repo.list_categories()}

    def resolve_category_filter(
        self,
        category_codes: Sequence[str] = (),
        *,
        domain_codes: Sequence[str] = (),
        group_codes: Sequence[str] = (),
        situation_codes: Sequence[str] = (),
    ) -> CategoryFilter:
        """Validate canonical and legacy inputs and translate them to active category codes."""
        explicit = self._expanded_category_codes(category_codes)
        try:
            legacy = self._compatibility.translate(
                domain_codes=domain_codes,
                group_codes=group_codes,
                situation_codes=situation_codes,
            )
        except ValueError as exc:
            raise TaxonomyCodeError(str(exc)) from exc
        domain_category_codes = self._expanded_category_codes(legacy.domain_targets)
        situation_category_codes = self._expanded_category_codes(legacy.situation_targets)
        expanded = self._expanded_category_codes((*explicit, *domain_category_codes, *situation_category_codes))
        category_domain_codes, category_situation_codes = self._compatibility.source_codes_for_categories(explicit)
        return CategoryFilter(
            codes=expanded,
            legacy_domain_codes=legacy.domain_codes,
            legacy_situation_codes=legacy.situation_codes,
            domain_category_codes=domain_category_codes,
            situation_category_codes=situation_category_codes,
            category_domain_codes=category_domain_codes,
            category_situation_codes=category_situation_codes,
        )

    def resolve_category_ids(self, category_filter: CategoryFilter) -> list[UUID]:
        """Resolve the expanded canonical category codes of ``category_filter`` to active ids."""
        return self._resolve_category_ids(category_filter.codes)

    def resolve_category_code_ids(self, codes: Sequence[str]) -> list[UUID]:
        """Resolve an already validated category-code selection to active ids."""
        return self._resolve_category_ids(codes)

    def canonical_scores(
        self,
        *,
        domain_scores: Mapping[str, float],
        situation_scores: Mapping[str, float],
    ) -> dict[str, float]:
        """Translate legacy scored tags to canonical scores using the frozen maximum policy."""
        return self._compatibility.canonical_scores(
            domain_scores=domain_scores,
            situation_scores=situation_scores,
        )

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
        """Map domain codes to ids, in input order; an unknown code raises TaxonomyCodeError."""
        return self._resolve(Domain, codes)

    def resolve_situation_ids(self, codes: Sequence[str]) -> list[UUID]:
        """Map life-situation codes to ids, in input order; an unknown code raises TaxonomyCodeError."""
        return self._resolve(LifeSituation, codes)

    def vocabulary(self) -> VocabularyResponse:
        """Return the active canonical category vocabulary with source parent metadata."""
        return VocabularyResponse(
            categories=[
                VocabularyTerm(
                    code=category.code,
                    parent_code=self._parent_code(category),
                    name_i18n=category.name_i18n,
                    description_i18n=category.description_i18n,
                    icon=category.icon,
                    source_parent_codes=sorted(
                        mapping.external_code
                        for mapping in category.external_mappings
                        if mapping.external_level == "parent"
                    ),
                )
                for category in self._repo.list_categories()
            ],
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
        """Convert a taxonomy row into a term read resolved to the locale."""
        return TermRead(
            code=term.code,
            name=pick_i18n(term.name_i18n, locale),
            description=pick_i18n(term.description_i18n, locale),
            icon=term.icon,
        )

    def to_category_tag(self, category: Category, *, locale: ResolvedLocale, confidence: float) -> CategoryTagRead:
        """Convert a category row and persisted score into a localized category tag."""
        return CategoryTagRead(code=category.code, name=pick_i18n(category.name_i18n, locale), confidence=confidence)

    def _list(self, model: TermModel, locale: ResolvedLocale) -> list[TermRead]:
        terms = self._repo.list_terms(model)
        return [self.to_term_read(term, locale=locale) for term in terms]

    def _resolve(self, model: TermModel, codes: Sequence[str]) -> list[UUID]:
        ids = self._repo.ids_for_codes(model, codes)
        unknown = sorted(set(codes) - ids.keys())
        if unknown:
            raise TaxonomyCodeError(f"Unknown {model.__tablename__} code(s): {', '.join(unknown)}")
        return [ids[code] for code in codes]

    def _category_node(
        self,
        category: Category,
        by_parent: Mapping[UUID | None, Sequence[Category]],
        locale: ResolvedLocale,
    ) -> CategoryNodeRead:
        """Build one category node and recursively map its direct children."""
        return CategoryNodeRead(
            code=category.code,
            parent_code=self._parent_code(category),
            name=pick_i18n(category.name_i18n, locale),
            description=pick_i18n(category.description_i18n, locale),
            icon=category.icon,
            children=[self._category_node(child, by_parent, locale) for child in by_parent.get(category.id, ())],
        )

    def _parent_code(self, category: Category) -> str | None:
        """Return the parent code for a category loaded by the repository."""
        return None if category.parent is None else category.parent.code

    def _expanded_category_codes(self, codes: Sequence[str]) -> tuple[str, ...]:
        """Validate active category codes and expand each selected node to its descendants."""
        unique = tuple(dict.fromkeys(codes))
        if not unique:
            return ()
        known = self._repo.ids_for_category_codes(unique)
        unknown = sorted(set(unique) - known.keys())
        if unknown:
            raise TaxonomyCodeError(f"Unknown or inactive category code(s): {', '.join(unknown)}")
        return self._repo.category_descendant_codes(unique)

    def _resolve_category_ids(self, codes: Sequence[str]) -> list[UUID]:
        """Resolve already-expanded category codes and preserve their tree order."""
        return list(self._repo.ids_for_category_codes(codes).values())
