#!/usr/bin/env bash
# Migration round trip: single head, upgrade, downgrade+upgrade the newest
# revision, and no model/migration drift. Run from `apps/api` against an
# empty `DATABASE_URL`; `ALEMBIC_CONFIG` may point at an alternate config
# (tests use this to run against an isolated copy of the chain).
set -euo pipefail

check_single_head() {
  local heads
  heads="$(alembic heads)"
  if [ "$(printf '%s\n' "$heads" | grep -c .)" -ne 1 ]; then
    echo "error: expected exactly one Alembic head, found:" >&2
    printf '%s\n' "$heads" >&2
    return 1
  fi
}

check_upgrade_head() {
  alembic upgrade head
}

check_round_trip() {
  alembic downgrade -1
  alembic upgrade head
}

check_no_drift() {
  alembic check
}

main() {
  check_single_head
  check_upgrade_head
  check_round_trip
  check_no_drift
  echo "✅ migrations: single head, upgrade, round trip and drift checks passed"
}

main "$@"
