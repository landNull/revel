"""IMAP fetch / SMTP send (#22). One account. Creds never stored on nodes."""

from __future__ import annotations

import email
import imaplib
import os
import shutil
import smtplib
import subprocess
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from revel.graph import Node
from revel.plane import create_node, list_nodes
from revel.store.base import GraphStore

SECRET_SERVICE = "revel"
SECRET_ACCOUNT = "mail"


def mail_env_path() -> Path:
    return Path(os.environ.get("REVEL_MAIL_ENV") or Path.home() / ".config" / "revel" / "mail.env")


def keyring_available() -> bool:
    return shutil.which("secret-tool") is not None


def keyring_get() -> str | None:
    if not keyring_available():
        return None
    try:
        out = subprocess.run(
            ["secret-tool", "lookup", "service", SECRET_SERVICE, "account", SECRET_ACCOUNT],
            check=False, capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    secret = out.stdout.strip()
    return secret or None


def keyring_set(password: str) -> bool:
    if not keyring_available():
        return False
    proc = subprocess.run(
        ["secret-tool", "store", "--label=Revel mail", "service", SECRET_SERVICE, "account", SECRET_ACCOUNT],
        input=password, text=True, capture_output=True, timeout=15, check=False,
    )
    return proc.returncode == 0


def write_mail_env(values: dict[str, str], *, include_password: bool) -> Path:
    path = mail_env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Revel mail. Mode 600. Do not commit. App password, not account password."]
    skip = set() if include_password else {"REVEL_MAIL_PASSWORD", "REVEL_IMAP_PASSWORD", "REVEL_SMTP_PASSWORD"}
    for key, value in values.items():
        if key in skip or not value:
            continue
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path


def _load_env_file() -> None:
    path = mail_env_path()
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def mail_config() -> dict[str, str]:
    _load_env_file()
    user = os.environ.get("REVEL_IMAP_USER") or os.environ.get("REVEL_MAIL_USER", "")
    password = (
        os.environ.get("REVEL_IMAP_PASSWORD")
        or os.environ.get("REVEL_MAIL_PASSWORD")
        or keyring_get()
        or ""
    )
    return {
        "imap_host": os.environ.get("REVEL_IMAP_HOST", ""),
        "imap_port": os.environ.get("REVEL_IMAP_PORT", "993"),
        "imap_tls": os.environ.get("REVEL_IMAP_TLS", "ssl"),
        "imap_user": user,
        "imap_password": password,
        "smtp_host": os.environ.get("REVEL_SMTP_HOST", ""),
        "smtp_port": os.environ.get("REVEL_SMTP_PORT", "465"),
        "smtp_tls": os.environ.get("REVEL_SMTP_TLS", "ssl"),
        "smtp_user": os.environ.get("REVEL_SMTP_USER", "") or user,
        "smtp_password": os.environ.get("REVEL_SMTP_PASSWORD", "") or password,
        "smtp_from": os.environ.get("REVEL_SMTP_FROM", "") or user,
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
        store, "email", subject or "(no subject)",
        payload={"message_id": mid, "from": sender, "date": date, "folder": folder, "column": "todo"},
        id=_node_id(mid),
    )


def ingest_rfc822(store: GraphStore, raw: bytes, folder: str = "INBOX") -> Node:
    msg = email.message_from_bytes(raw)
    return upsert_email(store, subject=msg.get("Subject", ""), message_id=msg.get("Message-ID", ""), sender=msg.get("From", ""), date=msg.get("Date", ""), folder=folder)


def fetch_inbox(store: GraphStore, limit: int = 20) -> list[Node]:
    if not configured("imap"):
        raise RuntimeError("set REVEL_IMAP_HOST, REVEL_IMAP_USER, REVEL_IMAP_PASSWORD")
    cfg = mail_config()
    port = int(cfg["imap_port"])
    mode = cfg["imap_tls"].lower()
    if mode == "ssl":
        client = imaplib.IMAP4_SSL(cfg["imap_host"], port)
    else:
        client = imaplib.IMAP4(cfg["imap_host"], port)
        if mode == "starttls":
            client.starttls()
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
    port = int(cfg["smtp_port"])
    mode = cfg["smtp_tls"].lower()
    if mode == "ssl":
        smtp = smtplib.SMTP_SSL(cfg["smtp_host"], port)
    else:
        smtp = smtplib.SMTP(cfg["smtp_host"], port)
        if mode == "starttls":
            smtp.starttls()
    try:
        smtp.login(cfg["smtp_user"], cfg["smtp_password"])
        smtp.send_message(msg)
    finally:
        smtp.quit()
    return upsert_email(store, subject=subject, message_id=msg.get("Message-ID", subject), sender=cfg["smtp_from"], folder="SENT")


def ingest_many(store: GraphStore, messages: Iterable[dict]) -> list[Node]:
    out = []
    for item in messages:
        out.append(upsert_email(store, subject=item.get("subject", ""), message_id=item.get("message_id", ""), sender=item.get("from", ""), date=item.get("date", ""), folder=item.get("folder", "INBOX")))
    return out
