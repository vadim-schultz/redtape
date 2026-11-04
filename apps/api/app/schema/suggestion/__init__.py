"""Suggestion create request and new-document payload schemas."""

from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.payload import NewDocumentPayload

__all__ = ["NewDocumentPayload", "SuggestionCreate"]
