#!/usr/bin/env python3
"""Download Google Drive '19 job hunt' tree into dev/job-hunt-staging for review.

Raster images (png/webp/tiff/gif/bmp) are converted to JPG after download.
PDF, INDD, AI, and other binaries are kept as-is.

Usage:
  py -3 scripts/download-job-hunt-drive.py
  py -3 scripts/download-job-hunt-drive.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def log(msg: str) -> None:
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()

V1 = Path(__file__).resolve().parents[1]
GWS = r"C:\nodejs\gws.cmd"
# LionDrive transfer copy (modified 2026-06-26)
ROOT_FOLDER_ID = "0B7mQCLs8jw8tfm4tT0NEc2pkSXRnWnA0ZE1YYWhYb29VR3pmcW5zemZhN1NUN09jMTRneEE"
STAGING = V1 / "dev" / "job-hunt-staging"
MANIFEST = STAGING / "manifest.json"

SKIP_MIMES = {
    "application/vnd.google-apps.folder",
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
    "application/vnd.google-apps.form",
    "application/vnd.google-apps.map",
    "application/vnd.google-apps.shortcut",
}

RASTER_EXT = {".png", ".webp", ".tif", ".tiff", ".gif", ".bmp"}


def gws_json(args: list[str]) -> dict:
    r = subprocess.run(args, capture_output=True)
    out = r.stdout.decode("utf-8", errors="replace")
    if not out.strip():
        err = r.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(err or "empty gws response")
    idx = out.find("{")
    if idx < 0:
        raise RuntimeError(out[:500])
    return json.loads(out[idx:])


def list_children(folder_id: str) -> list[dict]:
    files = []
    page_token = None
    while True:
        params = {
            "q": "'{0}' in parents and trashed = false".format(folder_id),
            "pageSize": 200,
            "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime)",
        }
        if page_token:
            params["pageToken"] = page_token
        data = gws_json(
            [GWS, "drive", "files", "list", "--params", json.dumps(params)]
        )
        files.extend(data.get("files", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return files


def sanitize_name(name: str) -> str:
    name = name.strip().rstrip(".")
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name)
    if not name:
        name = "_unnamed"
    return name[:180]


def download_file(file_id: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [
            GWS,
            "drive",
            "files",
            "get",
            "--params",
            json.dumps({"fileId": file_id, "alt": "media"}),
            "--output",
            str(dest),
        ],
        capture_output=True,
    )
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", errors="replace")
        raise RuntimeError("download failed {0}: {1}".format(dest.name, err[:300]))


def convert_to_jpg(path: Path) -> Path:
    ext = path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return path
    if ext not in RASTER_EXT:
        return path
    from PIL import Image

    out = path.with_suffix(".jpg")
    if out == path:
        return path
    img = Image.open(path)
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        alpha = img.split()[-1] if img.mode in ("RGBA", "LA") else None
        bg.paste(img, mask=alpha)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.save(out, "JPEG", quality=92, optimize=True)
    path.unlink(missing_ok=True)
    return out


def walk(
    folder_id: str,
    rel_parts: list[str],
    manifest: list[dict],
    dry_run: bool,
    stats: dict,
) -> None:
    for item in sorted(list_children(folder_id), key=lambda x: x["name"].lower()):
        name = sanitize_name(item["name"])
        mime = item.get("mimeType", "")
        rel = "/".join(rel_parts + [name])
        if mime == "application/vnd.google-apps.folder":
            walk(folder_id=item["id"], rel_parts=rel_parts + [name], manifest=manifest, dry_run=dry_run, stats=stats)
            continue
        if mime in SKIP_MIMES:
            manifest.append({"path": rel, "skipped": mime, "id": item["id"]})
            stats["skipped"] += 1
            continue
        dest = STAGING.joinpath(*rel_parts, name)
        entry = {
            "path": rel,
            "id": item["id"],
            "mimeType": mime,
            "size": item.get("size"),
            "modifiedTime": item.get("modifiedTime"),
            "local": str(dest.relative_to(V1)).replace("\\", "/"),
        }
        if dry_run:
            manifest.append(entry)
            stats["planned"] += 1
            print("[dry-run]", rel.encode("ascii", "replace").decode(), mime, item.get("size", ""))
            continue
        if dest.is_file() and dest.stat().st_size > 0:
            final = convert_to_jpg(dest)
            entry["local"] = str(final.relative_to(V1)).replace("\\", "/")
            entry["status"] = "exists"
            manifest.append(entry)
            stats["skipped_existing"] += 1
            continue
        try:
            log("download: " + rel.encode("ascii", "replace").decode())
            download_file(item["id"], dest)
            final = convert_to_jpg(dest)
            entry["local"] = str(final.relative_to(V1)).replace("\\", "/")
            entry["status"] = "ok"
            manifest.append(entry)
            stats["downloaded"] += 1
        except Exception as exc:
            entry["status"] = "error"
            entry["error"] = str(exc)
            manifest.append(entry)
            stats["errors"] += 1
            print("ERROR:", rel, exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    STAGING.mkdir(parents=True, exist_ok=True)
    readme = STAGING / "README.md"
    if not readme.is_file():
        readme.write_text(
            "# Job hunt staging (local review only)\n\n"
            "Downloaded from Google Drive `19 job hunt` (LionDrive transfer).\n"
            "Raster images converted to JPG. PDF/INDD/AI kept as-is.\n\n"
            "**Not for prod** — examine here, then copy chosen assets into `snapshot/`.\n"
            "This folder is gitignored.\n",
            encoding="utf-8",
        )

    manifest = []
    stats = {"planned": 0, "downloaded": 0, "skipped_existing": 0, "skipped": 0, "errors": 0}
    t0 = time.time()
    walk(ROOT_FOLDER_ID, ["19 job hunt"], manifest, args.dry_run, stats)
    MANIFEST.write_text(json.dumps({"stats": stats, "files": manifest}, indent=2), encoding="utf-8")
    print("\nDone in {0:.1f}s".format(time.time() - t0))
    print(json.dumps(stats, indent=2))
    print("manifest:", MANIFEST.relative_to(V1))
    return 1 if stats.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
