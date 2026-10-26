"""Probe an S3-compatible object store end to end and recommend a checksum configuration.

Reads the ``OBJECT_STORE_*`` settings from the environment and, under a unique ``probe/<uuid>/`` prefix,
runs put, exists, get, presigned GET (plain HTTP, no credentials), presigned GET with a download name,
delete, exists-after-delete and a leftover check, once per checksum variant. Prints a pass/fail table and
the recommended variant; never prints the secret access key. Exit codes: 0 a variant passed every step,
1 no variant did, 2 settings are missing.

Run from ``apps/api``: ``python -m scripts.object_store_probe``.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace

from app.config import Settings
from app.shared.object_store import CHECKSUM_MODES, ChecksumMode, S3Config, S3ObjectStore
from app.shared.object_store.provider import s3_config_from_settings

from scripts.object_store_probe_steps import STEPS, HttpGet, ProbeContext, ProbeRow, run_step, urllib_get

REQUIRED_SETTINGS = (
    "object_store_endpoint_url",
    "object_store_region",
    "object_store_bucket",
    "object_store_access_key_id",
    "object_store_secret_access_key",
)

BuildStore = Callable[[S3Config], S3ObjectStore]


@dataclass(frozen=True)
class VariantResult:
    """All step outcomes for one checksum variant."""

    checksum: ChecksumMode
    rows: tuple[ProbeRow, ...]

    @property
    def passed(self) -> bool:
        """Return whether every step passed."""
        return all(row.ok for row in self.rows)


def _run_variant(config: S3Config, checksum: ChecksumMode, http_get: HttpGet, build_store: BuildStore) -> VariantResult:
    store = build_store(replace(config, checksum=checksum))
    ctx = ProbeContext(store=store, http_get=http_get, prefix=f"probe/{uuid.uuid4()}/")
    return VariantResult(checksum, tuple(run_step(name, check, ctx) for name, check in STEPS))


def run_probe(
    config: S3Config, *, http_get: HttpGet = urllib_get, build_store: BuildStore = S3ObjectStore.from_config
) -> list[VariantResult]:
    """Run every step once per checksum variant against the store described by ``config``."""
    return [_run_variant(config, checksum, http_get, build_store) for checksum in CHECKSUM_MODES]


def recommend(results: list[VariantResult]) -> ChecksumMode | None:
    """Return the first variant, in preference order, that passed every step."""
    return next((result.checksum for result in results if result.passed), None)


def _format_variant(result: VariantResult) -> list[str]:
    lines = [f"Checksum variant: {result.checksum}"]
    lines += [f"  {row.step:<20} {'PASS' if row.ok else 'FAIL'}  {row.detail}" for row in result.rows]
    return lines


def render_report(results: list[VariantResult], secret: str) -> str:
    """Return the pass/fail table and the recommendation, with ``secret`` redacted wherever it appears."""
    lines = [line for result in results for line in [*_format_variant(result), ""]]
    lines.append(f"Recommended checksum variant: {recommend(results) or 'none (no variant passed every step)'}")
    report = "\n".join(lines)
    return report.replace(secret, "***") if secret else report


def _missing_settings(app_settings: Settings) -> list[str]:
    return [name.upper() for name in REQUIRED_SETTINGS if not getattr(app_settings, name)]


def main(
    *,
    app_settings: Settings | None = None,
    http_get: HttpGet = urllib_get,
    build_store: BuildStore = S3ObjectStore.from_config,
) -> int:
    """Run the probe from the environment settings and return the process exit code."""
    app_settings = app_settings or Settings(_env_file=None)
    if missing := _missing_settings(app_settings):
        print("Missing object store settings: " + ", ".join(missing))
        return 2
    results = run_probe(s3_config_from_settings(app_settings), http_get=http_get, build_store=build_store)
    print(render_report(results, app_settings.object_store_secret_access_key or ""))
    return 0 if recommend(results) else 1


if __name__ == "__main__":
    sys.exit(main())
