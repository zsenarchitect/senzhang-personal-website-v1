#!/usr/bin/env python3
"""Download embedded YouTube videos and patch project pages for offline playback."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Cover pages use fix-cover-video.py (background loop).
SKIP_COVER_PAGES = frozenset({"index.html", "cover-page.html"})
MENU_PAGES = frozenset({"menu.html"})

YOUTUBE_ID_RE = re.compile(
    r"(?:youtube\.com/embed/|youtu\.be/)([A-Za-z0-9_-]{11})",
    re.IGNORECASE,
)
START_RE = re.compile(r"[?&]start=(\d+)", re.IGNORECASE)

EMBED_BLOCK_RE = re.compile(
    r'<div\s+class="sqs-video-wrapper"[^>]*data-html="((?:[^"]|\n)*youtube(?:[^"]|\n)*)"[^>]*>\s*</div>',
    re.IGNORECASE,
)

OFFLINE_EMBED_STYLE = """
<style id="offline-embed-video-style">
.embed-block-wrapper:has([data-offline-static]) { position: relative; min-height: 200px; height: auto !important; }
.embed-block-wrapper .sqs-video-wrapper[data-offline-static] { display: none !important; }
.embed-block-wrapper .offline-embed-video-shell {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
}
.embed-block-wrapper .offline-embed-video-shell .ovp-player {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
}
.embed-block-wrapper .offline-embed-video-shell video.offline-embed-video {
  object-fit: contain; background: #000;
}
.embed-block-wrapper.ovp-aspect-fit {
  padding-bottom: 0 !important;
  min-height: 0 !important;
  height: auto !important;
  aspect-ratio: var(--ovp-aspect-ratio, auto);
}
.embed-block-wrapper.ovp-aspect-fit .offline-embed-video-shell {
  position: relative; top: auto; left: auto; width: 100%; height: auto;
  aspect-ratio: inherit;
}
.embed-block-wrapper.ovp-aspect-fit .offline-embed-video-shell .ovp-player {
  position: relative; top: auto; left: auto; width: 100%; height: auto;
  aspect-ratio: inherit; background: transparent;
}
.embed-block-wrapper.ovp-aspect-fit .offline-embed-video-shell video.offline-embed-video {
  object-fit: cover; background: transparent;
}
</style>
"""

MENU_AUTOPLAY_SCRIPT = """
<script id="offline-menu-video-autoplay">
document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('.offline-embed-video-shell video.offline-embed-video').forEach(function(v){
    v.muted=true;
    v.loop=true;
    v.setAttribute('playsinline','');
    v.setAttribute('webkit-playsinline','');
    var p=v.play();
    if(p&&p.catch){p.catch(function(){});}
  });
});
</script>
"""

OFFLINE_EMBED_VIDEO_CONTROLS_RE = re.compile(
    r'<video class="offline-embed-video" controls playsinline src="([^"]+)"></video>',
    re.IGNORECASE,
)

OFFLINE_EMBED_VIDEO_PLAIN_RE = re.compile(
    r'<video class="offline-embed-video" playsinline preload="metadata" src="([^"]+)"></video>',
    re.IGNORECASE,
)

MENU_MOBILE_LAYOUT_STYLE = """
<style id="offline-menu-mobile-layout">
@media (max-width: 800px) {
  #page-593e0796c534a5c8d10121cb .sqs-layout [class*="sqs-col"] {
    width: 100% !important;
    float: none !important;
  }
}
@media (max-width: 767px) {
  #page-593e0796c534a5c8d10121cb .sqs-image-shape-container-element.has-aspect-ratio {
    padding-bottom: 0 !important;
    height: auto !important;
    overflow: visible !important;
  }
  #page-593e0796c534a5c8d10121cb .sqs-image-shape-container-element img {
    position: static !important;
    width: 100% !important;
    height: auto !important;
    object-fit: contain !important;
  }
}
</style>
"""

OLD_MENU_MOBILE_STYLE_RE = re.compile(
    r'<style id="offline-menu-mobile-contain">.*?</style>\s*',
    re.DOTALL | re.IGNORECASE,
)

MENU_MOBILE_LAYOUT_STYLE_RE = re.compile(
    r'<style id="offline-menu-mobile-layout">.*?</style>\s*',
    re.DOTALL | re.IGNORECASE,
)

OFFLINE_EMBED_STYLE_RE = re.compile(
    r'<style id="offline-embed-video-style">.*?</style>\s*',
    re.DOTALL | re.IGNORECASE,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_youtube_from_data_html(attrs: str) -> tuple[str, int | None]:
    m = YOUTUBE_ID_RE.search(attrs)
    if not m:
        return "", None
    vid = m.group(1)
    sm = START_RE.search(attrs)
    start = int(sm.group(1)) if sm else None
    return vid, start


def download_video(media_dir: Path, video_id: str) -> Path:
    media_dir.mkdir(parents=True, exist_ok=True)
    out_path = media_dir / (video_id + ".mp4")
    cover = media_dir / "cover-background.mp4"
    if video_id == "mYPQl6m7kMY" and cover.is_file():
        if not out_path.is_file():
            import shutil
            shutil.copy2(cover, out_path)
        return out_path
    if out_path.is_file() and out_path.stat().st_size > 0:
        return out_path
    url = "https://www.youtube.com/watch?v={}".format(video_id)
    out_tmpl = str(media_dir / (video_id + ".%(ext)s"))
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
        url,
    ]
    print("Downloading {} -> {}".format(video_id, out_path.name))
    subprocess.run(cmd, check=True)
    if not out_path.is_file():
        candidates = sorted(media_dir.glob(video_id + ".*"))
        if not candidates:
            raise RuntimeError("yt-dlp finished but no output for {}".format(video_id))
        cand = candidates[0]
        if cand.suffix != ".mp4":
            cand.rename(out_path)
    return out_path


def video_src_rel(video_id: str, start: int | None) -> str:
    base = "_media/{}.mp4".format(video_id)
    if start is not None and start > 0:
        return base + "#t={}".format(start)
    return base


def build_offline_video_tag(src: str, menu_autoplay: bool) -> str:
    if menu_autoplay:
        return (
            '<video class="offline-embed-video" autoplay muted loop playsinline preload="metadata" '
            'src="{src}"></video>'
        ).format(src=src)
    return (
        '<video class="offline-embed-video" playsinline preload="metadata" '
        'src="{src}"></video>'
    ).format(src=src)


def replace_embed_block(
    match: re.Match[str], media_rel: dict[str, str], menu_autoplay: bool = False
) -> str:
    data_html = match.group(1)
    vid, start = parse_youtube_from_data_html(data_html)
    if not vid:
        return match.group(0)
    src = video_src_rel(vid, start)
    media_rel[vid] = "_media/{}.mp4".format(vid)
    tag = build_offline_video_tag(src, menu_autoplay)
    return (
        '<div class="sqs-video-wrapper" data-offline-static="1" '
        'data-offline-video="{src}"></div>'
        '<div class="offline-embed-video-shell">'
        "{tag}</div>"
    ).format(src=src, tag=tag)


def patch_menu_autoplay(html_path: Path) -> bool:
    """Menu grid videos: muted autoplay loops that fill their aspect-ratio cells."""
    if html_path.name not in MENU_PAGES:
        return False
    html = html_path.read_text(encoding="utf-8", errors="replace")
    if "offline-embed-video-shell" not in html:
        return False

    new_html = html
    new_html, n = OFFLINE_EMBED_VIDEO_CONTROLS_RE.subn(
        r'<video class="offline-embed-video" autoplay muted loop playsinline src="\1"></video>',
        new_html,
    )

    if OFFLINE_EMBED_STYLE_RE.search(new_html):
        new_html = OFFLINE_EMBED_STYLE_RE.sub(OFFLINE_EMBED_STYLE, new_html, count=1)

    new_html = OLD_MENU_MOBILE_STYLE_RE.sub("", new_html)
    if MENU_MOBILE_LAYOUT_STYLE_RE.search(new_html):
        new_html = MENU_MOBILE_LAYOUT_STYLE_RE.sub(MENU_MOBILE_LAYOUT_STYLE, new_html, count=1)
    elif 'id="offline-menu-mobile-layout"' not in new_html:
        new_html = new_html.replace("</head>", MENU_MOBILE_LAYOUT_STYLE + "\n</head>", 1)

    if 'id="offline-menu-video-autoplay"' not in new_html:
        new_html = new_html.replace("</body>", MENU_AUTOPLAY_SCRIPT + "\n</body>", 1)

    if new_html == html:
        return False
    html_path.write_text(new_html, encoding="utf-8")
    print("  menu autoplay/layout {}".format(html_path.name))
    return True


def patch_html_file(html_path: Path, media_rel: dict[str, str]) -> bool:
    html = html_path.read_text(encoding="utf-8", errors="replace")
    if "offline-embed-video-shell" in html and "youtube.com/embed" not in html:
        return False
    if "youtube.com/embed" not in html and "youtu.be" not in html:
        return False

    menu_autoplay = html_path.name in MENU_PAGES
    new_html = EMBED_BLOCK_RE.sub(
        lambda m: replace_embed_block(m, media_rel, menu_autoplay), html
    )
    if new_html == html:
        return False

    if OFFLINE_EMBED_STYLE.strip() not in new_html:
        new_html = new_html.replace("</head>", OFFLINE_EMBED_STYLE + "\n</head>", 1)

    html_path.write_text(new_html, encoding="utf-8")
    print("  patched {}".format(html_path.name))
    return True


def collect_video_ids(snap: Path) -> set[str]:
    ids: set[str] = set()
    for html_path in sorted(snap.glob("*.html")):
        if html_path.name in SKIP_COVER_PAGES:
            continue
        text = html_path.read_text(encoding="utf-8", errors="replace")
        for m in YOUTUBE_ID_RE.finditer(text):
            ids.add(m.group(1))
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline YouTube embeds in snapshot HTML")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    snap = repo_root() / "snapshot" / args.date
    media_dir = snap / "_media"
    manifest_path = snap / "manifest.json"
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    video_ids = collect_video_ids(snap)
    print("Project embed video IDs: {}".format(", ".join(sorted(video_ids)) or "(none)"))

    if not args.skip_download:
        for vid in sorted(video_ids):
            download_video(media_dir, vid)

    media_rel: dict[str, str] = {}
    patched_files: list[str] = []
    for html_path in sorted(snap.glob("*.html")):
        if html_path.name in SKIP_COVER_PAGES:
            continue
        if patch_html_file(html_path, media_rel):
            patched_files.append(html_path.name)

    for html_path in sorted(snap.glob("*.html")):
        if patch_menu_autoplay(html_path):
            if html_path.name not in patched_files:
                patched_files.append(html_path.name + " (autoplay)")

    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        offline = manifest.get("offline_videos", {})
        offline.update(
            {
                vid: {
                    "local": path,
                    "source": "https://www.youtube.com/watch?v={}".format(vid),
                    "patched_at": datetime.now(timezone.utc).isoformat(),
                }
                for vid, path in media_rel.items()
            }
        )
        manifest["offline_videos"] = offline
        manifest["offline_embed_videos_fixed_at"] = datetime.now(timezone.utc).isoformat()
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\nDone. Patched: {}.".format(", ".join(patched_files) or "(none)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
