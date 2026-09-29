"""ISO date helpers shared by calendar and gantt views."""

from __future__ import annotations

from datetime import date, datetime

from revel.graph import Node


def parse_day(value: object) -> date | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    if not text:
        return None
    if "T" in text:
        return datetime.fromisoformat(text).date()
    return date.fromisoformat(text[:10])


def iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def start_of(node: Node) -> date | None:
    return parse_day(node.payload.get("start") or node.payload.get("due"))


def end_of(node: Node) -> date | None:
    return parse_day(node.payload.get("end")) or start_of(node)


def due_of(node: Node) -> date | None:
    return parse_day(node.payload.get("due")) or start_of(node)
