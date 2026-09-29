"""Loadable demo graph. Same Node/Link types as production.

Ids are stable (demo-*) so a second load upserts instead of cloning.
"""

from __future__ import annotations

from revel.graph import Link
from revel.plane import create_node, list_nodes
from revel.store.base import GraphStore

# Story: Northwind wants a renewal. Work, CRM, comms, and support share one graph.
_NODES: tuple[dict, ...] = (
    {"id": "demo-project-renewal", "type": "project", "title": "Northwind renewal", "payload": {"column": "doing", "start": "2026-09-15", "end": "2026-10-31"}},
    {"id": "demo-milestone-kickoff", "type": "milestone", "title": "Kickoff signed", "payload": {"column": "done", "start": "2026-09-20", "end": "2026-09-20"}},
    {"id": "demo-task-brief", "type": "task", "title": "Write renewal brief", "payload": {"column": "doing", "start": "2026-09-22", "end": "2026-10-03", "progress": 40}},
    {"id": "demo-task-proposal", "type": "task", "title": "Draft proposal PDF", "payload": {"column": "todo", "start": "2026-10-04", "end": "2026-10-10", "progress": 0}},
    {"id": "demo-task-call", "type": "task", "title": "Schedule decision call", "payload": {"column": "todo", "due": "2026-10-15"}},
    {"id": "demo-file-brief", "type": "file", "title": "brief.md", "payload": {"column": "doing", "path": "docs/brief.md"}},
    {"id": "demo-email-intro", "type": "email", "title": "Re: contract renewal", "payload": {"column": "done", "start": "2026-09-18"}},
    {"id": "demo-event-call", "type": "event", "title": "Decision call", "payload": {"column": "todo", "start": "2026-10-15", "end": "2026-10-15"}},
    {"id": "demo-account-northwind", "type": "account", "title": "Northwind Traders", "payload": {"column": "doing"}},
    {"id": "demo-contact-ada", "type": "contact", "title": "Ada North", "payload": {"column": "doing", "role": "buyer"}},
    {"id": "demo-lead-inbound", "type": "lead", "title": "Inbound from trade show", "payload": {"column": "done"}},
    {"id": "demo-opp-renewal", "type": "opportunity", "title": "FY27 renewal", "payload": {"column": "doing", "value": "48000"}},
    {"id": "demo-ticket-login", "type": "ticket", "title": "SSO login flake", "payload": {"column": "doing", "due": "2026-10-02"}},
    {"id": "demo-campaign-q4", "type": "campaign", "title": "Q4 renewal drip", "payload": {"column": "doing", "start": "2026-10-01", "end": "2026-10-31"}},
    {"id": "demo-content-onepager", "type": "content", "title": "Renewal one-pager", "payload": {"column": "todo"}},
    {"id": "demo-inventory-seats", "type": "inventory_item", "title": "Seat pack 25", "payload": {"column": "todo", "sku": "SEAT-25"}},
    {"id": "demo-kb-sso", "type": "knowledge_article", "title": "How SSO login works", "payload": {"column": "done"}},
    {"id": "demo-user-sam", "type": "user", "title": "Sam Owner", "payload": {"column": "doing"}},
    {"id": "demo-group-sales", "type": "group", "title": "Sales", "payload": {"column": "doing"}},
)

_LINKS: tuple[tuple[str, str, str, str], ...] = (
    ("demo-link-lead-opp", "demo-lead-inbound", "demo-opp-renewal", "converted_to"),
    ("demo-link-opp-acct", "demo-opp-renewal", "demo-account-northwind", "belongs_to"),
    ("demo-link-contact-acct", "demo-contact-ada", "demo-account-northwind", "belongs_to"),
    ("demo-link-proj-acct", "demo-project-renewal", "demo-account-northwind", "relates_to"),
    ("demo-link-ms-proj", "demo-milestone-kickoff", "demo-project-renewal", "child_of"),
    ("demo-link-brief-proj", "demo-task-brief", "demo-project-renewal", "child_of"),
    ("demo-link-prop-proj", "demo-task-proposal", "demo-project-renewal", "child_of"),
    ("demo-link-call-proj", "demo-task-call", "demo-project-renewal", "child_of"),
    ("demo-link-blocks", "demo-task-brief", "demo-task-proposal", "blocks"),
    ("demo-link-file-task", "demo-file-brief", "demo-task-brief", "attached"),
    ("demo-link-email-task", "demo-email-intro", "demo-task-brief", "assigned"),
    ("demo-link-event-task", "demo-event-call", "demo-task-call", "relates_to"),
    ("demo-link-ticket-kb", "demo-ticket-login", "demo-kb-sso", "relates_to"),
    ("demo-link-ticket-acct", "demo-ticket-login", "demo-account-northwind", "belongs_to"),
    ("demo-link-campaign-opp", "demo-campaign-q4", "demo-opp-renewal", "relates_to"),
    ("demo-link-content-camp", "demo-content-onepager", "demo-campaign-q4", "child_of"),
    ("demo-link-inv-opp", "demo-inventory-seats", "demo-opp-renewal", "relates_to"),
    ("demo-link-sam-task", "demo-user-sam", "demo-task-brief", "assigned"),
    ("demo-link-sam-group", "demo-user-sam", "demo-group-sales", "member_of"),
    ("demo-link-group-owns", "demo-group-sales", "demo-opp-renewal", "owns"),
)


def load_demo(store: GraphStore) -> dict[str, int]:
    nodes = 0
    for spec in _NODES:
        create_node(store, spec["type"], spec["title"], payload=spec["payload"], id=spec["id"])
        nodes += 1
    links = 0
    for link_id, src, dst, kind in _LINKS:
        if store.get_link(link_id) is None:
            store.put_link(Link.create(src, dst, kind, id=link_id))
        links += 1
    return {"nodes": nodes, "links": links, "total_nodes": len(list_nodes(store))}


def dashboard(store: GraphStore) -> dict:
    nodes = list_nodes(store)
    by_type: dict[str, int] = {}
    by_column: dict[str, int] = {"todo": 0, "doing": 0, "done": 0}
    dated = 0
    for node in nodes:
        by_type[node.type] = by_type.get(node.type, 0) + 1
        col = str(node.payload.get("column") or "todo")
        if col not in by_column:
            by_column[col] = 0
        by_column[col] += 1
        if node.payload.get("start") or node.payload.get("due"):
            dated += 1
    recent = sorted(nodes, key=lambda n: n.created_at, reverse=True)[:8]
    return {
        "nodes": len(nodes),
        "links": len(store.all_links()),
        "dated": dated,
        "by_type": dict(sorted(by_type.items())),
        "by_column": by_column,
        "recent": [{"id": n.id, "type": n.type, "title": n.title, "column": n.payload.get("column")} for n in recent],
        "demo_loaded": any(n.id.startswith("demo-") for n in nodes),
    }
