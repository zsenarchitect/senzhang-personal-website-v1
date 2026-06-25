#!/usr/bin/env python3
"""Serve the latest senzhang.me offline snapshot locally."""
from __future__ import annotations

import argparse
import http.server
import io
import json
import os
import socket
import sys
import webbrowser
from pathlib import Path

# Squarespace platform JS POSTs analytics to /api/census/* on the page origin.
# Stub these during offline preview so SimpleHTTPRequestHandler does not 501.
STUB_API_PREFIXES = ("/api/", "/universal/")
PROJECTS_API = "/api/projects"


def projects_json_path() -> Path:
    return repo_root() / "data" / "projects.json"


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
    if bare == PROJECTS_API:
        return False
    return bare.startswith(STUB_API_PREFIXES)


def make_request_handler(quiet_api_logs: bool):
    class SnapshotRequestHandler(http.server.SimpleHTTPRequestHandler):
        # HTTP/1.1 enables Range requests so MP4 seek/scrub works in the video player.
        protocol_version = "HTTP/1.1"

        def _read_request_body(self) -> bytes:
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                return self.rfile.read(length)
            return b""

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _handle_projects_get(self) -> None:
            path = projects_json_path()
            if not path.is_file():
                sys.path.insert(0, str(repo_root() / "scripts"))
                from project_registry import merge_registry_on_disk

                merge_registry_on_disk()
            data = json.loads(path.read_text(encoding="utf-8"))
            self._send_json(200, data)

        def _handle_projects_post(self, body: bytes) -> None:
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"error": "invalid json"})
                return
            if not isinstance(payload, dict) or "projects" not in payload:
                self._send_json(400, {"error": "expected { projects: {...} }"})
                return
            out = projects_json_path()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            self._send_json(200, {"ok": True, "path": str(out)})

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
            bare = self.path.split("?", 1)[0]
            if bare == PROJECTS_API or is_stub_api_path(self.path):
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
            bare = self.path.split("?", 1)[0]
            if bare == PROJECTS_API:
                self._handle_projects_post(self._read_request_body())
                return
            if is_stub_api_path(self.path):
                self._send_stub_api()
                return
            self.send_error(501, "Unsupported method ('POST')")

        def do_PUT(self) -> None:
            if is_stub_api_path(self.path):
                self._send_stub_api()
                return
            self.send_error(501, "Unsupported method ('PUT')")

        def _maybe_clean_url_path(self) -> None:
            """Map /menu -> menu.html like Vercel cleanUrls for local QA."""
            bare = self.path.split("?", 1)[0]
            if bare.startswith(STUB_API_PREFIXES):
                return
            if os.path.splitext(bare)[1]:
                return
            clean = bare.rstrip("/")
            if clean in ("", "/"):
                candidate = "/index.html"
            else:
                candidate = clean + ".html"
            translated = self.translate_path(candidate)
            if not os.path.isfile(translated):
                idx = os.path.join(clean.lstrip("/"), "index.html")
                idx_path = self.translate_path("/" + idx.replace("\\", "/"))
                if os.path.isfile(idx_path):
                    candidate = "/" + idx.replace("\\", "/")
            if os.path.isfile(self.translate_path(candidate)):
                query = ""
                if "?" in self.path:
                    query = "?" + self.path.split("?", 1)[1]
                self.path = candidate + query

        def do_HEAD(self) -> None:
            if is_stub_api_path(self.path):
                self.send_error(404)
                return
            self._maybe_clean_url_path()
            return super().do_HEAD()

        def do_GET(self) -> None:
            bare = self.path.split("?", 1)[0]
            if bare == PROJECTS_API:
                self._handle_projects_get()
                return
            if is_stub_api_path(self.path):
                self.send_error(404)
                return
            self._maybe_clean_url_path()
            super().do_GET()

        def send_head(self):
            path = self.translate_path(self.path)
            if not os.path.isfile(path):
                return super().send_head()

            ctype = self.guess_type(path)
            if not (ctype.startswith("video/") or ctype.startswith("audio/")):
                return super().send_head()

            range_header = self.headers.get("Range")
            if not range_header:
                return super().send_head()

            try:
                file_size = os.path.getsize(path)
                start, end = self._parse_byte_range(range_header, file_size)
            except ValueError:
                self.send_error(416)
                return None

            length = end - start + 1
            with open(path, "rb") as handle:
                handle.seek(start)
                data = handle.read(length)

            self.send_response(206)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", "bytes {}-{}/{}".format(start, end, file_size))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Last-Modified", self.date_time_string(os.path.getmtime(path)))
            self.end_headers()
            return io.BytesIO(data)

        @staticmethod
        def _parse_byte_range(header: str, file_size: int) -> tuple[int, int]:
            if not header.startswith("bytes="):
                raise ValueError("unsupported range")
            spec = header.split("=", 1)[1].strip()
            if "," in spec:
                raise ValueError("multipart range unsupported")
            start_text, end_text = spec.split("-", 1)
            if start_text == "":
                suffix = int(end_text)
                start = max(file_size - suffix, 0)
                end = file_size - 1
            else:
                start = int(start_text)
                end = int(end_text) if end_text else file_size - 1
            if start > end or start >= file_size:
                raise ValueError("invalid range")
            end = min(end, file_size - 1)
            return start, end

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
    print("  Dashboard: http://{}:{}/dashboard".format(args.host, port))
    print("  Projects API: http://{}:{}/api/projects".format(args.host, port))
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
