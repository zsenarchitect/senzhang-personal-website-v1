#!/usr/bin/env python3
"""Rebuild works.html from menu.html — portfolio index with Works metadata.

Snapshot had works.html as a duplicate of museum-of-verbs.html. Live /works also
serves Museum of Verbs (Squarespace folder mis-route). Nav \"Works\" should show
the portfolio grid (menu.html content) with correct Works title/canonical.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def rebuild_works(snap: Path) -> Path:
    menu = snap / "menu.html"
    works = snap / "works.html"
    if not menu.is_file():
        raise SystemExit("Missing menu.html: {}".format(menu))

    html = menu.read_text(encoding="utf-8")

    html = html.replace("<title>Menu &mdash; Sen Zhang</title>", "<title>Works &mdash; Sen Zhang</title>")
    html = html.replace('href="menu.html"', 'href="works.html"', 1)  # canonical only (first in head)
    html = html.replace('content="Menu &mdash; Sen Zhang"', 'content="Works &mdash; Sen Zhang"')
    html = html.replace('content="Menu — Sen Zhang"', 'content="Works — Sen Zhang"')
    html = html.replace('content="menu.html"', 'content="works.html"')
    html = html.replace('"fullSiteTitle":"Menu \\u2014 Sen Zhang"', '"fullSiteTitle":"Works \\u2014 Sen Zhang"')
    html = html.replace(
        '"collection":{"title":"Menu","id":"593e0796c534a5c8d10121cb","fullUrl":"/menu"',
        '"collection":{"title":"Works","id":"593e0796c534a5c8d10121cb","fullUrl":"/works"',
    )
    html = html.replace(
        '<p style="text-align:center;white-space:pre-wrap;" class=""><a href="menu.html">back to top</a></p>',
        '<p style="text-align:center;white-space:pre-wrap;" class=""><a href="works.html">back to top</a></p>',
    )

    if "Museum of Verbs" in html[:2000]:
        raise SystemExit("works.html still looks like museum-of-verbs after patch")
    if "<title>Works" not in html:
        raise SystemExit("title patch failed")

    works.write_text(html, encoding="utf-8")
    return works


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild works.html from menu.html")
    parser.add_argument("date", nargs="?", default="2026-06-05", help="Snapshot folder YYYY-MM-DD")
    args = parser.parse_args()
    snap = repo_root() / "snapshot" / args.date
    out = rebuild_works(snap)
    print("Wrote {} ({:,} bytes) from menu.html".format(out, out.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
