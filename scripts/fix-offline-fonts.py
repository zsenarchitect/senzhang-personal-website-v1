#!/usr/bin/env python3
"""Download Google Fonts + Typekit binaries and wire them for offline use."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from crawl_config import PoliteFetcher, crawl_config_from_args, print_crawl_config

GSTATIC_RE = re.compile(r"url\((https://fonts\.gstatic\.com/[^)]+)\)")
TYPEKIT_CONFIG_RE = re.compile(r"window\.Typekit\.config=(\{.*?\});", re.DOTALL)
TYPEKIT_SRC_RE = re.compile(
    r'"src":"(https://use\.typekit\.net/af/[^"]+)"[^}]*"descriptors":\{"weight":"([^"]+)","style":"([^"]+)"'
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def hash_name(url: str, ext: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    return digest + ext


def typekit_woff2_url(template: str, weight: str, style: str) -> str:
    fvd = "{}{}".format(style[0], weight[0])
    return (
        template.replace("{format}", "l")
        .replace("{?primer,subset_id,fvd,v}", "?subset_id=2&fvd={}&v=3".format(fvd))
        .replace("{format}{?primer,subset_id,fvd,v}", "l?subset_id=2&fvd={}&v=3".format(fvd))
    )


def fix_google_fonts(snap: Path, fetcher: PoliteFetcher) -> list[dict[str, str]]:
    css_dir = snap / "_cdn" / "fonts.googleapis.com"
    gstatic_dir = snap / "_cdn" / "fonts.gstatic.com"
    gstatic_dir.mkdir(parents=True, exist_ok=True)
    fixed: list[dict[str, str]] = []

    for css_file in sorted(css_dir.iterdir()):
        if not css_file.is_file():
            continue
        text = css_file.read_text(encoding="utf-8")
        changed = False
        for match in GSTATIC_RE.finditer(text):
            url = match.group(1)
            ext = Path(urlparse(url).path).suffix or ".ttf"
            local_name = hash_name(url, ext)
            local_path = gstatic_dir / local_name
            if not local_path.is_file():
                local_path.write_bytes(fetcher.fetch(url))
                fetcher.pause_after("asset")
                print("  downloaded {}".format(url))
            rel = "../fonts.gstatic.com/{}".format(local_name)
            text = text.replace(url, rel)
            changed = True
            fixed.append({"url": url, "local": str(local_path.relative_to(snap)).replace("\\", "/")})
        if changed:
            css_file.write_text(text, encoding="utf-8")
            print("  rewrote {}".format(css_file.name))
    return fixed


def fix_typekit(snap: Path, fetcher: PoliteFetcher) -> list[dict[str, str]]:
    tk_dir = snap / "_cdn" / "use.typekit.net"
    css_lines: list[str] = []
    fixed: list[dict[str, str]] = []

    for js_file in sorted(tk_dir.glob("*.js")):
        text = js_file.read_text(encoding="utf-8", errors="replace")
        if "window.Typekit.config" not in text:
            continue
        for template, weight, style in TYPEKIT_SRC_RE.findall(text):
            url = typekit_woff2_url(template, weight, style)
            local_name = hash_name(url, ".woff2")
            local_path = tk_dir / local_name
            if not local_path.is_file():
                local_path.write_bytes(fetcher.fetch(url))
                fetcher.pause_after("asset")
                print("  downloaded typekit {}".format(url))
            family = "proxima-nova"
            font_style = style
            font_weight = weight
            rel = "use.typekit.net/{}".format(local_name)
            css_lines.append(
                "@font-face{{font-family:'{family}';src:url('{rel}') format('woff2');"
                "font-weight:{weight};font-style:{style};font-display:auto;}}".format(
                    family=family, rel=rel, weight=font_weight, style=font_style
                )
            )
            fixed.append({"url": url, "local": str(local_path.relative_to(snap)).replace("\\", "/")})

    if not css_lines:
        return fixed

    css_path = snap / "_cdn" / "offline-typekit.css"
    css_path.write_text("\n".join(css_lines) + "\n", encoding="utf-8")
    print("  wrote {}".format(css_path.relative_to(snap)))

    link_tag = '<link rel="stylesheet" href="_cdn/offline-typekit.css">'
    for html in snap.glob("*.html"):
        body = html.read_text(encoding="utf-8", errors="replace")
        if link_tag in body:
            continue
        if "offline-typekit.css" in body:
            continue
        if "use.typekit.net" not in body:
            continue
        needle = '<script type="text/javascript" src="_cdn/use.typekit.net/'
        if needle in body:
            body = body.replace(needle, link_tag + "\n" + needle, 1)
            html.write_text(body, encoding="utf-8")
            print("  linked typekit css in {}".format(html.name))
    return fixed


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix offline fonts in a snapshot")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    from crawl_config import add_crawl_cli_args

    add_crawl_cli_args(parser)
    args = parser.parse_args()
    config = crawl_config_from_args(args)
    fetcher = PoliteFetcher(config)

    snap = repo_root() / "snapshot" / args.date
    manifest_path = snap / "manifest.json"
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    print_crawl_config(config)
    print("Fixing Google Fonts in {}...".format(snap))
    google = fix_google_fonts(snap, fetcher)
    print("Fixing Typekit in {}...".format(snap))
    typekit = fix_typekit(snap, fetcher)

    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["fonts_offline_fixed_at"] = datetime.now(timezone.utc).isoformat()
        manifest["fonts_offline"] = {"google": google, "typekit": typekit}
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\nDone. Google: {}, Typekit: {}.".format(len(google), len(typekit)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
