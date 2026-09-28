"""Graph persistence adapters (M2).

Core types stay in revel.graph. This package talks to disk.
Default engine: Kuzu (D005). Memory store is for tests / no-kuzu hosts.
Neo4j is documented scale-only, not implemented here.
"""

from revel.store.base import GraphStore
from revel.store.memory import MemoryGraphStore
from revel.store.paths import default_store_path
from revel.store.factory import open_store

__all__ = [
    "GraphStore",
    "MemoryGraphStore",
    "default_store_path",
    "open_store",
]
