"""IMAP fetch / SMTP send (#22). One account. Creds never stored on nodes."""

from __future__ import annotations

import email
import imaplib
import os
import smtplib
from email.message import EmailMessage
from typing import Iterable

from revel.graph import Node
from revel.plane import create_node, list_nodes
from revel.store.base import GraphStore


def mail_config() -> dict[str, str]:
    return {
        "imap_host": os.environ.get("REVEL_IMAP_HOST", ""),
        "imap_user": os.environ.get("REVEL_IMAP_USER", ""),
        "imap_password": os.environ.get("REVEL_IMAP_PASSWORD", ""),
        "smtp_host": os.environ.get("REVEL_SMTP_HOST", ""),
        "smtp_user": os.environ.get("REVEL_SMTP_USER", "") or os.environ.get("REVEL_IMAP_USER", ""),
        "smtp_password": os.environ.get("REVEL_SMTP_PASSWORD", "") or os.environ.get("REVEL_IMAP_PASSWORD", ""),
        "smtp_from": os.environ.get("REVEL_SMTP_FROM", "") or os.environ.get("REVEL_IMAP_USER", ""),
        "imap_folder": os.environ.get("REVEL_IMAP_FOLDER", "INBOX"),
    }


def configured(kind: str = "imap") -> bool:
    cfg = mail_config()
    if kind == "smtp":
        return bool(cfg["smtp_host"] and cfg["smtp_user"] and cfg["smtp_password"])
    return bool(cfg["imap_host"] and cfg["imap_user"] and cfg["imap_password"])


def _node_id(message_id: str) -> str:
    cleaned = message_id.strip("<> ").replace("/", "_")[:80]
    return f"email-{cleaned or 'unknown'}"


def upsert_email(store: GraphStore, *, subject: str, message_id: str, sender: str = "", date: str = "", folder: str = "INBOX") -> Node:
    mid = message_id.strip() or subject
    existing = store.get_node(_node_id(mid))
    if existing:
        return existing
    for node in list_nodes(store, "email"):
        if node.payload.get("message_id") == mid:
            return node
    return create_node(
        store,
        "email",
        subject or "(no subject)",
        payload={"message_id": mid, "from": sender, "date": date, "folder": folder, "column": "todo"},
        id=_node_id(mid),
    )


def ingest_rfc822(store: GraphStore, raw: bytes, folder: str = "INBOX") -> Node:
    msg = email.message_from_bytes(raw)
    return upsert_email(
        store,
        subject=msg.get("Subject", ""),
        message_id=msg.get("Message-ID", ""),
        sender=msg.get("From", ""),
        date=msg.get("Date", ""),
        folder=folder,
    )


def fetch_inbox(store: GraphStore, limit: int = 20) -> list[Node]:
    if not configured("imap"):
        raise RuntimeError("set REVEL_IMAP_HOST, REVEL_IMAP_USER, REVEL_IMAP_PASSWORD")
    cfg = mail_config()
    client = imaplib.IMAP4_SSL(cfg["imap_host"])
    try:
        client.login(cfg["imap_user"], cfg["imap_password"])
        client.select(cfg["imap_folder"])
        _, data = client.search(None, "ALL")
        ids = data[0].split()[-limit:]
        nodes: list[Node] = []
        for mid in ids:
            _, payload = client.fetch(mid, "(RFC822)")
            if not payload or not payload[0]:
                continue
            raw = payload[0][1]
            if isinstance(raw, bytes):
                nodes.append(ingest_rfc822(store, raw, cfg["imap_folder"]))
        return nodes
    finally:
        try:
            client.logout()
        except Exception:
            pass


def send_mail(store: GraphStore, to: str, subject: str, body: str) -> Node:
    if not configured("smtp"):
        raise RuntimeError("set REVEL_SMTP_HOST, REVEL_SMTP_USER, REVEL_SMTP_PASSWORD")
    cfg = mail_config()
    msg = EmailMessage()
    msg["From"] = cfg["smtp_from"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL(cfg["smtp_host"]) as smtp:
        smtp.login(cfg["smtp_user"], cfg["smtp_password"])
        smtp.send_message(msg)
    return upsert_email(store, subject=subject, message_id=msg.get("Message-ID", subject), sender=cfg["smtp_from"], folder="SENT")


def ingest_many(store: GraphStore, messages: Iterable[dict]) -> list[Node]:
    out = []
    for item in messages:
        out.append(upsert_email(store, subject=item.get("subject", ""), message_id=item.get("message_id", ""), sender=item.get("from", ""), date=item.get("date", ""), folder=item.get("folder", "INBOX")))
    return out
