"""List projection: same nodes, ordered. No extra store."""

from __future__ import annotations

from datetime import date

from revel.graph import Node
from revel.plane import list_nodes
from revel.projection.dates import due_of
from revel.store.base import GraphStore


def listed(store: GraphStore, type: str | None = None, *, sort: str = "title") -> list[Node]:
    nodes = list(list_nodes(store, type))
    key = sort.strip().lower()
    if key == "due":
        return sorted(nodes, key=lambda n: (due_of(n) is None, due_of(n) or date.max, n.title.lower()))
    if key == "type":
        return sorted(nodes, key=lambda n: (n.type, n.title.lower()))
    return sorted(nodes, key=lambda n: n.title.lower())
