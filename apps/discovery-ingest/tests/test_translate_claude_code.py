"""The Claude Code engine's transport and reading: the command, the environment, the answer and its failures (search-first C19)."""

from __future__ import annotations

import json

import pytest
from discovery_ingest.translation.adapters.claude_code import ClaudeCodeTranslator
from discovery_ingest.translation.adapters.claude_code_cli import CliRequest, CliResult, CliTimeout
from discovery_ingest.translation.adapters.cloudflare_prompt import UNITS_SCHEMA
from discovery_ingest.translation.errors import (
    PermanentError,
    QuotaExceeded,
    TransientError,
    TranslationEngineError,
    Unauthorised,
    UnusableOutputError,
)
from discovery_ingest.translation.registry import EngineConfig, build_engine
from discovery_ingest.translation.units import Usage

import translation_engine_contract as contract
from claude_code_fakes import MODEL, SECRET, ClaudeCodeHarness, FakeCli, Reply, answered, envelope, faithful, units_in
from translation_fakes import batch, unit

BATCH = batch(
    unit("a", "Antrag auf Kindergeld", "Bitte reichen Sie den Antrag ein."),
    unit("b", "Wohngeld", ""),
    target="tr",
)
MODULE = "discovery_ingest.translation.adapters.claude_code"


def _translator(reply: Reply) -> tuple[ClaudeCodeTranslator, FakeCli]:
    cli = FakeCli(reply)
    environ = {"PATH": "/usr/bin", "ANTHROPIC_API_KEY": SECRET, "ANTHROPIC_AUTH_TOKEN": "tok-login-env"}
    return ClaudeCodeTranslator(cli, model=MODEL, environ=environ), cli


def _argv_value(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def test_the_command_turns_every_tool_off_and_carries_the_schema_the_model_and_no_api_key() -> None:
    """translation engine · the CLI runs with --tools "", the answer schema, the configured model and no API key in its environment."""
    translator, cli = _translator(answered)

    translator.translate(BATCH)

    request = cli.requests[0]
    argv = list(request.argv)
    assert argv[0] == "claude" and "--print" in argv and "--no-session-persistence" in argv
    assert _argv_value(argv, "--output-format") == "json"
    assert _argv_value(argv, "--tools") == ""
    assert json.loads(_argv_value(argv, "--json-schema")) == UNITS_SCHEMA
    assert _argv_value(argv, "--model") == MODEL
    assert "ANTHROPIC_API_KEY" not in request.env and "ANTHROPIC_AUTH_TOKEN" not in request.env
    assert request.env["PATH"] == "/usr/bin"


def test_the_german_units_and_the_target_language_travel_on_stdin_and_never_in_the_argv() -> None:
    """translation engine · the prompt is on stdin: the German text is data, never a command-line argument."""
    translator, cli = _translator(answered)

    translator.translate(BATCH)

    request = cli.requests[0]
    assert "Turkish" in request.stdin and "Antrag auf Kindergeld" in request.stdin
    assert all("Antrag" not in argument for argument in request.argv)


def test_the_answer_is_read_with_its_tokens_the_model_and_the_login_auth_mode() -> None:
    """translation engine · the structured answer gives one result per unit; usage is the call's tokens; auth is the login."""
    translator, _ = _translator(answered)

    outcome = translator.translate(BATCH)

    assert [(r.key, r.title, r.description) for r in outcome.results] == [
        ("a", "[en] Antrag auf Kindergeld", "[en] Bitte reichen Sie den Antrag ein."),
        ("b", "[en] Wohngeld", ""),
    ]
    assert outcome.usage == Usage("subscription", 1300.0)
    assert (outcome.model, outcome.auth) == (MODEL, "claude-login")


def test_an_answer_given_as_result_text_is_read_when_the_structured_output_is_absent() -> None:
    """translation engine · if the CLI puts the JSON in the result text instead, the answer is read the same way."""

    def reply(request: CliRequest) -> CliResult:
        return CliResult(0, envelope(result=json.dumps(faithful(units_in(request)))), "")

    translator, _ = _translator(reply)

    assert [r.key for r in translator.translate(BATCH).results] == ["a", "b"]


def test_an_unreadable_answer_is_asked_again_once_and_a_second_unreadable_answer_is_rejected() -> None:
    """translation engine · invalid JSON gets one repeat of the call; a second unreadable answer raises UnusableOutputError."""
    translator, cli = _translator(lambda _request: CliResult(0, "this is not json", ""))

    with pytest.raises(UnusableOutputError):
        translator.translate(BATCH)

    assert len(cli.requests) == 2


def test_an_unreadable_answer_followed_by_a_readable_one_is_accepted() -> None:
    """translation engine · after one unreadable answer the repeat is used and nothing is rejected."""
    seen: list[CliRequest] = []

    def reply(request: CliRequest) -> CliResult:
        seen.append(request)
        return CliResult(0, "not json", "") if len(seen) == 1 else answered(request)

    translator, _ = _translator(reply)

    assert [r.key for r in translator.translate(BATCH).results] == ["a", "b"]
    assert len(seen) == 2


@pytest.mark.parametrize(
    ("stdout", "stderr", "category"),
    [
        (envelope(is_error=True, result="API Error: Rate limit reached"), "", QuotaExceeded),
        (envelope(is_error=True, result="Claude AI usage limit reached|1760000000"), "", QuotaExceeded),
        (envelope(is_error=True, result="Not logged in · Please run /login"), "", Unauthorised),
        (envelope(is_error=True, result="It may not exist or you may not have access to it."), "", PermanentError),
        ("", "Error: socket hang up", TransientError),
    ],
    ids=["rate-limit", "usage-limit", "not-logged-in", "unknown-model", "other-non-zero-exit"],
)
def test_a_failed_call_maps_to_its_drain_category(stdout: str, stderr: str, category: type) -> None:
    """translation engine · quota, unauthorised, permanent and transient failures each raise their own category."""
    translator, _ = _translator(lambda _request: CliResult(1, stdout, stderr))

    with pytest.raises(TranslationEngineError) as raised:
        translator.translate(BATCH)

    assert type(raised.value) is category


def test_a_timeout_is_transient() -> None:
    """translation engine · a call that does not answer in time is a transient failure, so the batch is retried later."""

    def reply(_request: CliRequest) -> CliResult:
        raise CliTimeout("no answer within 240 seconds")

    translator, _ = _translator(reply)

    with pytest.raises(TransientError):
        translator.translate(BATCH)


def test_the_secret_is_redacted_from_an_error_message() -> None:
    """translation engine · an error that echoes an API key says the category, never the key."""
    translator, _ = _translator(
        lambda _request: CliResult(1, envelope(is_error=True, result=f"Not logged in ({SECRET})"), f"key {SECRET}")
    )

    with pytest.raises(Unauthorised) as raised:
        translator.translate(BATCH)

    assert SECRET not in str(raised.value) and SECRET not in repr(raised.value)


def test_the_registry_builds_the_engine_with_the_model_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """registry · claude-code is registered; CLAUDE_TRANSLATE_MODEL sets the model that the command carries."""
    monkeypatch.setenv("CLAUDE_TRANSLATE_MODEL", "claude-test-model")
    monkeypatch.setattr(f"{MODULE}.shutil.which", lambda _name: "/usr/local/bin/claude")
    cli = FakeCli(answered)
    monkeypatch.setattr(f"{MODULE}.run_subprocess", cli)

    engine = build_engine("claude-code", EngineConfig())
    engine.translate(BATCH)

    assert (engine.name, engine.usage_unit) == ("claude-code", "subscription")
    assert _argv_value(list(cli.requests[0].argv), "--model") == "claude-test-model"


def test_the_engine_refuses_to_start_without_the_claude_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """registry · without the claude command on PATH the engine cannot be built; the drain reports that before it claims."""
    monkeypatch.setattr(f"{MODULE}.shutil.which", lambda _name: None)

    with pytest.raises(ValueError, match="claude"):
        build_engine("claude-code", EngineConfig())


def test_claude_code_passes_every_conformance_check(caplog: pytest.LogCaptureFixture) -> None:
    """translation engine · the Claude Code adapter passes the shared adapter conformance suite."""
    contract.run_contract(ClaudeCodeHarness(), caplog)
