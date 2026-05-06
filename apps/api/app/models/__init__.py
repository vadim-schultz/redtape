from __future__ import annotations

from app.models.base import Base
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locale import SupportedLocale, UITranslation

__all__ = [
    "Base",
    "Document",
    "DocumentRequirement",
    "Jurisdiction",
    "JurisdictionKind",
    "SupportedLocale",
    "UITranslation",
]
