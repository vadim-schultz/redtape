"""The Claude Code translator: the ``llm`` prompt, glossary, answer schema and validators, answered by the ``claude`` CLI.

It registers itself as ``claude-code``, billed to the Claude Code allowance (unit ``subscription``), not to Cloudflare
neurons. Only the transport differs from ``llm``; the command is built in ``claude_code_cli``.
"""

from __future__ import annotations

import math
import shutil
from collections.abc import Mapping
from typing import Final

from discovery_ingest.extract.llm.prices import CHARS_PER_TOKEN
from discovery_ingest.translation.adapters.claude_code_cli import (
    COMMAND,
    CliRunner,
    CliTimeout,
    build_request,
    run_subprocess,
)
from discovery_ingest.translation.adapters.claude_code_errors import start_failure, timeout_failure
from discovery_ingest.translation.adapters.claude_code_output import CliAnswer, read_answer
from discovery_ingest.translation.adapters.cloudflare_answer import parse_answer
from discovery_ingest.translation.adapters.cloudflare_prompt import LANGUAGE_NAMES, build_messages
from discovery_ingest.translation.claude_code_settings import load_claude_code_settings, process_environment
from discovery_ingest.translation.errors import UnusableOutputError
from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES, provider_code, register_locale_map
from discovery_ingest.translation.registry import EngineConfig, register_engine
from discovery_ingest.translation.units import (
    CallLimits,
    TranslationBatch,
    TranslationOutcome,
    TranslationUnit,
    Usage,
    UsageUnit,
)

NAME: Final = "claude-code"
AUTH_MODE: Final = "claude-login"
"""Recorded with every call: the CLI ran on the Claude Code login, because its API key variables were removed."""
UNITS_PER_CALL: Final = 20
CONCURRENCY: Final = 4
OUTPUT_TOKENS_PER_INPUT_TOKEN: Final = 2.0


def prompt_text(batch: TranslationBatch, language: str) -> str:
    """Return the one prompt the CLI reads from stdin: the rules and glossary, then the units as data."""
    system, user = build_messages(batch, language)
    return f"{system['content']}\n\nUser message:\n{user['content']}"


class ClaudeCodeTranslator:
    """Translate batches with the Claude Code CLI: one call per batch of at most 20 units, answered as schema-checked JSON."""

    name = NAME
    usage_unit: UsageUnit = "subscription"

    def __init__(self, runner: CliRunner, *, model: str, environ: Mapping[str, str]) -> None:
        """Keep the runner, the model the command names, and the environment the CLI starts in."""
        self._runner = runner
        self._model = model
        self._environ = environ

    @property
    def limits(self) -> CallLimits:
        """Up to 20 units a call and four calls in flight at once; the drain's own setting may be lower."""
        return CallLimits(UNITS_PER_CALL, CONCURRENCY)

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        """Return one result per unit in order, the tokens the calls used, the model and the login auth mode."""
        results, tokens = self._readable(prompt_text(batch, _language(batch)), batch.units)
        return TranslationOutcome(results, Usage(self.usage_unit, float(tokens)), self._model, AUTH_MODE)

    def estimate(self, batch: TranslationBatch) -> Usage:
        """Return the tokens to reserve: the prompt's tokens in, about twice as many out."""
        prompt_tokens = math.ceil(len(prompt_text(batch, _language(batch))) / CHARS_PER_TOKEN)
        return Usage(self.usage_unit, float(prompt_tokens * (1 + OUTPUT_TOKENS_PER_INPUT_TOKEN)))

    def _readable(self, prompt: str, units: tuple[TranslationUnit, ...]) -> tuple[tuple[TranslationUnit, ...], int]:
        """Return the readable answer and the tokens of every call it took; an unreadable answer is asked for once more."""
        first = self._ask(prompt)
        try:
            return parse_answer(first.answer_json, units), first.tokens
        except UnusableOutputError:
            second = self._ask(prompt)
            return parse_answer(second.answer_json, units), first.tokens + second.tokens

    def _ask(self, prompt: str) -> CliAnswer:
        try:
            result = self._runner(build_request(prompt, self._model, self._environ))
        except CliTimeout as err:
            raise timeout_failure(err) from err
        except OSError as err:
            raise start_failure(err) from err
        return read_answer(result)


def _language(batch: TranslationBatch) -> str:
    return LANGUAGE_NAMES.get(provider_code(NAME, batch.target_locale), batch.target_locale)


def _build(config: EngineConfig) -> ClaudeCodeTranslator:
    """Build the translator; refuse to start without the claude command, because every batch would fail."""
    if shutil.which(COMMAND) is None:
        raise ValueError(f"the {COMMAND} command (Claude Code CLI) is not on PATH")
    model = config.model or load_claude_code_settings().claude_translate_model
    return ClaudeCodeTranslator(run_subprocess, model=model, environ=process_environment())


register_locale_map(NAME, {code: code for code in DEFAULT_TARGET_LOCALES})
register_engine(NAME, _build)
