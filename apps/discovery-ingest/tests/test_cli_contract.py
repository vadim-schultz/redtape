"""The command line contract: the 30 commands, their flags, defaults, help and usage errors.

The rows live in ``cli_contract.py`` and are compared with the live CLI through ``cli_adapters.py``. The
usage-error tests accept a ``SystemExit`` or a returned code, so they hold for the argparse CLI and its Typer
successor alike.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from discovery_ingest.cli import main

from cli_adapters import describe, groups
from cli_contract import COMMANDS, GROUPS, CommandSpec, OptionSpec

SAMPLE_UUID = "00000000-0000-0000-0000-000000000001"
GOLDEN_HELP = Path(__file__).parent / "golden" / "help"
HELP_PATHS: list[tuple[str, ...]] = [(), *[(group,) for group in GROUPS], *[spec.path for spec in COMMANDS]]
CUSTOM_SAMPLES = {"--keys": "12345678901234", "--minutes": "5", "--limit": "1"}


def run_cli(argv: list[str]) -> int:
    """Run the CLI in process and return its exit code, whether it returns the code or raises ``SystemExit``."""
    try:
        return main(argv)
    except SystemExit as err:
        return err.code if isinstance(err.code, int) else 0


def _by_path() -> dict[tuple[str, str], CommandSpec]:
    return {spec.path: spec for spec in describe()}


def _option(path: tuple[str, str], flag: str) -> OptionSpec:
    (match,) = [option for option in _by_path()[path].options if flag in option.flags]
    return match


def _sample(option: OptionSpec) -> str:
    if option.choices:
        return option.choices[0]
    if option.kind == "uuid":
        return SAMPLE_UUID
    if option.kind in ("int", "float"):
        return "1" if option.kind == "int" else "1.0"
    if option.kind == "custom":
        return CUSTOM_SAMPLES[option.flags[0]]
    return "x"


def _argv_without(spec: CommandSpec, skipped_flag: str) -> list[str]:
    """Build the required part of a command line, leaving out one required flag."""
    argv = [spec.group, spec.name]
    for option in spec.options:
        if option.required and skipped_flag not in option.flags:
            argv += [option.flags[0], _sample(option)]
    return argv


def test_the_command_set_is_exactly_the_twenty_eight_documented_commands() -> None:
    assert [spec.path for spec in describe()] == [spec.path for spec in COMMANDS]
    assert len(describe()) == 30


def test_the_root_registers_the_fifteen_groups_in_order() -> None:
    assert groups() == list(GROUPS)


@pytest.mark.parametrize("spec", COMMANDS, ids=lambda spec: f"{spec.group} {spec.name}")
def test_every_command_matches_its_contract_row(spec: CommandSpec) -> None:
    actual = _by_path()[spec.path]
    assert {option.flags for option in actual.options} == {option.flags for option in spec.options}
    for expected in spec.options:
        found = next(option for option in actual.options if option.flags == expected.flags)
        assert found == expected, f"{' '.join(spec.path)} {expected.flags[0]}"


def test_defaults_match_the_contract() -> None:
    assert _option(("llm", "eval"), "--prompt-version").default == "ext-6"
    assert _option(("worker", "drain"), "--browser-budget-seconds").default == 570.0
    assert _option(("worker", "drain"), "--max-batches").default == 1
    assert _option(("govdata", "fetch"), "--max-pages").default == 150
    assert _option(("candidates", "emit"), "--limit").default == 10
    assert _option(("candidates", "emit"), "--min-mentions").default == 0
    assert _option(("llm", "requeue"), "--limit").default == 50
    assert _option(("capture", "requeue"), "--limit").default == 50
    assert _option(("artifacts", "list"), "--limit").default == 20
    assert _option(("artifacts", "list"), "--kind").default == "html_snapshot"
    assert _option(("llm", "eval"), "--neuron-budget").default == 4000.0
    assert _option(("llm", "probe"), "--max-neurons").default == 900.0
    assert _option(("browser", "probe"), "--max-browser-seconds").default == 240.0
    assert _option(("candidates", "curate"), "--check-pages").default is True


def test_kinds_default_is_the_worker_default_kinds() -> None:
    kinds = _option(("worker", "drain"), "--kinds").default
    assert kinds == "fetch_url,enrich_metadata,harvest_payload,extract_page"


@pytest.mark.parametrize(
    "spec",
    [spec for spec in COMMANDS if any(option.required for option in spec.options)],
    ids=lambda spec: f"{spec.group} {spec.name}",
)
def test_missing_required_flag_exits_2(spec: CommandSpec) -> None:
    for option in spec.options:
        if option.required:
            assert run_cli(_argv_without(spec, option.flags[0])) == 2, option.flags[0]


def test_unknown_flag_exits_2() -> None:
    assert run_cli(["budget", "show", "--no-such-flag"]) == 2


@pytest.mark.parametrize("argv", [["nope"], ["budget", "nope"], ["candidates", "nope"]])
def test_unknown_command_exits_2(argv: list[str]) -> None:
    assert run_cli(argv) == 2


_TWENTY_ONE_SERVICE_IDS = [arg for _ in range(21) for arg in ("--service-id", SAMPLE_UUID)]


@pytest.mark.parametrize(
    "argv",
    [
        ["worker", "drain", "--max-tasks", "x"],
        ["worker", "drain", "--kinds", "nope"],
        ["worker", "drain", "--max-batches", "x"],
        ["budget", "show", "--resource", "nope"],
        ["budget", "show", "--require-remaining", "actions_minutes"],
        ["budget", "show", "--require-remaining", "x=1"],
        ["budget", "report-minutes", "--minutes", "0"],
        ["llm", "requeue", "--limit", "0"],
        ["llm", "requeue", "--limit", "201"],
        ["capture", "requeue", "--limit", "0"],
        ["capture", "requeue", "--limit", "201"],
        ["capture", "requeue", *_TWENTY_ONE_SERVICE_IDS],
        ["fim", "probe", "--keys", "123"],
        ["browser", "probe", "--variant", "nope"],
        ["artifacts", "list", "--host", "x", "--kind", "nope"],
        ["artifacts", "list", "--host", "x", "--limit", "0"],
        ["govdata", "run", "--input", "x", "--jurisdiction-id", "nope"],
    ],
    ids=lambda argv: " ".join(argv[:4]),
)
def test_invalid_values_exit_2(argv: list[str]) -> None:
    assert run_cli(argv) == 2


def test_emit_needs_exactly_one_of_id_or_all_staged() -> None:
    assert run_cli(["candidates", "emit"]) == 2
    assert run_cli(["candidates", "emit", "--id", SAMPLE_UUID, "--all-staged"]) == 2


@pytest.mark.parametrize("path", [(), *[(group,) for group in GROUPS]], ids=lambda path: " ".join(path) or "root")
def test_no_command_prints_help_and_exits_2(path: tuple[str, ...], capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(list(path)) == 2
    assert "usage:" in capsys.readouterr().out.lower()


@pytest.mark.parametrize("spec", COMMANDS, ids=lambda spec: f"{spec.group} {spec.name}")
def test_help_exits_0_for_every_command(spec: CommandSpec, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli([spec.group, spec.name, "--help"]) == 0
    assert "usage:" in capsys.readouterr().out.lower()


def _option_sentences(golden: str) -> list[str]:
    """Return the help sentence of every option in an argparse golden, with its continuation lines joined."""
    sentences: list[str] = []
    current: list[str] | None = None
    for line in golden.splitlines():
        if line.startswith("  -"):
            if current:
                sentences.append(" ".join(current))
            parts = re.split(r"\s{2,}", line.strip(), maxsplit=1)
            current = [parts[1]] if len(parts) == 2 else []
        elif current is not None and line.startswith(" " * 8) and line.strip():
            current.append(line.strip())
        else:
            if current:
                sentences.append(" ".join(current))
            current = None
    if current:
        sentences.append(" ".join(current))
    return [sentence for sentence in sentences if sentence and not sentence.startswith("show this")]


@pytest.mark.parametrize("path", HELP_PATHS, ids=lambda path: " ".join(path) or "root")
def test_help_keeps_every_flag_and_help_sentence(
    path: tuple[str, ...], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every flag and every option help sentence of the argparse golden appears in the help, ignoring whitespace."""
    monkeypatch.setenv("COLUMNS", "100")
    assert run_cli([*path, "--help"]) == 0
    golden = (GOLDEN_HELP / f"{'-'.join(path) or 'root'}.txt").read_text(encoding="utf-8")
    shown = re.sub(r"\s+", "", capsys.readouterr().out).lower()
    for flag in sorted(set(re.findall(r"--[a-z][a-z-]*", golden))):
        assert flag in shown, flag
    for sentence in _option_sentences(golden):
        assert re.sub(r"\s+", "", sentence).lower() in shown, sentence


def test_the_curate_help_keeps_the_reversal_epilog(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(["candidates", "curate", "--help"]) == 0
    assert "DELETE FROM discovery_candidate_edge WHERE extractor = 'manual';" in capsys.readouterr().out
