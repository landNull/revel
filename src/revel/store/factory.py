"""Open a store. Request: path + engine. Response: GraphStore."""

from __future__ import annotations

from pathlib import Path

from revel.store.base import GraphStore
from revel.store.memory import MemoryGraphStore
from revel.store.paths import default_store_path


def open_store(path: str | Path | None = None, *, engine: str = "kuzu") -> GraphStore:
    kind = engine.strip().lower()
    if kind == "memory":
        return MemoryGraphStore()
    if kind == "file":
        from revel.store.file_store import FileGraphStore

        raw = Path(path or default_store_path())
        json_path = raw.with_suffix(".json") if raw.suffix == ".kuzu" else raw
        return FileGraphStore(json_path)
    if kind in {"kuzu", "default"}:
        try:
            from revel.store.kuzu_store import KuzuGraphStore

            return KuzuGraphStore(path or default_store_path())
        except ImportError:
            return MemoryGraphStore()
    if kind == "neo4j":
        raise NotImplementedError("Neo4j is the scale path only (D005). Use kuzu.")
    raise ValueError(f"unknown store engine: {engine!r}")
