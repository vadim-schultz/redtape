"""Request-scoped facts about who is submitting a suggestion and how."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from litestar import Request
from litestar.params import Dependency, Parameter

from app.features.auth.principal import Principal
from app.features.suggestions.submitter import submitter_display_name, submitter_for
from app.features.suggestions.submitters import Submitter

IDEMPOTENCY_KEY_MAX_LENGTH = 128
IDEMPOTENCY_KEY_PATTERN = r"^[\x20-\x7e]+$"


@dataclass(frozen=True, slots=True)
class Submission:
    """The submitter, optional idempotency key and collection URL path of a create call."""

    submitter: Submitter
    display_name: str | None
    idempotency_key: str | None
    collection_path: str


def provide_submission(
    request: Request,
    principal: Annotated[Principal, Dependency(skip_validation=True)],
    idempotency_key: str | None = Parameter(
        header="Idempotency-Key",
        default=None,
        max_length=IDEMPOTENCY_KEY_MAX_LENGTH,
        pattern=IDEMPOTENCY_KEY_PATTERN,
    ),
) -> Submission:
    """Collect the submitter identity and idempotency header into one object."""
    return Submission(
        submitter=submitter_for(principal),
        display_name=submitter_display_name(principal),
        idempotency_key=idempotency_key,
        collection_path=request.url.path.rstrip("/"),
    )
