"""Tag consensus vocabulary (extraction chapter E1, loop D; merged into the SQL engine, chapter 1).

``axis_thresholds`` is the one place either consensus path reads its thresholds from (chapter 1, part B):
domain keeps the historical 2-procedure floor, situation relaxes to one (decision D2).
"""

from __future__ import annotations

import pytest
from app.config import settings
from app.features.discovery.tags import TagAxis, TagThresholds, axis_thresholds
from app.models.discovery import DiscoveryCandidateMention as Mention


def test_each_axis_points_at_its_own_mention_column() -> None:
    assert TagAxis.DOMAIN.column is Mention.domain_codes
    assert TagAxis.SITUATION.column is Mention.situation_codes


def test_domain_keeps_the_historical_two_procedure_floor_by_default() -> None:
    assert axis_thresholds(settings, TagAxis.DOMAIN) == TagThresholds(2, 0.5)


def test_situation_relaxes_to_one_procedure_by_default() -> None:
    assert axis_thresholds(settings, TagAxis.SITUATION) == TagThresholds(1, 0.5)


def test_each_axis_reads_its_own_settings_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "discovery_tag_min_procedures", 3)
    monkeypatch.setattr(settings, "discovery_tag_min_share", 0.9)
    monkeypatch.setattr(settings, "discovery_tag_min_procedures_situation", 1)
    monkeypatch.setattr(settings, "discovery_tag_min_share_situation", 0.1)

    assert axis_thresholds(settings, TagAxis.DOMAIN) == TagThresholds(3, 0.9)
    assert axis_thresholds(settings, TagAxis.SITUATION) == TagThresholds(1, 0.1)
