"""The llm concurrency option: 1 to 8 for llm_extract, refused outside that range before anything is claimed (chapter 5, loop C)."""

from __future__ import annotations

import pytest
from discovery_ingest.cli import main
from discovery_ingest.operations.drain import DrainOptions

LLM_OPTIONS = {"kinds": ("llm_extract",), "neuron_budget": 800.0}


@pytest.mark.parametrize("value", [0, 9])
def test_the_concurrency_option_is_rejected_below_1_and_above_8(value: int) -> None:
    """worker drain options · negative: 0 and 9 fail when the policy is built, and the message names the bound."""
    with pytest.raises(ValueError, match="concurrency must be between 1 and 8"):
        DrainOptions(**LLM_OPTIONS, concurrency=value).policy()


@pytest.mark.parametrize("value", [1, 3, 8])
def test_the_concurrency_option_accepts_1_to_8_for_llm_extract(value: int) -> None:
    """worker drain options · happy: 1, 3 and 8 build a policy that carries the value."""
    assert DrainOptions(**LLM_OPTIONS, concurrency=value).policy().concurrency == value


def test_concurrency_above_one_is_refused_when_the_drain_claims_other_kinds() -> None:
    """worker drain options · negative: concurrency 3 with the default kinds is refused; the pool is for llm_extract only."""
    with pytest.raises(ValueError, match="llm_extract as the only kind"):
        DrainOptions(concurrency=3).policy()


def test_the_cli_refuses_a_concurrency_of_nine_before_it_claims(capsys: pytest.CaptureFixture[str]) -> None:
    """worker drain CLI · negative: --concurrency 9 is a usage error (exit 2) and no machine API call is made."""
    code = main(["worker", "drain", "--kinds", "llm_extract", "--neuron-budget", "800", "--concurrency", "9"])

    assert code == 2
    assert "concurrency" in capsys.readouterr().err
