from __future__ import annotations

import argparse
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.db import SessionLocal
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locality import Locality
from app.schema.openplz import (
    OpenPLZDistrict,
    OpenPLZFederalState,
    OpenPLZLocality,
    OpenPLZMunicipality,
)
from app.services.openplz_client import OpenPLZClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "redtape-openplz")


def _stable_uuid(key: str) -> uuid.UUID:
    # Deterministic UUID so re-runs are idempotent.
    return uuid.uuid5(UUID_NAMESPACE, key)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _municipality_roles(type_str: str | None) -> list[str]:
    # "Kreisfreie Stadt" / "Stadtkreis" behave like both district + municipality.
    roles = ["MUNICIPALITY"]
    if type_str and ("Kreisfreie" in type_str or "Stadtkreis" in type_str):
        roles.append("DISTRICT")
    return roles


def upsert_jurisdiction(
    session,
    *,
    jurisdiction_id: uuid.UUID,
    kind: JurisdictionKind,
    geographic_parent_id: uuid.UUID | None,
    code: str,
    openplz_type: str | None,
    name_de: str,
    administrative_roles: list[str],
    postal_code: str | None = None,
    multiple_postal_codes: bool = False,
    touched_at: datetime,
) -> Jurisdiction:
    existing = session.execute(
        select(Jurisdiction).where(
            Jurisdiction.geographic_parent_id == geographic_parent_id,
            Jurisdiction.code == code,
        )
    ).scalar_one_or_none()

    if existing is None:
        return _insert_jurisdiction(
            session,
            jurisdiction_id=jurisdiction_id,
            kind=kind,
            geographic_parent_id=geographic_parent_id,
            code=code,
            openplz_type=openplz_type,
            name_de=name_de,
            administrative_roles=administrative_roles,
            postal_code=postal_code,
            multiple_postal_codes=multiple_postal_codes,
            touched_at=touched_at,
        )

    return _update_jurisdiction(
        existing,
        kind=kind,
        openplz_type=openplz_type,
        postal_code=postal_code,
        multiple_postal_codes=multiple_postal_codes,
        administrative_roles=administrative_roles,
        name_de=name_de,
        touched_at=touched_at,
    )


def _insert_jurisdiction(
    session,
    *,
    jurisdiction_id: uuid.UUID,
    kind: JurisdictionKind,
    geographic_parent_id: uuid.UUID | None,
    code: str,
    openplz_type: str | None,
    name_de: str,
    administrative_roles: list[str],
    postal_code: str | None,
    multiple_postal_codes: bool,
    touched_at: datetime,
) -> Jurisdiction:
    obj = Jurisdiction(
        id=jurisdiction_id,
        kind=kind,
        geographic_parent_id=geographic_parent_id,
        code=code,
        openplz_type=openplz_type,
        postal_code=postal_code,
        multiple_postal_codes=multiple_postal_codes,
        administrative_roles=administrative_roles,
        name_i18n={"de": name_de, "en": name_de},
        last_updated=touched_at.replace(tzinfo=None),
    )
    session.add(obj)
    return obj


def _update_jurisdiction(
    existing: Jurisdiction,
    *,
    kind: JurisdictionKind,
    openplz_type: str | None,
    postal_code: str | None,
    multiple_postal_codes: bool,
    administrative_roles: list[str],
    name_de: str,
    touched_at: datetime,
) -> Jurisdiction:
    # Update fields (idempotent re-import).
    existing.kind = kind
    existing.openplz_type = openplz_type
    existing.postal_code = postal_code
    existing.multiple_postal_codes = multiple_postal_codes
    existing.administrative_roles = administrative_roles
    existing.name_i18n = {"de": name_de, "en": name_de}
    existing.last_updated = touched_at.replace(tzinfo=None)
    return existing


def upsert_locality(
    session,
    *,
    locality_id: uuid.UUID,
    municipality_id: uuid.UUID,
    postal_code: str,
    name: str,
    touched_at: datetime,
) -> Locality:
    existing = session.execute(
        select(Locality).where(
            Locality.municipality_id == municipality_id,
            Locality.postal_code == postal_code,
            Locality.name == name,
        )
    ).scalar_one_or_none()

    if existing is None:
        return _insert_locality(
            session,
            locality_id=locality_id,
            municipality_id=municipality_id,
            postal_code=postal_code,
            name=name,
            touched_at=touched_at,
        )

    return _update_locality(
        existing,
        name=name,
        touched_at=touched_at,
    )


def _insert_locality(
    session,
    *,
    locality_id: uuid.UUID,
    municipality_id: uuid.UUID,
    postal_code: str,
    name: str,
    touched_at: datetime,
) -> Locality:
    obj = Locality(
        id=locality_id,
        municipality_id=municipality_id,
        postal_code=postal_code,
        name=name,
        name_i18n={"de": name, "en": name},
        last_updated=touched_at.replace(tzinfo=None),
    )
    session.add(obj)
    return obj


def _update_locality(
    existing: Locality,
    *,
    name: str,
    touched_at: datetime,
) -> Locality:
    existing.name_i18n = {"de": name, "en": name}
    existing.last_updated = touched_at.replace(tzinfo=None)
    return existing


@dataclass
class _ImportStats:
    processed: int = 0


class _OpenPLZLocationsDbOps:
    """Database operations for the import script (session + upserts + commits)."""

    def __init__(
        self,
        *,
        session,
        touched_at: datetime,
        dry_run: bool,
        commit_every: int,
    ) -> None:
        self._session = session
        self._touched_at = touched_at
        self._dry_run = dry_run
        self._commit_every = commit_every

    def upsert_jurisdiction(self, **kwargs) -> Jurisdiction:
        return upsert_jurisdiction(
            self._session,
            touched_at=self._touched_at,
            **kwargs,
        )

    def upsert_locality(self, **kwargs) -> Locality:
        return upsert_locality(
            self._session,
            touched_at=self._touched_at,
            **kwargs,
        )

    def maybe_commit(self, stats: _ImportStats) -> None:
        if self._dry_run:
            return
        if self._commit_every <= 0:
            return
        if stats.processed % self._commit_every == 0:
            self._session.commit()

    def finish(self) -> None:
        if self._dry_run:
            self._session.rollback()
        else:
            self._session.commit()

    def close(self) -> None:
        self._session.close()


class OpenPLZLocationsImporter:
    """Import orchestration: fetch + iterate OpenPLZ; delegate persistence to DbOps."""

    def __init__(
        self,
        *,
        language: str,
        dry_run: bool,
        commit_every: int,
        rate_limit_rps: float = 10.0,
    ) -> None:
        self._client = OpenPLZClient(language=language, rate_limit_rps=rate_limit_rps)
        self._touched_at = _utc_now()
        self._session = SessionLocal()
        self._db = _OpenPLZLocationsDbOps(
            session=self._session,
            touched_at=self._touched_at,
            dry_run=dry_run,
            commit_every=commit_every,
        )
        self._dry_run = dry_run
        self._stats = _ImportStats()
        self._country_id: uuid.UUID | None = None
        # Maps OpenPLZ municipality key -> DB id.
        # We can't rely solely on deterministic UUIDs if the DB already contains
        # partially-imported rows created by earlier runs with mismatched ids.
        self._municipality_id_by_code: dict[str, uuid.UUID] = {}

    def import_all(self) -> None:
        try:
            self._import_country()
            self._import_states()
            self._db.finish()
        finally:
            self._db.close()

    def _bump_and_maybe_commit(self) -> None:
        self._stats.processed += 1
        self._db.maybe_commit(self._stats)

    def _import_country(self) -> None:
        country_code = "DE"
        try:
            country = self._db.upsert_jurisdiction(
                jurisdiction_id=_stable_uuid(f"jurisdiction:COUNTRY:{country_code}"),
                kind=JurisdictionKind.COUNTRY,
                geographic_parent_id=None,
                code=country_code,
                openplz_type="Country",
                name_de="Deutschland",
                administrative_roles=["COUNTRY"],
                postal_code=None,
                multiple_postal_codes=False,
            )
        except IntegrityError as e:
            raise RuntimeError(f"Failed to upsert COUNTRY {country_code}: {e}") from e
        # Ensure the parent jurisdiction exists before inserting regions.
        # Otherwise, batched flushes can violate FK constraints.
        self._session.flush()
        self._bump_and_maybe_commit()
        self._country_id = country.id
        parent_exists = self._session.execute(
            select(Jurisdiction.id).where(Jurisdiction.id == self._country_id)
        ).scalar_one_or_none()
        if parent_exists is None:
            raise RuntimeError(f"Country parent not found after upsert: {self._country_id}")

    def _import_states(self) -> None:
        states_payload = self._client.get_json("FederalStates") or []
        for state in [OpenPLZFederalState.model_validate(item) for item in states_payload]:
            self._import_state(state)

    def _import_state(self, state: OpenPLZFederalState) -> None:
        state_code = state.key
        if self._country_id is None:
            raise RuntimeError("Country parent id is not set.")

        try:
            state = self._db.upsert_jurisdiction(
                jurisdiction_id=_stable_uuid(f"jurisdiction:REGION:{state_code}"),
                kind=JurisdictionKind.REGION,
                geographic_parent_id=self._country_id,
                code=state_code,
                openplz_type=None,
                name_de=state.name,
                administrative_roles=["REGION"],
                postal_code=None,
                multiple_postal_codes=False,
            )
        except IntegrityError as e:
            raise RuntimeError(
                "Failed to upsert REGION "
                f"code={state_code!r} expected_parent_country_id={self._country_id} "
                f"(kind={JurisdictionKind.COUNTRY.value}) error={e}"
            ) from e
        # Ensure the parent jurisdiction exists before inserting districts.
        self._session.flush()
        self._bump_and_maybe_commit()
        state_id = state.id
        self._import_districts_for_state(state_code=state_code, state_id=state_id)

    def _import_districts_for_state(self, *, state_code: str, state_id: uuid.UUID) -> None:
        districts_endpoint = f"FederalStates/{state_code}/Districts"
        for district_item in self._client.iter_paged(endpoint=districts_endpoint, page_size=50):
            district = OpenPLZDistrict.model_validate(district_item)
            district_code = district.key
            try:
                district = self._db.upsert_jurisdiction(
                    jurisdiction_id=_stable_uuid(f"jurisdiction:REGION:{district_code}"),
                    kind=JurisdictionKind.REGION,
                    geographic_parent_id=state_id,
                    code=district_code,
                    openplz_type=district.type,
                    name_de=district.name,
                    administrative_roles=["DISTRICT"],
                    postal_code=None,
                    multiple_postal_codes=False,
                )
            except IntegrityError as e:
                raise RuntimeError(
                    f"Failed to upsert DISTRICT region code={district_code!r} "
                    f"expected_parent_state_id={state_id} error={e}"
                ) from e
            # Ensure the district exists before inserting its municipalities.
            self._session.flush()
            self._bump_and_maybe_commit()
            district_id = district.id

            self._import_municipalities_for_district(
                district_code=district_code,
                district_id=district_id,
            )

    def _import_municipalities_for_district(self, *, district_code: str, district_id: uuid.UUID) -> None:
        municipalities_endpoint = f"Districts/{district_code}/Municipalities"
        for muni_item in self._client.iter_paged(endpoint=municipalities_endpoint, page_size=50):
            muni = OpenPLZMunicipality.model_validate(muni_item)
            muni_code = muni.key
            try:
                muni = self._db.upsert_jurisdiction(
                    jurisdiction_id=_stable_uuid(f"jurisdiction:MUNICIPALITY:{muni_code}"),
                    kind=JurisdictionKind.MUNICIPALITY,
                    geographic_parent_id=district_id,
                    code=muni_code,
                    openplz_type=muni.type,
                    name_de=muni.name,
                    administrative_roles=_municipality_roles(muni.type),
                    postal_code=muni.postal_code,
                    multiple_postal_codes=muni.multiple_postal_codes,
                )
            except IntegrityError as e:
                raise RuntimeError(
                    f"Failed to upsert MUNICIPALITY code={muni_code!r} "
                    f"expected_parent_district_id={district_id} error={e}"
                ) from e
            muni_id = muni.id
            self._municipality_id_by_code[muni_code] = muni_id
            self._bump_and_maybe_commit()

        # Ensure all municipalities exist before inserting localities.
        self._session.flush()
        self._import_localities_for_district(district_code=district_code)

    def _import_localities_for_district(self, *, district_code: str) -> None:
        localities_endpoint = f"Districts/{district_code}/Localities"
        for loc_item in self._client.iter_paged(endpoint=localities_endpoint, page_size=50):
            loc = OpenPLZLocality.model_validate(loc_item)
            if not loc.postal_code:
                continue

            muni_ref = loc.municipality
            if muni_ref is None:
                continue

            muni_code = muni_ref.key
            muni_id = self._municipality_id_by_code.get(
                muni_code, _stable_uuid(f"jurisdiction:MUNICIPALITY:{muni_code}")
            )
            loc_id = _stable_uuid(f"locality:{muni_code}:{loc.postal_code}:{loc.name}")

            self._db.upsert_locality(
                locality_id=loc_id,
                municipality_id=muni_id,
                postal_code=loc.postal_code,
                name=loc.name,
            )
            self._bump_and_maybe_commit()


def import_locations(language: str, *, dry_run: bool = False, commit_every: int = 1000) -> None:
    OpenPLZLocationsImporter(
        language=language,
        dry_run=dry_run,
        commit_every=commit_every,
        rate_limit_rps=10.0,
    ).import_all()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import OpenPLZ locations into Postgres.")
    parser.add_argument("--language", default="de", help="OpenPLZ language (default: de)")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no DB commit")
    parser.add_argument("--commit-every", type=int, default=1000, help="Commit batch size")
    args = parser.parse_args()

    import_locations(args.language, dry_run=args.dry_run, commit_every=args.commit_every)


if __name__ == "__main__":
    main()
