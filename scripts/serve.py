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

# Squarespace platform JS POSTs analytics to /api/census/* on the page origin.
# Stub these during offline preview so SimpleHTTPRequestHandler does not 501.
STUB_API_PREFIXES = ("/api/", "/universal/")


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


def is_stub_api_path(path: str) -> bool:
    bare = path.split("?", 1)[0]
    return bare.startswith(STUB_API_PREFIXES)


def make_request_handler(quiet_api_logs: bool):
    class SnapshotRequestHandler(http.server.SimpleHTTPRequestHandler):
        def _read_request_body(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                self.rfile.read(length)

        def _send_stub_api(self) -> None:
            self._read_request_body()
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:
            if is_stub_api_path(self.path):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header(
                    "Access-Control-Allow-Headers",
                    "Content-Type, X-Requested-With, Accept, Authorization",
                )
                self.end_headers()
                return
            self.send_error(501, "Unsupported method ('OPTIONS')")

        def do_POST(self) -> None:
            if is_stub_api_path(self.path):
                self._send_stub_api()
                return
            self.send_error(501, "Unsupported method ('POST')")

        def do_PUT(self) -> None:
            if is_stub_api_path(self.path):
                self._send_stub_api()
                return
            self.send_error(501, "Unsupported method ('PUT')")

        def log_message(self, format: str, *args) -> None:
            if quiet_api_logs and args:
                try:
                    request_line = format % args
                except Exception:
                    request_line = str(args)
                if " /api/" in request_line or " /universal/" in request_line:
                    return
            sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    return SnapshotRequestHandler


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
    parser.add_argument(
        "--quiet-api",
        action="store_true",
        help="Hide log lines for stubbed Squarespace /api/ requests",
    )
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

    handler = make_request_handler(args.quiet_api)
    httpd = http.server.ThreadingHTTPServer((args.host, port), handler)

    print("Serving senzhang.me legacy snapshot")
    print("  Root: {}".format(root))
    print("  URL:  {}".format(url))
    print("  QA:   live https://senzhang.me/  |  deployed https://legacy-personal-website.vercel.app/index.html")
    print("  Edits under snapshot/ appear on browser refresh (Ctrl+Shift+R). No server restart.")
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
