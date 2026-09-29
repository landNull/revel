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

detect_os
detect_init
detect_pkg_mgr

log "Revel foundation"
log "  repo:    $ROOT"
log "  host:    $OS_PRETTY ($OS_ID ${OS_LIKE})"
log "  init:    $INIT  (reference only; not a product requirement)"
log "  pkg:     ${PKG_MGR:-none}"
log "  user:    $(id -un) uid=$(id -u)"
log "  dry-run: $DRY_RUN"

log "probe tools"
EXISTING=()
MISSING_LOGICAL=()

if pick_python; then
  ok "python $("$PYTHON" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])') @ $PYTHON"
  EXISTING+=("python")
else
  miss "python >= ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}"
  MISSING_LOGICAL+=("python")
fi

if sqlite_ok; then
  ok "sqlite3 $(sqlite3 --version | awk '{print $1}')"
  EXISTING+=("sqlite")
else
  miss "sqlite3"
  MISSING_LOGICAL+=("sqlite")
fi

if have git; then
  ok "git $(git --version | awk '{print $3}')"
  EXISTING+=("git")
else
  miss "git"
  MISSING_LOGICAL+=("git")
fi

if have pipx; then
  ok "pipx $(pipx --version 2>/dev/null || echo present)"
else
  miss "pipx (optional; preferred later for packaging)"
fi

if have revelctl; then
  ok "revelctl on PATH: $(command -v revelctl)"
else
  miss "revelctl not on PATH yet"
fi

if have node; then
  ok "node $(node --version) (web widgets later; not required for M0)"
else
  miss "node (optional; JS widgets are views only)"
fi

if [[ -n "${PYTHON:-}" ]]; then
  if "$PYTHON" -c "import venv" 2>/dev/null; then
    ok "python venv module"
  else
    miss "python venv module"
    MISSING_LOGICAL+=("python")
  fi
  if "$PYTHON" -c "import pip" 2>/dev/null || have pip3 || have pip; then
    ok "pip available"
  else
    miss "pip"
    MISSING_LOGICAL+=("python")
  fi
fi

log "probe revel paths"
for d in "$REVEL_DATA" "$REVEL_CONFIG" "$REVEL_STATE"; do
  if [[ -d "$d" ]]; then
    ok "exists $d"
  else
    miss "missing $d"
  fi
done
if [[ -d "$REVEL_VENV" && -x "$REVEL_VENV/bin/python" ]]; then
  ok "venv $REVEL_VENV"
else
  miss "venv $REVEL_VENV"
fi
if [[ -f "$ROOT/pyproject.toml" || -f "$ROOT/setup.cfg" || -f "$ROOT/setup.py" ]]; then
  ok "package metadata in repo"
else
  miss "no pyproject.toml"
fi

uniq_words() {
  awk 'BEGIN { RS="[[:space:]]+" } NF && !seen[$0]++ { print $0 }'
}

if [[ ${#MISSING_LOGICAL[@]} -gt 0 ]]; then
  MISSING_LOGICAL_STR="$(printf '%s\n' "${MISSING_LOGICAL[@]}" | uniq_words | tr '\n' ' ')"
  PKGS_STR="$(packages_for $MISSING_LOGICAL_STR | uniq_words | tr '\n' ' ')"
  read -r -a PKGS <<< "${PKGS_STR}"
  if [[ ${#PKGS[@]} -gt 0 && -n "${PKGS[0]:-}" ]]; then
    log "install missing host packages"
    install_packages "${PKGS[@]}" || warn "package step failed or skipped"
    pick_python || true
  fi
fi

log "create user-space layout"
for d in "$REVEL_DATA" "$REVEL_CONFIG" "$REVEL_STATE" "$REVEL_DATA/store"; do
  if [[ -d "$d" ]]; then
    ok "keep $d"
  else
    run mkdir -p "$d"
    ok "mkdir $d"
  fi
done

if [[ ! -f "$REVEL_CONFIG/host.env" || "$DRY_RUN" == "1" ]]; then
  if [[ "$DRY_RUN" == "1" ]]; then
    log "  dry-run: write $REVEL_CONFIG/host.env"
  else
    cat >"$REVEL_CONFIG/host.env" <<EOF
# Written by scripts/install-revel.sh — host facts, not product identity.
REVEL_HOST_PRETTY="${OS_PRETTY}"
REVEL_HOST_ID="${OS_ID}"
REVEL_INIT="${INIT}"
REVEL_PYTHON="${PYTHON:-}"
REVEL_DATA="${REVEL_DATA}"
REVEL_CONFIG="${REVEL_CONFIG}"
REVEL_STATE="${REVEL_STATE}"
REVEL_STORE="${REVEL_DATA}/store"
EOF
    ok "wrote $REVEL_CONFIG/host.env"
  fi
else
  ok "keep $REVEL_CONFIG/host.env"
fi

if [[ "$MAKE_VENV" == "1" ]]; then
  if [[ -z "${PYTHON:-}" ]]; then
    warn "no Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+; skip venv"
  elif [[ -x "$REVEL_VENV/bin/python" ]]; then
    ok "reuse venv $REVEL_VENV"
  else
    log "create venv"
    run "$PYTHON" -m venv "$REVEL_VENV"
    ok "venv $REVEL_VENV"
  fi
  if [[ -x "$REVEL_VENV/bin/pip" ]]; then
    run "$REVEL_VENV/bin/pip" install --upgrade pip
    if [[ -f "$ROOT/pyproject.toml" ]]; then
      log "editable install from $ROOT"
      run "$REVEL_VENV/bin/pip" install -e "$ROOT"
    else
      miss "skip pip install -e . (no package skeleton yet)"
    fi
  fi
fi

LOCAL_BIN="$HOME/.local/bin"
if [[ -d "$REVEL_VENV/bin" ]]; then
  if [[ ":$PATH:" == *":$LOCAL_BIN:"* ]]; then
    ok "\$HOME/.local/bin on PATH"
  else
    warn "add \$HOME/.local/bin to PATH to pick up revelctl later"
  fi
  if [[ -x "$REVEL_VENV/bin/revelctl" ]]; then
    if [[ ! -e "$LOCAL_BIN/revelctl" ]]; then
      run mkdir -p "$LOCAL_BIN"
      run ln -sf "$REVEL_VENV/bin/revelctl" "$LOCAL_BIN/revelctl"
      ok "link $LOCAL_BIN/revelctl"
    else
      ok "link exists $LOCAL_BIN/revelctl"
    fi
  fi
fi

log "done"
log "  data    $REVEL_DATA"
log "  config  $REVEL_CONFIG"
log "  state   $REVEL_STATE"
log "  venv    $REVEL_VENV"
log "  store   $REVEL_DATA/store  (Kuzu file in M2, not now)"
if [[ "$DRY_RUN" == "1" ]]; then
  log "dry-run: no changes committed"
fi
log "next: M0 #6 package skeleton, then pip install -e . from the venv"
