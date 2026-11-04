"""Re-export the shared legacy taxonomy compatibility adapter for feature callers."""

from app.shared.taxonomy_compatibility import LegacyAxis, LegacyTaxonomyAdapter, LegacyTranslation

__all__ = ["LegacyAxis", "LegacyTaxonomyAdapter", "LegacyTranslation"]
