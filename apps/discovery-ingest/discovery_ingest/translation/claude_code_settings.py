"""Claude Code settings: the model the CLI runs, and the environment it starts in.

This is the one translation module that reads the process environment, because the CLI needs the login variables and
the subprocess must not get the API key variables (those are stripped by the transport).
"""

from __future__ import annotations

import os
from typing import Final

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MODEL: Final = "claude-sonnet-5-5"


class ClaudeCodeSettings(BaseSettings):
    """``CLAUDE_TRANSLATE_MODEL``: the model the CLI runs; read from the process environment only."""

    model_config = SettingsConfigDict(extra="ignore")

    claude_translate_model: str = Field(default=DEFAULT_MODEL, min_length=1, validation_alias="CLAUDE_TRANSLATE_MODEL")


def load_claude_code_settings() -> ClaudeCodeSettings:
    """Load the Claude Code settings from the environment."""
    return ClaudeCodeSettings()


def process_environment() -> dict[str, str]:
    """Return a copy of this process's environment, which the CLI inherits minus its API key variables."""
    return dict(os.environ)
