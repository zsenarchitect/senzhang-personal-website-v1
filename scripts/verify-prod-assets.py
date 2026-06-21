#!/usr/bin/env python3
"""Smoke-test deployed Vercel assets are real files, not Git LFS pointer stubs."""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request

LFS_PREFIX = b"version https://git-lfs.github.com/spec/v1"

PROBES = (
    ("template-css", "/_cdn/static1.squarespace.com/3f6928579d7ce4659e88.css", 50_000),
    ("header-logo-gif", "/_cdn/images.squarespace-cdn.com/aed6f33c10cccaffe417.gif", 1_000),
    ("squarespace-js", "/_cdn/assets.squarespace.com/fbe4baf7c30df45ea3ff.js", 10_000),
)


def check_url(base: str, path: str, min_bytes: int) -> tuple[bool, str]:
    url = base.rstrip("/") + path
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
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
    return True, "{} OK ({} bytes)".format(url, size)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify deployed archive CDN assets")
    parser.add_argument(
        "--base",
        default="https://legacy-personal-website.vercel.app",
        help="Production base URL",
    )
    args = parser.parse_args()

    failed = 0
    for label, path, min_bytes in PROBES:
        ok, message = check_url(args.base, path, min_bytes)
        print("[{}] {}".format(label, message))
        if not ok:
            failed += 1

    if failed:
        print(
            "\nFAIL: {} probe(s) bad. Redeploy from a machine with `git lfs pull`, "
            "and enable Git LFS in Vercel project Settings -> Git.".format(failed),
            file=sys.stderr,
        )
        return 1

    print("\nAll production CDN probes passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
