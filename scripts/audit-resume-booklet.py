#!/usr/bin/env python3
"""Audit 231014 Resume Booklet Links/ assets and propose import manifest."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

V1 = Path(__file__).resolve().parents[1]
SNAP = V1 / "snapshot" / "2026-06-05"
PROJECTS_MEDIA = SNAP / "_media" / "projects"
MANIFEST_PATH = V1 / "dev" / "resume-booklet-manifest.json"

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
CONTENT_RE = re.compile(r"<Content>([^<]*)</Content>")
QR_CANDIDATES = (
    "monopoly game play.png",
    "Battleship hex game play3.png",
    "Battleship hex UI.png",
    "battleship layout UI.png",
)


def find_booklet_folder() -> Path:
    matches = sorted(V1.glob("*231014*"))
    dirs = [p for p in matches if p.is_dir()]
    if not dirs:
        raise FileNotFoundError("No booklet folder matching *231014* in repo root")
    if len(dirs) > 1:
        raise RuntimeError("Multiple booklet folders: {0}".format([p.name for p in dirs]))
    return dirs[0]


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_dimensions(path: Path) -> dict | None:
    if path.suffix.lower() not in IMAGE_EXT:
        return None
    try:
        from PIL import Image

        with Image.open(path) as img:
            w, h = img.size
        return {"width": w, "height": h}
    except Exception:
        return None


def slugify_stem(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem)
    return stem.strip("-") or "asset"


def next_gallery_name(slug: str, ext: str) -> str:
    folder = PROJECTS_MEDIA / slug
    nums = []
    if folder.is_dir():
        for f in folder.iterdir():
            if not f.is_file():
                continue
            m = re.match(r"^(\d+)\.", f.name, re.I)
            if m:
                nums.append(int(m.group(1)))
    n = (max(nums) + 1) if nums else 2
    return "{0:02d}{1}".format(n, ext.lower())


def build_md5_index() -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    if not PROJECTS_MEDIA.is_dir():
        return index
    for slug_dir in PROJECTS_MEDIA.iterdir():
        if not slug_dir.is_dir():
            continue
        slug = slug_dir.name
        for f in slug_dir.rglob("*"):
            if not f.is_file():
                continue
            try:
                digest = md5_file(f)
            except OSError:
                continue
            rel = f.relative_to(PROJECTS_MEDIA).as_posix()
            index.setdefault(digest, []).append({"slug": slug, "path": rel})
    return index


def parse_idml_content(idml_path: Path) -> list[str]:
    blocks: list[str] = []
    with zipfile.ZipFile(idml_path) as zf:
        for name in zf.namelist():
            if not (name.startswith("Stories/") and name.endswith(".xml")):
                continue
            text = zf.read(name).decode("utf-8", errors="replace")
            for m in CONTENT_RE.finditer(text):
                value = m.group(1).strip()
                if value:
                    blocks.append(value)
    return blocks


def try_qr_decode(path: Path) -> list[str]:
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode as zbar_decode
    except ImportError:
        return []

    urls: list[str] = []
    try:
        with Image.open(path) as img:
            for item in zbar_decode(img):
                data = item.data.decode("utf-8", errors="replace").strip()
                if data and data not in urls:
                    urls.append(data)
    except Exception:
        return []
    return urls


def propose_mapping(filename: str) -> tuple[str, str, str, str | None]:
    """Return targetSlug, role, destName, reviewNote."""
    lower = filename.lower()

    if filename == "c01.jpg":
        return "bilibili-hq", "cover", "cover.jpg", None
    if filename == "c02.jpg":
        return "bytedance-hq", "gallery", next_gallery_name("bytedance-hq", ".jpg"), None
    if filename == "C07 EA.jpg":
        return "enneadtab-ecosystem", "gallery", next_gallery_name("enneadtab-ecosystem", ".jpg"), None
    if filename == "3.jpg":
        return "taopu-603-smartcity", "gallery", next_gallery_name("taopu-603-smartcity", ".jpg"), "default pending review"
    if fnmatch.fnmatch(filename, "Generative Study*.png") or filename == "programmable family.png":
        return "bilibili-hq", "gallery", next_gallery_name("bilibili-hq", Path(filename).suffix), None
    if filename == "bytedance layout script_flip.png":
        return "bytedance-hq", "gallery", next_gallery_name("bytedance-hq", ".png"), None

    if (
        fnmatch.fnmatch(filename, "A-000A*")
        or fnmatch.fnmatch(filename, "A-002*")
        or fnmatch.fnmatch(filename, "A - 002*")
        or filename.startswith("[1]_006")
        or filename.startswith("[1]_056")
    ):
        ext = Path(filename).suffix.lower() or ".pdf"
        return "ftz-shanghai", "source_pdf+gallery_thumb", "source/{0}".format(slugify_stem(filename) + ext), None

    if fnmatch.fnmatch(lower, "a-301*.pdf") or fnmatch.fnmatch(lower, "a-348*.pdf"):
        ext = Path(filename).suffix.lower() or ".pdf"
        return "bilibili-hq", "source_pdf", "source/{0}".format(slugify_stem(filename) + ext), None

    if filename == "panel type 4 elev._quick diagram.ai":
        return "ftz-shanghai", "source_ai", "source/panel-type-4-elev-quick-diagram.ai", None
    if filename == "sample curtain panel.psd":
        return "bilibili-hq", "source_psd", "source/sample-curtain-panel.psd", None

    monopoly_battleship = (
        "monopoly game play.png",
        "Battleship hex game play3.png",
        "Battleship hex UI.png",
        "battleship layout UI.png",
    )
    if filename in monopoly_battleship or fnmatch.fnmatch(lower, "battleship*.png"):
        ext = Path(filename).suffix.lower()
        return "revit-games", "gallery", next_gallery_name("revit-games", ext), None

    if filename == "231014 resume.indd":
        return "_booklet", "source_indd", "231014-resume.indd", None

    raise ValueError("Unmapped Links file: {0}".format(filename))


def main() -> int:
    booklet = find_booklet_folder()
    links_dir = booklet / "Links"
    if not links_dir.is_dir():
        raise FileNotFoundError("Links folder missing under {0}".format(booklet))

    idml_path = booklet / "231014 Resume Booklet.idml"
    idml_blocks: list[str] = []
    if idml_path.is_file():
        idml_blocks = parse_idml_content(idml_path)

    link_files = sorted(f for f in links_dir.iterdir() if f.is_file())
    md5_index = build_md5_index()

    rows = []
    qr_decodes = []
    mapped = 0

    for path in link_files:
        digest = md5_file(path)
        dims = image_dimensions(path)
        target_slug, role, dest_name, review_note = propose_mapping(path.name)
        mapped += 1

        dupes = md5_index.get(digest, [])
        dupe_match = dupes[0] if dupes else None

        row = {
            "sourceName": path.name,
            "md5": digest,
            "size": path.stat().st_size,
            "dimensions": dims,
            "targetSlug": target_slug,
            "role": role,
            "destName": dest_name,
            "status": "proposed",
        }
        if review_note:
            row["reviewNote"] = review_note
        if dupe_match:
            row["existingDuplicate"] = dupe_match
        rows.append(row)

        if path.name in QR_CANDIDATES or fnmatch.fnmatch(path.name.lower(), "battleship*.png"):
            urls = try_qr_decode(path)
            if urls:
                qr_decodes.append({"sourceName": path.name, "urls": urls})

    manifest = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bookletFolder": booklet.relative_to(V1).as_posix(),
        "idmlPath": idml_path.relative_to(V1).as_posix() if idml_path.is_file() else None,
        "linksCoverage": {"total": len(link_files), "mapped": mapped},
        "idmlContentBlockCount": len(idml_blocks),
        "idmlContentBlocks": idml_blocks,
        "qrDecodes": qr_decodes,
        "links": rows,
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("Booklet folder found ({0} links)".format(len(link_files)))
    print("Mapped: {0}/{1}".format(mapped, len(link_files)))
    print("IDML content blocks: {0}".format(len(idml_blocks)))
    print("Manifest: {0}".format(MANIFEST_PATH))
    if qr_decodes:
        print("QR decodes:")
        for item in qr_decodes:
            print("  {0}: {1}".format(item["sourceName"], item["urls"]))
    else:
        print("QR decodes: none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
