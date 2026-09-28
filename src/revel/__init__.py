"""Revel core package.

Public surface is Node/Link plus create/link/query/mutate (D006).
This tree is the community edition (D008, AGPL-3.0).
"""

from revel.graph import Link, Node, default_registry

__version__ = "0.1.0"

__all__ = ["Link", "Node", "default_registry", "__version__"]
