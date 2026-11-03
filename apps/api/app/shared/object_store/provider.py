"""Build the configured object store from settings; ``None`` when storage is not configured."""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, settings
from app.shared.object_store.errors import ObjectStoreUnavailableError
from app.shared.object_store.metered import MeteredObjectStore
from app.shared.object_store.port import ObjectStore, ObjectStoreMeter, noop_meter
from app.shared.object_store.s3 import S3ObjectStore
from app.shared.object_store.s3_client import S3Config


@lru_cache(maxsize=4)
def _shared_s3_store(config: S3Config) -> S3ObjectStore:
    """Reuse one boto3 client per distinct configuration; the metering wrapper stays per call."""
    return S3ObjectStore.from_config(config)


def s3_config_from_settings(app_settings: Settings) -> S3Config:
    """Map the object store settings to an S3Config; empty values become empty strings and region defaults to auto."""
    return S3Config(
        endpoint_url=app_settings.object_store_endpoint_url,
        region=app_settings.object_store_region or "auto",
        bucket=app_settings.object_store_bucket or "",
        access_key_id=app_settings.object_store_access_key_id or "",
        secret_access_key=app_settings.object_store_secret_access_key or "",
        force_path_style=app_settings.object_store_force_path_style,
    )


def build_object_store(app_settings: Settings, meter: ObjectStoreMeter = noop_meter) -> ObjectStore | None:
    """Return the metered S3 store for ``app_settings`` or ``None`` when storage is not configured."""
    if not app_settings.object_store_enabled:
        return None
    return MeteredObjectStore(_shared_s3_store(s3_config_from_settings(app_settings)), meter)


def get_object_store(meter: ObjectStoreMeter = noop_meter) -> ObjectStore | None:
    """Return the application's store, or ``None``; pass a ledger-backed ``meter`` to enforce caps."""
    return build_object_store(settings, meter)


def provide_object_store() -> ObjectStore | None:
    """Litestar dependency ``object_store``: the unmetered-by-default store, or ``None`` when not configured.

    Takes no arguments so it exposes no request parameters; routes that must enforce caps override the
    ``object_store`` dependency with a provider that calls :func:`get_object_store` with a real meter.
    """
    return get_object_store()


def require_store(store: ObjectStore | None) -> ObjectStore:
    """Return ``store`` or raise :class:`ObjectStoreUnavailableError` (HTTP 503) when it is ``None``."""
    if store is None:
        raise ObjectStoreUnavailableError("Object storage is not configured")
    return store


def require_object_store(meter: ObjectStoreMeter = noop_meter) -> ObjectStore:
    """Return the application's store or raise :class:`ObjectStoreUnavailableError` (HTTP 503)."""
    return require_store(get_object_store(meter))
