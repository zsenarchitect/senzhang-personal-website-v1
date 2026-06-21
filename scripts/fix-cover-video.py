#!/usr/bin/env python3
"""Download homepage cover YouTube video and patch cover pages for offline playback."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

VIDEO_ID = "mYPQl6m7kMY"
YOUTUBE_URL = "https://www.youtube.com/watch?v={}".format(VIDEO_ID)
from cover_video_effects import apply_cover_effects, build_cover_style, build_playback_script, parse_gallery_config

COVER_PAGES = ("index.html", "cover-page.html")

OFFLINE_VIDEO_STYLE = build_cover_style(2, 13)

LAYER_BACK_SHELL_RE = re.compile(
    r'(<div class="sqs-slide-layer layer-back[^"]*">)\s*'
    r'(<div class="sqs-slide-layer-content">)',
    re.IGNORECASE,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def download_video(media_dir: Path) -> Path:
    media_dir.mkdir(parents=True, exist_ok=True)
    out_tmpl = str(media_dir / "cover-background.%(ext)s")
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-f",
        "best[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        out_tmpl,
        YOUTUBE_URL,
    ]
    print("Running: {}".format(" ".join(cmd)))
    subprocess.run(cmd, check=True)
    mp4 = media_dir / "cover-background.mp4"
    if not mp4.is_file():
        candidates = sorted(media_dir.glob("cover-background.*"))
        if not candidates:
            raise RuntimeError("yt-dlp finished but no output file found")
        mp4 = candidates[0]
        if mp4.suffix != ".mp4":
            mp4.rename(media_dir / "cover-background.mp4")
            mp4 = media_dir / "cover-background.mp4"
    return mp4


def patch_cover_html(snap: Path, video_rel: str, poster_rel: str) -> list[str]:
    patched: list[str] = []
    shell = (
        '<div class="offline-cover-video-shell">'
        '<video class="offline-cover-video" autoplay muted loop playsinline '
        'src="{src}" poster="{poster}"></video></div>\n  '
    ).format(src=video_rel, poster=poster_rel)
    for name in COVER_PAGES:
        html_path = snap / name
        if not html_path.is_file():
            continue
        html = html_path.read_text(encoding="utf-8", errors="replace")
        if "offline-cover-video-shell" in html:
            html, _ = apply_cover_effects(html)
            html_path.write_text(html, encoding="utf-8")
            patched.append(name)
            print("  refreshed effects {}".format(name))
            continue
        if OFFLINE_VIDEO_STYLE.strip() not in html:
            html = html.replace("</head>", OFFLINE_VIDEO_STYLE + "\n</head>", 1)
        html, n = LAYER_BACK_SHELL_RE.subn(r"\1\n  " + shell + r"\2", html, count=1)
        if n == 0:
            continue
        html, _ = apply_cover_effects(html)
        html_path.write_text(html, encoding="utf-8")
        patched.append(name)
        print("  patched {}".format(name))
    return patched


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline homepage cover video")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    parser.add_argument("--skip-download", action="store_true", help="Only patch HTML if mp4 exists")
    args = parser.parse_args()

    snap = repo_root() / "snapshot" / args.date
    media_dir = snap / "_media"
    manifest_path = snap / "manifest.json"
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    mp4 = media_dir / "cover-background.mp4"
    if not mp4.is_file() and not args.skip_download:
        print("Downloading cover video {}...".format(YOUTUBE_URL))
        mp4 = download_video(media_dir)
    elif not mp4.is_file():
        raise SystemExit("Missing {} (run without --skip-download)".format(mp4))

    poster_rel = "_cdn/static1.squarespace.com/39c6f80dd61c257d8eef.png"
    video_rel = "_media/cover-background.mp4"
    print("Patching cover pages...")
    patched = patch_cover_html(snap, video_rel, poster_rel)

    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["cover_video_offline_fixed_at"] = datetime.now(timezone.utc).isoformat()
        manifest["cover_video_local"] = video_rel
        manifest["cover_video_source"] = YOUTUBE_URL
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\nDone. Patched: {}.".format(", ".join(patched) or "(none)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
