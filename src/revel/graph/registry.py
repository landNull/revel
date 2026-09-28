"""Extensible registry of node types (#8).

The 17 core types are registered at import. Extra types can be added
without a new app or table.
"""

from __future__ import annotations

from collections.abc import Iterable

from revel.graph.errors import UnknownNodeTypeError

CORE_NODE_TYPES: tuple[str, ...] = (
    "task",
    "project",
    "milestone",
    "file",
    "email",
    "event",
    "lead",
    "opportunity",
    "account",
    "contact",
    "ticket",
    "campaign",
    "content",
    "inventory_item",
    "knowledge_article",
    "user",
    "group",
)


class NodeTypeRegistry:
    def __init__(self, types: Iterable[str] = CORE_NODE_TYPES) -> None:
        self._types: dict[str, None] = {}
        for name in types:
            self.register(name)

    def register(self, name: str) -> str:
        key = _norm(name)
        if not key:
            raise UnknownNodeTypeError("node type must be a non-empty name")
        self._types[key] = None
        return key

    def known(self, name: str) -> bool:
        return _norm(name) in self._types

    def require(self, name: str) -> str:
        key = _norm(name)
        if key not in self._types:
            raise UnknownNodeTypeError(f"unknown node type: {name!r}")
        return key

    def names(self) -> tuple[str, ...]:
        return tuple(self._types)


def _norm(name: str) -> str:
    return str(name).strip().lower()


default_registry = NodeTypeRegistry()


def register_node_type(name: str) -> str:
    """Extend the process-wide registry."""
    return default_registry.register(name)
