"""Promote or demote a user by email.

Run from `apps/api` (the user must have logged in at least once, so its row exists):
  python -m scripts.set_user_role <email> <role>
"""

from __future__ import annotations

import argparse
import sys

from app.db import SessionLocal
from app.features.auth.repository import UserRepository
from app.features.auth.service import UnknownRoleError, UnknownUserError, UserService
from app.models import AppUser


def _set_role_or_exit(service: UserService, email: str, role: str) -> AppUser:
    try:
        return service.set_role(email, role)
    except (UnknownRoleError, UnknownUserError) as exc:
        print(f"set_user_role: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Set the role of the user identified by email, committing only when the role is accepted."""
    parser = argparse.ArgumentParser(description="Set an app_user's role by email.")
    parser.add_argument("email")
    parser.add_argument("role")
    args = parser.parse_args()

    with SessionLocal() as session:
        user = _set_role_or_exit(UserService(UserRepository(session)), args.email, args.role)
        session.commit()

    print(f"set_user_role: {user.email} is now {user.role.value}")


if __name__ == "__main__":
    main()
