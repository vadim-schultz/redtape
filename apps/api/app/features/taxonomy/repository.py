"""Persistence for the canonical category tree."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.taxonomy import Category


class TaxonomyRepository:
    """Persistence for the active canonical category tree."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to the session it queries through."""
        self._session = session

    def list_categories(self) -> Sequence[Category]:
        """List active categories depth-first, ordered by each node's contract sort order."""
        rows = list(
            self._session.scalars(
                select(Category).where(Category.is_active).options(selectinload(Category.external_mappings))
            ).all()
        )
        by_parent: dict[UUID | None, list[Category]] = defaultdict(list)
        active_ids = {row.id for row in rows}
        for row in rows:
            if row.parent_id is None or row.parent_id in active_ids:
                by_parent[row.parent_id].append(row)
        for children in by_parent.values():
            children.sort(key=lambda category: (category.sort_order, category.code))
        ordered: list[Category] = []

        def visit(parent_id: UUID | None) -> None:
            """Append a node and its active descendants in contract order."""
            for category in by_parent[parent_id]:
                ordered.append(category)
                visit(category.id)

        visit(None)
        usable_count = sum(len(children) for children in by_parent.values())
        if len(ordered) != usable_count:
            raise ValueError("Invalid category taxonomy: active cycle cannot be served")
        return ordered

    def ids_for_category_codes(self, codes: Iterable[str]) -> dict[str, UUID]:
        """Map active canonical category codes to ids; inactive and unknown codes are absent."""
        requested = set(codes)
        return {category.code: category.id for category in self.list_categories() if category.code in requested}

    def category_descendant_codes(self, codes: Sequence[str]) -> tuple[str, ...]:
        """Return selected active category codes and all active descendants in tree order."""
        categories = self.list_categories()
        children: dict[str, list[str]] = defaultdict(list)
        by_id = {category.id: category.code for category in categories}
        for category in categories:
            if category.parent_id is not None and category.parent_id in by_id:
                children[by_id[category.parent_id]].append(category.code)
        selected = set(codes)
        expanded: list[str] = []

        def visit(code: str) -> None:
            """Append ``code`` and recursively append its descendants."""
            if code in expanded:
                return
            expanded.append(code)
            for child in children[code]:
                visit(child)

        for category in categories:
            if category.code in selected:
                visit(category.code)
        return tuple(expanded)
