"""Tag consensus vocabulary (extraction chapter E1, loop D; merged into the SQL engine, chapter 1)."""

from __future__ import annotations

from app.features.discovery.tags import TagAxis
from app.models.discovery import DiscoveryCandidateMention as Mention


def test_each_axis_points_at_its_own_mention_column() -> None:
    assert TagAxis.DOMAIN.column is Mention.domain_codes
    assert TagAxis.SITUATION.column is Mention.situation_codes
