#!/usr/bin/env bash
# Validate discovery CoS skill markdown (chapters 8–11).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CANON_REL="docs/discovery/government-data-sources.md"
STAGING_REL=".plans/discovery-layer/02-staging-model-and-api.md"

usage() {
  echo "usage: $0 <govdata|pvog|fim|leika|all>" >&2
  exit 2
}

skill_path_for() {
  case "$1" in
    govdata) echo ".cursor/skills/redtape-govdata/SKILL.md" ;;
    pvog) echo ".cursor/skills/redtape-pvog/SKILL.md" ;;
    fim) echo ".cursor/skills/redtape-fim/SKILL.md" ;;
    leika) echo ".cursor/skills/redtape-leika/SKILL.md" ;;
    *) return 1 ;;
  esac
}

require_heading() {
  local file="$1"
  local heading="$2"
  if ! grep -qF "$heading" "$file"; then
    echo "error: $file missing heading: $heading" >&2
    exit 1
  fi
}

check_skill_file() {
  local skill_key="$1"
  local rel
  rel="$(skill_path_for "$skill_key")" || {
    echo "error: unknown skill key: $skill_key" >&2
    exit 1
  }
  local file="$ROOT/$rel"
  if [[ ! -f "$file" ]]; then
    echo "error: missing skill file: $rel" >&2
    exit 1
  fi

  require_heading "$file" "## When to use"
  require_heading "$file" "## Mapping"

  if ! grep -qF "$STAGING_REL" "$file"; then
    echo "error: $rel must link to $STAGING_REL" >&2
    exit 1
  fi

  if ! grep -qF "$CANON_REL" "$file" && ! grep -qF "## Authoritative documentation" "$file"; then
    echo "error: $rel must link to $CANON_REL or include ## Authoritative documentation" >&2
    exit 1
  fi

  local url_count
  url_count="$(grep -oE 'https://[^ )>]+' "$file" | wc -l | tr -d ' ')"
  if [[ "$url_count" -lt 3 ]]; then
    echo "error: $rel must include at least three https:// URLs (found $url_count)" >&2
    exit 1
  fi

  case "$skill_key" in
    govdata)
      if ! grep -qE 'GOVDATA_CKAN_BASE_URL|GOVDATA_PACKAGE_ID' "$file"; then
        echo "error: $rel must document GOVDATA_CKAN_BASE_URL and GOVDATA_PACKAGE_ID" >&2
        exit 1
      fi
      ;;
  esac

  echo "ok: $rel"
}

main() {
  local target="${1:-}"
  [[ -n "$target" ]] || usage

  case "$target" in
    all)
      for key in govdata pvog fim leika; do
        if [[ -f "$ROOT/$(skill_path_for "$key")" ]]; then
          check_skill_file "$key"
        fi
      done
      ;;
    govdata | pvog | fim | leika)
      check_skill_file "$target"
      ;;
    *)
      usage
      ;;
  esac
}

main "$@"
