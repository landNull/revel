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
    mutate_node,
    neighbors,
    query_node,
)
from revel.projection.calendar import events_between
from revel.projection.dates import end_of, start_of
from revel.projection.gantt import to_frappe_gantt
from revel.projection.kanban import COLUMNS, board, move_card
from revel.projection.listing import listed
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
    p_list.add_argument("--sort", choices=("title", "due", "type"), default="title")

    p_mut = sub.add_parser("mutate", help="change title or payload")
    p_mut.add_argument("id")
    p_mut.add_argument("--title")
    p_mut.add_argument("--set", dest="sets", action="append", default=[])

    p_board = sub.add_parser("board", help="Kanban projection of nodes")
    p_board.add_argument("type", nargs="?")

    p_move = sub.add_parser("move", help="move a node to a Kanban column")
    p_move.add_argument("id")
    p_move.add_argument("column", choices=COLUMNS)

    p_cal = sub.add_parser("cal", help="calendar projection of dated nodes")
    p_cal.add_argument("type", nargs="?")

    p_gantt = sub.add_parser("gantt", help="gantt projection of dated nodes")
    p_gantt.add_argument("type", nargs="?")

    p_serve = sub.add_parser("serve", help="HTTP adapter (FastAPI)")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    sub.add_parser("demo", help="upsert the Northwind demo graph")
    sub.add_parser("dashboard", help="print node/link counts")

    p_file = sub.add_parser("file", help="filesystem adapter (~/Revel/files)")
    file_sub = p_file.add_subparsers(dest="file_cmd")
    p_add = file_sub.add_parser("add", help="copy a host file into ~/Revel/files")
    p_add.add_argument("path")
    p_add.add_argument("--to", dest="attach_to", help="attach to an existing node id")
    file_sub.add_parser("root", help="print ~/Revel/files")
    p_cat = file_sub.add_parser("cat", help="print bytes from a file node")
    p_cat.add_argument("id")

    sub.add_parser("whoami", help="upsert OS user/group nodes for this process (no sudo)")

    p_mail = sub.add_parser("mail", help="IMAP/SMTP adapter (env credentials)")
    mail_sub = p_mail.add_subparsers(dest="mail_cmd")
    mail_sub.add_parser("status", help="show hosts/tls and whether a secret is present")
    p_secret = mail_sub.add_parser("secret", help="store Zoho app password in keyring or mail.env")
    p_secret.add_argument("password", nargs="?", help="omit to prompt")
    p_secret.add_argument("--file-only", action="store_true", help="skip keyring; write mail.env mode 600")
    p_fetch = mail_sub.add_parser("fetch", help="fetch inbox into email nodes")
    p_fetch.add_argument("--limit", type=int, default=20)
    p_send = mail_sub.add_parser("send", help="send via SMTP and record an email node")
    p_send.add_argument("to")
    p_send.add_argument("subject")
    p_send.add_argument("body")

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.cmd is None:
        parser.print_help()
        return 0

    store = _store_from_env()
    try:
        if args.cmd == "create":
            node = create_node(store, args.type, args.title, payload=_payload(args.sets), id=args.id)
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
            for node in listed(store, args.type, sort=args.sort):
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
        if args.cmd == "cal":
            rows = events_between(store, type=args.type)
            if not rows:
                sys.stdout.write("(no dated nodes; set payload start=YYYY-MM-DD)\n")
                return 0
            for node in rows:
                a = start_of(node)
                b = end_of(node)
                span = a.isoformat() if a and a == b else f"{a} .. {b}"
                sys.stdout.write(f"{span}  {node.id}  {node.type}  {node.title}\n")
            return 0
        if args.cmd == "demo":
            from revel.demo import load_demo
            result = load_demo(store)
            sys.stdout.write(f"demo  nodes={result['nodes']} links={result['links']} store_total={result['total_nodes']}\n")
            return 0
        if args.cmd == "dashboard":
            from revel.demo import dashboard
            snap = dashboard(store)
            sys.stdout.write(f"nodes={snap['nodes']} links={snap['links']} dated={snap['dated']} demo={snap['demo_loaded']}\n")
            for name, count in snap["by_column"].items():
                sys.stdout.write(f"  [{name}] {count}\n")
            return 0
        if args.cmd == "mail":
            from revel.adapters import mail as mail_ad
            if args.mail_cmd == "status":
                cfg = mail_ad.mail_config()
                secret = "keyring" if mail_ad.keyring_get() else (
                    "env-file" if mail_ad.mail_env_path().is_file() and (cfg["imap_password"] or cfg["smtp_password"]) else ("env" if cfg["imap_password"] else "missing")
                )
                sys.stdout.write(
                    f"imap={'yes' if mail_ad.configured('imap') else 'no'} {cfg['imap_host']}:{cfg['imap_port']}/{cfg['imap_tls']}  "
                    f"smtp={'yes' if mail_ad.configured('smtp') else 'no'} {cfg['smtp_host']}:{cfg['smtp_port']}/{cfg['smtp_tls']}  "
                    f"secret={secret} keyring={'yes' if mail_ad.keyring_available() else 'no'}\n"
                )
                return 0
            if args.mail_cmd == "secret":
                import getpass
                password = args.password or getpass.getpass("Zoho app password: ")
                if not password:
                    sys.stderr.write("empty secret\n")
                    return 1
                used = "file"
                if not args.file_only and mail_ad.keyring_set(password):
                    used = "keyring"
                    mail_ad.write_mail_env({
                        "REVEL_IMAP_HOST": os.environ.get("REVEL_IMAP_HOST", "imap.zoho.com"),
                        "REVEL_IMAP_PORT": os.environ.get("REVEL_IMAP_PORT", "993"),
                        "REVEL_IMAP_TLS": os.environ.get("REVEL_IMAP_TLS", "ssl"),
                        "REVEL_SMTP_HOST": os.environ.get("REVEL_SMTP_HOST", "smtp.zoho.com"),
                        "REVEL_SMTP_PORT": os.environ.get("REVEL_SMTP_PORT", "465"),
                        "REVEL_SMTP_TLS": os.environ.get("REVEL_SMTP_TLS", "ssl"),
                        "REVEL_MAIL_USER": os.environ.get("REVEL_MAIL_USER") or os.environ.get("REVEL_IMAP_USER", ""),
                    }, include_password=False)
                else:
                    mail_ad.write_mail_env({
                        "REVEL_IMAP_HOST": os.environ.get("REVEL_IMAP_HOST", "imap.zoho.com"),
                        "REVEL_IMAP_PORT": os.environ.get("REVEL_IMAP_PORT", "993"),
                        "REVEL_IMAP_TLS": os.environ.get("REVEL_IMAP_TLS", "ssl"),
                        "REVEL_SMTP_HOST": os.environ.get("REVEL_SMTP_HOST", "smtp.zoho.com"),
                        "REVEL_SMTP_PORT": os.environ.get("REVEL_SMTP_PORT", "465"),
                        "REVEL_SMTP_TLS": os.environ.get("REVEL_SMTP_TLS", "ssl"),
                        "REVEL_MAIL_USER": os.environ.get("REVEL_MAIL_USER") or os.environ.get("REVEL_IMAP_USER", ""),
                        "REVEL_MAIL_PASSWORD": password,
                    }, include_password=True)
                sys.stdout.write(f"stored in {used}  {mail_ad.mail_env_path()}\n")
                return 0
            if args.mail_cmd == "fetch":
                for node in mail_ad.fetch_inbox(store, limit=args.limit):
                    _print_node(node)
                return 0
            if args.mail_cmd == "send":
                node = mail_ad.send_mail(store, args.to, args.subject, args.body)
                _print_node(node)
                return 0
            sys.stderr.write("revelctl mail status|fetch|send\n")
            return 1
        if args.cmd == "whoami":
            from revel.adapters.os_users import sync_current
            user, group = sync_current(store)
            _print_node(user)
            if group:
                _print_node(group)
            return 0
        if args.cmd == "file":
            from revel.adapters.fs import files_root, ingest_file, read_bytes
            if args.file_cmd == "root":
                sys.stdout.write(f"{files_root()}\n")
                return 0
            if args.file_cmd == "add":
                node = ingest_file(store, args.path, attach_to=args.attach_to)
                _print_node(node)
                return 0
            if args.file_cmd == "cat":
                node = query_node(store, args.id)
                if node is None or node.type != "file":
                    sys.stderr.write(f"unknown file node: {args.id}\n")
                    return 1
                sys.stdout.buffer.write(read_bytes(node))
                return 0
            sys.stderr.write("revelctl file add|root|cat\n")
            return 1
        if args.cmd == "serve":
            try:
                import uvicorn
            except ImportError:
                sys.stderr.write("pip install 'revel[web]' to serve HTTP\n")
                return 1
            from revel.web import app
            uvicorn.run(app, host=args.host, port=args.port)
            return 0
        if args.cmd == "gantt":
            rows = to_frappe_gantt(store, args.type)
            if not rows:
                sys.stdout.write("(no dated nodes; set payload start=YYYY-MM-DD)\n")
                return 0
            for item in rows:
                deps = f"  deps={item['dependencies']}" if item.get("dependencies") else ""
                sys.stdout.write(f"{item['start']} .. {item['end']}  {item['progress']:>3}%  {item['id']}  {item['name']}{deps}\n")
            return 0
    except (KeyError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    finally:
        store.close()
    return 1
