#!/usr/bin/env bash
# Revel host foundation installer.
# Distro-agnostic. Author workstation is recorded in revel.settings.json only.
#
# Usage:
#   ./scripts/install-revel.sh
#   ./scripts/install-revel.sh --dry-run
#   ./scripts/install-revel.sh --yes
#   ./scripts/install-revel.sh --no-venv
#
# Looks for existing tools first. Asks before any sudo.

set -euo pipefail

DRY_RUN=0
ASSUME_YES=0
MAKE_VENV=1

usage() {
  cat <<'EOF'
Usage: install-revel.sh [options]

  --dry-run   Probe only; print what would change
  --yes       Answer yes to sudo / create prompts
  --no-venv   Skip user venv creation
  -h, --help  Show this help

Does not encode any distro or init system as a requirement.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --yes|-y) ASSUME_YES=1 ;;
    --no-venv) MAKE_VENV=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
REVEL_DATA="${XDG_DATA_HOME}/revel"
REVEL_CONFIG="${XDG_CONFIG_HOME}/revel"
REVEL_STATE="${XDG_STATE_HOME}/revel"
REVEL_VENV="${REVEL_DATA}/venv"
PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=11

log() { printf '%s\n' "$*"; }
ok() { printf '  [ok]  %s\n' "$*"; }
miss() { printf '  [..]  %s\n' "$*"; }
warn() { printf '  [!!]  %s\n' "$*"; }

confirm() {
  local prompt="$1"
  if [[ "$ASSUME_YES" == "1" ]]; then
    return 0
  fi
  if [[ ! -t 0 ]]; then
    warn "non-interactive stdin; pass --yes to approve: ${prompt}"
    return 1
  fi
  local reply
  read -r -p "${prompt} [y/N] " reply
  [[ "$reply" == "y" || "$reply" == "Y" || "$reply" == "yes" ]]
}

have() { command -v "$1" >/dev/null 2>&1; }

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    log "  dry-run: $*"
    return 0
  fi
  "$@"
}
