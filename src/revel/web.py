"""FastAPI HTTP adapter (D007). Same plane as revelctl. Widgets are not here."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from revel.plane import (
    create_node,
    link_nodes,
    list_nodes,
    mutate_node,
    neighbors,
    query_node,
)
from revel.projection.calendar import to_fullcalendar
from revel.projection.gantt import to_frappe_gantt
from revel.projection.kanban import to_jkanban
from revel.store import open_store

_STORE = None


def get_store():
    global _STORE
    if _STORE is None:
        _STORE = open_store()
    return _STORE


def set_store(store) -> None:
    global _STORE
    _STORE = store


class NodeIn(BaseModel):
    type: str
    title: str
    payload: dict[str, Any] = Field(default_factory=dict)
    id: str | None = None


class LinkIn(BaseModel):
    source_id: str
    target_id: str
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)


class MutateIn(BaseModel):
    title: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


def _node_out(node) -> dict:
    return {
        "id": node.id,
        "type": node.type,
        "title": node.title,
        "payload": node.payload,
        "created_at": node.created_at.isoformat(),
    }


def create_app() -> FastAPI:
    app = FastAPI(title="revel", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        return {"ok": True}

    @app.post("/nodes")
    def http_create(body: NodeIn) -> dict:
        node = create_node(
            get_store(), body.type, body.title, payload=body.payload, id=body.id
        )
        return _node_out(node)

    @app.get("/nodes")
    def http_list(type: str | None = None) -> list[dict]:
        return [_node_out(n) for n in list_nodes(get_store(), type)]

    @app.get("/nodes/{node_id}")
    def http_query(node_id: str) -> dict:
        node = query_node(get_store(), node_id)
        if node is None:
            raise HTTPException(404, "unknown node")
        outgoing, incoming = neighbors(get_store(), node_id)
        return {
            **_node_out(node),
            "outgoing": [ln.id for ln in outgoing],
            "incoming": [ln.id for ln in incoming],
        }

    @app.patch("/nodes/{node_id}")
    def http_mutate(node_id: str, body: MutateIn) -> dict:
        try:
            node = mutate_node(
                get_store(), node_id, title=body.title, payload=body.payload
            )
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        return _node_out(node)

    @app.post("/links")
    def http_link(body: LinkIn) -> dict:
        try:
            link = link_nodes(
                get_store(),
                body.source_id,
                body.target_id,
                body.kind,
                payload=body.payload,
            )
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        return {
            "id": link.id,
            "source_id": link.source_id,
            "target_id": link.target_id,
            "kind": link.kind,
        }

    @app.get("/board")
    def http_board(type: str | None = None) -> list[dict]:
        return to_jkanban(get_store(), type)

    @app.get("/calendar")
    def http_cal(type: str | None = None) -> list[dict]:
        return to_fullcalendar(get_store(), type)

    @app.get("/gantt")
    def http_gantt(type: str | None = None) -> list[dict]:
        return to_frappe_gantt(get_store(), type)

    return app


app = create_app()
