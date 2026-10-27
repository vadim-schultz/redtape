"""The single place that builds a boto3 S3 client from configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import boto3
from botocore.client import BaseClient
from botocore.config import Config

ChecksumMode = Literal["when_required", "when_supported"]
"""``when_supported`` is the recent boto3 default; ``when_required`` avoids CRC headers non-AWS stores dislike."""

CHECKSUM_MODES: tuple[ChecksumMode, ...] = ("when_required", "when_supported")


@dataclass(frozen=True)
class S3Config:
    """Everything needed to talk to one S3-compatible bucket (Cloudflare R2 first)."""

    bucket: str
    access_key_id: str
    secret_access_key: str = field(repr=False)
    region: str = "auto"
    endpoint_url: str | None = None
    force_path_style: bool = True
    checksum: ChecksumMode = "when_required"


def create_s3_client(config: S3Config) -> BaseClient:
    """Return a signature v4 client with path-style addressing and the configured checksum mode."""
    return boto3.client(
        "s3",
        endpoint_url=config.endpoint_url,
        region_name=config.region,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        config=_client_config(config),
    )


def _client_config(config: S3Config) -> Config:
    return Config(
        signature_version="s3v4",
        s3={"addressing_style": "path" if config.force_path_style else "auto"},
        request_checksum_calculation=config.checksum,
        response_checksum_validation=config.checksum,
        connect_timeout=5,
        read_timeout=30,
        retries={"max_attempts": 2, "mode": "standard"},
    )
