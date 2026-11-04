"""Carrier for the discovery list handlers: one repository filter and one page, built once per request."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from app.features.discovery.repository import Page

FilterT = TypeVar("FilterT")


@dataclass(frozen=True, slots=True)
class DiscoveryListQuery(Generic[FilterT]):
    """A repository filter plus the page to read, built once per request."""

    filters: FilterT
    page: Page
