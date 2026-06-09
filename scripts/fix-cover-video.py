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
COVER_PAGES = ("index.html", "cover-page.html")

OFFLINE_VIDEO_STYLE = """
<style id="offline-cover-video-style">
.sqs-slice-gallery-item.gallery-video-background #player { display: none !important; }
.sqs-slice-gallery-item.gallery-video-background video.offline-cover-video {
  position: absolute; top: 50%; left: 50%; min-width: 100%; min-height: 100%;
  width: auto; height: auto; transform: translate(-50%, -50%); object-fit: cover;
  z-index: 0;
}
.sqs-slice-gallery-item.gallery-video-background .custom-fallback-image { display: none !important; }
</style>
"""

OFFLINE_VIDEO_SNIPPET = """
<video class="offline-cover-video" autoplay muted loop playsinline
  src="{src}" poster="{poster}"></video>
"""


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
    snippet = OFFLINE_VIDEO_SNIPPET.format(src=video_rel, poster=poster_rel)
    for name in COVER_PAGES:
        html_path = snap / name
        if not html_path.is_file():
            continue
        html = html_path.read_text(encoding="utf-8", errors="replace")
        if "offline-cover-video" in html:
            patched.append(name)
            continue
        if OFFLINE_VIDEO_STYLE not in html:
            html = html.replace("</head>", OFFLINE_VIDEO_STYLE + "\n</head>", 1)
        if '<div id="player"></div>' in html:
            html = html.replace(
                '<div id="player"></div>',
                '<div id="player"></div>' + snippet,
                1,
            )
        elif "gallery-video-background" in html:
            html = re.sub(
                r'(<div class="sqs-slice-gallery-item gallery-video-background[^>]*>)',
                r"\1" + snippet,
                html,
                count=1,
            )
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
