"""Contract tests for the object store port, run against both adapters, plus the metered decorator."""

from __future__ import annotations

from collections.abc import Callable, Generator
from urllib.parse import parse_qs, urlparse

import boto3
import pytest
from app.shared.object_store import (
    InMemoryObjectStore,
    MeteredObjectStore,
    ObjectNotFoundError,
    ObjectStore,
    ObjectStoreQuotaError,
    ObjectStoreUnavailableError,
    OperationClass,
    S3Config,
    S3ObjectStore,
)
from moto import mock_aws

BUCKET = "test-bucket"
REGION = "us-east-1"


def _s3_config(*, bucket: str = BUCKET, endpoint_url: str | None = None) -> S3Config:
    return S3Config(
        endpoint_url=endpoint_url,
        region=REGION,
        bucket=bucket,
        access_key_id="test-access-key",
        secret_access_key="test-secret-key",
    )


@pytest.fixture
def moto_bucket() -> Generator[None, None, None]:
    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET)
        yield


@pytest.fixture(params=["memory", "s3"])
def store(request: pytest.FixtureRequest) -> ObjectStore:
    if request.param == "memory":
        return InMemoryObjectStore()
    request.getfixturevalue("moto_bucket")
    return S3ObjectStore.from_config(_s3_config())


def _expiry_seconds(url: str) -> int:
    query = parse_qs(urlparse(url).query)
    key = "X-Amz-Expires" if "X-Amz-Expires" in query else "expires_in"
    return int(query[key][0])


def test_put_then_get_returns_the_same_bytes_and_content_type(store: ObjectStore) -> None:
    store.put("a/b.html", b"<p>hi</p>", "text/html")

    assert store.get("a/b.html") == b"<p>hi</p>"


def test_get_returns_the_stored_content_type_in_the_s3_adapter(moto_bucket: None) -> None:
    store = S3ObjectStore.from_config(_s3_config())
    store.put("shot.png", b"\x89PNG", "image/png")

    head = boto3.client("s3", region_name=REGION).head_object(Bucket=BUCKET, Key="shot.png")

    assert head["ContentType"] == "image/png"


def test_exists_is_false_before_put_and_true_after_and_delete_makes_it_false(store: ObjectStore) -> None:
    assert store.exists("k") is False

    store.put("k", b"x", "text/plain")
    assert store.exists("k") is True

    store.delete("k")
    assert store.exists("k") is False


def test_get_of_a_missing_key_raises_object_not_found(store: ObjectStore) -> None:
    with pytest.raises(ObjectNotFoundError):
        store.get("missing")


def test_delete_of_a_missing_key_is_a_no_op(store: ObjectStore) -> None:
    store.delete("missing")

    assert store.exists("missing") is False


def test_presigned_url_carries_the_default_and_a_custom_expiry(store: ObjectStore) -> None:
    default_url = store.presigned_get_url("k")
    custom_url = store.presigned_get_url("k", expires_in=60)

    assert _expiry_seconds(default_url) == 300
    assert _expiry_seconds(custom_url) == 60


def test_presigned_url_is_minted_without_a_network_call() -> None:
    store = S3ObjectStore.from_config(_s3_config(endpoint_url="https://unreachable.invalid"))

    url = store.presigned_get_url("k", expires_in=120)

    assert url.startswith("https://unreachable.invalid/")
    assert _expiry_seconds(url) == 120


def test_presigned_url_with_download_name_asks_for_an_attachment(store: ObjectStore) -> None:
    url = store.presigned_get_url("k", download_name='page "1".html')

    assert "attachment" in str(parse_qs(urlparse(url).query))
    assert 'filename="page 1.html"' in str(parse_qs(urlparse(url).query))


def test_presigned_url_without_download_name_has_no_disposition_override(store: ObjectStore) -> None:
    url = store.presigned_get_url("k")

    assert "disposition" not in url.lower()


def test_memory_presigned_url_is_deterministic() -> None:
    store = InMemoryObjectStore()

    assert store.presigned_get_url("k") == store.presigned_get_url("k")
    assert store.presigned_get_url("k").startswith("memory://")


def test_s3_adapter_maps_a_missing_bucket_to_unavailable() -> None:
    with mock_aws():
        store = S3ObjectStore.from_config(_s3_config(bucket="no-such-bucket"))

        with pytest.raises(ObjectStoreUnavailableError):
            store.put("k", b"x", "text/plain")


def test_s3_adapter_maps_an_unreachable_endpoint_to_unavailable() -> None:
    store = S3ObjectStore.from_config(_s3_config(endpoint_url="http://127.0.0.1:1"))

    with pytest.raises(ObjectStoreUnavailableError):
        store.get("k")


Meter = Callable[[OperationClass, int], None]


def _recording_meter() -> tuple[Meter, list[tuple[str, int]]]:
    calls: list[tuple[str, int]] = []

    def meter(kind: OperationClass, n: int) -> None:
        calls.append((kind, n))

    return meter, calls


def test_metered_store_counts_put_and_delete_as_class_a_get_and_exists_as_class_b(store: ObjectStore) -> None:
    meter, calls = _recording_meter()
    metered = MeteredObjectStore(store, meter)

    metered.put("k", b"x", "text/plain")
    metered.get("k")
    metered.exists("k")
    metered.delete("k")

    assert calls == [("class_a", 1), ("class_b", 1), ("class_b", 1), ("class_a", 1)]


def test_metered_store_counts_presign_as_nothing(store: ObjectStore) -> None:
    meter, calls = _recording_meter()

    MeteredObjectStore(store, meter).presigned_get_url("k", download_name="k.html")

    assert calls == []


def test_a_meter_that_raises_stops_the_call_before_the_inner_store_is_touched() -> None:
    inner = InMemoryObjectStore()
    inner.put("keep", b"1", "text/plain")

    def over_cap(kind: OperationClass, n: int) -> None:
        raise ObjectStoreQuotaError(f"{kind} cap reached")

    metered = MeteredObjectStore(inner, over_cap)

    with pytest.raises(ObjectStoreQuotaError):
        metered.put("new", b"2", "text/plain")
    with pytest.raises(ObjectStoreQuotaError):
        metered.delete("keep")
    with pytest.raises(ObjectStoreQuotaError):
        metered.get("keep")

    assert inner.exists("new") is False
    assert inner.get("keep") == b"1"


def test_quota_error_is_an_unavailable_error_so_routes_and_workers_treat_it_alike() -> None:
    assert issubclass(ObjectStoreQuotaError, ObjectStoreUnavailableError)
