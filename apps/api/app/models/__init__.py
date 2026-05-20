from __future__ import annotations

from app.models.base import Base
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locale import SupportedLocale, UITranslation
from app.models.locality import Locality

__all__ = [
    "Base",
    "Document",
    "DocumentRequirement",
    "Jurisdiction",
    "JurisdictionKind",
    "Locality",
    "SupportedLocale",
    "UITranslation",
]
