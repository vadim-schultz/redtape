"""SQL expressions that the admin candidate list orders by, beyond the candidate's own columns."""

from __future__ import annotations

from sqlalchemy import ColumnElement, func

from app.models.jurisdiction import Jurisdiction


def jurisdiction_name_expression() -> ColumnElement[str]:
    """Return the lower-cased German, else English, else code name of the candidate's jurisdiction."""
    german, english = Jurisdiction.name_i18n["de"].as_string(), Jurisdiction.name_i18n["en"].as_string()
    return func.lower(func.coalesce(german, english, Jurisdiction.code, ""))


def role_count_expression(roles: ColumnElement) -> ColumnElement[int]:
    """Return the number of distinct roles in the ``roles`` array, ``0`` for a candidate without a mention."""
    return func.coalesce(func.cardinality(roles), 0)


def role_set_expression(roles: ColumnElement) -> ColumnElement[str]:
    """Return the ``roles`` array as text so candidates with the same role set sort together."""
    return func.coalesce(func.array_to_string(roles, ","), "")
