#!/usr/bin/env python3
"""Stamp deploy build id into HTML for cache busting and verification."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ASSET_URL_RE = re.compile(
    r'((?:href|src)\s*=\s*")((?:_cdn/|_media/)[^"]*)(")',
    re.IGNORECASE,
)
DATA_OFFLINE_VIDEO_RE = re.compile(
    r'(data-offline-video\s*=\s*")((?:_cdn/|_media/)[^"]*)(")',
    re.IGNORECASE,
)
SRCSET_RE = re.compile(
    r'(srcset\s*=\s*")([^"]+)(")',
    re.IGNORECASE,
)
OLD_V_RE = re.compile(r"\?v=[A-Za-z0-9._-]+")
META_BUILD_RE = re.compile(
    r'<meta name="archive-build" content="[^"]*"\s*/?\s*>',
    re.IGNORECASE,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def git_short_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root(),
            text=True,
        )
        return out.strip()
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def bust_asset_url(url: str, build_id: str) -> str:
    fragment = ""
    if "#" in url:
        base, frag = url.split("#", 1)
        fragment = "#" + frag
    else:
        base = url
    bare = OLD_V_RE.sub("", base)
    sep = "&" if "?" in bare else "?"
    return bare + sep + "v=" + build_id + fragment


def patch_srcset(value: str, build_id: str) -> str:
    parts = []
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        bits = chunk.split()
        bits[0] = bust_asset_url(bits[0], build_id)
        parts.append(" ".join(bits))
    return ", ".join(parts)


def patch_html(html: str, build_id: str) -> str:
    def asset_repl(m: re.Match[str]) -> str:
        return m.group(1) + bust_asset_url(m.group(2), build_id) + m.group(3)

    html = ASSET_URL_RE.sub(asset_repl, html)
    html = DATA_OFFLINE_VIDEO_RE.sub(asset_repl, html)

    def srcset_repl(m: re.Match[str]) -> str:
        return m.group(1) + patch_srcset(m.group(2), build_id) + m.group(3)

    html = SRCSET_RE.sub(srcset_repl, html)

    meta = '<meta name="archive-build" content="{}" />'.format(build_id)
    if META_BUILD_RE.search(html):
        html = META_BUILD_RE.sub(meta, html, count=1)
    else:
        html = html.replace("<head>", "<head>\n" + meta, 1)
        if meta not in html:
            html = html.replace("<head>\n", "<head>\n" + meta + "\n", 1)

    return html


def main() -> int:
    parser = argparse.ArgumentParser(description="Stamp archive build id for cache busting")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    parser.add_argument("--build-id", help="Override build id (default: git short SHA)")
    args = parser.parse_args()

    snap = repo_root() / "snapshot" / args.date
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    build_id = args.build_id or git_short_sha()
    stamped = 0
    for html_path in sorted(snap.glob("*.html")):
        html = html_path.read_text(encoding="utf-8", errors="replace")
        new_html = patch_html(html, build_id)
        if new_html != html:
            html_path.write_text(new_html, encoding="utf-8")
            stamped += 1

    version_path = snap / "archive-version.json"
    version_path.write_text(
        json.dumps(
            {
                "build_id": build_id,
                "stamped_at": datetime.now(timezone.utc).isoformat(),
                "snapshot_date": args.date,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("Stamped build_id={} on {} HTML files.".format(build_id, stamped))
    print("Verify: https://legacy-personal-website.vercel.app/archive-version.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
