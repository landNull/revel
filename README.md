# Revel

Community edition (public, AGPL-3.0). Thesis: a project manager that treats every element as a task node.

**Agents and contributors:** `AGENTS.md` → `revel.settings.json` only. Do not fork the brief.

- Core language: Python 3.11+
- Store: explicit graph (D005); default embedded Kuzu, Neo4j scale-only
- Control plane: `revelctl` (D006 API-first; TUI/web are clients)
- License: AGPL-3.0 community edition (D008); hosted subscriber features proprietary, not in this repo
- Surfaces: CLI, Textual TUI, FastAPI web (D007); JS widgets are views only
- Out of scope: Enlite/EFL desktop UI; any single-distro dependency; Orange/conda (parked)
- Reference workstation: Devuan Excalibur, init sysvinit (not a runtime requirement)

## Host foundation

```sh
./scripts/install-revel.sh --dry-run   # probe only
./scripts/install-revel.sh             # ask before sudo
./scripts/install-revel.sh --yes       # non-interactive approve
```

The installer looks for Python 3.11+, sqlite3, git, pip/venv, existing `revelctl`, and XDG paths. It prompts before using sudo to install missing host packages. User data lives under `~/.local/share/revel` and `~/.config/revel`. No distro or init system is required.
