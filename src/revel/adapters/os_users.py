"""Optional OS identity adapter (D004 / #23).

Read the account already running this process. Never useradd.
"""

from __future__ import annotations

import os
import pwd
from pathlib import Path

from revel.graph import Node
from revel.plane import create_node, link_nodes
from revel.store.base import GraphStore

try:
    import grp
except ImportError:
    grp = None  # type: ignore[assignment]


def current_uid() -> int:
    return os.getuid()


def lookup_user(uid: int | None = None) -> dict:
    rec = pwd.getpwuid(current_uid() if uid is None else uid)
    return {
        "uid": rec.pw_uid,
        "name": rec.pw_name,
        "home": rec.pw_dir,
        "gid": rec.pw_gid,
        "gecos": rec.pw_gecos,
    }


def lookup_group(gid: int) -> dict | None:
    if grp is None:
        return None
    rec = grp.getgrgid(gid)
    return {"gid": rec.gr_gid, "name": rec.gr_name}


def user_node_id(uid: int) -> str:
    return f"os-user-{uid}"


def group_node_id(gid: int) -> str:
    return f"os-group-{gid}"


def sync_current(store: GraphStore) -> tuple[Node, Node | None]:
    info = lookup_user()
    user = create_node(
        store,
        "user",
        info["name"],
        payload={
            "uid": info["uid"],
            "gid": info["gid"],
            "home": info["home"],
            "gecos": info["gecos"],
            "revel_home": str(Path(info["home"]) / "Revel"),
            "column": "doing",
        },
        id=user_node_id(info["uid"]),
    )
    group_node = None
    ginfo = lookup_group(info["gid"])
    if ginfo:
        group_node = create_node(
            store,
            "group",
            ginfo["name"],
            payload={"gid": ginfo["gid"], "column": "doing"},
            id=group_node_id(ginfo["gid"]),
        )
        existing = {link.target_id for link in store.links_from(user.id)}
        if group_node.id not in existing:
            link_nodes(store, user.id, group_node.id, "member_of")
    return user, group_node
