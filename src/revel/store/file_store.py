"""JSON file store. Used when Kuzu is not installed.

Not SQL. Same Node/Link objects as memory and Kuzu.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from revel.graph import Link, Node


class FileGraphStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._nodes: dict[str, Node] = {}
        self._links: dict[str, Link] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.is_file():
            return
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        for item in raw.get("nodes", []):
            node = Node(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                payload=dict(item.get("payload") or {}),
                created_at=datetime.fromisoformat(item["created_at"]),
            )
            self._nodes[node.id] = node
        for item in raw.get("links", []):
            link = Link(
                id=item["id"],
                source_id=item["source_id"],
                target_id=item["target_id"],
                kind=item["kind"],
                payload=dict(item.get("payload") or {}),
                created_at=datetime.fromisoformat(item["created_at"]),
            )
            self._links[link.id] = link

    def _save(self) -> None:
        payload = {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "title": n.title,
                    "payload": n.payload,
                    "created_at": n.created_at.isoformat(),
                }
                for n in self._nodes.values()
            ],
            "links": [
                {
                    "id": ln.id,
                    "source_id": ln.source_id,
                    "target_id": ln.target_id,
                    "kind": ln.kind,
                    "payload": ln.payload,
                    "created_at": ln.created_at.isoformat(),
                }
                for ln in self._links.values()
            ],
        }
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def put_node(self, node: Node) -> Node:
        self._nodes[node.id] = node
        self._save()
        return node

    def get_node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def put_link(self, link: Link) -> Link:
        if link.source_id not in self._nodes or link.target_id not in self._nodes:
            raise KeyError("both ends of a link must exist as nodes")
        self._links[link.id] = link
        self._save()
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

    def delete_link(self, link_id: str) -> None:
        self._links.pop(link_id, None)
        self._save()

    def delete_node(self, node_id: str) -> None:
        self._nodes.pop(node_id, None)
        drop = [lid for lid, link in self._links.items() if link.source_id == node_id or link.target_id == node_id]
        for lid in drop:
            self._links.pop(lid, None)
        self._save()

    def close(self) -> None:
        return None
