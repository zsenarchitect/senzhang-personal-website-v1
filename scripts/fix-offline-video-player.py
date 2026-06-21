#!/usr/bin/env python3
"""Inject custom offline video player assets and strip native browser controls."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

PLAYER_CSS = "_cdn/offline-video-player/offline-video-player.css"
PLAYER_JS = "_cdn/offline-video-player/offline-video-player.js"

PLAYER_ASSETS = """
<link rel="stylesheet" href="{css}">
<script defer src="{js}"></script>
""".format(
    css=PLAYER_CSS,
    js=PLAYER_JS,
)

UPDATED_EMBED_STYLE = """
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

OLD_EMBED_STYLE_RE = re.compile(
    r'<style id="offline-embed-video-style">.*?</style>\s*',
    re.DOTALL | re.IGNORECASE,
)

OLD_PLAYER_ASSETS_RE = re.compile(
    r'<link rel="stylesheet" href="_cdn/offline-video-player/offline-video-player\.css">\s*'
    r'<script defer src="_cdn/offline-video-player/offline-video-player\.js"></script>\s*',
    re.IGNORECASE,
)

VIDEO_WITH_CONTROLS_RE = re.compile(
    r'<video class="offline-embed-video"\s+controls\s+playsinline\s+src="([^"]+)"></video>',
    re.IGNORECASE,
)

VIDEO_AUTOPLAY_RE = re.compile(
    r'<video class="offline-embed-video"\s+autoplay\s+muted\s+loop\s+playsinline\s+src="([^"]+)"></video>',
    re.IGNORECASE,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def ensure_player_assets(snap: Path) -> None:
    css_path = snap / PLAYER_CSS.replace("/", "\\").replace("\\", "/")
    js_path = snap / PLAYER_JS.replace("/", "\\").replace("\\", "/")
    repo_css = repo_root() / "snapshot" / "2026-06-05" / "_cdn" / "offline-video-player" / "offline-video-player.css"
    repo_js = repo_root() / "snapshot" / "2026-06-05" / "_cdn" / "offline-video-player" / "offline-video-player.js"
    # Copy canonical assets into target snapshot if missing (e.g. new date folder).
    css_path.parent.mkdir(parents=True, exist_ok=True)
    if not css_path.is_file() and repo_css.is_file():
        css_path.write_text(repo_css.read_text(encoding="utf-8"), encoding="utf-8")
    if not js_path.is_file() and repo_js.is_file():
        js_path.write_text(repo_js.read_text(encoding="utf-8"), encoding="utf-8")


def patch_html(html: str) -> tuple[str, bool]:
    if "offline-embed-video" not in html:
        return html, False

    changed = False
    new_html = html

    if OLD_EMBED_STYLE_RE.search(new_html):
        new_html = OLD_EMBED_STYLE_RE.sub(UPDATED_EMBED_STYLE, new_html, count=1)
        changed = True
    elif 'id="offline-embed-video-style"' not in new_html:
        new_html = new_html.replace("</head>", UPDATED_EMBED_STYLE + "\n</head>", 1)
        changed = True

    new_html2, n_controls = VIDEO_WITH_CONTROLS_RE.subn(
        r'<video class="offline-embed-video" playsinline preload="metadata" src="\1"></video>',
        new_html,
    )
    if n_controls:
        new_html = new_html2
        changed = True

    new_html2, n_auto = VIDEO_AUTOPLAY_RE.subn(
        r'<video class="offline-embed-video" autoplay muted loop playsinline preload="metadata" src="\1"></video>',
        new_html,
    )
    if n_auto:
        new_html = new_html2
        changed = True

    new_html = OLD_PLAYER_ASSETS_RE.sub("", new_html)
    if PLAYER_CSS not in new_html:
        new_html = new_html.replace("</head>", PLAYER_ASSETS + "\n</head>", 1)
        changed = True

    return new_html, changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply custom offline video player to snapshot HTML")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    args = parser.parse_args()

    snap = repo_root() / "snapshot" / args.date
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    ensure_player_assets(snap)
    patched: list[str] = []
    for html_path in sorted(snap.glob("*.html")):
        original = html_path.read_text(encoding="utf-8")
        updated, changed = patch_html(original)
        if changed:
            html_path.write_text(updated, encoding="utf-8")
            patched.append(html_path.name)

    print("Patched {} HTML files with offline video player.".format(len(patched)))
    for name in patched:
        print("  {}".format(name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
