"""Vendor-neutral object storage: the port, errors and adapters. Only this package imports boto3."""

from __future__ import annotations

from app.shared.object_store.errors import (
    ObjectNotFoundError,
    ObjectStoreError,
    ObjectStoreQuotaError,
    ObjectStoreUnavailableError,
)
from app.shared.object_store.memory import InMemoryObjectStore
from app.shared.object_store.metered import MeteredObjectStore
from app.shared.object_store.port import (
    PRESIGN_TTL_SECONDS,
    ObjectStore,
    ObjectStoreMeter,
    OperationClass,
    noop_meter,
)
from app.shared.object_store.s3 import S3ObjectStore
from app.shared.object_store.s3_client import CHECKSUM_MODES, ChecksumMode, S3Config, create_s3_client

__all__ = [
    "CHECKSUM_MODES",
    "PRESIGN_TTL_SECONDS",
    "ChecksumMode",
    "InMemoryObjectStore",
    "MeteredObjectStore",
    "ObjectNotFoundError",
    "ObjectStore",
    "ObjectStoreError",
    "ObjectStoreMeter",
    "ObjectStoreQuotaError",
    "ObjectStoreUnavailableError",
    "OperationClass",
    "S3Config",
    "S3ObjectStore",
    "create_s3_client",
    "noop_meter",
]
