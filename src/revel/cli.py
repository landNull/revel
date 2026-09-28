"""revelctl entry point.

Stub only (issue #6). The control-plane API is not implemented yet.
Request: whatever you type after `revelctl`.
Response: status text. Work below this layer arrives in M1–M3.
"""

from __future__ import annotations

import sys

from revel import __version__


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        sys.stdout.write(
            "revelctl — control-plane client (skeleton)\n"
            "\n"
            "Later requests: create, link, query, mutate nodes.\n"
            "This stub has no graph backend yet.\n"
        )
        return 0
    if args and args[0] in ("-V", "--version"):
        sys.stdout.write(f"{__version__}\n")
        return 0
    sys.stdout.write(
        f"revelctl {__version__} (package skeleton). "
        "Graph API not wired. Next floors: M1 types, M2 Kuzu, M3 commands.\n"
    )
    return 0
