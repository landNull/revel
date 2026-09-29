"""Kuzu adapter. Import kuzu only here.

Schema is one node table + one relationship table so all 17 types
share the same graph. Payload is JSON text.

Scale path (not implemented): same Node/Link objects behind a Neo4j
driver. Do not add Neo4j until this adapter works on a workstation.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from revel.graph import Link, Node

_NODE_TABLE = "RevelNode"
_REL_TABLE = "RevelLink"


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class KuzuGraphStore:
    def __init__(self, path: str | Path) -> None:
        try:
            import kuzu
        except ImportError as exc:
            raise ImportError(
                "Kuzu is not installed. From the revel venv: pip install 'revel[store]'"
            ) from exc
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._db = kuzu.Database(str(self._path))
        self._conn = kuzu.Connection(self._db)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.execute(
            f"CREATE NODE TABLE IF NOT EXISTS {_NODE_TABLE}("
            "id STRING PRIMARY KEY, type STRING, title STRING, "
            "payload STRING, created_at STRING)"
        )
        self._conn.execute(
            f"CREATE REL TABLE IF NOT EXISTS {_REL_TABLE}("
            f"FROM {_NODE_TABLE} TO {_NODE_TABLE}, "
            "link_id STRING, kind STRING, payload STRING, created_at STRING)"
        )

    def put_node(self, node: Node) -> Node:
        payload = json.dumps(node.payload)
        self._conn.execute(
            f"MERGE (n:{_NODE_TABLE} {{id: $id}}) "
            "SET n.type = $type, n.title = $title, "
            "n.payload = $payload, n.created_at = $created_at",
            {
                "id": node.id,
                "type": node.type,
                "title": node.title,
                "payload": payload,
                "created_at": _iso(node.created_at),
            },
        )
        return node

    def get_node(self, node_id: str) -> Node | None:
        result = self._conn.execute(
            f"MATCH (n:{_NODE_TABLE} {{id: $id}}) "
            "RETURN n.id, n.type, n.title, n.payload, n.created_at",
            {"id": node_id},
        )
        row = _one_row(result)
        if row is None:
            return None
        return _node_from_row(row)

    def put_link(self, link: Link) -> Link:
        if self.get_node(link.source_id) is None or self.get_node(link.target_id) is None:
            raise KeyError("both ends of a link must exist as nodes")
        payload = json.dumps(link.payload)
        params = {
            "src": link.source_id,
            "dst": link.target_id,
            "link_id": link.id,
            "kind": link.kind,
            "payload": payload,
            "created_at": _iso(link.created_at),
        }
        existing = self.get_link(link.id)
        if existing is not None:
            self._conn.execute(
                f"MATCH (a:{_NODE_TABLE})-[r:{_REL_TABLE}]->(b:{_NODE_TABLE}) "
                "WHERE r.link_id = $link_id "
                "SET r.kind = $kind, r.payload = $payload, r.created_at = $created_at",
                params,
            )
            return link
        # SET properties after CREATE so Kuzu does not parse a map-literal
        # with an extra closing brace (seen on pipx wheels).
        self._conn.execute(
            f"MATCH (a:{_NODE_TABLE} {{id: $src}}), (b:{_NODE_TABLE} {{id: $dst}}) "
            f"CREATE (a)-[r:{_REL_TABLE}]->(b) "
            "SET r.link_id = $link_id, r.kind = $kind, "
            "r.payload = $payload, r.created_at = $created_at",
            params,
        )
        return link

    def get_link(self, link_id: str) -> Link | None:
        result = self._conn.execute(
            f"MATCH (a:{_NODE_TABLE})-[r:{_REL_TABLE}]->(b:{_NODE_TABLE}) "
            "WHERE r.link_id = $link_id "
            "RETURN r.link_id, a.id, b.id, r.kind, r.payload, r.created_at",
            {"link_id": link_id},
        )
        row = _one_row(result)
        if row is None:
            return None
        return _link_from_row(row)

    def links_from(self, node_id: str) -> list[Link]:
        result = self._conn.execute(
            f"MATCH (a:{_NODE_TABLE} {{id: $id}})-[r:{_REL_TABLE}]->(b:{_NODE_TABLE}) "
            "RETURN r.link_id, a.id, b.id, r.kind, r.payload, r.created_at",
            {"id": node_id},
        )
        return [_link_from_row(row) for row in _all_rows(result)]

    def links_to(self, node_id: str) -> list[Link]:
        result = self._conn.execute(
            f"MATCH (a:{_NODE_TABLE})-[r:{_REL_TABLE}]->(b:{_NODE_TABLE} {{id: $id}}) "
            "RETURN r.link_id, a.id, b.id, r.kind, r.payload, r.created_at",
            {"id": node_id},
        )
        return [_link_from_row(row) for row in _all_rows(result)]

    def all_nodes(self) -> list[Node]:
        result = self._conn.execute(
            f"MATCH (n:{_NODE_TABLE}) "
            "RETURN n.id, n.type, n.title, n.payload, n.created_at"
        )
        return [_node_from_row(row) for row in _all_rows(result)]

    def all_links(self) -> list[Link]:
        result = self._conn.execute(
            f"MATCH (a:{_NODE_TABLE})-[r:{_REL_TABLE}]->(b:{_NODE_TABLE}) "
            "RETURN r.link_id, a.id, b.id, r.kind, r.payload, r.created_at"
        )
        return [_link_from_row(row) for row in _all_rows(result)]

    def close(self) -> None:
        self._conn = None
        self._db = None


def _one_row(result) -> tuple | None:
    rows = _all_rows(result)
    return rows[0] if rows else None


def _all_rows(result) -> list[tuple]:
    rows: list[tuple] = []
    if result is None:
        return rows
    has_next = getattr(result, "has_next", None)
    get_next = getattr(result, "get_next", None)
    if callable(has_next) and callable(get_next):
        while result.has_next():
            rows.append(tuple(result.get_next()))
        return rows
    try:
        return [tuple(row) for row in result]
    except TypeError:
        return rows


def _node_from_row(row: tuple) -> Node:
    payload = json.loads(row[3] or "{}")
    return Node(
        id=row[0],
        type=row[1],
        title=row[2],
        payload=payload,
        created_at=_parse_dt(row[4]),
    )


def _link_from_row(row: tuple) -> Link:
    payload = json.loads(row[4] or "{}")
    return Link(
        id=row[0],
        source_id=row[1],
        target_id=row[2],
        kind=row[3],
        payload=payload,
        created_at=_parse_dt(row[5]),
    )
