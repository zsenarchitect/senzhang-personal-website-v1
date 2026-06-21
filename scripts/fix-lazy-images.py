#!/usr/bin/env python3
"""Promote data-src to src on lazy Squarespace images (offline / no ImageLoader)."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
DATA_SRC_RE = re.compile(r'\bdata-src="([^"]+)"', re.IGNORECASE)
SRC_RE = re.compile(r'\bsrc="([^"]*)"', re.IGNORECASE)


def has_src_attr(tag: str) -> bool:
    return re.search(r'(?:^|\s)src\s*=', tag, re.IGNORECASE) is not None


def fix_img_tag(tag: str) -> tuple[str, bool]:
    ds = DATA_SRC_RE.search(tag)
    if not ds:
        return tag, False
    url = ds.group(1)
    if not url or url.startswith("data:"):
        return tag, False
    if has_src_attr(tag):
        return tag, False
    new_tag = tag.replace("<img", '<img src="{}"'.format(url), 1)
    new_tag = re.sub(r'\bdata-load="false"', 'data-load="true"', new_tag, flags=re.IGNORECASE)
    return new_tag, True


def patch_html(html: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        new_tag, changed = fix_img_tag(m.group(0))
        if changed:
            count += 1
        return new_tag

    return IMG_TAG_RE.sub(repl, html), count


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix lazy-loaded img tags missing src")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    args = parser.parse_args()

    snap = Path(__file__).resolve().parent.parent / "snapshot" / args.date
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    total = 0
    files: list[str] = []
    for html_path in sorted(snap.glob("*.html")):
        html = html_path.read_text(encoding="utf-8", errors="replace")
        new_html, n = patch_html(html)
        if n:
            html_path.write_text(new_html, encoding="utf-8")
            files.append("{} ({})".format(html_path.name, n))
            total += n

    print("Fixed {} img tags in {} files.".format(total, len(files)))
    for line in files:
        print("  ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
