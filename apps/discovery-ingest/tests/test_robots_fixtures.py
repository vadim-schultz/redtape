"""The real robots.txt files of four hosts, captured 2026-10-28, give the verdicts their sites mean."""

from __future__ import annotations

from pathlib import Path

import pytest
from discovery_ingest.config import BOT_PRODUCT_TOKEN
from discovery_ingest.worker.robots_rules import RobotsRules

FIXTURES = Path(__file__).parent / "fixtures" / "robots"

FUEHRUNGSZEUGNIS = "www.fuehrungszeugnis.bund.de"
DIPUL = "www.dipul.de"
DPMA = "register.dpma.de"
BAFIN = "www.bafin.de"

# (host, path, allowed)
VERDICTS = [
    (FUEHRUNGSZEUGNIS, "/", True),
    (FUEHRUNGSZEUGNIS, "/anything-else", False),
    (DIPUL, "/", False),
    (DIPUL, "/anything", False),
    (DIPUL, "/robots.txt", True),
    (DPMA, "/", False),
    (DPMA, "/DPMAregister/Uebersicht", True),
    (DPMA, "/DPMAregister/other", False),
    (BAFIN, "/", True),
    (BAFIN, "/DE/Service", True),
    (BAFIN, "/DE/_pgb/x", False),
    (BAFIN, "/Login/x", False),
    (BAFIN, "/SiteGlobals/Modules/x", True),
    (BAFIN, "/SiteGlobals/Other/x", False),
]


def _rules(host: str) -> RobotsRules:
    lines = (FIXTURES / f"{host}.txt").read_text(encoding="utf-8").splitlines()
    return RobotsRules.parse(lines, BOT_PRODUCT_TOKEN)


@pytest.mark.parametrize(("host", "path", "expected"), VERDICTS, ids=[f"{h}{p}" for h, p, _ in VERDICTS])
def test_a_real_robots_file_yields_the_verdict_its_site_means(host: str, path: str, expected: bool) -> None:
    """Each host's real file allows what it explicitly allows and blocks the rest; dipul.de stays blocked."""
    assert _rules(host).allowed(f"https://{host}{path}") is expected
