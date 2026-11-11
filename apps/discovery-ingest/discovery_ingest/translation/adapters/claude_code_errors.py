"""Map a failed ``claude`` call onto the port's categories, and keep API keys out of every message that quotes the CLI.

A usage or rate limit is a quota stop, a login problem is unauthorised, a model or request the CLI refuses is permanent,
and anything else that failed is transient (a retry may help). Unreadable output is not a failure here: it is the
answer reader's business, because it gets one repeat.
"""

from __future__ import annotations

import re
from typing import Final

from discovery_ingest.translation.adapters.claude_code_cli import CliResult, CliTimeout
from discovery_ingest.translation.errors import (
    PermanentError,
    QuotaExceeded,
    TransientError,
    TranslationEngineError,
    Unauthorised,
)

QUOTA_MARKERS: Final = ("usage limit", "limit reached", "rate limit", "rate_limit", "too many requests")
AUTH_MARKERS: Final = ("not logged in", "please run /login", "invalid api key", "authentication_error", "unauthorized")
PERMANENT_MARKERS: Final = ("may not exist", "not have access", "prompt is too long", "invalid_request")
_CATEGORIES: Final[tuple[tuple[tuple[str, ...], type[TranslationEngineError]], ...]] = (
    (QUOTA_MARKERS, QuotaExceeded),
    (AUTH_MARKERS, Unauthorised),
    (PERMANENT_MARKERS, PermanentError),
)
EXCERPT_CHARS: Final = 200
_KEY_LIKE: Final = re.compile(r"sk-[A-Za-z0-9_\-]{4,}")


def excerpt(text: str) -> str:
    """Return the start of ``text`` with anything that looks like an API key replaced."""
    return _KEY_LIKE.sub("sk-<redacted>", text)[:EXCERPT_CHARS]


def failure_for(result: CliResult, result_text: str | None) -> TranslationEngineError:
    """Return the category of a call that exited non-zero or reported an error; the first matching marker decides."""
    said = " ".join(part for part in (result_text, result.stderr, result.stdout) if part).lower()
    category = next((cls for markers, cls in _CATEGORIES if any(m in said for m in markers)), TransientError)
    detail = excerpt(result_text or result.stderr or result.stdout)
    return category(f"the claude CLI exited {result.returncode}: {detail}")


def timeout_failure(err: CliTimeout) -> TransientError:
    """Map a call that did not finish in time to a transient failure: the batch is tried again later."""
    return TransientError(f"the claude CLI did not finish in time: {excerpt(str(err))}")


def start_failure(err: OSError) -> TransientError:
    """Map a process that could not start to a transient failure, so its batch is not failed for good."""
    return TransientError(f"the claude CLI could not be started: {excerpt(str(err))}")
