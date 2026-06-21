#!/usr/bin/env python3
"""Find image refs in HTML that are missing on disk."""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

IMG_URL_RE = re.compile(
    r'(?:src|data-src|data-image|href)=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
SRCSET_RE = re.compile(r'srcset=["\']([^"\']+)["\']', re.IGNORECASE)


def collect_urls(html: str) -> set[str]:
    urls: set[str] = set()
    for m in IMG_URL_RE.finditer(html):
        u = unquote(m.group(1).strip())
        if u and not u.startswith(("data:", "javascript:", "mailto:", "#")):
            urls.add(u)
    for m in SRCSET_RE.finditer(html):
        for part in m.group(1).split(","):
            tok = part.strip().split()[0] if part.strip() else ""
            if tok:
                urls.add(unquote(tok))
    return urls


def is_local(u: str) -> bool:
    return not u.startswith(("http://", "https://", "//"))


def main() -> int:
    snap = Path(__file__).resolve().parent.parent / "snapshot" / "2026-06-05"
    pages = [sys.argv[1]] if len(sys.argv) > 1 else sorted(p.name for p in snap.glob("*.html"))

    total_missing: Counter[str] = Counter()
    for name in pages:
        html_path = snap / name
        if not html_path.is_file():
            continue
        html = html_path.read_text(encoding="utf-8", errors="replace")
        missing = []
        for u in sorted(collect_urls(html)):
            if not is_local(u):
                continue
            rel = u.split("?", 1)[0].split("#", 1)[0]
            if not (snap / rel.replace("/", "\\")).is_file() and not (snap / rel).is_file():
                missing.append(rel)
        if missing:
            print("\n{} — {} missing".format(name, len(missing)))
            for m in missing[:20]:
                print("  ", m)
            if len(missing) > 20:
                print("  ... +{} more".format(len(missing) - 20))
            total_missing[name] = len(missing)

    print("\nSummary:", dict(total_missing) if total_missing else "all local refs OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
