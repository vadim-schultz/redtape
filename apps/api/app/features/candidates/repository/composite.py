"""The session-bound repository of the public candidate view."""

from __future__ import annotations

from app.features.candidates.repository.card_repository import CardRepository
from app.features.candidates.repository.descriptions import DescriptionRepository
from app.features.candidates.repository.screenshots import ScreenshotRepository
from app.features.candidates.repository.tag_scores import TagScoreRepository
from app.features.candidates.repository.translations import TranslationIndexRepository
from app.features.discovery.repository import CandidateListingRepository, CompletenessRepository, EdgeRepository


class PublicCandidateRepository(
    CardRepository,
    DescriptionRepository,
    ScreenshotRepository,
    TagScoreRepository,
    TranslationIndexRepository,
    CandidateListingRepository,
    CompletenessRepository,
    EdgeRepository,
):
    """Cards, descriptions and screenshots of the public view, plus the discovery reads it reuses."""
