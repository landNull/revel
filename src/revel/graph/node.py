"""A work object is one kind of thing: a node with a type (#8, #10–#14)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from revel.graph.registry import NodeTypeRegistry, default_registry


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    title: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        type: str,
        title: str,
        *,
        payload: dict[str, Any] | None = None,
        id: str | None = None,
        registry: NodeTypeRegistry | None = None,
    ) -> Node:
        """Request: type + title. Response: a Node. Store not involved."""
        reg = registry or default_registry
        kind = reg.require(type)
        text = str(title).strip()
        if not text:
            raise ValueError("node title must be non-empty")
        return cls(
            id=id or str(uuid4()),
            type=kind,
            title=text,
            payload=dict(payload or {}),
        )
