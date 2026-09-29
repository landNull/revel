"""In-process store. Survives only as long as the process (not M2 production)."""

from __future__ import annotations

from revel.graph import Link, Node


class MemoryGraphStore:
    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._links: dict[str, Link] = {}

    def put_node(self, node: Node) -> Node:
        self._nodes[node.id] = node
        return node

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def put_link(self, link: Link) -> Link:
        if link.source_id not in self._nodes or link.target_id not in self._nodes:
            raise KeyError("both ends of a link must exist as nodes")
        self._links[link.id] = link
        return link

    def get_link(self, link_id: str) -> Link | None:
        return self._links.get(link_id)

    def links_from(self, node_id: str) -> list[Link]:
        return [link for link in self._links.values() if link.source_id == node_id]

    def links_to(self, node_id: str) -> list[Link]:
        return [link for link in self._links.values() if link.target_id == node_id]

    def all_nodes(self) -> list[Node]:
        return list(self._nodes.values())

    def all_links(self) -> list[Link]:
        return list(self._links.values())

    def close(self) -> None:
        return None
