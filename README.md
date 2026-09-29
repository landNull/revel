# Revel

Community edition (public, AGPL-3.0). Thesis: a project manager that treats every element as a task node.

## Credits

- Created by: **StarMarketingTeam**
- Coded with: **Grok** (xAI) — implementation assistance on the community graph, `revelctl` skeleton, and project brief
- Repository owner: [landNull](https://github.com/landNull)

**Agents and contributors:** `AGENTS.md` → `revel.settings.json` only. Do not fork the brief.

- Core language: Python 3.11+
- Store: explicit graph (D005); default embedded Kuzu, Neo4j scale-only
- Control plane: `revelctl` (D006 API-first; TUI/web are clients)
- License: AGPL-3.0 community edition (D008); hosted subscriber features proprietary, not in this repo
- Surfaces: CLI, FastAPI web (D007); JS widgets are views only. Chrome is Bootstrap 5 plus `revel.css` tokens (D012). Textual TUI parked (D010).
- Out of scope: native toolkit desktop UI; any single-distro or init dependency; third-party ML GUI or conda runtime
- Reference workstation: Devuan Excalibur, init sysvinit (not a runtime requirement)

## Host foundation

```sh
./scripts/install-revel.sh --dry-run   # probe only
./scripts/install-revel.sh             # ask before sudo
./scripts/install-revel.sh --yes       # non-interactive approve
```

The installer looks for Python 3.11+, sqlite3, git, pip/venv, existing `revelctl`, and XDG paths. It prompts before using sudo to install missing host packages. Graph store data lives under XDG (`~/.local/share/revel`). User files live in `~/Revel/files`. No distro or init system is required.

## Install (no distro package)

Wheel / editable (community):

```sh
python3 -m venv ~/.venvs/revel
. ~/.venvs/revel/bin/activate
pip install -e '.[web]'          # CLI + FastAPI
# pip install -e '.[store]'      # optional Kuzu
revelctl --help
```

pipx (isolated CLI):

```sh
pipx install .
# or from a built wheel:
python3 -m pip install build
python3 -m build
pipx install dist/revel-0.1.0-py3-none-any.whl
```

Container (optional; same Python entrypoint):

```sh
docker build -t revel:0.1.0 .
docker run --rm -p 8000:8000 -v "$HOME/Revel:/root/Revel" revel:0.1.0 serve --host 0.0.0.0
```

There is no `.deb` / `pacman` / AUR policy. No named distro or init is a product requirement.
