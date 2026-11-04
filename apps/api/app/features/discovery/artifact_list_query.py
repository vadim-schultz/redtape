"""Query provider for the machine artifact listing."""

from __future__ import annotations

from litestar.params import Parameter

from app.features.discovery.list_query import DiscoveryListQuery
from app.features.discovery.repository import ArtifactFilter, Page
from app.models.discovery import DiscoveryArtifactKind
from app.shared.paging import PageParams


def provide_artifact_query(
    page: PageParams,
    kind: DiscoveryArtifactKind | None = Parameter(query="kind", default=None),
    host: str | None = Parameter(query="host", default=None, min_length=1, max_length=253),
) -> DiscoveryListQuery[ArtifactFilter]:
    """Collect the artifact list parameters into one filter and page."""
    artifact_filter = ArtifactFilter(kind=kind, host=host)
    return DiscoveryListQuery(filters=artifact_filter, page=Page(page.offset, page.limit))
