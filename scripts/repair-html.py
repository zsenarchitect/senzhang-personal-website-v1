#!/usr/bin/env python3
"""Re-fetch HTML pages, download any new assets, and re-apply offline link rewriting."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from snapshot import (
    SITE,
    SITEMAP,
    download_all,
    extract_urls,
    fetch,
    parse_sitemap,
    rewrite_html,
    url_to_local_path,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-06-05"
    snapshot_dir = repo_root() / "snapshot" / date
    manifest_path = snapshot_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("Missing manifest: {}".format(manifest_path))

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    url_map = {
        url: snapshot_dir / rel.replace("\\", "/")
        for url, rel in manifest.get("url_to_local", {}).items()
    }

    print("Fetching sitemap...")
    pages, _ = parse_sitemap(fetch(SITEMAP))
    pages_to_fetch = list(pages)
    if SITE + "/" not in pages_to_fetch:
        pages_to_fetch.insert(0, SITE + "/")

    all_html: dict[str, str] = {}
    discovered: set[str] = set()

    print("Re-fetching {} HTML pages...".format(len(pages_to_fetch)))
    for page in pages_to_fetch:
        html = fetch(page).decode("utf-8", errors="replace")
        all_html[page] = html
        discovered.update(extract_urls(html, page))
        print("  fetched {}".format(page))
        time.sleep(0.15)

    missing = sorted(u for u in discovered if u not in url_map)
    if missing:
        print("\nDownloading {} newly discovered assets...".format(len(missing)))
        new_map, errors = download_all(set(missing), snapshot_dir)
        url_map.update(new_map)
        if errors:
            print("  {} download errors".format(len(errors)), file=sys.stderr)

    print("\nRewriting HTML...")
    for page, html in all_html.items():
        local = url_to_local_path(page, snapshot_dir)
        local.parent.mkdir(parents=True, exist_ok=True)
        fixed = rewrite_html(html, local, snapshot_dir, url_map)
        local.write_text(fixed, encoding="utf-8")
        print("  fixed {}".format(local.name))

    manifest["url_to_local"] = {
        u: str(p.relative_to(snapshot_dir)).replace("\\", "/")
        for u, p in sorted(url_map.items())
    }
    manifest["html_repaired_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\nDone. Restart serve.ps1 and reload the browser.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
