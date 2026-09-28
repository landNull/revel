"""revelctl — control-plane client (M3).

Request: a verb and arguments.
Response: printed Node/Link ids. Store is opened per invocation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from revel import __version__
from revel.plane import (
    create_node,
    link_nodes,
    list_nodes,
    mutate_node,
    neighbors,
    query_node,
)
from revel.projection.kanban import COLUMNS, board, move_card
from revel.store import open_store


def _store_from_env():
    engine = os.environ.get("REVEL_STORE_ENGINE", "kuzu")
    path = os.environ.get("REVEL_STORE_PATH")
    return open_store(path, engine=engine)


def _print_node(node) -> None:
    extra = f" payload={json.dumps(node.payload)}" if node.payload else ""
    sys.stdout.write(f"{node.id}  {node.type}  {node.title}{extra}\n")


def _print_link(link) -> None:
    sys.stdout.write(f"{link.id}  {link.source_id} -[{link.kind}]-> {link.target_id}\n")


def _payload(pairs: list[str] | None) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError(f"payload must be key=value, got {item!r}")
        key, value = item.split("=", 1)
        data[key] = value
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="revelctl",
        description="Revel control plane. Create, link, query, and mutate nodes.",
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd")

    p_create = sub.add_parser("create", help="create a node")
    p_create.add_argument("type")
    p_create.add_argument("title")
    p_create.add_argument("--id")
    p_create.add_argument("--set", dest="sets", action="append", default=[])

    p_link = sub.add_parser("link", help="link two existing nodes")
    p_link.add_argument("source_id")
    p_link.add_argument("target_id")
    p_link.add_argument("kind")

    p_query = sub.add_parser("query", help="show one node and its links")
    p_query.add_argument("id")

    p_list = sub.add_parser("list", help="list nodes, optionally by type")
    p_list.add_argument("type", nargs="?")

    p_mut = sub.add_parser("mutate", help="change title or payload")
    p_mut.add_argument("id")
    p_mut.add_argument("--title")
    p_mut.add_argument("--set", dest="sets", action="append", default=[])

    p_board = sub.add_parser("board", help="Kanban projection of nodes")
    p_board.add_argument("type", nargs="?")

    p_move = sub.add_parser("move", help="move a node to a Kanban column")
    p_move.add_argument("id")
    p_move.add_argument("column", choices=COLUMNS)

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.cmd is None:
        parser.print_help()
        return 0

    store = _store_from_env()
    try:
        if args.cmd == "create":
            node = create_node(
                store, args.type, args.title, payload=_payload(args.sets), id=args.id
            )
            _print_node(node)
            return 0
        if args.cmd == "link":
            link = link_nodes(store, args.source_id, args.target_id, args.kind)
            _print_link(link)
            return 0
        if args.cmd == "query":
            node = query_node(store, args.id)
            if node is None:
                sys.stderr.write(f"unknown node: {args.id}\n")
                return 1
            _print_node(node)
            outgoing, incoming = neighbors(store, node.id)
            for link in outgoing:
                sys.stdout.write("  out  ")
                _print_link(link)
            for link in incoming:
                sys.stdout.write("  in   ")
                _print_link(link)
            return 0
        if args.cmd == "list":
            for node in list_nodes(store, args.type):
                _print_node(node)
            return 0
        if args.cmd == "mutate":
            node = mutate_node(store, args.id, title=args.title, payload=_payload(args.sets))
            _print_node(node)
            return 0
        if args.cmd == "board":
            columns = board(store, args.type)
            for name in COLUMNS:
                sys.stdout.write(f"[{name}]\n")
                nodes = columns[name]
                if not nodes:
                    sys.stdout.write("  (empty)\n")
                for node in nodes:
                    sys.stdout.write(f"  {node.id}  {node.type}  {node.title}\n")
            return 0
        if args.cmd == "move":
            node = move_card(store, args.id, args.column)
            _print_node(node)
            return 0
    except (KeyError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    finally:
        store.close()
    return 1
