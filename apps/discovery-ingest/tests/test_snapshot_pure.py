"""The snapshot pipeline is pure: importing it loads no HTTP client, cloud SDK or database driver."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
BANNED_MODULES = ("httpx", "boto3", "botocore", "psycopg", "psycopg2", "sqlalchemy", "asyncpg")


def test_importing_the_pipeline_loads_no_http_client_cloud_sdk_or_database_driver() -> None:
    code = (
        "import sys\n"
        "import discovery_ingest.snapshot_translation\n"
        f"print(sorted(name for name in {BANNED_MODULES!r} if name in sys.modules))\n"
    )
    done = subprocess.run([sys.executable, "-c", code], cwd=APP_ROOT, capture_output=True, text=True, check=True)
    assert done.stdout.strip() == "[]"
