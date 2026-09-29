"""Gantt projection for Frappe Gantt (M6) and CLI.

Dependencies come from directed links with kind blocks|depends|blocked_by.
"""

from __future__ import annotations

from revel.graph import Node
from revel.plane import list_nodes
from revel.projection.dates import end_of, iso, start_of
from revel.store.base import GraphStore

_DEP_KINDS = frozenset({"blocks", "depends", "depends_on", "blocked_by"})


def _progress(node: Node) -> float:
    raw = node.payload.get("progress", 0)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, value))


def _deps(store: GraphStore, node: Node) -> list[str]:
    ids: list[str] = []
    for link in store.links_to(node.id):
        if link.kind in _DEP_KINDS:
            ids.append(link.source_id)
    for link in store.links_from(node.id):
        if link.kind in {"depends", "depends_on"}:
            ids.append(link.target_id)
    return ids


def scheduled(store: GraphStore, type: str | None = None) -> list[Node]:
    return [node for node in list_nodes(store, type) if start_of(node)]


def to_frappe_gantt(store: GraphStore, type: str | None = None) -> list[dict]:
    tasks: list[dict] = []
    for node in scheduled(store, type):
        item = {
            "id": node.id,
            "name": node.title,
            "start": iso(start_of(node)),
            "end": iso(end_of(node)),
            "progress": _progress(node),
        }
        deps = _deps(store, node)
        if deps:
            item["dependencies"] = ",".join(deps)
        tasks.append(item)
    return tasks
