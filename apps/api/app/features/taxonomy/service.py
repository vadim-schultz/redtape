"""Canonical category reads and the category-code resolution that filters and writes share."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from uuid import UUID

from app.features.taxonomy.repository import TaxonomyRepository
from app.i18n_resolution import pick_i18n
from app.models.taxonomy import Category
from app.schema.taxonomy.read import CategoryNodeRead, CategoryTagRead, VocabularyResponse, VocabularyTerm
from app.shared.locale import ResolvedLocale


class TaxonomyCodeError(ValueError):
    """Raised when a category code is not an active canonical category."""


class TaxonomyService:
    """Read the canonical category tree and resolve category codes for list filters and writes."""

    def __init__(self, repository: TaxonomyRepository) -> None:
        """Bind the service to its taxonomy repository."""
        self._repo = repository

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

    def require_category_codes(self, codes: Sequence[str]) -> None:
        """Raise :class:`TaxonomyCodeError` naming every code that is not an active canonical category."""
        unique = tuple(dict.fromkeys(codes))
        unknown = sorted(set(unique) - self.known_category_codes(unique))
        if unknown:
            raise TaxonomyCodeError(f"Unknown category code(s): {', '.join(unknown)}")

    def expand_category_codes(self, codes: Sequence[str]) -> tuple[str, ...]:
        """Return the selected category codes and all their active descendants in tree order.

        An unknown or inactive code raises :class:`TaxonomyCodeError`; a filter never silently drops it.
        """
        self.require_category_codes(codes)
        return self._repo.category_descendant_codes(tuple(dict.fromkeys(codes)))

    def resolve_category_ids(self, codes: Sequence[str]) -> list[UUID]:
        """Resolve active category codes to ids in tree order; inactive and unknown codes are absent."""
        return list(self._repo.ids_for_category_codes(codes).values())

    def known_category_codes(self, codes: Iterable[str]) -> set[str]:
        """Return the subset of active canonical category codes."""
        return set(self._repo.ids_for_category_codes(codes))

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

    def to_category_tag(self, category: Category, *, locale: ResolvedLocale, confidence: float) -> CategoryTagRead:
        """Convert a category row and its persisted confidence into a localized category tag."""
        return CategoryTagRead(code=category.code, name=pick_i18n(category.name_i18n, locale), confidence=confidence)

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
