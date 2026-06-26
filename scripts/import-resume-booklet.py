#!/usr/bin/env python3
"""Import approved rows from dev/resume-booklet-manifest.json into snapshot _media."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import project_page

V1 = Path(__file__).resolve().parents[1]
SNAP = V1 / "snapshot" / "2026-06-05"
MEDIA = SNAP / "_media"
MANIFEST = V1 / "dev" / "resume-booklet-manifest.json"
IMPORT_LOG = V1 / "dev" / "resume-booklet-import-log.json"
REGISTRY_PATH = V1 / "data" / "projects.json"


def find_booklet() -> Path:
    for p in V1.glob("*231014*"):
        if p.is_dir():
            return p
    raise SystemExit("Booklet folder not found")


def kebab(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem)
    return stem.strip("-") or "asset"


def next_gallery_num(slug_dir: Path) -> int:
    nums = []
    for f in slug_dir.glob("*"):
        m = project_page.GALLERY_NUM.match(f.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=1) + 1


def render_pdf_thumb(pdf_path: Path, out_jpg: Path) -> None:
    import fitz

    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=144)
    pix.save(str(out_jpg))
    doc.close()


def psd_to_jpg(psd_path: Path, out_jpg: Path) -> None:
    try:
        from psd_tools import PSDImage
    except ImportError:
        from PIL import Image

        im = Image.open(psd_path)
        im.convert("RGB").save(out_jpg, "JPEG", quality=88)
        return
    psd = PSDImage.open(psd_path)
    im = psd.composite()
    im.convert("RGB").save(out_jpg, "JPEG", quality=88)


def ai_to_jpg_pdf(ai_path: Path, out_jpg: Path, out_pdf: Path) -> bool:
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    # Try Inkscape for PDF + PNG then convert to JPG
    inkscape = shutil.which("inkscape")
    if inkscape:
        png_tmp = out_jpg.with_suffix(".png")
        subprocess.run(
            [inkscape, str(ai_path), "--export-type=png", "--export-filename", str(png_tmp)],
            check=False,
            capture_output=True,
        )
        subprocess.run(
            [inkscape, str(ai_path), "--export-type=pdf", "--export-filename", str(out_pdf)],
            check=False,
            capture_output=True,
        )
        if png_tmp.is_file():
            from PIL import Image

            Image.open(png_tmp).convert("RGB").save(out_jpg, "JPEG", quality=88)
            png_tmp.unlink(missing_ok=True)
            return out_jpg.is_file()
    return False


def download_youtube(video_id: str, dest: Path) -> None:
    if dest.is_file() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = "https://www.youtube.com/watch?v={0}".format(video_id)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "yt_dlp",
            "-f",
            "best[ext=mp4]/best",
            "--merge-output-format",
            "mp4",
            "-o",
            str(dest.with_suffix(".%(ext)s")),
            url,
        ],
        check=True,
    )


def copy_booklet_archive(booklet: Path) -> None:
    fonts_dst = MEDIA / "_booklet" / "fonts"
    source_dst = MEDIA / "_booklet" / "_source"
    fonts_dst.mkdir(parents=True, exist_ok=True)
    source_dst.mkdir(parents=True, exist_ok=True)
    df = booklet / "Document fonts"
    if df.is_dir():
        for f in df.iterdir():
            if f.is_file():
                shutil.copy2(f, fonts_dst / f.name)
    idml = booklet / "231014 Resume Booklet.idml"
    if idml.is_file():
        shutil.copy2(idml, source_dst / "231014-resume-booklet.idml")


def update_registry_media_slots(registry: dict, slug: str, slots: list[dict]) -> None:
    proj = registry.setdefault("projects", {}).setdefault(slug, {})
    proj["mediaSlots"] = slots


def main() -> int:
    if not MANIFEST.is_file():
        raise SystemExit("Run audit-resume-booklet.py first")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    booklet = find_booklet()
    links = booklet / "Links"
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    log_entries = []
    slots_by_slug: dict[str, list[dict]] = {}
    gallery_counters: dict[str, int] = {}

    for row in manifest.get("links", manifest.get("rows", [])):
        if row.get("status") not in ("approved", "proposed"):
            continue
        name = row.get("sourceName") or row.get("sourceFile")
        slug = row["targetSlug"]
        role = row["role"]
        label = row.get("label") or name
        dest_hint = row.get("destName", "")
        src = links / name
        if not src.is_file():
            log_entries.append({"source": name, "status": "missing_source"})
            continue

        if slug == "_booklet":
            dst = MEDIA / "_booklet" / "_source" / (kebab(name) + src.suffix.lower())
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            log_entries.append({"source": name, "dest": str(dst.relative_to(SNAP)), "status": "ok"})
            continue

        slug_dir = MEDIA / "projects" / slug
        slug_dir.mkdir(parents=True, exist_ok=True)
        source_dir = slug_dir / "_source"
        source_dir.mkdir(parents=True, exist_ok=True)

        entry = {"source": name, "slug": slug, "role": role}

        if role == "gallery":
            ext = src.suffix.lower()
            if ext in (".jpg", ".jpeg"):
                dest_name = "cover.jpg" if "c01" in name or "c02" in name else None
                if not dest_name:
                    n = gallery_counters.get(slug, next_gallery_num(slug_dir) - 1)
                    if slug not in gallery_counters:
                        gallery_counters[slug] = n
                    gallery_counters[slug] += 1
                    dest_name = "{0:02d}.jpg".format(gallery_counters[slug])
                dest = slug_dir / dest_name
                shutil.copy2(src, dest)
                entry["dest"] = str(dest.relative_to(MEDIA))
                slots_by_slug.setdefault(slug, []).append(
                    {"role": "gallery", "file": dest_name, "label": label, "sourceLink": name}
                )
            elif ext == ".png":
                n = gallery_counters.get(slug, next_gallery_num(slug_dir) - 1)
                if slug not in gallery_counters:
                    gallery_counters[slug] = n
                gallery_counters[slug] += 1
                dest_name = "{0:02d}.jpg".format(gallery_counters[slug])
                dest = slug_dir / dest_name
                from PIL import Image

                Image.open(src).convert("RGB").save(dest, "JPEG", quality=88)
                entry["dest"] = str(dest.relative_to(MEDIA))
                slots_by_slug.setdefault(slug, []).append(
                    {"role": "gallery", "file": dest_name, "label": label, "sourceLink": name}
                )
            entry["status"] = "ok"
        elif role in ("source_pdf", "source_pdf+gallery_thumb"):
            pdf_name = kebab(name) + (Path(name).suffix.lower() or ".pdf")
            if not pdf_name.endswith(".pdf"):
                pdf_name += ".pdf"
            pdf_dest = source_dir / pdf_name
            shutil.copy2(src, pdf_dest)
            n = gallery_counters.get(slug, next_gallery_num(slug_dir) - 1)
            if slug not in gallery_counters:
                gallery_counters[slug] = n
            gallery_counters[slug] += 1
            thumb_name = "{0:02d}.jpg".format(gallery_counters[slug])
            thumb_dest = slug_dir / thumb_name
            try:
                render_pdf_thumb(pdf_dest, thumb_dest)
                entry["galleryThumb"] = thumb_name
                slots_by_slug.setdefault(slug, []).append(
                    {
                        "role": "gallery",
                        "file": thumb_name,
                        "label": label,
                        "sourceLink": name,
                    }
                )
            except Exception as exc:
                entry["convertError"] = str(exc)
            slots_by_slug.setdefault(slug, []).append(
                {"role": "source_pdf", "file": "_source/" + pdf_name, "label": label}
            )
            entry["dest"] = str(pdf_dest.relative_to(MEDIA))
            entry["status"] = "ok"
        elif role == "source_psd":
            psd_dest = source_dir / name
            shutil.copy2(src, psd_dest)
            n = gallery_counters.get(slug, next_gallery_num(slug_dir) - 1)
            if slug not in gallery_counters:
                gallery_counters[slug] = n
            gallery_counters[slug] += 1
            jpg_name = "{0:02d}.jpg".format(gallery_counters[slug])
            jpg_dest = slug_dir / jpg_name
            try:
                psd_to_jpg(src, jpg_dest)
                slots_by_slug.setdefault(slug, []).append(
                    {"role": "gallery", "file": jpg_name, "label": label, "sourceLink": name}
                )
            except Exception as exc:
                entry["convertError"] = str(exc)
            slots_by_slug.setdefault(slug, []).append(
                {"role": "source_psd", "file": "_source/" + name, "label": label}
            )
            entry["dest"] = str(psd_dest.relative_to(MEDIA))
            entry["status"] = "ok"
        elif role == "source_ai":
            ai_dest = source_dir / name
            shutil.copy2(src, ai_dest)
            n = gallery_counters.get(slug, next_gallery_num(slug_dir) - 1)
            if slug not in gallery_counters:
                gallery_counters[slug] = n
            gallery_counters[slug] += 1
            jpg_name = "{0:02d}.jpg".format(gallery_counters[slug])
            pdf_name = kebab(name) + ".pdf"
            jpg_dest = slug_dir / jpg_name
            pdf_dest = source_dir / pdf_name
            if not ai_to_jpg_pdf(src, jpg_dest, pdf_dest):
                entry["convertError"] = "ai_export_failed"
            else:
                slots_by_slug.setdefault(slug, []).append(
                    {"role": "gallery", "file": jpg_name, "label": label, "sourceLink": name}
                )
            slots_by_slug.setdefault(slug, []).append(
                {"role": "source_ai", "file": "_source/" + name, "label": label}
            )
            if pdf_dest.is_file():
                slots_by_slug.setdefault(slug, []).append(
                    {"role": "source_pdf", "file": "_source/" + pdf_name, "label": label + " PDF"}
                )
            entry["dest"] = str(ai_dest.relative_to(MEDIA))
            entry["status"] = "ok" if not entry.get("convertError") else "convert_failed"

        log_entries.append(entry)

    copy_booklet_archive(booklet)

    # Revit games demo videos from QR
    demo_videos = []
    for q in manifest.get("qrDecodes", manifest.get("qrUrls", [])):
        urls = q.get("urls") or ([q.get("url")] if q.get("url") else [])
        src_name = (q.get("sourceName") or q.get("sourceFile") or "").lower()
        game = "monopoly" if "monopoly" in src_name else "battleship"
        for url in urls:
            vid = q.get("youtubeId") or ""
            if not vid:
                m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
                vid = m.group(1) if m else ""
            if not vid:
                continue
            label = "Monopoly demo" if game == "monopoly" else "Battleship Hex demo"
            local = "projects/revit-games/{0}.mp4".format(vid)
            dest = MEDIA / local
            try:
                download_youtube(vid, dest)
            except Exception as exc:
                log_entries.append(
                    {"source": "youtube:" + vid, "status": "download_failed", "error": str(exc)}
                )
            demo_videos.append(
                {
                    "label": label,
                    "youtubeId": vid,
                    "source": url,
                    "local": local,
                }
            )
    if demo_videos:
        registry["projects"]["revit-games"]["demoVideos"] = demo_videos

    for slug, slots in slots_by_slug.items():
        update_registry_media_slots(registry, slug, slots)

    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    log = {
        "importedAt": datetime.now(timezone.utc).isoformat(),
        "entries": log_entries,
        "slotsBySlug": slots_by_slug,
        "bookletFonts": str((MEDIA / "_booklet" / "fonts").relative_to(SNAP)),
    }
    IMPORT_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")

    touched = sorted(set(slots_by_slug) | {"revit-games"})
    for slug in touched:
        if slug in registry.get("projects", {}):
            project_page.sync_project_gallery(slug, registry)

    print("Imported {0} entries; synced: {1}".format(len(log_entries), ", ".join(touched)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
