#!/usr/bin/env python3
"""Re-apply Squarespace-matched blur/brightness + playback speed on offline cover video."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cover_video_effects import apply_cover_effects, parse_gallery_config, filter_css

COVER_PAGES = ("index.html", "cover-page.html")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply cover video blur/filter CSS offline")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    args = parser.parse_args()

    snap = repo_root() / "snapshot" / args.date
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    patched: list[str] = []
    for name in COVER_PAGES:
        html_path = snap / name
        if not html_path.is_file():
            continue
        html = html_path.read_text(encoding="utf-8", errors="replace")
        if "offline-cover-video-shell" not in html:
            print("  skip {} (no offline cover shell)".format(name))
            continue
        speed, filt, strength = parse_gallery_config(html)
        css, is_blur = filter_css(filt, strength)
        print("  {} filter={} strength={} -> {} speed={}".format(name, filt, strength, css or "none", speed))
        new_html, _ = apply_cover_effects(html)
        if new_html != html:
            html_path.write_text(new_html, encoding="utf-8")
            patched.append(name)

    print("\nDone. Patched: {}.".format(", ".join(patched) or "(none)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
