"""In-process control plane (D006).

Request: create / link / query / mutate / list.
Response: Node, Link, or lists of those.
TUI and FastAPI should call these functions, not the store directly.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from revel.graph import Link, Node
from revel.store.base import GraphStore


def create_node(
    store: GraphStore,
    type: str,
    title: str,
    *,
    payload: dict[str, Any] | None = None,
    id: str | None = None,
) -> Node:
    node = Node.create(type, title, payload=payload, id=id)
    return store.put_node(node)


def link_nodes(
    store: GraphStore,
    source_id: str,
    target_id: str,
    kind: str,
    *,
    payload: dict[str, Any] | None = None,
) -> Link:
    source = store.get_node(source_id)
    target = store.get_node(target_id)
    if source is None or target is None:
        raise KeyError("both ends of a link must exist as nodes")
    return store.put_link(Link.create(source, target, kind, payload=payload))


def query_node(store: GraphStore, node_id: str) -> Node | None:
    return store.get_node(node_id)


def list_nodes(store: GraphStore, type: str | None = None) -> list[Node]:
    nodes = store.all_nodes()
    if type:
        want = type.strip().lower()
        return [node for node in nodes if node.type == want]
    return nodes


def neighbors(store: GraphStore, node_id: str) -> tuple[list[Link], list[Link]]:
    return store.links_from(node_id), store.links_to(node_id)


def mutate_node(
    store: GraphStore,
    node_id: str,
    *,
    title: str | None = None,
    payload: dict[str, Any] | None = None,
    replace_payload: bool = False,
) -> Node:
    node = store.get_node(node_id)
    if node is None:
        raise KeyError(f"unknown node: {node_id}")
    new_title = title.strip() if title is not None else node.title
    if not new_title:
        raise ValueError("node title must be non-empty")
    new_payload = dict(node.payload)
    if payload:
        if replace_payload:
            new_payload = dict(payload)
        else:
            new_payload.update(payload)
    updated = replace(node, title=new_title, payload=new_payload)
    return store.put_node(updated)
