"""Domain errors of reading a stored translation; the discovery handlers and the candidate router map them to HTTP."""

from __future__ import annotations

from app.features.discovery.errors import DiscoveryNotFoundError
from app.schema.candidate.document_translation import DocumentTranslationCode, DocumentTranslationError


class TranslationNotFoundError(DiscoveryNotFoundError):
    """The candidate has no stored translation into the requested locale, or its stored text cannot be read."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Translation not found")


class DocumentUnavailableError(Exception):
    """A candidate's document has no blocks to show; the candidate router answers 404 with ``body``."""

    def __init__(self, code: DocumentTranslationCode, reason: str | None = None) -> None:
        """Build the error from the code the answer carries and the skip ``reason``, when there is one."""
        super().__init__(code.value)
        self.body = DocumentTranslationError(code=code, reason=reason)
