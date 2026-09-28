from __future__ import annotations

from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locale import SupportedLocale, UITranslation
from app.models.locality import Locality
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.taxonomy import Domain, LifeSituation
from app.models.user import AppUser, UserRole

__all__ = [
    "ApiKey",
    "AppUser",
    "Base",
    "Document",
    "DocumentRequirement",
    "Domain",
    "Jurisdiction",
    "JurisdictionKind",
    "LifeSituation",
    "Locality",
    "Suggestion",
    "SuggestionKind",
    "SuggestionSource",
    "SuggestionStatus",
    "SupportedLocale",
    "UITranslation",
    "UserRole",
]
