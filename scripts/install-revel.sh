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

# --- host probe -------------------------------------------------------------

detect_os() {
  OS_ID="unknown"
  OS_LIKE=""
  OS_PRETTY="unknown"
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_ID="${ID:-unknown}"
    OS_LIKE="${ID_LIKE:-}"
    OS_PRETTY="${PRETTY_NAME:-$OS_ID}"
  fi
}

detect_init() {
  INIT="unknown"
  if [[ -d /run/systemd/system ]] && have systemctl; then
    INIT="systemd"
  elif [[ -x /sbin/init ]] && /sbin/init --version 2>/dev/null | grep -qi sysv; then
    INIT="sysvinit"
  elif [[ -d /etc/init.d ]] && [[ -x /sbin/init ]]; then
    INIT="sysvinit"
  elif [[ -x /sbin/runit-init ]] || [[ -d /etc/runit ]]; then
    INIT="runit"
  fi
}

detect_pkg_mgr() {
  PKG_MGR=""
  PKG_INSTALL=()
  if have apt-get; then
    PKG_MGR="apt-get"
    PKG_INSTALL=(apt-get install -y)
  elif have pacman; then
    PKG_MGR="pacman"
    PKG_INSTALL=(pacman -S --needed --noconfirm)
  elif have dnf; then
    PKG_MGR="dnf"
    PKG_INSTALL=(dnf install -y)
  elif have apk; then
    PKG_MGR="apk"
    PKG_INSTALL=(apk add)
  elif have zypper; then
    PKG_MGR="zypper"
    PKG_INSTALL=(zypper install -y)
  fi
}

packages_for() {
  local need=("$@")
  local out=()
  local p
  for p in "${need[@]}"; do
    case "$PKG_MGR:$p" in
      apt-get:python) out+=(python3 python3-venv python3-pip python3-dev) ;;
      apt-get:sqlite) out+=(sqlite3 libsqlite3-dev) ;;
      apt-get:git) out+=(git) ;;
      apt-get:build) out+=(build-essential) ;;
      pacman:python) out+=(python python-pip) ;;
      pacman:sqlite) out+=(sqlite) ;;
      pacman:git) out+=(git) ;;
      pacman:build) out+=(base-devel) ;;
      dnf:python) out+=(python3 python3-pip python3-devel) ;;
      dnf:sqlite) out+=(sqlite sqlite-devel) ;;
      dnf:git) out+=(git) ;;
      dnf:build) out+=(gcc gcc-c++ make) ;;
      apk:python) out+=(python3 py3-pip py3-virtualenv) ;;
      apk:sqlite) out+=(sqlite sqlite-dev) ;;
      apk:git) out+=(git) ;;
      apk:build) out+=(build-base) ;;
      zypper:python) out+=(python3 python3-pip python3-devel) ;;
      zypper:sqlite) out+=(sqlite3 sqlite3-devel) ;;
      zypper:git) out+=(git) ;;
      zypper:build) out+=(gcc make) ;;
      *) ;;
    esac
  done
  printf '%s\n' "${out[@]}"
}

python_ok() {
  local bin="$1"
  have "$bin" || return 1
  "$bin" -c "import sys; raise SystemExit(0 if sys.version_info >= (${PYTHON_MIN_MAJOR}, ${PYTHON_MIN_MINOR}) else 1)" 2>/dev/null
}

pick_python() {
  PYTHON=""
  local c
  for c in python3.13 python3.12 python3.11 python3 python; do
    if python_ok "$c"; then
      PYTHON="$(command -v "$c")"
      return 0
    fi
  done
  return 1
}

sqlite_ok() {
  have sqlite3 || return 1
  sqlite3 --version >/dev/null 2>&1
}

sudo_cmd() {
  if [[ "$(id -u)" -eq 0 ]]; then
    printf '%s\n' ""
    return 0
  fi
  if ! have sudo; then
    warn "sudo not found and not root"
    return 1
  fi
  printf '%s\n' "sudo"
}

install_packages() {
  local pkgs=("$@")
  [[ ${#pkgs[@]} -eq 0 ]] && return 0
  if [[ -z "$PKG_MGR" ]]; then
    warn "no supported package manager; install manually: ${pkgs[*]}"
    return 1
  fi
  local wrapper
  wrapper="$(sudo_cmd)" || return 1
  log "need packages: ${pkgs[*]}"
  if ! confirm "install with ${wrapper:+$wrapper }${PKG_MGR}?"; then
    warn "skipped package install"
    return 1
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    log "  dry-run: ${wrapper} ${PKG_INSTALL[*]} ${pkgs[*]}"
    return 0
  fi
  if [[ "$PKG_MGR" == "apt-get" ]]; then
    ${wrapper} apt-get update
  fi
  ${wrapper} "${PKG_INSTALL[@]}" "${pkgs[@]}"
}
