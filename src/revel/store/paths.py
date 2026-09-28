"""XDG data path. Distro/init are not part of the path."""

from __future__ import annotations

import os
from pathlib import Path


def default_store_path() -> Path:
    data = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(data) / "revel" / "store" / "revel.kuzu"
