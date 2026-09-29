"""Calendar projection for FullCalendar standard plugins (M6) and CLI."""

from __future__ import annotations

from datetime import date

from revel.graph import Node
from revel.plane import list_nodes
from revel.projection.dates import end_of, iso, start_of
from revel.store.base import GraphStore


def dated_nodes(store: GraphStore, type: str | None = None) -> list[Node]:
    return [node for node in list_nodes(store, type) if start_of(node)]


def events_between(
    store: GraphStore,
    start: date | None = None,
    end: date | None = None,
    type: str | None = None,
) -> list[Node]:
    out: list[Node] = []
    for node in dated_nodes(store, type):
        begins = start_of(node)
        finishes = end_of(node)
        if begins is None:
            continue
        if start and finishes and finishes < start:
            continue
        if end and begins > end:
            continue
        out.append(node)
    return sorted(out, key=lambda n: start_of(n) or date.min)


def to_fullcalendar(store: GraphStore, type: str | None = None) -> list[dict]:
    events: list[dict] = []
    for node in dated_nodes(store, type):
        events.append(
            {
                "id": node.id,
                "title": node.title,
                "start": iso(start_of(node)),
                "end": iso(end_of(node)),
                "extendedProps": {"type": node.type, "column": node.payload.get("column")},
            }
        )
    return events
