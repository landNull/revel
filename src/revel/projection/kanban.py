"""Kanban is a view, not a second task table.

Column lives on node.payload['column']: todo | doing | done.
jKanban JSON is produced here for M6; the web widget must not invent cards.
"""

from __future__ import annotations

from revel.graph import Node
from revel.plane import list_nodes, mutate_node
from revel.store.base import GraphStore

COLUMNS: tuple[str, ...] = ("todo", "doing", "done")
DEFAULT_COLUMN = "todo"


def column_of(node: Node) -> str:
    raw = str(node.payload.get("column") or DEFAULT_COLUMN).strip().lower()
    return raw if raw in COLUMNS else DEFAULT_COLUMN


def board(store: GraphStore, type: str | None = None) -> dict[str, list[Node]]:
    columns: dict[str, list[Node]] = {name: [] for name in COLUMNS}
    for node in list_nodes(store, type):
        columns[column_of(node)].append(node)
    return columns


def move_card(store: GraphStore, node_id: str, column: str) -> Node:
    dest = column.strip().lower()
    if dest not in COLUMNS:
        raise ValueError(f"unknown column {column!r}; use {', '.join(COLUMNS)}")
    return mutate_node(store, node_id, payload={"column": dest})


def to_jkanban(store: GraphStore, type: str | None = None) -> list[dict]:
    """Same payload jKanban / SortableJS will consume later."""
    titles = {"todo": "To Do", "doing": "Doing", "done": "Done"}
    out: list[dict] = []
    for name, nodes in board(store, type).items():
        out.append(
            {
                "id": name,
                "title": titles[name],
                "item": [
                    {
                        "id": node.id,
                        "title": node.title,
                        "type": node.type,
                    }
                    for node in nodes
                ],
            }
        )
    return out
