"""The live probe's logic, exercised against moto (no real R2, no credentials)."""

from __future__ import annotations

from collections.abc import Generator

import boto3
import pytest
import requests
from app.config import Settings
from app.shared.object_store import CHECKSUM_MODES, S3Config, S3ObjectStore
from moto import mock_aws
from scripts.object_store_probe import (
    main,
    recommend,
    render_report,
    run_probe,
)
from scripts.object_store_probe_steps import HttpReply

BUCKET = "probe-bucket"
SECRET = "super-secret-value-123"

SETTINGS = Settings(
    _env_file=None,
    object_store_endpoint_url="https://s3.amazonaws.com",
    object_store_region="us-east-1",
    object_store_bucket=BUCKET,
    object_store_access_key_id="probe-key-id",
    object_store_secret_access_key=SECRET,
)

CONFIG = S3Config(
    endpoint_url="https://s3.amazonaws.com",
    region="us-east-1",
    bucket=BUCKET,
    access_key_id="probe-key-id",
    secret_access_key=SECRET,
)


@pytest.fixture
def moto_bucket() -> Generator[None, None, None]:
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield


def _http_get(url: str) -> HttpReply:
    response = requests.get(url, timeout=10)
    return HttpReply(status=response.status_code, headers=dict(response.headers), body=response.content)


class _DeleteFails(S3ObjectStore):
    def delete(self, key: str) -> None:
        raise RuntimeError(f"delete refused for secret {SECRET}")


def test_probe_reports_all_steps_passing_against_a_working_store(
    moto_bucket: None, capsys: pytest.CaptureFixture[str]
) -> None:
    results = run_probe(CONFIG, http_get=_http_get)

    assert [result.checksum for result in results] == list(CHECKSUM_MODES)
    assert all(row.ok for result in results for row in result.rows), render_report(results, SECRET)
    assert recommend(results) == "when_required"
    assert main(app_settings=SETTINGS, http_get=_http_get) == 0
    assert "when_required" in capsys.readouterr().out


def test_probe_reports_the_failing_step_and_exits_non_zero_when_delete_fails(
    moto_bucket: None, capsys: pytest.CaptureFixture[str]
) -> None:
    results = run_probe(CONFIG, http_get=_http_get, build_store=_DeleteFails.from_config)
    failed = {row.step for result in results for row in result.rows if not row.ok}

    assert {"delete", "exists_after_delete", "leftover_objects"} <= failed
    assert recommend(results) is None
    assert main(app_settings=SETTINGS, http_get=_http_get, build_store=_DeleteFails.from_config) == 1
    assert "FAIL" in capsys.readouterr().out


def test_probe_exits_with_usage_error_and_names_missing_settings_when_unconfigured(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(app_settings=Settings(_env_file=None, object_store_bucket="only-this")) == 2

    output = capsys.readouterr().out
    assert "OBJECT_STORE_ENDPOINT_URL" in output
    assert "only-this" not in output


def test_probe_output_never_includes_the_secret_access_key(
    moto_bucket: None, capsys: pytest.CaptureFixture[str]
) -> None:
    main(app_settings=SETTINGS, http_get=_http_get)
    main(app_settings=SETTINGS, http_get=_http_get, build_store=_DeleteFails.from_config)

    assert SECRET not in capsys.readouterr().out
    assert SECRET not in repr(CONFIG)
