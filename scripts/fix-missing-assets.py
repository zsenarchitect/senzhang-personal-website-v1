#!/usr/bin/env python3
"""Download manifest-mapped files that are missing on disk (no HTML re-fetch)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from crawl_config import PoliteFetcher, add_crawl_cli_args, crawl_config_from_args, print_crawl_config
from snapshot import download_all


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Download missing manifest assets")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    add_crawl_cli_args(parser)
    args = parser.parse_args()
    config = crawl_config_from_args(args)
    fetcher = PoliteFetcher(config)
    print_crawl_config(config)

    snap = repo_root() / "snapshot" / args.date
    manifest_path = snap / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    url_map = manifest.get("url_to_local", {})

    missing_urls: list[str] = []
    for url, rel in url_map.items():
        p = snap / rel.replace("\\", "/")
        if p.is_file():
            continue
        if "senzhang.me" in url:
            continue  # phantom page keys
        missing_urls.append(url)

    if not missing_urls:
        print("No CDN assets missing on disk.")
        return 0

    print("Downloading {} missing manifest assets...".format(len(missing_urls)))
    path_map, errors = download_all(set(missing_urls), snap, fetcher)
    print("  downloaded {}  errors {}".format(len(path_map), len(errors)))
    if errors:
        for u, e in errors[:10]:
            print("  FAIL {}: {}".format(u[:80], e), file=sys.stderr)

    manifest["missing_assets_fixed_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
