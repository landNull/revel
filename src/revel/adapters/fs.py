"""Local filesystem adapter (#21).

Canonical tree: ~/Revel/files/<name>
Override with REVEL_HOME. Bytes stay on the host FS. Graph stores path + hash.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from revel.graph import Node
from revel.plane import create_node, link_nodes, list_nodes
from revel.store.base import GraphStore


def revel_home() -> Path:
    override = os.environ.get("REVEL_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / "Revel").resolve()


def files_root() -> Path:
    root = revel_home() / "files"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unique_dest(name: str) -> Path:
    dest = files_root() / name
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    n = 2
    while True:
        candidate = files_root() / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def ingest_file(
    store: GraphStore,
    src: str | Path,
    *,
    attach_to: str | None = None,
) -> Node:
    source = Path(src).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"not a file: {source}")
    digest = _hash_file(source)
    for node in list_nodes(store, "file"):
        if node.payload.get("sha256") == digest:
            if attach_to:
                link_nodes(store, node.id, attach_to, "attached")
            return node
    dest = source if files_root() in source.parents or source.parent == files_root() else None
    if dest is None:
        dest = _unique_dest(source.name)
        shutil.copy2(source, dest)
        digest = _hash_file(dest)
    node = create_node(
        store,
        "file",
        dest.name,
        payload={
            "path": str(dest),
            "sha256": digest,
            "bytes": dest.stat().st_size,
            "column": "todo",
        },
    )
    if attach_to:
        link_nodes(store, node.id, attach_to, "attached")
    return node


def read_bytes(node: Node) -> bytes:
    path = node.payload.get("path")
    if not path:
        raise ValueError("file node has no path")
    return Path(path).read_bytes()
