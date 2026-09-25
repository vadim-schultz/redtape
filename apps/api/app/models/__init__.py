from __future__ import annotations

from app.models.base import Base
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locale import SupportedLocale, UITranslation
from app.models.locality import Locality
from app.models.taxonomy import Domain, LifeSituation

__all__ = [
    "Base",
    "Document",
    "DocumentRequirement",
    "Domain",
    "Jurisdiction",
    "JurisdictionKind",
    "LifeSituation",
    "Locality",
    "SupportedLocale",
    "UITranslation",
]
