#!/usr/bin/env python3
"""Local import picker API: browse job-hunt staging and copy assets into snapshot."""
from __future__ import annotations

import json
import mimetypes
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import pdf_pages
import project_page

V1 = Path(__file__).resolve().parents[1]
STAGING = V1 / "dev" / "job-hunt-staging"
MANIFEST_PATH = STAGING / "manifest.json"
SELECTIONS_PATH = STAGING / "selections.json"
DECISIONS_PATH = STAGING / "import-decisions.json"
SNAP = V1 / "snapshot" / "2026-06-05"
MEDIA = SNAP / "_media"

IMAGE_MIMES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/tiff",
    }
)
IMAGE_EXT = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"})
DESIGN_EXT = frozenset({".ai", ".indd", ".dwg", ".eps", ".psd", ".zip", ".rar", ".7z"})
PDF_EXT = frozenset({".pdf"})

PRESETS = [
    {"id": "ennead-bilibili-renders", "label": "Bilibili renders", "prefix": "19 job hunt/Ennead Architects/Bilibili/04 Renderings"},
    {"id": "ennead-bytedance", "label": "Ennead / Bytedance", "prefix": "19 job hunt/Ennead Architects/Bytedance Shenzhen"},
    {"id": "ennead-ftz", "label": "Ennead / FTZ", "prefix": "19 job hunt/Ennead Architects/FTZ"},
    {"id": "for-portfolio", "label": "For Portfolio", "prefix": "19 job hunt/For Portfolio"},
    {"id": "resume-bg", "label": "Resume booklets", "prefix": "19 job hunt/High-Res Jpg Background"},
    {"id": "resumes", "label": "Resume PDFs", "prefix": "19 job hunt"},
]

FOLDER_SLUG_HINTS = [
    (re.compile(r"bilibili", re.I), "bilibili-hq"),
    (re.compile(r"bytedance", re.I), "bytedance-hq"),
    (re.compile(r"ftz", re.I), "ftz-shanghai"),
    (re.compile(r"hudson", re.I), "hudson-yards"),
    (re.compile(r"enneadtab", re.I), "enneadtab-ecosystem"),
    (re.compile(r"bimrunner", re.I), "bimrunner"),
    (re.compile(r"renderpolish", re.I), "renderpolisher"),
    (re.compile(r"realm", re.I), "realm"),
    (re.compile(r"ideafactory", re.I), "ideafactory"),
    (re.compile(r"museum.of.verb", re.I), "museum-of-verbs"),
    (re.compile(r"liberty", re.I), "liberty-museum"),
    (re.compile(r"forumfold", re.I), "forumfold"),
    (re.compile(r"gravity", re.I), "gravity-rises"),
    (re.compile(r"block.field", re.I), "block-field"),
]

ROLE_DEST = {
    "cover": "projects/{slug}/cover.jpg",
    "gallery": "projects/{slug}/{name}",
    "speaking_cover": "speaking/{slug}/cover.jpg",
    "resume": "Sen-Zhang-Resume.pdf",
}

_manifest_cache: dict | None = None
_manifest_by_path: dict[str, dict] | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def staging_ready() -> bool:
    return MANIFEST_PATH.is_file() and STAGING.is_dir()


def load_manifest() -> dict:
    global _manifest_cache
    if _manifest_cache is None:
        if not MANIFEST_PATH.is_file():
            return {"stats": {}, "files": []}
        _manifest_cache = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return _manifest_cache


def _manifest_index() -> dict[str, dict]:
    global _manifest_by_path
    if _manifest_by_path is None:
        _manifest_by_path = {}
        for item in load_manifest().get("files", []):
            path = _norm_rel(item.get("path", ""))
            if path:
                _manifest_by_path[path] = item
    return _manifest_by_path


def invalidate_manifest_cache() -> None:
    global _manifest_cache, _manifest_by_path
    _manifest_cache = None
    _manifest_by_path = None


def _file_ready(item: dict) -> bool:
    return not item.get("error") and item.get("status") in ("exists", "ok")


def _norm_rel(path: str) -> str:
    return path.replace("\\", "/").lstrip("/")


def _staging_file(rel: str) -> Path:
    rel = _norm_rel(rel)
    root = STAGING.resolve()

    item = _manifest_index().get(rel)
    if item:
        local = item.get("local")
        if local:
            local_path = (V1 / _norm_rel(local)).resolve()
            if local_path.is_file():
                return local_path

    target = (STAGING / rel).resolve()
    if target.is_file():
        if not str(target).startswith(str(root)):
            raise ValueError("path outside staging")
        return target

    # Drive downloader converts png/webp/... to jpg on disk; manifest path keeps original ext.
    ext = Path(rel).suffix.lower()
    if ext in {".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}:
        jpg_target = (STAGING / (rel[: -len(ext)] + ".jpg")).resolve()
        if jpg_target.is_file() and str(jpg_target).startswith(str(root)):
            return jpg_target

    if not str(target).startswith(str(root)):
        raise ValueError("path outside staging")
    return target


def _read_head(path: Path, n: int = 16) -> bytes:
    with path.open("rb") as handle:
        return handle.read(n)


def is_pdf_compatible(path: Path) -> bool:
    """Many Illustrator exports embed a PDF preview."""
    ext = path.suffix.lower()
    if ext in PDF_EXT:
        return True
    if ext not in {".ai", ".eps"}:
        return False
    try:
        return _read_head(path, 5).startswith(b"%PDF")
    except OSError:
        return False


def view_as(path: str, mime: str = "", staging: Path | None = None) -> str:
    """Preview mode for the browser UI."""
    ext = Path(path).suffix.lower()
    if mime in IMAGE_MIMES or ext in IMAGE_EXT:
        return "image"
    if ext in PDF_EXT or mime == "application/pdf":
        return "pdf"
    if staging is None:
        try:
            staging = _staging_file(path)
        except ValueError:
            staging = None
    if staging is not None and staging.is_file() and is_pdf_compatible(staging):
        return "pdf"
    if ext in {".zip", ".rar", ".7z"}:
        return "zip"
    if ext in DESIGN_EXT or mime in {
        "application/postscript",
        "application/illustrator",
        "application/vnd.adobe.illustrator",
    }:
        return "design"
    return "other"


def file_kind(path: str, mime: str = "") -> str:
    ext = Path(path).suffix.lower()
    if mime in IMAGE_MIMES or ext in IMAGE_EXT:
        return "image"
    if ext == ".pdf" or mime == "application/pdf":
        return "pdf"
    if ext in DESIGN_EXT:
        return "design"
    return "other"


def suggest_slug(path: str, registry_slugs: list[str] | None = None) -> str | None:
    registry_slugs = registry_slugs or []
    for pattern, slug in FOLDER_SLUG_HINTS:
        if pattern.search(path) and slug in registry_slugs:
            return slug
    for pattern, slug in FOLDER_SLUG_HINTS:
        if pattern.search(path):
            return slug
    return None


def _load_registry_slugs() -> list[str]:
    reg_path = V1 / "data" / "projects.json"
    if not reg_path.is_file():
        return []
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    return list(data.get("projects", {}).keys())


def build_summary() -> dict:
    data = load_manifest()
    files = [f for f in data.get("files", []) if _file_ready(f)]
    by_kind: dict[str, int] = {}
    total_bytes = 0
    for item in files:
        kind = file_kind(item.get("path", ""), item.get("mimeType", ""))
        by_kind[kind] = by_kind.get(kind, 0) + 1
        try:
            total_bytes += int(item.get("size") or 0)
        except (TypeError, ValueError):
            pass
    counts = decision_counts()
    decided = counts["imported"] + counts["rejected"]
    return {
        "ready": staging_ready(),
        "manifest": str(MANIFEST_PATH.relative_to(V1)),
        "fileCount": len(files),
        "totalBytes": total_bytes,
        "byKind": by_kind,
        "presets": PRESETS,
        "stats": data.get("stats", {}),
        "decisions": counts,
        "progress": {
            "manifestFiles": len(files),
            "decided": decided,
            "imported": counts["imported"],
            "rejected": counts["rejected"],
        },
        "capabilities": [
            "decisions",
            "pdf-meta",
            "pdf-preview",
            "extract-pages",
            "reject-pdf",
        ],
    }


def _is_pdf_rel(rel: str) -> bool:
    return pdf_pages.is_pdf_path(rel)


def _row_from_page(
    page: dict,
    pdf_rel: str,
    index: dict,
    decisions: dict,
    registry_slugs: list[str],
    hide_decided: bool,
) -> dict | None:
    path = _norm_rel(page.get("path", ""))
    decision = decisions.get(path, {})
    status = decision.get("status", "pending")
    if hide_decided and status in ("imported", "rejected"):
        return None
    page_num = int(page.get("page") or 0)
    return {
        "path": path,
        "name": Path(path).name,
        "ext": ".jpg",
        "kind": "image",
        "viewAs": "image",
        "mimeType": "image/jpeg",
        "size": int(page.get("size") or 0),
        "modifiedTime": index.get("convertedAt", ""),
        "suggestedSlug": suggest_slug(pdf_rel, registry_slugs),
        "decision": status,
        "importDest": decision.get("dest", ""),
        "sourcePdf": pdf_rel,
        "pageNum": page_num,
        "pdfPageCount": int(index.get("pageCount") or 0),
        "isPdfPage": True,
    }


def _list_pdf_page_files(
    pdf_rel: str,
    q: str,
    limit: int,
    offset: int,
    hide_decided: bool,
) -> dict:
    pdf_rel = _norm_rel(pdf_rel)
    pdf_path = _staging_file(pdf_rel)
    if not pdf_path.is_file():
        raise FileNotFoundError("missing pdf: " + pdf_rel)
    meta = pdf_pages.pdf_document_meta(STAGING, pdf_rel, pdf_path)
    index = pdf_pages.pdf_pages_info(STAGING, pdf_rel, pdf_path) or {"pages": []}
    q_lower = q.strip().lower()
    decisions = load_decisions().get("files", {})
    registry_slugs = _load_registry_slugs()
    rows = []
    for page in index.get("pages", []):
        row = _row_from_page(page, pdf_rel, index, decisions, registry_slugs, hide_decided)
        if not row:
            continue
        if q_lower and q_lower not in row["path"].lower() and q_lower not in pdf_rel.lower():
            continue
        rows.append(row)
    rows.sort(key=lambda r: r["pageNum"])
    total = len(rows)
    page = rows[offset : offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "files": page,
        "pdfSource": pdf_rel,
        "pageCount": meta.get("pageCount", 0),
        "extractedCount": meta.get("extractedCount", 0),
    }


def pdf_meta(rel: str) -> dict:
    pdf_rel = _norm_rel(rel)
    if not _is_pdf_rel(pdf_rel):
        raise ValueError("rel must be a .pdf path")
    pdf_path = _staging_file(pdf_rel)
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_rel)
    return pdf_pages.pdf_document_meta(STAGING, pdf_rel, pdf_path)


def extract_pdf_pages(rel: str, page_nums: list) -> dict:
    pdf_rel = _norm_rel(rel)
    if not _is_pdf_rel(pdf_rel):
        raise ValueError("stagingPath must be a .pdf file")
    pdf_path = _staging_file(pdf_rel)
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_rel)
    nums = []
    for raw in page_nums:
        try:
            nums.append(int(raw))
        except (TypeError, ValueError):
            continue
    if not nums:
        raise ValueError("pages required (list of page numbers)")
    return pdf_pages.ensure_pdf_page_list(STAGING, pdf_rel, pdf_path, nums)


def preview_pdf_page(rel: str, page_num: int) -> Path:
    pdf_rel = _norm_rel(rel)
    if not _is_pdf_rel(pdf_rel):
        raise ValueError("rel must be a .pdf path")
    pdf_path = _staging_file(pdf_rel)
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_rel)
    page_num = int(page_num)
    page_count = pdf_pages.get_page_count(pdf_path)
    if page_num < 1 or page_num > page_count:
        raise ValueError("page out of range")
    return pdf_pages.preview_page_path(STAGING, pdf_rel, pdf_path, page_num)


def list_files(
    prefix: str = "",
    kind: str = "",
    q: str = "",
    limit: int = 200,
    offset: int = 0,
    hide_decided: bool = True,
) -> dict:
    prefix = _norm_rel(prefix)
    if _is_pdf_rel(prefix):
        try:
            return _list_pdf_page_files(prefix, q, limit, offset, hide_decided)
        except FileNotFoundError:
            pass
        except RuntimeError as exc:
            return {
                "total": 0,
                "offset": offset,
                "limit": limit,
                "files": [],
                "error": str(exc),
                "pdfSource": prefix,
            }

    q_lower = q.strip().lower()
    data = load_manifest()
    decisions = load_decisions().get("files", {})
    registry_slugs = _load_registry_slugs()
    rows = []
    for item in data.get("files", []):
        if not _file_ready(item):
            continue
        path = _norm_rel(item.get("path", ""))
        if prefix and not path.startswith(prefix):
            continue
        fk = file_kind(path, item.get("mimeType", ""))
        if kind == "pdf":
            if fk != "pdf":
                continue
            rest = path[len(prefix) + 1 :] if prefix else path
            if prefix and "/" in rest:
                continue
            if not prefix and "/" in path:
                continue
            pdf_path = STAGING / path
            info = pdf_pages.pdf_pages_info(STAGING, path, pdf_path if pdf_path.is_file() else None)
            rows.append(
                {
                    "path": path,
                    "name": Path(path).name,
                    "ext": ".pdf",
                    "kind": "pdf",
                    "viewAs": "pdf",
                    "mimeType": item.get("mimeType", "application/pdf"),
                    "size": int(item.get("size") or 0),
                    "modifiedTime": item.get("modifiedTime", ""),
                    "suggestedSlug": suggest_slug(path, registry_slugs),
                    "decision": decisions.get(path, {}).get("status", "pending"),
                    "importDest": decisions.get(path, {}).get("dest", ""),
                    "isPdfFolder": True,
                    "pageCount": int((info or {}).get("pageCount") or 0),
                }
            )
            continue
        if fk == "pdf":
            continue
        if kind and fk != kind:
            continue
        if q_lower and q_lower not in path.lower():
            continue
        decision = decisions.get(path, {})
        status = decision.get("status", "pending")
        if hide_decided and status in ("imported", "rejected"):
            continue
        try:
            disk = _staging_file(path)
            disk_ok = disk.is_file()
        except (ValueError, OSError):
            disk = None
            disk_ok = False
        if fk == "image" and not disk_ok:
            continue
        va = view_as(path, item.get("mimeType", ""), disk if disk_ok else None)
        manifest_ext = Path(path).suffix.lower()
        disk_ext = disk.suffix.lower() if disk_ok else manifest_ext
        rows.append(
            {
                "path": path,
                "name": Path(path).name,
                "ext": manifest_ext,
                "onDiskExt": disk_ext,
                "kind": fk,
                "viewAs": va,
                "mimeType": item.get("mimeType", ""),
                "size": disk.stat().st_size if disk_ok else int(item.get("size") or 0),
                "modifiedTime": item.get("modifiedTime", ""),
                "suggestedSlug": suggest_slug(path, registry_slugs),
                "decision": status,
                "importDest": decision.get("dest", ""),
                "convertedToJpg": manifest_ext == ".png" and disk_ext == ".jpg",
            }
        )
    rows.sort(key=lambda r: r["path"].lower())
    total = len(rows)
    page = rows[offset : offset + limit]
    return {"total": total, "offset": offset, "limit": limit, "files": page}


def list_folders(prefix: str = "", depth: int = 2) -> dict:
    """Return immediate child folder names under prefix."""
    prefix = _norm_rel(prefix)
    if prefix and not prefix.endswith("/"):
        prefix = prefix + "/"
    if _is_pdf_rel(prefix.rstrip("/")):
        return {"prefix": prefix.rstrip("/"), "folders": []}

    data = load_manifest()
    children: dict[str, int] = {}
    pdf_children: dict[str, str] = {}
    for item in data.get("files", []):
        if not _file_ready(item):
            continue
        path = _norm_rel(item.get("path", ""))
        if prefix and not path.startswith(prefix):
            continue
        rest = path[len(prefix) :] if prefix else path
        if "/" in rest:
            folder = rest.split("/", 1)[0]
            children[folder] = children.get(folder, 0) + 1
            continue
        if rest.lower().endswith(".pdf"):
            pdf_children[rest] = path
    folders = [
        {"name": name, "path": (prefix + name).rstrip("/"), "fileCount": count}
        for name, count in sorted(children.items(), key=lambda x: x[0].lower())
    ]
    for name, pdf_rel in sorted(pdf_children.items(), key=lambda x: x[0].lower()):
        pdf_path = STAGING / pdf_rel
        page_count = 0
        extracted = 0
        if pdf_path.is_file():
            meta = pdf_pages.pdf_document_meta(STAGING, pdf_rel, pdf_path)
            page_count = int(meta.get("pageCount") or 0)
            extracted = int(meta.get("extractedCount") or 0)
        folders.append(
            {
                "name": name,
                "path": pdf_rel,
                "fileCount": extracted or page_count,
                "isPdfPages": True,
                "pageCount": page_count,
                "extractedCount": extracted,
            }
        )
    folders.sort(key=lambda f: f["name"].lower())
    return {"prefix": prefix.rstrip("/"), "folders": folders}


def load_decisions() -> dict:
    if not DECISIONS_PATH.is_file():
        return {"version": 1, "updatedAt": None, "files": {}}
    return json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))


def save_decisions(data: dict) -> dict:
    data["version"] = 1
    data["updatedAt"] = _utc_now()
    data.setdefault("files", {})
    DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DECISIONS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def decision_counts() -> dict:
    files = load_decisions().get("files", {})
    counts = {"pending": 0, "imported": 0, "rejected": 0}
    for meta in files.values():
        status = meta.get("status", "")
        if status in counts:
            counts[status] += 1
    return counts


def get_decision(rel: str) -> dict | None:
    return load_decisions().get("files", {}).get(_norm_rel(rel))


def _next_gallery_index(slug: str) -> int:
    folder = MEDIA / "projects" / slug
    if not folder.is_dir():
        return 1
    nums = []
    for path in folder.iterdir():
        if not path.is_file():
            continue
        match = re.match(r"^(\d+)", path.name)
        if match:
            nums.append(int(match.group(1)))
    return (max(nums) if nums else 0) + 1


def import_one_item(item: dict, dry_run: bool = False) -> dict:
    rel = _norm_rel(item.get("stagingPath", ""))
    slug = str(item.get("targetSlug", "")).strip()
    role = str(item.get("role", "gallery")).strip() or "gallery"
    if role != "resume" and not slug:
        raise ValueError("targetSlug required")
    src = _staging_file(rel)
    if not src.is_file():
        raise FileNotFoundError("missing staging file: " + rel)
    src_ext = src.suffix.lower()
    gallery_idx = _next_gallery_index(slug) - 1 if role == "gallery" else 0
    dest = _dest_for_item(
        {
            "stagingPath": rel,
            "targetSlug": slug,
            "role": role,
            "destName": item.get("destName", ""),
            "sourceExt": src_ext,
        },
        gallery_idx,
    )
    entry = {
        "stagingPath": rel,
        "dest": str(dest.relative_to(V1)).replace("\\", "/"),
        "ok": False,
    }
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    entry["ok"] = True
    return entry


def decide_file(
    staging_path: str,
    action: str,
    target_slug: str = "",
    role: str = "gallery",
) -> dict:
    rel = _norm_rel(staging_path)
    if not rel:
        raise ValueError("stagingPath required")
    data = load_decisions()
    files = data.setdefault("files", {})
    now = _utc_now()

    if action == "reject":
        files[rel] = {"status": "rejected", "decidedAt": now}
        save_decisions(data)
        return {"stagingPath": rel, "status": "rejected"}

    if action != "use":
        raise ValueError("action must be use or reject")

    if not target_slug and role != "resume":
        raise ValueError("targetSlug required for use")
    if role == "resume" or re.search(r"resume", rel, re.I):
        role = "resume"
        target_slug = ""

    result = import_one_item(
        {
            "stagingPath": rel,
            "targetSlug": target_slug,
            "role": role,
        },
        dry_run=False,
    )
    entry = {
        "status": "imported",
        "targetSlug": target_slug,
        "role": role,
        "dest": result.get("dest", ""),
        "decidedAt": now,
        "importedAt": now,
    }
    source = pdf_pages.source_pdf_for_page(STAGING, rel)
    if source:
        entry["sourcePdf"] = source[0]
        entry["pageNum"] = source[1]
    try:
        files[rel] = entry
        save_decisions(data)
    except Exception:
        dest_rel = result.get("dest")
        if dest_rel:
            dest_path = V1 / dest_rel
            if dest_path.is_file():
                try:
                    dest_path.unlink()
                except OSError:
                    pass
        raise
    gallery_synced = False
    gallery_sync_error = None
    if role == "gallery" and target_slug:
        try:
            project_page.sync_project_gallery(target_slug)
            gallery_synced = True
        except Exception as exc:
            gallery_sync_error = str(exc)
    out = {
        "stagingPath": rel,
        "status": "imported",
        "dest": result.get("dest"),
        "ok": result.get("ok"),
        "gallerySynced": gallery_synced,
    }
    if gallery_sync_error:
        out["gallerySyncError"] = gallery_sync_error
    return out


def reject_pdf_all(pdf_rel: str) -> dict:
    """Skip all pages of a PDF that are not already decided."""
    pdf_rel = _norm_rel(pdf_rel)
    if not _is_pdf_rel(pdf_rel):
        raise ValueError("stagingPath must be a .pdf file")
    pdf_path = _staging_file(pdf_rel)
    if not pdf_path.is_file():
        raise FileNotFoundError("missing pdf: " + pdf_rel)
    page_count = pdf_pages.get_page_count(pdf_path)
    data = load_decisions()
    files = data.setdefault("files", {})
    now = _utc_now()
    skipped = 0
    for page_num in range(1, page_count + 1):
        path = pdf_pages.page_rel(STAGING, pdf_rel, page_num)
        if files.get(path, {}).get("status") in ("imported", "rejected"):
            continue
        files[path] = {
            "status": "rejected",
            "decidedAt": now,
            "sourcePdf": pdf_rel,
            "pageNum": page_num,
        }
        skipped += 1
    save_decisions(data)
    return {
        "stagingPath": pdf_rel,
        "status": "rejected",
        "pagesSkipped": skipped,
        "pageCount": page_count,
    }


def undo_decision(staging_path: str) -> dict:
    rel = _norm_rel(staging_path)
    data = load_decisions()
    files = data.get("files", {})
    if rel in files:
        del files[rel]
        save_decisions(data)
    return {"stagingPath": rel, "status": "pending"}


def load_selections() -> dict:
    if not SELECTIONS_PATH.is_file():
        return {"version": 1, "updatedAt": None, "items": []}
    return json.loads(SELECTIONS_PATH.read_text(encoding="utf-8"))


def save_selections(payload: dict) -> dict:
    items = payload.get("items", [])
    if not isinstance(items, list):
        raise ValueError("items must be a list")
    clean = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rel = _norm_rel(str(item.get("stagingPath", "")))
        if not rel:
            continue
        clean.append(
            {
                "stagingPath": rel,
                "targetSlug": str(item.get("targetSlug", "")).strip(),
                "role": str(item.get("role", "gallery")).strip() or "gallery",
                "destName": str(item.get("destName", "")).strip(),
            }
        )
    out = {"version": 1, "updatedAt": _utc_now(), "items": clean}
    SELECTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SELECTIONS_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def _dest_for_item(item: dict, index: int) -> Path:
    role = item.get("role", "gallery")
    slug = item.get("targetSlug", "").strip()
    staging_path = item.get("stagingPath", "")
    ext = str(item.get("sourceExt") or Path(staging_path).suffix.lower() or ".jpg")
    if ext not in IMAGE_EXT and ext != ".pdf":
        ext = ".jpg" if role != "resume" else ".pdf"
    if ext == ".jpeg":
        ext = ".jpg"

    if role == "resume":
        rel = ROLE_DEST["resume"]
        return MEDIA / rel

    if role == "speaking_cover":
        if not slug:
            raise ValueError("speaking_cover requires targetSlug")
        # Site templates expect cover.jpg; PNG sources are flattened on import.
        return MEDIA / "speaking" / slug / "cover.jpg"

    if role == "cover":
        if not slug:
            raise ValueError("cover requires targetSlug")
        cover_name = "cover.png" if ext == ".png" else "cover.jpg"
        return MEDIA / "projects" / slug / cover_name

    # gallery
    if not slug:
        raise ValueError("gallery requires targetSlug")
    dest_name = item.get("destName") or "{:02d}{}".format(index + 1, ext)
    if dest_name == ".jpg" or dest_name == ext:
        dest_name = "{:02d}{}".format(index + 1, ext)
    return MEDIA / "projects" / slug / dest_name


def execute_import(dry_run: bool = False) -> dict:
    selections = load_selections()
    items = selections.get("items", [])
    results = []
    ok = 0
    errors = 0

    slug_gallery_idx: dict[str, int] = {}

    for i, item in enumerate(items):
        rel = item.get("stagingPath", "")
        entry = {"stagingPath": rel, "ok": False}
        try:
            src = _staging_file(rel)
            if not src.is_file():
                raise FileNotFoundError("missing staging file")
            slug = item.get("targetSlug", "").strip()
            if slug not in slug_gallery_idx:
                slug_gallery_idx[slug] = 0
            idx = slug_gallery_idx[slug]
            if item.get("role", "gallery") == "gallery":
                slug_gallery_idx[slug] = idx + 1
            dest = _dest_for_item(
                {**item, "destName": item.get("destName"), "sourceExt": src.suffix.lower()},
                idx,
            )
            entry["dest"] = str(dest.relative_to(V1)).replace("\\", "/")
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
            entry["ok"] = True
            ok += 1
        except Exception as exc:
            entry["error"] = str(exc)
            errors += 1
        results.append(entry)

    report = {
        "dryRun": dry_run,
        "importedAt": _utc_now(),
        "ok": ok,
        "errors": errors,
        "results": results,
    }
    if not dry_run:
        log_path = STAGING / "import-log.json"
        log_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report["log"] = str(log_path.relative_to(V1))
    return report


def zip_listing(path: Path, limit: int = 80) -> list[dict]:
    import zipfile

    out = []
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist()[:limit]:
                out.append(
                    {
                        "name": info.filename,
                        "size": info.file_size,
                        "dir": info.is_dir(),
                    }
                )
    except (OSError, zipfile.BadZipFile) as exc:
        return [{"name": "(cannot read zip: {})".format(exc), "size": 0, "dir": False}]
    return out


def preview_meta(rel: str) -> dict:
    path = _staging_file(rel)
    if not path.is_file():
        raise FileNotFoundError(rel)
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "application/octet-stream"
    va = view_as(rel, mime, path)
    if va == "pdf" and path.suffix.lower() in {".ai", ".eps"}:
        mime = "application/pdf"
    meta = {
        "path": _norm_rel(rel),
        "name": path.name,
        "ext": path.suffix.lower(),
        "size": path.stat().st_size,
        "viewAs": va,
        "mime": mime,
        "pdfCompatible": is_pdf_compatible(path),
        "url": "/api/import/file?rel=" + quote(rel, safe=""),
    }
    if va == "zip":
        meta["zipEntries"] = zip_listing(path)
    elif va == "design":
        meta["note"] = (
            "Native design file — use Open file to launch Illustrator/InDesign/CAD, "
            "or download for offline review."
        )
        if is_pdf_compatible(path):
            meta["note"] = "PDF-compatible preview available (embedded in file)."
            meta["viewAs"] = "pdf"
            meta["mime"] = "application/pdf"
    return meta


def preview_delivery(rel: str) -> tuple[str, Path, str]:
    """Return (content-type, path, content-disposition) for file streaming."""
    meta = preview_meta(rel)
    path = _staging_file(rel)
    disp = 'inline; filename="{}"'.format(path.name.replace('"', ""))
    return meta["mime"], path, disp


def preview_mime(rel: str) -> tuple[str, Path]:
    mime, path, _ = preview_delivery(rel)
    return mime, path


def registry_for_picker() -> dict:
    reg_path = V1 / "data" / "projects.json"
    if not reg_path.is_file():
        return {"projects": {}}
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    out = {}
    for slug, meta in data.get("projects", {}).items():
        out[slug] = {
            "slug": slug,
            "title": meta.get("title", slug),
            "category": meta.get("category", "academic"),
        }
    return {"projects": out}
