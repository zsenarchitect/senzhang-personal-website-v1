#!/usr/bin/env python3
"""Fix Squarespace has-aspect-ratio image blocks for offline viewing (img must fill padded box)."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

STYLE_ID = "offline-aspect-ratio-fix"
STYLE_CHECK = '<style id="offline-aspect-ratio-fix">'

ASPECT_CSS = """
<style id="offline-aspect-ratio-fix">
.sqs-image-shape-container-element.has-aspect-ratio {
  position: relative;
}
.sqs-image-shape-container-element.has-aspect-ratio > img {
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
  width: 100% !important;
  height: 100% !important;
  object-fit: cover;
  object-position: center center;
}
</style>
"""

STYLE_RE = re.compile(
    r'<style id="offline-aspect-ratio-fix">.*?</style>\s*',
    re.DOTALL | re.IGNORECASE,
)


def inject_aspect_fix(html: str) -> str:
    if STYLE_CHECK in html:
        return STYLE_RE.sub(ASPECT_CSS.strip() + "\n", html, count=1)
    if "</head>" in html:
        return html.replace("</head>", ASPECT_CSS + "\n</head>", 1)
    return ASPECT_CSS + html


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("date", nargs="?", default="2026-06-05")
    args = parser.parse_args()

    snap = Path(__file__).resolve().parent.parent / "snapshot" / args.date
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    patched = 0
    for html_path in sorted(snap.rglob("*.html")):
        if "_cdn" in html_path.parts:
            continue
        html = html_path.read_text(encoding="utf-8", errors="replace")
        if "has-aspect-ratio" not in html:
            continue
        new_html = inject_aspect_fix(html)
        if new_html != html:
            html_path.write_text(new_html, encoding="utf-8")
            patched += 1
    print("Patched aspect-ratio fix into {} HTML files.".format(patched))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
