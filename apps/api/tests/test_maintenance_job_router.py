"""Tests for the platform maintenance job calendar router."""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ROUTER_PATH = _REPO_ROOT / "scripts" / "maintenance_job_router.py"


def _load_router() -> object:
    spec = importlib.util.spec_from_file_location("maintenance_job_router", _ROUTER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


router = _load_router()
resolve_maintenance_job = router.resolve_maintenance_job
DEFAULT_ANCHOR = router.DEFAULT_MAINTENANCE_ANCHOR_DATE


def test_maintenance_router_day_0_selects_openplz() -> None:
    """On anchor day (days % 6 == 0) the scheduled job is OpenPLZ import."""

    assert resolve_maintenance_job(date(2026, 1, 1), DEFAULT_ANCHOR, None) == "openplz"


def test_maintenance_router_day_3_selects_discovery() -> None:
    """Three days after anchor (days % 6 == 3) the scheduled job is discovery."""

    assert resolve_maintenance_job(date(2026, 1, 4), DEFAULT_ANCHOR, None) == "discovery"


def test_maintenance_router_day_1_selects_skip() -> None:
    """Off-cycle days (e.g. days % 6 == 1) succeed without running a heavy job."""

    assert resolve_maintenance_job(date(2026, 1, 2), DEFAULT_ANCHOR, None) == "skip"


def test_maintenance_router_dispatch_override_forces_discovery() -> None:
    """workflow_dispatch job input overrides the calendar when set."""

    assert resolve_maintenance_job(date(2026, 1, 1), DEFAULT_ANCHOR, "discovery") == "discovery"
