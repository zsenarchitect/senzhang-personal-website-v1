#!/usr/bin/env python3
"""Copy mobile + desktop nav blocks from menu.html to every snapshot page."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "snapshot" / "2026-06-05"
MENU = SNAP / "menu.html"

RE_MOBILE = re.compile(
    r'<div id="mobileNav"><div class="wrapper">.*?</div></div>',
    re.DOTALL,
)
RE_MAIN = re.compile(
    r'<nav id="mainNavigation"[^>]*>.*?</nav>',
    re.DOTALL,
)
RE_SECONDARY = re.compile(
    r'<nav id="secondaryNavigation"[^>]*>.*?</nav>',
    re.DOTALL,
)


def extract_blocks(menu_html: str) -> dict[str, str]:
    blocks = {}
    for key, pattern in (
        ("mobile", RE_MOBILE),
        ("main", RE_MAIN),
        ("secondary", RE_SECONDARY),
    ):
        match = pattern.search(menu_html)
        if not match:
            raise SystemExit("menu.html missing {} nav block".format(key))
        blocks[key] = match.group(0)
    return blocks


def sync_html(html: str, blocks: dict[str, str]) -> tuple[str, list[str]]:
    changed = []
    for key, pattern in (
        ("mobile", RE_MOBILE),
        ("main", RE_MAIN),
        ("secondary", RE_SECONDARY),
    ):
        if not pattern.search(html):
            continue
        html = pattern.sub(blocks[key], html, count=1)
        changed.append(key)
    return html, changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync nav from menu.html to snapshot pages")
    parser.add_argument("--snap", type=Path, default=SNAP)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    snap = args.snap
    menu = snap / "menu.html"
    if not menu.is_file():
        print("Missing {}".format(menu), file=sys.stderr)
        return 1

    menu_html = menu.read_text(encoding="utf-8")
    blocks = extract_blocks(menu_html)
    updated = 0
    skipped = 0

    for path in sorted(snap.rglob("*.html")):
        if path.name == "menu.html":
            continue
        html = path.read_text(encoding="utf-8")
        if "mainNavigation" not in html and "mobileNav" not in html:
            skipped += 1
            continue
        new_html, changed = sync_html(html, blocks)
        if not changed:
            skipped += 1
            continue
        if new_html != html:
            updated += 1
            rel = path.relative_to(snap)
            print("sync {} ({})".format(rel, ",".join(changed)))
            if not args.dry_run:
                path.write_text(new_html, encoding="utf-8")

    print("Updated {} page(s); skipped {}.".format(updated, skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
