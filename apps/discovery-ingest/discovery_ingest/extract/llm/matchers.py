"""The response matchers that Step 0 of chapter E4 can change: what a daily-quota error and a JSON-mode failure look like.

Defaults come from Cloudflare's documentation (neuron allowance error ``4006`` with status ``429``; ``JSON Mode
couldn't be met``). If the probe or the first natural quota hit shows another body, change the constants here only.
"""

from __future__ import annotations

from dataclasses import dataclass

QUOTA_STATUS = 429
QUOTA_CODES = frozenset({4006})
QUOTA_PHRASES = ("daily free allocation", "used up your daily")
JSON_MODE_PHRASES = ("json mode couldn't be met", "json mode could not be met")


@dataclass(frozen=True, slots=True)
class ErrorInfo:
    """What an error response says: its status, the Cloudflare error codes and the message text (lower case)."""

    status: int
    codes: frozenset[int]
    text: str


def is_quota_error(info: ErrorInfo) -> bool:
    """Whether ``info`` is the daily neuron allowance error (matched by status and code, or by status and phrase)."""
    if info.status != QUOTA_STATUS:
        return False
    return bool(info.codes & QUOTA_CODES) or any(phrase in info.text for phrase in QUOTA_PHRASES)


def is_json_mode_failure(info: ErrorInfo) -> bool:
    """Whether ``info`` says the model could not meet the JSON schema."""
    return any(phrase in info.text for phrase in JSON_MODE_PHRASES)
