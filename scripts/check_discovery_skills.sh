#!/usr/bin/env bash
# Verify discovery-layer CoS skill files (chapters 8–11).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$ROOT/.cursor/skills"
CANON_REF="docs/discovery/government-data-sources.md"
CANON_HEADING="Authoritative documentation"
MIN_HTTPS=3

check_skill() {
  local name="$1"
  local required_heading="$2"
  local path="$SKILLS_DIR/redtape-${name}/SKILL.md"
  if [[ ! -f "$path" ]]; then
    echo "check_discovery_skills: missing $path" >&2
    return 1
  fi
  if ! grep -q "$required_heading" "$path"; then
    echo "check_discovery_skills: $path must contain heading matching: $required_heading" >&2
    return 1
  fi
  if ! grep -qE "${CANON_REF}|## ${CANON_HEADING}" "$path"; then
    echo "check_discovery_skills: $path must link to $CANON_REF or contain '## ${CANON_HEADING}'" >&2
    return 1
  fi
  local https_count
  https_count="$(grep -o 'https://' "$path" | wc -l)"
  if [[ "$https_count" -lt $MIN_HTTPS ]]; then
    echo "check_discovery_skills: $path must contain at least $MIN_HTTPS https:// URLs (found $https_count)" >&2
    return 1
  fi
  echo "ok: redtape-${name}"
}

if [[ $# -eq 0 ]]; then
  check_skill govdata "Mapping"
  check_skill pvog "Authentication"
  check_skill fim "Rate limits"
  check_skill leika "external_id"
  exit 0
fi

case "$1" in
  govdata) check_skill govdata "Mapping" ;;
  pvog) check_skill pvog "Authentication" ;;
  fim) check_skill fim "Rate limits" ;;
  leika) check_skill leika "external_id" ;;
  *)
    echo "usage: $0 [govdata|pvog|fim|leika]" >&2
    exit 2
    ;;
esac
