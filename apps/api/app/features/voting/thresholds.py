"""The pure rule that turns a vote score into a suggestion status."""

from __future__ import annotations

from app.models.suggestion import SuggestionStatus


def decide_status(score: int, approve: int, reject: int) -> SuggestionStatus:
    """Return the status a vote score implies: approved at or above approve, rejected at or below reject, else pending."""
    if score >= approve:
        return SuggestionStatus.APPROVED
    if score <= reject:
        return SuggestionStatus.REJECTED
    return SuggestionStatus.PENDING
