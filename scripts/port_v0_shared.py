#!/usr/bin/env python3
"""Shared v0 MDX parsing and slug -> file mapping."""
from __future__ import annotations

import shutil
from pathlib import Path

V0 = Path(r"C:\Users\szhang\github\Personal\senzhang-personal-website-v0-failed-attempt")
V1 = Path(__file__).resolve().parents[1]
SNAP = V1 / "snapshot" / "2026-06-05"
MEDIA = SNAP / "_media"

# v1 snapshot slug -> v0 architecture MDX basename
MDX_SLUG_MAP = {
    "app-ghost-hunter-1": "beijing-untouched",
    "black-hole-horizon-1": "ticket-booth-for-nose",
    "takenaka-pavillion": "takenaka-pavilion",
}

CONTENT_DIR = {
    "academic": "architecture",
    "professional": "architecture",
    "code": "code",
    "speaking": "speaking",
}

META_FIELDS = (
    "subtitle",
    "cover",
    "date",
    "role",
    "location",
    "event",
    "stack",
    "embed",
    "abstract",
    "studio",
    "partner",
    "repo",
    "liveUrl",
)


def parse_mdx(path: Path) -> tuple[dict, str]:
    t = path.read_text(encoding="utf-8")
    e = t.index("---", 3)
    fr, body = t[3:e].strip(), t[e + 3 :].strip()
    meta, lk = {}, None
    for line in fr.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and lk:
            meta.setdefault(lk, []).append(line.strip()[2:].strip())
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if v == "":
                lk, meta[k] = k, []
            else:
                lk, meta[k] = None, v
    return meta, body


def mdx_basename(slug: str) -> str:
    return MDX_SLUG_MAP.get(slug, slug)


def mdx_path_for(slug: str, category: str) -> Path | None:
    folder = CONTENT_DIR.get(category)
    if not folder:
        return None
    path = V0 / "src" / "content" / folder / (mdx_basename(slug) + ".mdx")
    return path if path.is_file() else None


def media(url: str) -> str:
    return "_media/" + url.lstrip("/")


def copy_asset(url: str | None) -> str | None:
    if not url:
        return None
    src = V0 / "public" / url.lstrip("/")
    if not src.is_file():
        print("WARN missing", src)
        return None
    dst = MEDIA / url.lstrip("/")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return media(url)
