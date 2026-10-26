"""Object store settings, the optional dependency provider and the 503 mapping."""

from __future__ import annotations

import pytest
from app.config import Settings
from app.main import create_app
from app.shared.dependencies import shared_dependencies
from app.shared.object_store import (
    MeteredObjectStore,
    ObjectNotFoundError,
    ObjectStore,
    ObjectStoreQuotaError,
    ObjectStoreUnavailableError,
    OperationClass,
)
from app.shared.object_store.http import object_store_exception_handlers
from app.shared.object_store.provider import build_object_store, require_object_store
from litestar import Litestar, get
from litestar.status_codes import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from litestar.testing import TestClient

_ALL_SETTINGS = {
    "object_store_endpoint_url": "https://acct.r2.cloudflarestorage.com",
    "object_store_region": "auto",
    "object_store_bucket": "discovery-artifacts",
    "object_store_access_key_id": "key-id",
    "object_store_secret_access_key": "key-secret",
}


def _settings(**overrides: str | None) -> Settings:
    return Settings(_env_file=None, **{**_ALL_SETTINGS, **overrides})


@pytest.mark.parametrize("missing", sorted(_ALL_SETTINGS))
def test_object_store_is_disabled_when_any_required_setting_is_missing(missing: str) -> None:
    assert _settings(**{missing: None}).object_store_enabled is False


def test_object_store_is_disabled_by_default() -> None:
    assert Settings(_env_file=None).object_store_enabled is False


def test_object_store_is_enabled_when_all_settings_are_present() -> None:
    settings = _settings()

    assert settings.object_store_enabled is True
    assert settings.object_store_force_path_style is True
    assert settings.object_store_max_bytes == 8 * 1024**3


def test_build_object_store_is_none_when_disabled_and_a_store_when_enabled() -> None:
    assert build_object_store(Settings(_env_file=None)) is None
    assert build_object_store(_settings()) is not None


def test_build_object_store_wraps_the_adapter_with_the_given_meter() -> None:
    calls: list[tuple[OperationClass, int]] = []
    store = build_object_store(_settings(), lambda kind, n: calls.append((kind, n)))

    assert isinstance(store, MeteredObjectStore)
    store.presigned_get_url("k")
    assert calls == []


def _app_requiring_the_store() -> Litestar:
    @get("/probe", sync_to_thread=False)
    def probe() -> dict[str, str]:
        require_object_store()
        return {"status": "stored"}

    return Litestar([probe], exception_handlers=object_store_exception_handlers)


def test_require_object_store_raises_the_unavailable_error_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.shared.object_store.provider.settings", Settings(_env_file=None))

    with pytest.raises(ObjectStoreUnavailableError, match="not configured"):
        require_object_store()


def test_unavailable_error_is_mapped_to_503_with_a_clear_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.shared.object_store.provider.settings", Settings(_env_file=None))

    with TestClient(_app_requiring_the_store()) as client:
        response = client.get("/probe")

    assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
    assert "not configured" in response.json()["detail"]


def test_require_object_store_returns_a_store_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.shared.object_store.provider.settings", _settings())

    with TestClient(_app_requiring_the_store()) as client:
        assert client.get("/probe").status_code == HTTP_200_OK


def test_quota_error_is_mapped_to_503_like_unavailable() -> None:
    @get("/quota", sync_to_thread=False)
    def quota() -> None:
        raise ObjectStoreQuotaError("r2 class_a monthly cap reached")

    with TestClient(Litestar([quota], exception_handlers=object_store_exception_handlers)) as client:
        response = client.get("/quota")

    assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
    assert "cap reached" in response.json()["detail"]


def test_the_object_store_dependency_injects_none_when_storage_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.shared.object_store.provider.settings", Settings(_env_file=None))

    @get("/injected", sync_to_thread=False)
    def injected(object_store: ObjectStore | None) -> dict[str, bool]:
        return {"unconfigured": object_store is None}

    with TestClient(Litestar([injected], dependencies=shared_dependencies)) as client:
        assert client.get("/injected").json() == {"unconfigured": True}


def test_only_availability_errors_are_mapped_to_503() -> None:
    assert set(object_store_exception_handlers) == {ObjectStoreUnavailableError}
    assert not issubclass(ObjectNotFoundError, ObjectStoreUnavailableError)


def test_the_app_boots_without_object_store_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.shared.object_store.provider.settings", Settings(_env_file=None))

    app = create_app()

    assert ObjectStoreUnavailableError in app.exception_handlers
    with TestClient(app) as client:
        assert client.get("/health").status_code == HTTP_200_OK
