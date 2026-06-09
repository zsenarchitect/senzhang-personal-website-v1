#!/usr/bin/env python3
"""Audit local snapshot vs live senzhang.me for page and asset completeness."""
from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SITE = "https://senzhang.me"
USER_AGENT = "senzhang-legacy-audit/1.0"

EXTRACT_URL_RE = re.compile(
    r"https?://[^\s\"'<>\\]+|"
    r"//(?:[a-z0-9-]+\.)+"
    r"(?:squarespace\.com|squarespace-cdn\.com|typekit\.net|googleapis\.com|gstatic\.com|youtu\.be|youtube\.com)"
    r"[^\s\"'<>\\]*",
    re.IGNORECASE,
)

ALLOWED_OFFLINE = {
    "senzhang.me", "www.senzhang.me",
    "static1.squarespace.com", "images.squarespace-cdn.com",
    "assets.squarespace.com", "fonts.googleapis.com", "fonts.gstatic.com",
    "use.typekit.net", "p.typekit.net",
}


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def classify_url(url: str) -> str:
    if url.startswith("//"):
        url = "https:" + url
    if not url.startswith("http"):
        return "relative"
    host = urlparse(url).netloc.lower()
    if host in ALLOWED_OFFLINE or host.endswith(".squarespace.com"):
        return "mirrorable"
    if "youtube" in host or "youtu.be" in host:
        return "youtube"
    if "facebook" in host or "twitter" in host or "google-analytics" in host:
        return "analytics_social"
    return "external"


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-06-05"
    root = Path(__file__).resolve().parent.parent
    snap = root / "snapshot" / date
    manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
    url_to_local = manifest.get("url_to_local", {})
    pages = manifest.get("sitemap_pages", [])

    live_assets: dict[str, set[str]] = {}
    local_assets: dict[str, set[str]] = {}
    category_live: defaultdict[str, set[str]] = defaultdict(set)
    missing_mirrorable: list[tuple[str, str]] = []
    local_only_external: defaultdict[str, int] = defaultdict(int)

    print("Auditing {} pages...\n".format(len(pages)))

    for page in pages:
        slug = urlparse(page).path.strip("/") or "index"
        local_file = snap / (slug + ".html")
        if not local_file.is_file():
            local_file = snap / "index.html" if slug == "index" else local_file

        try:
            live_html = fetch(page)
            time.sleep(0.15)
        except Exception as exc:
            print("  LIVE FAIL {}: {}".format(page, exc))
            continue

        local_html = local_file.read_text(encoding="utf-8", errors="replace")
        live_urls = set(EXTRACT_URL_RE.findall(live_html))
        local_urls = set(EXTRACT_URL_RE.findall(local_html))

        live_assets[page] = live_urls
        local_assets[page] = local_urls

        for u in live_urls:
            cat = classify_url(u)
            category_live[cat].add(u)
            if cat == "mirrorable" and u not in url_to_local:
                # protocol-relative vs https
                norm = u if u.startswith("http") else "https:" + u
                if norm not in url_to_local and u not in url_to_local:
                    missing_mirrorable.append((page, u))

        # External refs still in local HTML (not rewritten = expected for some)
        for u in local_urls:
            cat = classify_url(u)
            if cat not in ("mirrorable", "relative"):
                local_only_external[cat] += 1

    # Local file existence for mapped URLs
    missing_files = []
    for url, rel in url_to_local.items():
        p = snap / rel.replace("\\", "/")
        if not p.is_file():
            missing_files.append((url, rel))

    # Style-related: CSS + font URLs on homepage
    home_live = fetch(SITE + "/")
    home_local = (snap / "index.html").read_text(encoding="utf-8")
    css_live = set(re.findall(r'href="([^"]+\.css[^"]*)"', home_live, re.I))
    css_local = set(re.findall(r'href="([^"]+\.css[^"]*)"', home_local, re.I))
    css_live_abs = {u for u in css_live if u.startswith("http") or u.startswith("//") or u.startswith("_cdn")}
    css_local_abs = {u for u in css_local if u.startswith("_cdn") or u.startswith("http")}

    report = {
        "snapshot_date": date,
        "pages_audited": len(pages),
        "url_map_entries": len(url_to_local),
        "missing_local_files": len(missing_files),
        "missing_mirrorable_refs": len(missing_mirrorable),
        "live_asset_categories": {k: len(v) for k, v in sorted(category_live.items())},
        "local_external_refs_by_category": dict(local_only_external),
        "homepage_css_links_live": len(css_live),
        "homepage_css_links_local": len(css_local),
        "homepage_css_local_cdn": len([c for c in css_local if c.startswith("_cdn")]),
        "download_errors_manifest": len(manifest.get("download_errors", [])),
        "sample_missing_mirrorable": missing_mirrorable[:30],
        "sample_missing_files": missing_files[:20],
    }

    out = root / "snapshot" / date / "audit-report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=== AUDIT SUMMARY ===")
    print("Pages audited:              {}".format(report["pages_audited"]))
    print("URL map entries:            {}".format(report["url_map_entries"]))
    print("Missing files on disk:      {}".format(report["missing_local_files"]))
    print("Live mirrorable not in map: {}".format(report["missing_mirrorable_refs"]))
    print("Manifest download errors:   {}".format(report["download_errors_manifest"]))
    print()
    print("Live asset categories (unique URLs across all pages):")
    for k, v in report["live_asset_categories"].items():
        print("  {:20s} {}".format(k, v))
    print()
    print("External refs still in local HTML (count across pages):")
    for k, v in sorted(local_only_external.items()):
        print("  {:20s} {}".format(k, v))
    print()
    print("Homepage CSS links: live={} local={} local_cdn={}".format(
        report["homepage_css_links_live"],
        report["homepage_css_links_local"],
        report["homepage_css_local_cdn"],
    ))
    print()
    print("Full report: {}".format(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
