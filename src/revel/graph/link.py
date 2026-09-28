"""Directed link between any two nodes (#9).

Assignment onto a task is a link, not a join table per pair.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from revel.graph.errors import UnknownLinkKindError
from revel.graph.node import Node

CORE_LINK_KINDS: tuple[str, ...] = (
    "assigned",
    "attached",
    "blocks",
    "child_of",
    "belongs_to",
    "converted_to",
    "relates_to",
    "owns",
    "member_of",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LinkKind:
    """Known verbs. Extra kinds are allowed; empty is not."""

    ASSIGNED = "assigned"
    ATTACHED = "attached"
    BLOCKS = "blocks"
    CHILD_OF = "child_of"
    BELONGS_TO = "belongs_to"
    CONVERTED_TO = "converted_to"
    RELATES_TO = "relates_to"
    OWNS = "owns"
    MEMBER_OF = "member_of"

    @staticmethod
    def require(name: str) -> str:
        key = str(name).strip().lower()
        if not key:
            raise UnknownLinkKindError("link kind must be a non-empty name")
        return key


@dataclass(frozen=True)
class Link:
    id: str
    source_id: str
    target_id: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        source: Node | str,
        target: Node | str,
        kind: str,
        *,
        payload: dict[str, Any] | None = None,
        id: str | None = None,
    ) -> Link:
        """Request: from, to, verb. Response: a directed Link."""
        src = source.id if isinstance(source, Node) else str(source)
        dst = target.id if isinstance(target, Node) else str(target)
        if not src or not dst:
            raise ValueError("link source and target ids must be non-empty")
        if src == dst:
            raise ValueError("link cannot point a node at itself")
        return cls(
            id=id or str(uuid4()),
            source_id=src,
            target_id=dst,
            kind=LinkKind.require(kind),
            payload=dict(payload or {}),
        )
