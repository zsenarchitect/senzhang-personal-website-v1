#!/usr/bin/env python3
"""
Create a dated 1:1 offline snapshot of https://senzhang.me (Squarespace).

Downloads all sitemap pages, embedded assets from Squarespace CDNs, fonts,
and platform JS/CSS. Rewrites HTML links for offline browsing.

Crawl politeness is configured via scripts/crawl-config.json (default profile: safe).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse

from crawl_config import (
    CrawlConfig,
    PoliteFetcher,
    add_crawl_cli_args,
    crawl_config_from_args,
    print_crawl_config,
)

SITE = "https://senzhang.me"
SITEMAP = SITE + "/sitemap.xml"

ALLOWED_NETLOCS = {
    "senzhang.me",
    "www.senzhang.me",
    "static1.squarespace.com",
    "images.squarespace-cdn.com",
    "assets.squarespace.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "use.typekit.net",
    "p.typekit.net",
}

# Only match real absolute URLs — never bare "/css" or "/script" inside HTML tags.
EXTRACT_URL_RE = re.compile(
    r"https?://[^\s\"'<>\\]+|"
    r"//(?:[a-z0-9-]+\.)+"
    r"(?:squarespace\.com|squarespace-cdn\.com|typekit\.net|googleapis\.com|gstatic\.com)"
    r"[^\s\"'<>\\]*",
    re.IGNORECASE,
)

SKIP_EXTENSIONS = {".json", ".xml"}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def normalize_url(url: str, base: str = SITE) -> str | None:
    if not url or url.startswith(("mailto:", "javascript:", "data:", "#")):
        return None
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = urljoin(SITE, url)
    elif not url.startswith("http"):
        url = urljoin(base, url)

    parsed = urlparse(url)
    if not parsed.netloc:
        return None
    if parsed.netloc not in ALLOWED_NETLOCS:
        return None
    # Skip bare domain URLs (no path) — not downloadable files
    if not parsed.path or parsed.path == "/":
        if not parsed.query:
            return None

    # Drop fragments; keep query (Squarespace image format params matter)
    clean = parsed._replace(fragment="")
    return urlunparse(clean)


def url_to_local_path(url: str, snapshot_dir: Path) -> Path:
    parsed = urlparse(url)

    if parsed.netloc in ("senzhang.me", "www.senzhang.me"):
        path = parsed.path or "/"
        rel = path.strip("/")
        if not rel:
            rel = "index.html"
        elif not Path(rel).suffix:
            rel = rel + ".html"
        return snapshot_dir / rel

    # CDN assets: hash-based paths avoid Windows MAX_PATH and file/dir clashes
    ext = Path(parsed.path).suffix
    if not ext:
        # Guess from query or default
        if "format=" in (parsed.query or ""):
            ext = ".bin"
        else:
            ext = ""
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    name = digest + ext
    return snapshot_dir / "_cdn" / parsed.netloc / name


def extract_urls(content: str, base_url: str) -> set[str]:
    found: set[str] = set()
    for raw in EXTRACT_URL_RE.findall(content):
        normalized = normalize_url(raw, base_url)
        if normalized:
            found.add(normalized)
    return found


def parse_sitemap(xml_bytes: bytes) -> tuple[list[str], list[str]]:
    root = ET.fromstring(xml_bytes)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9", "img": "http://www.google.com/schemas/sitemap-image/1.1"}
    pages: list[str] = []
    images: list[str] = []
    for url_el in root.findall("sm:url", ns):
        loc = url_el.find("sm:loc", ns)
        if loc is not None and loc.text:
            pages.append(loc.text.strip())
        for img in url_el.findall("img:image/img:loc", ns):
            if img.text:
                n = normalize_url(img.text.strip())
                if n:
                    images.append(n)
    return pages, images


def relative_href(from_path: Path, to_path: Path) -> str:
    return os.path.relpath(to_path, from_path.parent).replace("\\", "/")


def rewrite_html(html: str, page_path: Path, snapshot_dir: Path, url_map: dict[str, Path]) -> str:
    replacements: dict[str, str] = {}
    for abs_url, local in url_map.items():
        if not local.exists():
            continue
        rel = relative_href(page_path, local)
        replacements[abs_url] = rel
        parsed = urlparse(abs_url)
        path_q = parsed.path + (("?" + parsed.query) if parsed.query else "")
        replacements["//" + parsed.netloc + path_q] = rel
        if parsed.scheme == "https":
            replacements["http://" + parsed.netloc + path_q] = rel

    for url in sorted(replacements, key=len, reverse=True):
        html = html.replace(url, replacements[url])

    def fix_internal_href(match: re.Match[str]) -> str:
        path = match.group(1).strip("/")
        if not path:
            target = snapshot_dir / "index.html"
        else:
            target = snapshot_dir / (path + ".html")
        if not target.is_file():
            return match.group(0)
        rel = relative_href(page_path, target)
        return 'href="{}"'.format(rel)

    html = re.sub(r'href="(/[A-Za-z0-9._-]+)/?"', fix_internal_href, html)
    return html


def download_all(
    urls: set[str],
    snapshot_dir: Path,
    fetcher: PoliteFetcher,
) -> tuple[dict[str, Path], list[dict[str, str]]]:
    url_map: dict[str, Path] = {}
    errors: list[dict[str, str]] = []
    sorted_urls = sorted(urls, key=lambda u: (urlparse(u).netloc, u))

    for i, url in enumerate(sorted_urls, 1):
        local = url_to_local_path(url, snapshot_dir)
        url_map[url] = local
        if local.exists() and local.stat().st_size > 0:
            print(f"  [{i}/{len(sorted_urls)}] skip (exists) {url}")
            continue

        local.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = fetcher.fetch(url)
            local.write_bytes(data)
            print(f"  [{i}/{len(sorted_urls)}] ok {url}")
            fetcher.pause_after("asset")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            errors.append({"url": url, "error": str(exc)})
            print(f"  [{i}/{len(sorted_urls)}] FAIL {url}: {exc}", file=sys.stderr)

    return url_map, errors


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline snapshot of senzhang.me")
    parser.add_argument(
        "date",
        nargs="?",
        default=None,
        help="Snapshot folder name YYYY-MM-DD (default: today UTC)",
    )
    add_crawl_cli_args(parser)
    return parser


def run_snapshot(date: str, config: CrawlConfig) -> int:
    snapshot_dir = repo_root() / "snapshot" / date
    if snapshot_dir.exists():
        print(f"Snapshot dir exists: {snapshot_dir}")
        print("Remove it first or pass a different date.")
        return 1

    fetcher = PoliteFetcher(config)
    snapshot_dir.mkdir(parents=True)
    print_crawl_config(config)
    print(f"Fetching sitemap: {SITEMAP}")
    sitemap_bytes = fetcher.fetch(SITEMAP)
    fetcher.pause_after("page")
    pages, sitemap_images = parse_sitemap(sitemap_bytes)

    all_urls: set[str] = set()
    all_urls.update(pages)
    all_urls.update(sitemap_images)

    print(f"Sitemap: {len(pages)} pages, {len(sitemap_images)} image refs")
    print("Crawling pages for linked assets...")

    page_html: dict[str, str] = {}
    for page in pages:
        try:
            raw = fetcher.fetch(page).decode("utf-8", errors="replace")
            page_html[page] = raw
            found = extract_urls(raw, page)
            before = len(all_urls)
            all_urls.update(found)
            print(f"  {page}: +{len(all_urls) - before} assets")
            fetcher.pause_after("page")
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"  FAIL page {page}: {exc}", file=sys.stderr)

    # Homepage may redirect; ensure root is included
    if SITE not in all_urls and SITE + "/" not in all_urls:
        try:
            raw = fetcher.fetch(SITE + "/").decode("utf-8", errors="replace")
            page_html[SITE + "/"] = raw
            all_urls.add(SITE + "/")
            all_urls.update(extract_urls(raw, SITE + "/"))
            fetcher.pause_after("page")
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"  FAIL homepage: {exc}", file=sys.stderr)

    # Filter out non-downloadable
    all_urls = {u for u in all_urls if normalize_url(u)}

    print(f"\nDownloading {len(all_urls)} URLs...")
    url_map, errors = download_all(all_urls, snapshot_dir, fetcher)

    print("\nRewriting HTML for offline links...")
    for page_url, html in page_html.items():
        local = url_to_local_path(page_url, snapshot_dir)
        local.parent.mkdir(parents=True, exist_ok=True)
        rewritten = rewrite_html(html, local, snapshot_dir, url_map)
        local.write_text(rewritten, encoding="utf-8")

    files = list(snapshot_dir.rglob("*"))
    file_list = [f for f in files if f.is_file()]
    total_bytes = sum(f.stat().st_size for f in file_list)

    manifest = {
        "snapshot_date": date,
        "source_url": SITE,
        "platform": "Squarespace",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "crawl_config": config.to_manifest_dict(),
        "page_count_sitemap": len(pages),
        "url_count": len(all_urls),
        "file_count": len(file_list),
        "total_bytes": total_bytes,
        "sitemap_pages": pages,
        "download_errors": errors,
        "offline_entry": "index.html",
        "url_to_local": {u: str(url_map[u].relative_to(snapshot_dir)).replace("\\", "/") for u in sorted(url_map)},
    }
    manifest_path = snapshot_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\nDone.")
    print(f"  Snapshot: {snapshot_dir}")
    print(f"  Files:    {len(file_list)}")
    print(f"  Size:     {total_bytes / (1024 * 1024):.2f} MB")
    print(f"  Errors:   {len(errors)}")
    print(f"  Open:     {snapshot_dir / 'index.html'}")
    return 0 if not errors else 2


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    config = crawl_config_from_args(args)
    return run_snapshot(date, config)


if __name__ == "__main__":
    raise SystemExit(main())
