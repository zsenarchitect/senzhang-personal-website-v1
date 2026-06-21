#!/usr/bin/env python3
"""Re-apply manifest URL rewriting to snapshot HTML (offline _cdn paths)."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from snapshot import rewrite_html

REFERENCE_OFFLINE_HEAD = "museum-of-verbs.html"
HEAD_START_MARKERS = (
    '<link rel="stylesheet" href="_cdn/offline-typekit.css">',
    '<script type="text/javascript" src="_cdn/use.typekit.net/',
)
HEAD_END_MARKER = "<!-- End of Squarespace Headers -->"


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_url_map(snap: Path) -> dict[str, Path]:
    manifest_path = snap / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    url_map: dict[str, Path] = {}
    for url, rel in manifest.get("url_to_local", {}).items():
        local = snap / rel.replace("\\", "/")
        if local.is_file():
            url_map[url] = local
    return url_map


def extract_offline_head(reference_html: str) -> str | None:
    start = -1
    for marker in HEAD_START_MARKERS:
        idx = reference_html.find(marker)
        if idx >= 0:
            start = idx
            break
    if start < 0:
        return None
    end = reference_html.find(HEAD_END_MARKER, start)
    if end < 0:
        return None
    return reference_html[start:end]


def sync_stale_head(html: str, reference_head: str) -> tuple[str, bool]:
    if "//assets.squarespace.com" not in html and "https://static1.squarespace.com/static/sitecss/" not in html:
        return html, False
    start = -1
    for marker in (
        '<link rel="preconnect" href="https://use.typekit.net"',
        '<script type="text/javascript" src="//use.typekit.net/',
    ):
        idx = html.find(marker)
        if idx >= 0:
            start = idx
            break
    if start < 0:
        return html, False
    end = html.find(HEAD_END_MARKER, start)
    if end < 0:
        return html, False
    return html[:start] + reference_head + html[end:], True


def patch_largest_srcset_data_image(html: str) -> tuple[str, int]:
    """Point data-image at the widest srcset candidate for lightbox full-size loads."""
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        tag = match.group(0)
        srcset_m = re.search(r'\bsrcset="([^"]+)"', tag, re.IGNORECASE)
        if not srcset_m:
            return tag
        best_url = ""
        best_w = -1
        for part in srcset_m.group(1).split(","):
            part = part.strip()
            bits = part.rsplit(" ", 1)
            if len(bits) != 2:
                continue
            url, descriptor = bits
            if not descriptor.endswith("w"):
                continue
            try:
                width = int(descriptor[:-1])
            except ValueError:
                continue
            if width > best_w:
                best_w = width
                best_url = url
        if not best_url:
            return tag
        new_tag = tag
        for attr in ("data-image", "data-src"):
            if re.search(r'\b' + attr + r'="', new_tag, re.IGNORECASE):
                new_tag = re.sub(
                    r'\b' + attr + r'="[^"]*"',
                    '{}="{}"'.format(attr, best_url),
                    new_tag,
                    count=1,
                    flags=re.IGNORECASE,
                )
        if new_tag != tag:
            count += 1
        return new_tag

    return re.sub(r"<img\b[^>]*\bsrcset=\"[^\"]+\"[^>]*>", repl, html, flags=re.IGNORECASE), count


def main() -> int:
    parser = argparse.ArgumentParser(description="Relocalize snapshot HTML asset URLs from manifest")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    args = parser.parse_args()

    snap = repo_root() / "snapshot" / args.date
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    url_map = load_url_map(snap)
    reference_path = snap / REFERENCE_OFFLINE_HEAD
    reference_head = None
    if reference_path.is_file():
        reference_head = extract_offline_head(reference_path.read_text(encoding="utf-8"))

    patched: list[str] = []
    for html_path in sorted(snap.glob("*.html")):
        original = html_path.read_text(encoding="utf-8")
        html = original
        html = rewrite_html(html, html_path, snap, url_map)
        if reference_head:
            html, _head = sync_stale_head(html, reference_head)
        html, _srcset = patch_largest_srcset_data_image(html)
        if html != original:
            html_path.write_text(html, encoding="utf-8")
            patched.append(html_path.name)

    print("Relocalized {} HTML files.".format(len(patched)))
    for name in patched:
        print("  {}".format(name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
