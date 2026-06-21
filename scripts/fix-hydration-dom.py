#!/usr/bin/env python3
"""Move offline video nodes out of Squarespace React-managed wrappers (hydration fix)."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from cover_video_effects import apply_cover_effects, build_cover_style

COVER_PAGES = ("index.html", "cover-page.html")

NEW_COVER_STYLE = build_cover_style(2, 13)

NEW_EMBED_STYLE = """<style id="offline-embed-video-style">
.embed-block-wrapper:has([data-offline-static]) { position: relative; min-height: 200px; height: auto !important; }
.embed-block-wrapper .sqs-video-wrapper[data-offline-static] { display: none !important; }
.embed-block-wrapper .offline-embed-video-shell {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
}
.embed-block-wrapper .offline-embed-video-shell video.offline-embed-video {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; background: #000;
}
</style>"""

COVER_VIDEO_IN_GALLERY_RE = re.compile(
    r'<div id="player"></div>\s*'
    r'<video class="offline-cover-video" autoplay muted loop playsinline\s+'
    r'src="([^"]+)" poster="([^"]+)"></video>',
    re.IGNORECASE,
)

COVER_SHELL_RE = re.compile(
    r'(<div class="sqs-slide-layer layer-back[^"]*">)\s*'
    r'(<div class="sqs-slide-layer-content">)',
    re.IGNORECASE,
)

EMBED_IN_WRAPPER_RE = re.compile(
    r'<div class="sqs-video-wrapper offline-youtube-replaced" data-offline-video="([^"]+)">'
    r'<video class="offline-embed-video" controls playsinline src="([^"]+)"></video></div>',
    re.IGNORECASE,
)

OLD_COVER_STYLE_RE = re.compile(
    r'<style id="offline-cover-video-style">.*?</style>',
    re.DOTALL | re.IGNORECASE,
)

OLD_EMBED_STYLE_RE = re.compile(
    r'<style id="offline-embed-video-style">.*?</style>',
    re.DOTALL | re.IGNORECASE,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def replace_style(html: str, old_re: re.Pattern[str], new_style: str, style_id: str) -> str:
    if old_re.search(html):
        return old_re.sub(new_style, html, count=1)
    if style_id not in html:
        return html.replace("</head>", new_style + "\n</head>", 1)
    return html


def patch_cover_page(html: str) -> tuple[str, bool]:
    changed = False
    shell_src = None
    shell_poster = None

    def lift_video(m: re.Match[str]) -> str:
        nonlocal changed, shell_src, shell_poster
        changed = True
        shell_src = m.group(1)
        shell_poster = m.group(2)
        return '<div id="player"></div>'

    html2 = COVER_VIDEO_IN_GALLERY_RE.sub(lift_video, html)
    if not changed and "offline-cover-video-shell" in html:
        html2, _ = apply_cover_effects(html)
        return html2, html2 != html
    if not changed:
        return html, False

    shell = (
        '<div class="offline-cover-video-shell">'
        '<video class="offline-cover-video" autoplay muted loop playsinline '
        'src="{src}" poster="{poster}"></video></div>\n  '
    ).format(src=shell_src, poster=shell_poster)

    if "offline-cover-video-shell" not in html2:
        html2, n = COVER_SHELL_RE.subn(r"\1\n  " + shell + r"\2", html2, count=1)
        if n == 0:
            return html, False

    html2 = replace_style(html2, OLD_COVER_STYLE_RE, NEW_COVER_STYLE, "offline-cover-video-style")
    html2, _ = apply_cover_effects(html2)
    return html2, True


def patch_embeds(html: str) -> tuple[str, bool]:
    if "offline-youtube-replaced" not in html and "offline-embed-video-shell" not in html:
        return html, False

    def repl(m: re.Match[str]) -> str:
        src = m.group(1)
        return (
            '<div class="sqs-video-wrapper" data-offline-static="1" '
            'data-offline-video="{src}"></div>'
            '<div class="offline-embed-video-shell">'
            '<video class="offline-embed-video" controls playsinline src="{src}"></video>'
            "</div>"
        ).format(src=src)

    html2, n = EMBED_IN_WRAPPER_RE.subn(repl, html)
    if n == 0 and "offline-embed-video-shell" in html:
        html2 = replace_style(html2, OLD_EMBED_STYLE_RE, NEW_EMBED_STYLE, "offline-embed-video-style")
        return html2, False

    if n == 0:
        return html, False

    html2 = replace_style(html2, OLD_EMBED_STYLE_RE, NEW_EMBED_STYLE, "offline-embed-video-style")
    return html2, True


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix Squarespace hydration DOM for offline videos")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    args = parser.parse_args()

    snap = repo_root() / "snapshot" / args.date
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    patched: list[str] = []
    for html_path in sorted(snap.glob("*.html")):
        html = html_path.read_text(encoding="utf-8", errors="replace")
        orig = html
        if html_path.name in COVER_PAGES:
            html, _ = patch_cover_page(html)
        html, _ = patch_embeds(html)
        if html != orig:
            html_path.write_text(html, encoding="utf-8")
            patched.append(html_path.name)
            print("  patched {}".format(html_path.name))

    print("\nDone. Patched: {}.".format(", ".join(patched) or "(none)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
