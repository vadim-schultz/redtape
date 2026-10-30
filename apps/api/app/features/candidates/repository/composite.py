"""The session-bound repository of the public candidate view."""

from __future__ import annotations

from app.features.candidates.repository.cards import CardRepository
from app.features.candidates.repository.descriptions import DescriptionRepository
from app.features.candidates.repository.screenshots import ScreenshotRepository
from app.features.discovery.repository import CandidateListingRepository, CompletenessRepository, EdgeRepository


class PublicCandidateRepository(
    CardRepository,
    DescriptionRepository,
    ScreenshotRepository,
    CandidateListingRepository,
    CompletenessRepository,
    EdgeRepository,
):
    """Cards, descriptions and screenshots of the public view, plus the discovery reads it reuses."""
