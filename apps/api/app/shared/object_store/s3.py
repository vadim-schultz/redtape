"""``ObjectStore`` adapter over any S3-compatible endpoint (Cloudflare R2 first)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Self

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.shared.object_store.errors import ObjectNotFoundError, ObjectStoreUnavailableError
from app.shared.object_store.port import PRESIGN_TTL_SECONDS, content_disposition
from app.shared.object_store.s3_client import S3Config, create_s3_client

_MISSING_KEY_CODES = frozenset({"NoSuchKey", "404", "NotFound"})


@contextmanager
def _translated_errors(key: str) -> Iterator[None]:
    """Map a missing key to :class:`ObjectNotFoundError` and any other boto failure to unavailable."""
    try:
        yield
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in _MISSING_KEY_CODES:
            raise ObjectNotFoundError(key) from exc
        raise ObjectStoreUnavailableError(f"Object store refused the call ({code or 'ClientError'})") from exc
    except BotoCoreError as exc:
        raise ObjectStoreUnavailableError(f"Object store unreachable ({type(exc).__name__})") from exc


class S3ObjectStore:
    """Store objects in one bucket using put, get, head, delete and presigned GET only.

    No ACLs, versioning, tagging, list or Content-MD5 are used.
    """

    def __init__(self, client: BaseClient, bucket: str) -> None:
        """Wrap an already configured ``client`` for ``bucket``."""
        self._client = client
        self._bucket = bucket

    @classmethod
    def from_config(cls, config: S3Config) -> Self:
        """Build the client from ``config`` and wrap it."""
        return cls(create_s3_client(config), config.bucket)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        """Upload ``data`` with its ``content_type`` (Class A)."""
        with _translated_errors(key):
            self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        """Download ``key`` (Class B) or raise :class:`ObjectNotFoundError`."""
        with _translated_errors(key):
            body: bytes = self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()
            return body

    def exists(self, key: str) -> bool:
        """HEAD ``key`` (Class B); a 404 means absent."""
        try:
            with _translated_errors(key):
                self._client.head_object(Bucket=self._bucket, Key=key)
        except ObjectNotFoundError:
            return False
        return True

    def delete(self, key: str) -> None:
        """Delete ``key`` (Class A); S3 treats a missing key as success."""
        with _translated_errors(key):
            self._client.delete_object(Bucket=self._bucket, Key=key)

    def presigned_get_url(
        self, key: str, *, expires_in: int = PRESIGN_TTL_SECONDS, download_name: str | None = None
    ) -> str:
        """Sign a GET URL locally; no request is made."""
        params = {"Bucket": self._bucket, "Key": key}
        if download_name is not None:
            params["ResponseContentDisposition"] = content_disposition(download_name)
        url: str = self._client.generate_presigned_url("get_object", Params=params, ExpiresIn=expires_in)
        return url

    def count_prefix(self, prefix: str) -> int:
        """Count objects under ``prefix`` with one LIST call (Class A); a diagnostic for the probe, not part of the port."""
        with _translated_errors(prefix):
            listing = self._client.list_objects_v2(Bucket=self._bucket, Prefix=prefix, MaxKeys=1000)
        return int(listing.get("KeyCount", 0))
