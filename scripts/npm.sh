#!/usr/bin/env bash
# Run npm in apps/web. Reads NPM_REGISTRY from the gitignored repo-root .env
# when present, then rewrites lockfile resolved URLs back to the public registry.
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
  # apps/web/.npmrc sets replace-registry-host=never so CI keeps public URLs.
  # Local installs through NPM_REGISTRY need the default host rewrite.
  export npm_config_replace_registry_host=npmjs
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
