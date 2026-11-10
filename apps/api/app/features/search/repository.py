"""Reads and writes of the search text: candidate inputs, the upsert with tsvectors and keyset pages."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, Float, cast, func, select
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql.dml import ReturningInsert

from app.features.discovery.repository.base import SessionRepository
from app.features.search.text import TS_CONFIG_BY_LOCALE, BuiltText, MentionExcerpt
from app.models.discovery import DiscoveryCandidateMention, DiscoveryDocumentCandidate
from app.models.search import CandidateSearchText as SearchText


@dataclass(frozen=True, slots=True)
class LengthStats:
    """How many search texts a locale has and how long the median and the 95th percentile are, in characters."""

    rows: int
    p50: int
    p95: int


def _vector(config: str, text: str) -> ColumnElement[str]:
    """Return the SQL that builds the tsvector of ``text`` for the text-search ``config``, accents removed."""
    return func.to_tsvector(cast(config, REGCONFIG), func.unaccent(text))


def _upsert_statement(candidate_id: UUID, built: BuiltText) -> ReturningInsert[tuple[UUID]]:
    """Return the insert that updates the row only when its content hash differs, and returns the id it wrote."""
    values = {
        "text": built.text,
        "tsv_native": _vector(TS_CONFIG_BY_LOCALE[built.locale], built.text),
        "tsv_simple": _vector("simple", built.text),
        "content_hash": built.content_hash,
    }
    insert = pg_insert(SearchText).values(candidate_id=candidate_id, locale=built.locale, **values)
    return insert.on_conflict_do_update(
        index_elements=[SearchText.candidate_id, SearchText.locale],
        set_={**values, "updated_at": func.now()},
        where=SearchText.content_hash != built.content_hash,
    ).returning(SearchText.candidate_id)


class SearchTextRepository(SessionRepository):
    """Read candidate inputs and write ``candidate_search_text`` rows."""

    def candidate_titles(self, candidate_id: UUID) -> dict[str, str] | None:
        """Return the title map of the candidate, or ``None`` when it does not exist."""
        stmt = select(DiscoveryDocumentCandidate.title_i18n).where(DiscoveryDocumentCandidate.id == candidate_id)
        return self._session.scalar(stmt)

    def mention_excerpts(self, candidate_id: UUID) -> list[MentionExcerpt]:
        """Return the excerpt and score of every mention of the candidate."""
        mention = DiscoveryCandidateMention
        stmt = select(mention.id, mention.excerpt, mention.direct_category_confidence).where(
            mention.candidate_id == candidate_id
        )
        return [MentionExcerpt(*row) for row in self._session.execute(stmt).all()]

    def upsert_search_text(self, candidate_id: UUID, built: BuiltText) -> bool:
        """Write the row with its tsvectors; return ``False`` and leave the row untouched when the hash is unchanged."""
        return self._session.execute(_upsert_statement(candidate_id, built)).first() is not None

    def candidate_ids_after(self, after: UUID | None, limit: int) -> list[UUID]:
        """Return up to ``limit`` candidate ids greater than ``after``, ascending (keyset page)."""
        stmt = select(DiscoveryDocumentCandidate.id).order_by(DiscoveryDocumentCandidate.id).limit(limit)
        if after is not None:
            stmt = stmt.where(DiscoveryDocumentCandidate.id > after)
        return list(self._session.scalars(stmt))

    def text_length_stats(self, locale: str) -> LengthStats:
        """Return the row count and the p50 and p95 text length of ``locale``."""
        length = cast(func.length(SearchText.text), Float)
        stmt = select(
            func.count(),
            func.percentile_cont(0.5).within_group(length),
            func.percentile_cont(0.95).within_group(length),
        ).where(SearchText.locale == locale)
        rows, p50, p95 = self._session.execute(stmt).one()
        return LengthStats(rows, round(p50 or 0), round(p95 or 0))
