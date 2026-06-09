#!/usr/bin/env python3
"""Serve the latest senzhang.me offline snapshot locally."""
from __future__ import annotations

import argparse
import http.server
import os
import socket
import sys
import webbrowser
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def latest_snapshot(snapshot_root: Path) -> Path:
    dates = sorted(
        (d for d in snapshot_root.iterdir() if d.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    if not dates:
        raise SystemExit(
            "No snapshots found under snapshot/. Run .\\scripts\\snapshot.ps1 first."
        )
    entry = dates[0] / "index.html"
    if not entry.is_file():
        raise SystemExit("Latest snapshot has no index.html: {}".format(dates[0]))
    return dates[0]


def pick_port(host: str, preferred: int) -> int:
    for port in (preferred, preferred + 1, preferred + 2, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return sock.getsockname()[1]
            except OSError:
                continue
    raise SystemExit("Could not bind a local port.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve senzhang.me legacy snapshot locally.")
    parser.add_argument("--date", help="Snapshot folder name (default: latest)")
    parser.add_argument("--port", type=int, default=8765, help="Preferred port (default: 8765)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--no-open", action="store_true", help="Do not open a browser tab")
    args = parser.parse_args()

    snapshot_root = repo_root() / "snapshot"
    if args.date:
        root = snapshot_root / args.date
        if not (root / "index.html").is_file():
            raise SystemExit("Snapshot not found or missing index.html: {}".format(root))
    else:
        root = latest_snapshot(snapshot_root)

    os.chdir(root)
    port = pick_port(args.host, args.port)
    url = "http://{}:{}/index.html".format(args.host, port)

    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.ThreadingHTTPServer((args.host, port), handler)

    print("Serving senzhang.me legacy snapshot")
    print("  Root: {}".format(root))
    print("  URL:  {}".format(url))
    print("  Stop: Ctrl+C")
    print("")

    if not args.no_open:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
