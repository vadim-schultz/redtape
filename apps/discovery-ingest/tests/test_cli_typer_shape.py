"""The Typer shape of the CLI: groups, the lazy context, the one error handler, and main(argv)."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer
from discovery_ingest.cli import main
from discovery_ingest.cli.errors import handles_api_errors
from discovery_ingest.client import DiscoveryMachineApiError

from cli_adapters import groups
from cli_contract import GROUPS

CLI_PACKAGE = Path(__file__).resolve().parents[1] / "discovery_ingest" / "cli"


def test_root_app_registers_the_sixteen_groups_in_order() -> None:
    assert groups() == list(GROUPS)


@pytest.mark.parametrize("group", GROUPS)
def test_group_without_subcommand_exits_2_and_prints_group_help(group: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([group]) == 2
    out = capsys.readouterr().out
    assert f"Usage: discovery_ingest {group} [OPTIONS] COMMAND" in out


def test_ctx_obj_is_lazy_and_probes_need_no_api_settings(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Neither --help nor the probes read DISCOVERY_API_URL or DISCOVERY_API_KEY."""

    def no_settings_read(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the ingest settings were read")

    monkeypatch.setattr("discovery_ingest.cli.context.load_ingest_settings", no_settings_read)
    monkeypatch.setattr("discovery_ingest.operations.probes.probe_keys", lambda *_args: [])
    monkeypatch.setattr("discovery_ingest.operations.probes.probe_lines", lambda _results: [])
    monkeypatch.setattr("discovery_ingest.operations.probes.gate_passed", lambda _results: True)
    monkeypatch.delenv("DISCOVERY_API_URL", raising=False)
    monkeypatch.delenv("DISCOVERY_API_KEY", raising=False)

    assert main(["--help"]) == 0
    assert main(["budget", "--help"]) == 0
    assert main(["fim", "probe", "--keys", "99154021000000"]) == 0
    capsys.readouterr()


def test_api_refusal_prints_label_and_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    @handles_api_errors("fim")
    def refused() -> None:
        raise DiscoveryMachineApiError(422, "refused")

    with pytest.raises(typer.Exit) as stop:
        refused()

    assert stop.value.exit_code == 1
    assert capsys.readouterr().err == "fim command failed: discovery machine API 422: refused\n"


def test_api_refusal_without_a_label_prints_only_the_refusal(capsys: pytest.CaptureFixture[str]) -> None:
    @handles_api_errors(None)
    def refused() -> None:
        raise DiscoveryMachineApiError(500, "boom")

    with pytest.raises(typer.Exit):
        refused()

    assert capsys.readouterr().err == "discovery machine API 500: boom\n"


def test_main_returns_the_code_and_never_raises_systemexit(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    assert main([]) == 2
    assert main(["budget", "nope"]) == 2
    capsys.readouterr()


@pytest.mark.parametrize("flag", ["--install-completion", "--show-completion"])
def test_completion_options_are_not_exposed(flag: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([flag]) == 2
    capsys.readouterr()


def test_cli_package_imports_no_argparse() -> None:
    for path in CLI_PACKAGE.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "import argparse" not in text and "from argparse" not in text, path
