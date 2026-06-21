#!/usr/bin/env python3
"""Smoke-test deployed Vercel assets are real files, not Git LFS pointer stubs."""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request

LFS_PREFIX = b"version https://git-lfs.github.com/spec/v1"
MP4_FTYP = b"ftyp"

# CDN + offline video player (deploy-time patches inject the player bundle).
CDN_PROBES = (
    ("template-css", "/_cdn/static1.squarespace.com/3f6928579d7ce4659e88.css", 50_000),
    ("header-logo-gif", "/_cdn/images.squarespace-cdn.com/aed6f33c10cccaffe417.gif", 1_000),
    ("squarespace-js", "/_cdn/assets.squarespace.com/fbe4baf7c30df45ea3ff.js", 10_000),
    ("offline-video-player-js", "/_cdn/offline-video-player/offline-video-player.js", 1_000),
)

# Offline YouTube -> _media/*.mp4 (see docs/completeness-2026-06-19.md).
MEDIA_PROBES = (
    ("museum-video", "/_media/4sQc0d3HRck.mp4", 1_000_000),
    ("works-hero-video", "/_media/fAl5EJuQpUM.mp4", 100_000),
)

PAGE_PROBES = (
    ("home", "/"),
    ("museum-of-verbs", "/museum-of-verbs"),
    ("tokyo-antilibrary", "/tokyo-antilibrary"),
    ("about-me", "/about-me"),
)


def check_binary(base: str, path: str, min_bytes: int) -> tuple[bool, str]:
    url = base.rstrip("/") + path
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read(256)
            size_hdr = resp.headers.get("Content-Length")
            size = int(size_hdr) if size_hdr else len(body)
    except urllib.error.HTTPError as exc:
        return False, "{} -> HTTP {}".format(url, exc.code)
    except Exception as exc:
        return False, "{} -> {}".format(url, exc)

    if body.startswith(LFS_PREFIX):
        return False, "{} looks like Git LFS pointer ({} bytes)".format(url, size)
    if size < min_bytes:
        return False, "{} too small ({} bytes, need >= {})".format(url, size, min_bytes)
    if path.endswith(".mp4") and MP4_FTYP not in body[:32]:
        return False, "{} missing MP4 ftyp magic ({} bytes)".format(url, size)
    return True, "{} OK ({} bytes)".format(url, size)


def check_page(base: str, path: str) -> tuple[bool, str]:
    url = base.rstrip("/") + path
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            body = resp.read(8192).decode("utf-8", errors="replace")
            size_hdr = resp.headers.get("Content-Length")
            size = int(size_hdr) if size_hdr else len(body)
    except urllib.error.HTTPError as exc:
        return False, "{} -> HTTP {}".format(url, exc.code)
    except Exception as exc:
        return False, "{} -> {}".format(url, exc)

    if size < 5_000:
        return False, "{} HTML too small ({} bytes)".format(url, size)
    if "<html" not in body.lower():
        return False, "{} missing <html> root".format(url)
    return True, "{} OK ({} bytes)".format(url, size)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify deployed archive CDN/media/page assets")
    parser.add_argument(
        "--base",
        default="https://legacy-personal-website.vercel.app",
        help="Production base URL",
    )
    args = parser.parse_args()

    failed = 0
    for label, path, min_bytes in CDN_PROBES + MEDIA_PROBES:
        ok, message = check_binary(args.base, path, min_bytes)
        print("[{}] {}".format(label, message))
        if not ok:
            failed += 1

    for label, path in PAGE_PROBES:
        ok, message = check_page(args.base, path)
        print("[page:{}] {}".format(label, message))
        if not ok:
            failed += 1

    if failed:
        print(
            "\nFAIL: {} probe(s) bad. Redeploy from a smudged tree:\n"
            "  git lfs pull\n"
            "  .\\scripts\\verify-cdn-assets.ps1\n"
            "  .\\scripts\\deploy-vercel.ps1 -Prod\n"
            "Never rely on git-push deploy for this LFS archive.",
            file=sys.stderr,
        )
        return 1

    print("\nAll production probes passed (CDN, _media mp4, key pages).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
