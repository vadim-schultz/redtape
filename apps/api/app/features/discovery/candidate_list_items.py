"""Rows of the admin candidate list: the response item of a row and the check of its taxonomy-code filters."""

from __future__ import annotations

from app.features.discovery.read_mappers import candidate_read
from app.features.discovery.repository.candidate_completeness import CandidateCompleteness
from app.features.discovery.repository.candidate_completeness_flags import FLAG_NAMES
from app.features.discovery.repository.candidate_filter_flags import CompletenessFilter
from app.features.discovery.repository.candidate_listing import CandidateListRow
from app.features.taxonomy.service import TaxonomyService
from app.models.discovery import DiscoveryMentionRole
from app.schema.candidate import CandidateFlags
from app.schema.discovery.read import CandidateListItemRead
from app.shared.list_query.errors import InvalidParam, raise_if_any


def list_item(row: CandidateListRow, done: CandidateCompleteness) -> CandidateListItemRead:
    """Return the response item of ``row`` with the completeness ``done`` of its candidate."""
    base = candidate_read(row.candidate, mention_count=row.mention_count)
    return CandidateListItemRead(
        **base.model_dump(),
        roles=[DiscoveryMentionRole(role) for role in row.roles],
        jurisdiction_name_i18n=row.jurisdiction_name_i18n,
        completeness=done.completeness,
        complete=done.complete,
        flags=CandidateFlags(**{name: getattr(done, name) for name in FLAG_NAMES}),
    )


def reject_unknown_codes(narrowing: CompletenessFilter, taxonomy: TaxonomyService) -> None:
    """Raise a validation error naming every code filter whose code is not in the taxonomy."""
    checks = (
        ("filter[domain]", narrowing.domain, taxonomy.known_domain_codes),
        ("filter[situation]", narrowing.situation, taxonomy.known_situation_codes),
    )
    unknown = [(key, code) for key, code, known in checks if code is not None and not known([code])]
    raise_if_any([InvalidParam(key, f"Unknown code: {code}") for key, code in unknown])
