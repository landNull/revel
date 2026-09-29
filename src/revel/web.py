"""FastAPI HTTP adapter (D007). Same plane as revelctl. HTML pages are views."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from revel.plane import (
    create_node,
    delete_node,
    link_nodes,
    list_nodes,
    mutate_node,
    neighbors,
    query_node,
)
from revel.projection.calendar import to_fullcalendar
from revel.projection.gantt import to_frappe_gantt
from revel.demo import dashboard, load_demo
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


_HEAD = """
  <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\">
  <link rel=\"stylesheet\" href=\"/static/ui/revel.css\">
  <script defer src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js\"></script>
  <script defer src=\"/static/ui/revel-theme.js\"></script>
"""

_NAV = """
<nav class=\"navbar navbar-expand-md revel-nav\">
  <div class=\"container-fluid\">
    <a class=\"navbar-brand\" href=\"/\">Revel</a>
    <button class=\"navbar-toggler\" type=\"button\" data-bs-toggle=\"collapse\" data-bs-target=\"#revelNav\">
      <span class=\"navbar-toggler-icon\"></span>
    </button>
    <div class=\"collapse navbar-collapse\" id=\"revelNav\">
      <ul class=\"navbar-nav me-auto\">
        <li class=\"nav-item\"><a class=\"nav-link\" href=\"/ui/dashboard\">Dashboard</a></li>
        <li class=\"nav-item\"><a class=\"nav-link\" href=\"/ui/board\">Board</a></li>
        <li class=\"nav-item\"><a class=\"nav-link\" href=\"/ui/calendar\">Calendar</a></li>
        <li class=\"nav-item\"><a class=\"nav-link\" href=\"/ui/gantt\">Gantt</a></li>
        <li class=\"nav-item\"><a class=\"nav-link\" href=\"/docs\">API</a></li>
      </ul>
      <button type=\"button\" class=\"btn btn-sm btn-outline-light\" id=\"revel-theme-toggle\">Dark</button>
    </div>
  </div>
</nav>
"""


def _page(name: str) -> HTMLResponse:
    html = files(\"revel.ui\").joinpath(name).read_text(encoding=\"utf-8\")
    html = html.replace(\"<!--REVEL_HEAD-->\", _HEAD, 1)
    html = html.replace(\"<!--REVEL_NAV-->\", _NAV, 1)
    return HTMLResponse(html)


def create_app() -> FastAPI:
    app = FastAPI(title=\"revel\", version=\"0.1.0\")
    static_dir = Path(__file__).resolve().parent / \"ui\" / \"static\"
    app.mount(\"/static/ui\", StaticFiles(directory=static_dir), name=\"static_ui\")

    @app.get(\"/\", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        return _page(\"dashboard.html\")

    @app.get(\"/ui/dashboard\", response_class=HTMLResponse)
    def ui_dash() -> HTMLResponse:
        return _page(\"dashboard.html\")

    @app.get(\"/ui/board\", response_class=HTMLResponse)
    def ui_board() -> HTMLResponse:
        return _page(\"board.html\")

    @app.get(\"/ui/calendar\", response_class=HTMLResponse)
    def ui_cal() -> HTMLResponse:
        return _page(\"calendar.html\")

    @app.get(\"/ui/gantt\", response_class=HTMLResponse)
    def ui_gantt() -> HTMLResponse:
        return _page(\"gantt.html\")

    @app.get(\"/health\")
    def health() -> dict:
        return {\"ok\": True}

    @app.post(\"/nodes\")
    def http_create(body: NodeIn) -> dict:
        node = create_node(
            get_store(), body.type, body.title, payload=body.payload, id=body.id
        )
        return _node_out(node)

    @app.get(\"/nodes\")
    def http_list(type: str | None = None) -> list[dict]:
        return [_node_out(n) for n in list_nodes(get_store(), type)]

    @app.get(\"/nodes/{node_id}\")
    def http_query(node_id: str) -> dict:
        node = query_node(get_store(), node_id)
        if node is None:
            raise HTTPException(404, \"unknown node\")
        outgoing, incoming = neighbors(get_store(), node_id)
        return {
            **_node_out(node),
            \"outgoing\": [ln.id for ln in outgoing],
            \"incoming\": [ln.id for ln in incoming],
        }

    @app.patch(\"/nodes/{node_id}\")
    def http_mutate(node_id: str, body: MutateIn) -> dict:
        try:
            node = mutate_node(
                get_store(), node_id, title=body.title, payload=body.payload
            )
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        return _node_out(node)

    @app.delete(\"/nodes/{node_id}\")
    def http_delete(node_id: str) -> dict:
        try:
            deleted = delete_node(get_store(), node_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        return {\"id\": deleted, \"deleted\": True}

    @app.post(\"/links\")
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
            \"id\": link.id,
            \"source_id\": link.source_id,
            \"target_id\": link.target_id,
            \"kind\": link.kind,
        }

    @app.get(\"/board\")
    def http_board(type: str | None = None) -> list[dict]:
        return to_jkanban(get_store(), type)

    @app.get(\"/calendar\")
    def http_cal(type: str | None = None) -> list[dict]:
        return to_fullcalendar(get_store(), type)

    @app.get(\"/gantt\")
    def http_gantt(type: str | None = None) -> list[dict]:
        return to_frappe_gantt(get_store(), type)

    @app.get(\"/stats\")
    def http_stats() -> dict:
        return dashboard(get_store())

    @app.post(\"/demo\")
    def http_demo() -> dict:
        return load_demo(get_store())

    return app


app = create_app()
