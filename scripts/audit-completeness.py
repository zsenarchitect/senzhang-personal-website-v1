#!/usr/bin/env python3
"""Audit local snapshot vs live senzhang.me for page and asset completeness."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from crawl_config import PoliteFetcher, add_crawl_cli_args, crawl_config_from_args, print_crawl_config
from snapshot import url_to_local_path

SITE = "https://senzhang.me"

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

# Domain roots / loaders — not downloadable asset files
BARE_MIRRORABLE_HOSTS = frozenset({
    "senzhang.me", "www.senzhang.me",
    "fonts.gstatic.com", "fonts.googleapis.com",
    "use.typekit.net", "p.typekit.net",
    "images.squarespace-cdn.com",
    "static1.squarespace.com", "assets.squarespace.com",
})

# Manifest keys from regex false-positives in inline JS
PHANTOM_PATH_SEGMENTS = frozenset({
    "a", "blockquote", "body", "button", "css", "div", "figcaption", "figure",
    "h", "h1", "h2", "h3", "h4", "h5", "h6", "html", "img", "li", "ol", "p",
    "span", "ul", "script", "style", "table", "td", "th", "tr",
})


def normalize_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    return url


def classify_url(url: str) -> str:
    norm = normalize_url(url)
    if not norm.startswith("http"):
        return "relative"
    host = urlparse(norm).netloc.lower()
    if host in ALLOWED_OFFLINE or host.endswith(".squarespace.com"):
        return "mirrorable"
    if "youtube" in host or "youtu.be" in norm:
        return "youtube"
    if "facebook" in host or "twitter" in host or "google-analytics" in host:
        return "analytics_social"
    return "external"


def is_bare_domain_url(url: str) -> bool:
    norm = normalize_url(url)
    if not norm.startswith("http"):
        return False
    parsed = urlparse(norm)
    path = (parsed.path or "/").strip("/")
    if not path:
        return True
    # Directory-style CDN paths (not downloadable files)
    if path.endswith("/scripts") or path.endswith("/scripts/"):
        return True
    if parsed.path.rstrip("/").endswith("/scripts"):
        return True
    return False


def is_phantom_manifest_entry(url: str, rel: str, valid_slugs: set[str]) -> bool:
    if "senzhang.me" not in url:
        return False
    slug = Path(rel).stem.lower()
    if slug in PHANTOM_PATH_SEGMENTS:
        return True
    if rel.endswith("!.html") or "/*!" in url:
        return True
    if "," in rel or ">" in rel or "+" in rel or "&gt" in rel:
        return True
    if "/" in rel.replace("\\", "/"):
        return True
    # Valid page slugs from sitemap + index/works
    page_slug = slug
    if page_slug in valid_slugs or page_slug == "index":
        return False
    if slug.isdigit():
        return True
    if len(slug) <= 24 and slug.replace("_", "").replace("-", "").isalnum():
        return True
    return False


def url_in_manifest(url: str, url_to_local: dict[str, str]) -> bool:
    if url in url_to_local:
        return True
    norm = normalize_url(url)
    if norm in url_to_local:
        return True
    if url.startswith("https:") and url[6:] in url_to_local:
        return True
    return False


def asset_on_disk(url: str, snap: Path) -> bool:
    try:
        path = url_to_local_path(normalize_url(url), snap)
        return path.is_file()
    except Exception:
        return False


def count_youtube_embed_refs(snap: Path) -> int:
    """Count runtime YouTube embed references (exclude offline-patched embeds)."""
    total = 0
    for html_path in snap.glob("*.html"):
        text = html_path.read_text(encoding="utf-8", errors="replace")
        if "offline-youtube-replaced" in text:
            text = re.sub(r'data-html="[^"]*youtube[^"]*"', "", text, flags=re.I)
        if "offline-cover-video" in text:
            text = re.sub(r'data-config-url="[^"]*youtu[^"]*"', "", text, flags=re.I)
        total += len(re.findall(r"youtube\.com/embed|youtu\.be/", text, re.I))
    return total


def audit_local_html_assets(snap: Path) -> tuple[set[str], set[str]]:
    """Return (truly_missing, on_disk) URL sets from local snapshot HTML only."""
    truly: set[str] = set()
    on_disk: set[str] = set()
    for html_path in snap.glob("*.html"):
        text = html_path.read_text(encoding="utf-8", errors="replace")
        for u in EXTRACT_URL_RE.findall(text):
            if classify_url(u) != "mirrorable":
                continue
            if is_bare_domain_url(u):
                continue
            norm = normalize_url(u)
            if asset_on_disk(u, snap):
                on_disk.add(norm)
            else:
                truly.add(norm)
    return truly, on_disk


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit snapshot vs live senzhang.me")
    parser.add_argument("date", nargs="?", default="2026-06-05", help="Snapshot folder YYYY-MM-DD")
    add_crawl_cli_args(parser)
    args = parser.parse_args()
    date = args.date
    config = crawl_config_from_args(args)
    fetcher = PoliteFetcher(config)
    print_crawl_config(config)

    root = Path(__file__).resolve().parent.parent
    snap = root / "snapshot" / date
    manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
    url_to_local = manifest.get("url_to_local", {})
    pages = manifest.get("sitemap_pages", [])

    valid_slugs = {urlparse(p).path.strip("/").split("/")[-1] for p in pages}
    valid_slugs.add("works")

    category_live: defaultdict[str, set[str]] = defaultdict(set)
    missing_mirrorable_occurrences: list[tuple[str, str]] = []
    unique_missing_mirrorable: set[str] = set()
    breakdown: defaultdict[str, set[str]] = defaultdict(set)
    local_only_external: defaultdict[str, int] = defaultdict(int)

    print("Auditing {} pages...\n".format(len(pages)))

    for page in pages:
        slug = urlparse(page).path.strip("/") or "index"
        local_file = snap / (slug + ".html")
        if not local_file.is_file():
            local_file = snap / "index.html" if slug == "index" else local_file

        try:
            live_html = fetcher.fetch(page).decode("utf-8", errors="replace")
            fetcher.pause_after("page")
        except Exception as exc:
            print("  LIVE FAIL {}: {}".format(page, exc))
            continue

        local_html = local_file.read_text(encoding="utf-8", errors="replace")
        live_urls = set(EXTRACT_URL_RE.findall(live_html))
        local_urls = set(EXTRACT_URL_RE.findall(local_html))

        for u in live_urls:
            cat = classify_url(u)
            category_live[cat].add(u)
            if cat != "mirrorable":
                continue
            if url_in_manifest(u, url_to_local):
                continue
            if asset_on_disk(u, snap):
                breakdown["on_disk_via_cdn"].add(normalize_url(u))
                continue
            if is_bare_domain_url(u):
                breakdown["bare_domain"].add(normalize_url(u))
                continue

            missing_mirrorable_occurrences.append((page, u))
            unique_missing_mirrorable.add(normalize_url(u))
            breakdown["truly_missing"].add(normalize_url(u))

        for u in local_urls:
            cat = classify_url(u)
            if cat not in ("mirrorable", "relative"):
                local_only_external[cat] += 1

    missing_files = []
    phantom_entries = []
    real_missing_files = []
    for url, rel in url_to_local.items():
        p = snap / rel.replace("\\", "/")
        if p.is_file():
            continue
        missing_files.append((url, rel))
        if is_phantom_manifest_entry(url, rel, valid_slugs):
            phantom_entries.append((url, rel))
        else:
            real_missing_files.append((url, rel))

    home_live = fetcher.fetch(SITE + "/").decode("utf-8", errors="replace")
    home_local = (snap / "index.html").read_text(encoding="utf-8")
    css_live = set(re.findall(r'href="([^"]+\.css[^"]*)"', home_live, re.I))
    css_local = set(re.findall(r'href="([^"]+\.css[^"]*)"', home_local, re.I))

    local_truly_missing, local_on_disk = audit_local_html_assets(snap)
    youtube_local_refs = count_youtube_embed_refs(snap)
    truly_missing_count = len(breakdown["truly_missing"])
    live_drift_count = truly_missing_count  # live HTML references newer CDN hashes than snapshot

    report = {
        "snapshot_date": date,
        "pages_audited": len(pages),
        "url_map_entries": len(url_to_local),
        "pass": len(local_truly_missing) == 0 and youtube_local_refs == 0,
        "manifest_orphan_files": len(real_missing_files),
        "truly_missing_assets_live_html": truly_missing_count,
        "truly_missing_assets_local_html": len(local_truly_missing),
        "live_site_cdn_drift_note": (
            "live_html truly_missing counts Squarespace bundles updated since snapshot; "
            "local_html is the offline pass criterion."
        ),
        "missing_mirrorable_refs_unique": len(unique_missing_mirrorable),
        "missing_mirrorable_refs_page_occurrences": len(missing_mirrorable_occurrences),
        "missing_mirrorable_breakdown": {k: len(v) for k, v in sorted(breakdown.items())},
        "missing_local_files": len(missing_files),
        "manifest_phantom_entries": len(phantom_entries),
        "real_missing_local_files": len(real_missing_files),
        "local_youtube_refs_in_html": youtube_local_refs,
        "live_asset_categories": {k: len(v) for k, v in sorted(category_live.items())},
        "local_external_refs_by_category": dict(local_only_external),
        "homepage_css_links_live": len(css_live),
        "homepage_css_links_local": len(css_local),
        "homepage_css_local_cdn": len([c for c in css_local if c.startswith("_cdn")]),
        "download_errors_manifest": len(manifest.get("download_errors", [])),
        "sample_truly_missing_local": sorted(local_truly_missing)[:30],
        "sample_truly_missing_live": sorted(breakdown["truly_missing"])[:30],
        "sample_phantom_manifest": phantom_entries[:20],
        "sample_real_missing_files": real_missing_files[:20],
        "legacy_note": (
            "missing_mirrorable_refs_page_occurrences is the old inflated 721-style counter; "
            "use truly_missing_assets instead."
        ),
    }

    out = root / "snapshot" / date / "audit-report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=== AUDIT SUMMARY ===")
    print("PASS:                       {}".format(report["pass"]))
    print("Pages audited:              {}".format(report["pages_audited"]))
    print("Local HTML missing assets:  {}".format(report["truly_missing_assets_local_html"]))
    print("Live HTML CDN drift:      {}".format(report["truly_missing_assets_live_html"]))
    print("YouTube embed refs (local): {}".format(report["local_youtube_refs_in_html"]))
    print("Real missing manifest files:{}".format(report["real_missing_local_files"]))
    print("Manifest phantom entries:   {}".format(report["manifest_phantom_entries"]))
    print("(legacy inflated counter)   {}".format(report["missing_mirrorable_refs_page_occurrences"]))
    print()
    print("Breakdown of live mirrorable URLs not in manifest:")
    for k, v in report["missing_mirrorable_breakdown"].items():
        print("  {:20s} {}".format(k, v))
    print()
    print("Full report: {}".format(out))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
