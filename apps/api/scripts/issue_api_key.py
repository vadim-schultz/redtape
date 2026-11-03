"""Issue or revoke a machine API key.

Run from `apps/api`:
  python -m scripts.issue_api_key --name crawler-prod
  python -m scripts.issue_api_key --revoke <key_prefix>

The plaintext key is printed exactly once, on issue, and is never stored or logged.
"""

from __future__ import annotations

import argparse
import sys

from app.db import SessionLocal
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyError, ApiKeyService


def _issue(service: ApiKeyService, name: str) -> None:
    key = service.issue(name)
    print(f"issue_api_key: new key (copy it now, it will not be shown again): {key}")


def _revoke_or_exit(service: ApiKeyService, key_prefix: str) -> None:
    try:
        service.revoke(key_prefix)
    except ApiKeyError as exc:
        print(f"issue_api_key: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"issue_api_key: revoked key with prefix {key_prefix}")


def main() -> None:
    """Issue or revoke a machine API key from the command line, committing only when the command succeeds."""
    parser = argparse.ArgumentParser(description="Issue or revoke a machine API key.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--name", help="Issue a new key with this name, e.g. crawler-prod")
    group.add_argument("--revoke", metavar="PREFIX", help="Revoke the key with this key_prefix")
    args = parser.parse_args()

    with SessionLocal() as session:
        service = ApiKeyService(ApiKeyRepository(session))
        if args.name:
            _issue(service, args.name)
        else:
            _revoke_or_exit(service, args.revoke)
        session.commit()


if __name__ == "__main__":
    main()
