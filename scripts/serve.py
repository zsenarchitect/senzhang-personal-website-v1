#!/usr/bin/env python3
"""Serve the latest senzhang.me offline snapshot locally."""
from __future__ import annotations

import argparse
import http.server
import io
import json
import os
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path

# Squarespace platform JS POSTs analytics to /api/census/* on the page origin.
# Stub these during offline preview so SimpleHTTPRequestHandler does not 501.
STUB_API_PREFIXES = ("/api/", "/universal/")
PROJECTS_API = "/api/projects"
IMPORT_API = "/api/import"
ASSET_CORNER_SCRIPT = "/__dev__/asset-corner.js"
ASSET_CORNER_TAG = '<script src="/__dev__/asset-corner.js" defer></script>'


def rebuild_site_from_registry() -> list[str]:
    """Rebuild section grids and resume after dashboard saves."""
    root = repo_root()
    script = root / "scripts" / "apply-portfolio-config.py"
    if not script.is_file():
        return []
    subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        check=False,
    )
    return ["apply-portfolio-config.py"]


def projects_json_path() -> Path:
    return repo_root() / "data" / "projects.json"


def dashboard_html_path() -> Path:
    return repo_root() / "dev" / "dashboard" / "index.html"


def import_picker_html_path() -> Path:
    return repo_root() / "dev" / "import-picker" / "index.html"


def asset_corner_js_path() -> Path:
    return repo_root() / "dev" / "asset-corner.js"


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
    if bare == PROJECTS_API or bare.startswith(IMPORT_API):
        return False
    return bare.startswith(STUB_API_PREFIXES)


def make_request_handler(quiet_api_logs: bool):
    dashboard_path = dashboard_html_path()
    import_picker_path = import_picker_html_path()

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
            sys.path.insert(0, str(repo_root() / "scripts"))
            from dashboard_api import enrich_registry_with_thumbnails
            from project_registry import sync_section_order

            sync_section_order(data)
            data = enrich_registry_with_thumbnails(data)
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
            sys.path.insert(0, str(repo_root() / "scripts"))
            from dashboard_api import strip_dashboard_fields
            from project_registry import enforce_section_covers, sync_section_order

            payload = strip_dashboard_fields(payload)
            payload["sectionOrder"] = sync_section_order(payload)
            enforce_section_covers(payload)
            out = projects_json_path()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            rebuilt = rebuild_site_from_registry()
            self._send_json(200, {"ok": True, "path": str(out), "rebuilt": rebuilt})

        def _import_api_module(self):
            sys.path.insert(0, str(repo_root() / "scripts"))
            import import_picker_api

            return import_picker_api

        def _stream_file(self, path: Path, mime: str, disposition: str) -> None:
            import re

            try:
                size = path.stat().st_size
            except OSError as exc:
                self._send_json(500, {"error": str(exc)})
                return

            start = 0
            end = size - 1
            status = 200
            range_header = self.headers.get("Range")
            if range_header:
                match = re.match(r"bytes=(\d*)-(\d*)", range_header.strip())
                if match:
                    if match.group(1):
                        start = int(match.group(1))
                    if match.group(2):
                        end = int(match.group(2))
                    if start > end or start >= size:
                        self.send_response(416)
                        self.send_header("Content-Range", "bytes */{}".format(size))
                        self.end_headers()
                        return
                    end = min(end, size - 1)
                    status = 206

            length = end - start + 1
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Disposition", disposition)
            self.send_header("Accept-Ranges", "bytes")
            if status == 206:
                self.send_header("Content-Range", "bytes {}-{}/{}".format(start, end, size))
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "private, max-age=3600")
            self.end_headers()
            try:
                with path.open("rb") as handle:
                    handle.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk = handle.read(min(1024 * 256, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError, OSError):
                return

        def _handle_import_get(self, bare: str, query: str) -> None:
            from urllib.parse import parse_qs

            ipa = self._import_api_module()
            qs = parse_qs(query)
            if bare == IMPORT_API + "/summary":
                self._send_json(200, ipa.build_summary())
                return
            if bare == IMPORT_API + "/selections":
                self._send_json(200, ipa.load_selections())
                return
            if bare == IMPORT_API + "/registry":
                self._send_json(200, ipa.registry_for_picker())
                return
            if bare == IMPORT_API + "/decisions":
                self._send_json(200, ipa.load_decisions())
                return
            if bare == IMPORT_API + "/folders":
                prefix = (qs.get("prefix") or [""])[0]
                self._send_json(200, ipa.list_folders(prefix))
                return
            if bare == IMPORT_API + "/files":
                prefix = (qs.get("prefix") or [""])[0]
                kind = (qs.get("kind") or [""])[0]
                q = (qs.get("q") or [""])[0]
                try:
                    limit = int((qs.get("limit") or ["200"])[0])
                    offset = int((qs.get("offset") or ["0"])[0])
                    hide_decided = (qs.get("hideDecided") or ["1"])[0] not in ("0", "false", "no")
                except ValueError:
                    self._send_json(400, {"error": "invalid limit or offset"})
                    return
                self._send_json(
                    200,
                    ipa.list_files(prefix, kind, q, limit, offset, hide_decided),
                )
                return
            if bare == IMPORT_API + "/preview-meta":
                rel = (qs.get("rel") or [""])[0]
                if not rel:
                    self._send_json(400, {"error": "rel required"})
                    return
                try:
                    self._send_json(200, ipa.preview_meta(rel))
                except (ValueError, FileNotFoundError) as exc:
                    self._send_json(404, {"error": str(exc)})
                return
            if bare == IMPORT_API + "/pdf-meta":
                rel = (qs.get("rel") or [""])[0]
                if not rel:
                    self._send_json(400, {"error": "rel required"})
                    return
                try:
                    self._send_json(200, ipa.pdf_meta(rel))
                except (ValueError, FileNotFoundError) as exc:
                    self._send_json(404, {"error": str(exc)})
                return
            if bare == IMPORT_API + "/pdf-preview":
                rel = (qs.get("rel") or [""])[0]
                try:
                    page_num = int((qs.get("page") or ["1"])[0])
                except ValueError:
                    self._send_json(400, {"error": "invalid page"})
                    return
                if not rel:
                    self._send_json(400, {"error": "rel required"})
                    return
                try:
                    path = ipa.preview_pdf_page(rel, page_num)
                except (ValueError, FileNotFoundError) as exc:
                    self._send_json(404, {"error": str(exc)})
                    return
                self._stream_file(path, "image/jpeg", 'inline; filename="page.jpg"')
                return
            if bare == IMPORT_API + "/file":
                rel = (qs.get("rel") or [""])[0]
                if not rel:
                    self._send_json(400, {"error": "rel required"})
                    return
                try:
                    mime, path, disposition = ipa.preview_delivery(rel)
                except (ValueError, FileNotFoundError) as exc:
                    self._send_json(404, {"error": str(exc)})
                    return
                self._stream_file(path, mime, disposition)
                return
            self._send_json(404, {"error": "not found"})

        def _handle_import_post(self, bare: str, body: bytes) -> None:
            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"error": "invalid json"})
                return
            ipa = self._import_api_module()
            if bare == IMPORT_API + "/selections":
                try:
                    out = ipa.save_selections(payload)
                except ValueError as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                self._send_json(200, out)
                return
            if bare == IMPORT_API + "/execute":
                dry_run = bool(payload.get("dryRun"))
                try:
                    report = ipa.execute_import(dry_run=dry_run)
                except Exception as exc:
                    self._send_json(500, {"error": str(exc)})
                    return
                self._send_json(200, report)
                return
            if bare == IMPORT_API + "/decide":
                action = str(payload.get("action", "")).strip()
                rel = str(payload.get("stagingPath", "")).strip()
                try:
                    if action == "undo":
                        out = ipa.undo_decision(rel)
                    elif action == "reject-pdf":
                        out = ipa.reject_pdf_all(rel)
                    elif action == "extract-pages":
                        pages = payload.get("pages", [])
                        if not isinstance(pages, list):
                            self._send_json(400, {"error": "pages must be a list"})
                            return
                        out = ipa.extract_pdf_pages(rel, pages)
                    else:
                        out = ipa.decide_file(
                            rel,
                            action,
                            str(payload.get("targetSlug", "")).strip(),
                            str(payload.get("role", "gallery")).strip() or "gallery",
                        )
                except (ValueError, FileNotFoundError) as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                except Exception as exc:
                    self._send_json(500, {"error": str(exc)})
                    return
                self._send_json(200, out)
                return
            self._send_json(404, {"error": "not found"})

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
            if bare == PROJECTS_API or bare.startswith(IMPORT_API) or is_stub_api_path(self.path):
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
            if bare.startswith(IMPORT_API):
                self._handle_import_post(bare, self._read_request_body())
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

        def _is_import_picker_path(self) -> bool:
            bare = self.path.split("?", 1)[0].rstrip("/")
            return bare == "/import-picker" or bare.startswith("/import-picker/")

        def _is_dashboard_path(self) -> bool:
            bare = self.path.split("?", 1)[0].rstrip("/")
            return bare in ("/dashboard", "/dashboard/index.html")

        def _is_asset_corner_script(self) -> bool:
            bare = self.path.split("?", 1)[0].rstrip("/")
            return bare == ASSET_CORNER_SCRIPT.rstrip("/")

        def _should_inject_asset_corner(self, translated_path: str) -> bool:
            if not translated_path.endswith(".html"):
                return False
            if not os.path.isfile(translated_path):
                return False
            rel = os.path.relpath(translated_path, os.getcwd()).replace("\\", "/")
            if rel.startswith("_cdn/") or "/_cdn/" in rel:
                return False
            return True

        def _inject_dev_html_patches(self, html: str) -> str:
            sys.path.insert(0, str(repo_root() / "scripts"))
            from fix_offline_aspect_images import inject_aspect_fix

            html = inject_aspect_fix(html)
            if ASSET_CORNER_TAG in html or "asset-corner.js" in html:
                return html
            lower = html.lower()
            idx = lower.rfind("</body>")
            if idx < 0:
                return html + "\n" + ASSET_CORNER_TAG + "\n"
            return html[:idx] + ASSET_CORNER_TAG + "\n" + html[idx:]

        def _serve_asset_corner_js(self) -> None:
            path = asset_corner_js_path()
            if not path.is_file():
                self.send_error(404, "asset-corner.js not found")
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _serve_snapshot_html(self, translated_path: str) -> None:
            try:
                text = Path(translated_path).read_text(encoding="utf-8")
            except OSError as exc:
                self.send_error(500, str(exc))
                return
            text = self._inject_dev_html_patches(text)
            body = text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _serve_import_picker(self) -> None:
            bare = self.path.split("?", 1)[0].rstrip("/")
            root = repo_root() / "dev" / "import-picker"
            if bare in ("/import-picker", ""):
                path = root / "index.html"
            else:
                rel = bare[len("/import-picker/") :]
                if not rel or ".." in rel.replace("\\", "/"):
                    self.send_error(400)
                    return
                path = root / rel
            if not path.is_file():
                self.send_error(404, "Import picker asset not found")
                return
            body = path.read_bytes()
            ctype = "text/html; charset=utf-8"
            if path.suffix == ".js":
                ctype = "application/javascript; charset=utf-8"
            elif path.suffix == ".css":
                ctype = "text/css; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _serve_dashboard(self) -> None:
            if not dashboard_path.is_file():
                self.send_error(404, "Dashboard is local-dev only (missing dev/dashboard/index.html)")
                return
            body = dashboard_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_HEAD(self) -> None:
            if self._is_dashboard_path():
                if dashboard_path.is_file():
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                else:
                    self.send_error(404)
                return
            if self._is_import_picker_path():
                if (repo_root() / "dev" / "import-picker" / "index.html").is_file():
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                else:
                    self.send_error(404)
                return
            if is_stub_api_path(self.path):
                self.send_error(404)
                return
            if self._is_asset_corner_script():
                if asset_corner_js_path().is_file():
                    self.send_response(200)
                    self.send_header("Content-Type", "application/javascript; charset=utf-8")
                    self.end_headers()
                else:
                    self.send_error(404)
                return
            self._maybe_clean_url_path()
            return super().do_HEAD()

        def do_GET(self) -> None:
            bare = self.path.split("?", 1)[0]
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            if self._is_dashboard_path():
                self._serve_dashboard()
                return
            if self._is_import_picker_path():
                self._serve_import_picker()
                return
            if bare == PROJECTS_API:
                self._handle_projects_get()
                return
            if bare.startswith(IMPORT_API):
                self._handle_import_get(bare, query)
                return
            if is_stub_api_path(self.path):
                self.send_error(404)
                return
            if self._is_asset_corner_script():
                self._serve_asset_corner_js()
                return
            self._maybe_clean_url_path()
            translated = self.translate_path(self.path.split("?", 1)[0])
            if self._should_inject_asset_corner(translated):
                self._serve_snapshot_html(translated)
                return
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
    print("  Dashboard (local only): http://{}:{}/dashboard".format(args.host, port))
    print("  Import picker: http://{}:{}/import-picker".format(args.host, port))
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
