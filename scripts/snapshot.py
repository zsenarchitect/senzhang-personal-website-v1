#!/usr/bin/env python3
"""
Create a dated 1:1 offline snapshot of https://senzhang.me (Squarespace).

Downloads all sitemap pages, embedded assets from Squarespace CDNs, fonts,
and platform JS/CSS. Rewrites HTML links for offline browsing.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

SITE = "https://senzhang.me"
SITEMAP = SITE + "/sitemap.xml"
USER_AGENT = "senzhang-legacy-archive/1.0 (+https://github.com/zsenarchitect/senzhang-legacy-website-archive)"

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

URL_RE = re.compile(
    r"""(?P<quote>['"]?)(?P<url>(?:https?:)?//[^\s'"<>]+|/[^\s'"<>]+)(?P=quote)""",
    re.IGNORECASE,
)

SKIP_EXTENSIONS = {".json", ".xml"}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def fetch(url: str, timeout: int = 60) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


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
    for match in URL_RE.finditer(content):
        raw = match.group("url")
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
    def replacer(match: re.Match[str]) -> str:
        quote = match.group("quote") or ""
        raw = match.group("url")
        normalized = normalize_url(raw, SITE)
        if not normalized or normalized not in url_map:
            return match.group(0)
        local = url_map[normalized]
        rel = relative_href(page_path, local)
        return quote + rel + quote

    return URL_RE.sub(replacer, html)


def download_all(urls: set[str], snapshot_dir: Path) -> tuple[dict[str, Path], list[dict[str, str]]]:
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
            data = fetch(url)
            local.write_bytes(data)
            print(f"  [{i}/{len(sorted_urls)}] ok {url}")
            time.sleep(0.15)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            errors.append({"url": url, "error": str(exc)})
            print(f"  [{i}/{len(sorted_urls)}] FAIL {url}: {exc}", file=sys.stderr)

    return url_map, errors


def main() -> int:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if len(sys.argv) > 1:
        date = sys.argv[1]

    snapshot_dir = repo_root() / "snapshot" / date
    if snapshot_dir.exists():
        print(f"Snapshot dir exists: {snapshot_dir}")
        print("Remove it first or pass a different date as argv[1].")
        return 1

    snapshot_dir.mkdir(parents=True)
    print(f"Fetching sitemap: {SITEMAP}")
    sitemap_bytes = fetch(SITEMAP)
    pages, sitemap_images = parse_sitemap(sitemap_bytes)

    all_urls: set[str] = set()
    all_urls.update(pages)
    all_urls.update(sitemap_images)

    print(f"Sitemap: {len(pages)} pages, {len(sitemap_images)} image refs")
    print("Crawling pages for linked assets...")

    page_html: dict[str, str] = {}
    for page in pages:
        try:
            raw = fetch(page).decode("utf-8", errors="replace")
            page_html[page] = raw
            found = extract_urls(raw, page)
            before = len(all_urls)
            all_urls.update(found)
            print(f"  {page}: +{len(all_urls) - before} assets")
            time.sleep(0.2)
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"  FAIL page {page}: {exc}", file=sys.stderr)

    # Homepage may redirect; ensure root is included
    if SITE not in all_urls and SITE + "/" not in all_urls:
        try:
            raw = fetch(SITE + "/").decode("utf-8", errors="replace")
            page_html[SITE + "/"] = raw
            all_urls.add(SITE + "/")
            all_urls.update(extract_urls(raw, SITE + "/"))
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"  FAIL homepage: {exc}", file=sys.stderr)

    # Filter out non-downloadable
    all_urls = {u for u in all_urls if normalize_url(u)}

    print(f"\nDownloading {len(all_urls)} URLs...")
    url_map, errors = download_all(all_urls, snapshot_dir)

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


if __name__ == "__main__":
    raise SystemExit(main())
