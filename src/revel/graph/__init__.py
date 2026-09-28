"""Core graph types. No store engine here (M2 / Kuzu).

Request: construct a Node or Link.
Response: a value object. Persistence is a later adapter.
"""

from revel.graph.errors import UnknownNodeTypeError, UnknownLinkKindError
from revel.graph.families import (
    COMMS_TYPES,
    CRM_TYPES,
    IDENTITY_TYPES,
    MARKETING_TYPES,
    SUPPORT_TYPES,
    WORK_TYPES,
)
from revel.graph.link import Link, LinkKind
from revel.graph.node import Node
from revel.graph.registry import (
    CORE_NODE_TYPES,
    NodeTypeRegistry,
    default_registry,
    register_node_type,
)

__all__ = [
    "COMMS_TYPES",
    "CORE_NODE_TYPES",
    "CRM_TYPES",
    "IDENTITY_TYPES",
    "Link",
    "LinkKind",
    "MARKETING_TYPES",
    "Node",
    "NodeTypeRegistry",
    "SUPPORT_TYPES",
    "UnknownLinkKindError",
    "UnknownNodeTypeError",
    "WORK_TYPES",
    "default_registry",
    "register_node_type",
]
