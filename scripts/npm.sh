#!/usr/bin/env bash
# Run npm in apps/web. Uses NPM_REGISTRY from the repo-root .env when present,
# and rewrites any corporate resolved URLs back to the public registry.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/.env"
  set +a
fi

if [ -n "${NPM_REGISTRY:-}" ]; then
  export npm_config_registry="$NPM_REGISTRY"
fi

cd "$ROOT/apps/web"
npm "$@"

python3 - "$ROOT/apps/web/package-lock.json" "${NPM_REGISTRY:-}" << 'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
registry = sys.argv[2]
public = "https://registry.npmjs.org/"
text = path.read_text()
updated = text
if registry:
    mirror = registry if registry.endswith("/") else f"{registry}/"
    if mirror != public:
        updated = text.replace(mirror, public)
if updated != text:
    path.write_text(updated)
PY
