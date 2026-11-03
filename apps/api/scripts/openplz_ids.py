"""Deterministic UUID derivation shared by the OpenPLZ import and cleanup scripts.

`scripts/import_openplz_locations.py` and `scripts/cleanup_openplz_data.py` each
need to compute the same id for the same OpenPLZ row: the importer so re-runs
are idempotent, the cleanup script so it can recognise OpenPLZ-derived rows by
id. Before this module they each kept their own copy of the namespace and the
key format, so a typo in one place would silently orphan rows.

The key strings below must never change: the ids they produce are persisted in
the `jurisdiction` and `locality` tables.
"""

from __future__ import annotations

import uuid

UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "redtape-openplz")


def stable_uuid(key: str) -> uuid.UUID:
    """Derive a deterministic UUID from `key` so re-runs are idempotent."""
    return uuid.uuid5(UUID_NAMESPACE, key)


def country_id(code: str) -> uuid.UUID:
    """Derive the id of the COUNTRY jurisdiction with this OpenPLZ code."""
    return stable_uuid(f"jurisdiction:COUNTRY:{code}")


def region_id(code: str) -> uuid.UUID:
    """Derive the id of the REGION jurisdiction with this OpenPLZ code.

    OpenPLZ federal states and districts are both stored as `kind=REGION`, so
    this one function covers both.
    """
    return stable_uuid(f"jurisdiction:REGION:{code}")


def municipality_id(code: str) -> uuid.UUID:
    """Derive the id of the MUNICIPALITY jurisdiction with this OpenPLZ code."""
    return stable_uuid(f"jurisdiction:MUNICIPALITY:{code}")


def locality_id(municipality_code: str, postal_code: str, name: str) -> uuid.UUID:
    """Derive the id of the locality row for this municipality, postal code and name."""
    return stable_uuid(f"locality:{municipality_code}:{postal_code}:{name}")
