#!/usr/bin/env python3
"""Convert staging PDFs to cached JPG pages for the import picker."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PDF_PAGES_ROOT_NAME = "_pdf-pages"
PREVIEW_DIR_NAME = ".preview"
RENDER_DPI = 144
JPG_QUALITY = 85
MAX_EDGE_PX = 2400


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_fitz():
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError(
            "pymupdf is required for PDF preview. Run: py -3 -m pip install pymupdf"
        ) from exc
    return fitz


def pages_root(staging: Path) -> Path:
    return staging / PDF_PAGES_ROOT_NAME


def pdf_rel_norm(rel: str) -> str:
    return rel.replace("\\", "/").lstrip("/")


def pages_dir(staging: Path, pdf_rel: str) -> Path:
    return pages_root(staging) / pdf_rel_norm(pdf_rel)


def preview_dir(staging: Path, pdf_rel: str) -> Path:
    return pages_dir(staging, pdf_rel) / PREVIEW_DIR_NAME


def index_path(staging: Path, pdf_rel: str) -> Path:
    return pages_dir(staging, pdf_rel) / "index.json"


def page_filename(page_num: int) -> str:
    return "page-{:03d}.jpg".format(page_num)


def page_rel(staging: Path, pdf_rel: str, page_num: int) -> str:
    rel = "{}/{}/{}".format(
        PDF_PAGES_ROOT_NAME,
        pdf_rel_norm(pdf_rel),
        page_filename(page_num),
    )
    return rel


def is_pdf_path(rel: str) -> bool:
    return Path(pdf_rel_norm(rel)).suffix.lower() == ".pdf"


def is_derived_page_path(rel: str) -> bool:
    rel = pdf_rel_norm(rel)
    return rel.startswith(PDF_PAGES_ROOT_NAME + "/") and rel.lower().endswith(".jpg")


def source_pdf_for_page(staging: Path, page_rel_path: str) -> tuple[str, int] | None:
    rel = pdf_rel_norm(page_rel_path)
    if not is_derived_page_path(rel):
        return None
    parts = rel.split("/")
    if len(parts) < 3:
        return None
    pdf_rel = "/".join(parts[1:-1])
    if not pdf_rel.lower().endswith(".pdf"):
        return None
    idx = index_path(staging, pdf_rel)
    if not idx.is_file():
        return None
    try:
        data = json.loads(idx.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    name = parts[-1]
    for page in data.get("pages", []):
        if page.get("path", "").endswith(name):
            return pdf_rel, int(page.get("page") or 0)
    page_num = 0
    try:
        page_num = int(name.replace("page-", "").replace(".jpg", ""))
    except ValueError:
        pass
    return pdf_rel, page_num


def _source_fingerprint(path: Path) -> tuple[float, int]:
    stat = path.stat()
    return stat.st_mtime, stat.st_size


def _source_matches(index: dict, pdf_path: Path, pdf_rel: str) -> bool:
    try:
        mtime, size = _source_fingerprint(pdf_path)
    except OSError:
        return False
    return (
        index.get("sourcePdf") == pdf_rel_norm(pdf_rel)
        and float(index.get("sourceMtime") or 0) == mtime
        and int(index.get("sourceSize") or -1) == size
    )


def _load_index(staging: Path, pdf_rel: str) -> dict | None:
    idx = index_path(staging, pdf_rel)
    if not idx.is_file():
        return None
    try:
        return json.loads(idx.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def get_page_count(pdf_path: Path) -> int:
    fitz = _require_fitz()
    doc = fitz.open(pdf_path)
    try:
        return doc.page_count
    finally:
        doc.close()


def _render_page_to_file(pdf_path: Path, page_num: int, out_file: Path) -> None:
    fitz = _require_fitz()
    doc = fitz.open(pdf_path)
    try:
        if page_num < 1 or page_num > doc.page_count:
            raise ValueError("page out of range: {}".format(page_num))
        page = doc.load_page(page_num - 1)
        zoom = RENDER_DPI / 72.0
        rect = page.rect
        max_dim = max(rect.width, rect.height) * zoom
        if max_dim > MAX_EDGE_PX:
            zoom = zoom * (MAX_EDGE_PX / max_dim)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(out_file), jpg_quality=JPG_QUALITY)
    finally:
        doc.close()


def _write_index(staging: Path, pdf_rel: str, pdf_path: Path, pages: list[dict]) -> dict:
    mtime, size = _source_fingerprint(pdf_path)
    page_count = get_page_count(pdf_path)
    pages.sort(key=lambda p: int(p.get("page") or 0))
    index = {
        "sourcePdf": pdf_rel_norm(pdf_rel),
        "sourceMtime": mtime,
        "sourceSize": size,
        "convertedAt": _utc_now(),
        "pageCount": page_count,
        "pages": pages,
    }
    index_path(staging, pdf_rel).write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return index


def pdf_document_meta(staging: Path, pdf_rel: str, pdf_path: Path) -> dict:
    """Page count + which pages are already extracted as assets."""
    pdf_rel = pdf_rel_norm(pdf_rel)
    page_count = get_page_count(pdf_path)
    index = _load_index(staging, pdf_rel)
    pages = []
    extracted = []
    if index and _source_matches(index, pdf_path, pdf_rel):
        pages = list(index.get("pages", []))
        extracted = sorted(int(p.get("page") or 0) for p in pages)
        if int(index.get("pageCount") or 0) != page_count:
            index = None
            pages = []
            extracted = []
    return {
        "sourcePdf": pdf_rel,
        "pageCount": page_count,
        "extractedPages": extracted,
        "extractedCount": len(extracted),
        "pages": pages,
    }


def ensure_pdf_page(staging: Path, pdf_rel: str, pdf_path: Path, page_num: int) -> dict:
    """Extract one PDF page as a picker asset JPG."""
    pdf_rel = pdf_rel_norm(pdf_rel)
    page_num = int(page_num)
    if page_num < 1:
        raise ValueError("page must be >= 1")

    index = _load_index(staging, pdf_rel)
    if index and _source_matches(index, pdf_path, pdf_rel):
        for page in index.get("pages", []):
            if int(page.get("page") or 0) == page_num:
                return page

    out_dir = pages_dir(staging, pdf_rel)
    out_file = out_dir / page_filename(page_num)
    _render_page_to_file(pdf_path, page_num, out_file)
    entry = {
        "page": page_num,
        "path": page_rel(staging, pdf_rel, page_num),
        "size": out_file.stat().st_size,
        "extractedAt": _utc_now(),
    }

    pages = []
    if index and _source_matches(index, pdf_path, pdf_rel):
        pages = list(index.get("pages", []))
    pages = [p for p in pages if int(p.get("page") or 0) != page_num]
    pages.append(entry)
    _write_index(staging, pdf_rel, pdf_path, pages)
    return entry


def ensure_pdf_pages(staging: Path, pdf_rel: str, pdf_path: Path) -> dict:
    """Extract every page (used by skip-all and bulk flows)."""
    pdf_rel = pdf_rel_norm(pdf_rel)
    page_count = get_page_count(pdf_path)
    pages = []
    for page_num in range(1, page_count + 1):
        pages.append(ensure_pdf_page(staging, pdf_rel, pdf_path, page_num))
    return _load_index(staging, pdf_rel) or {"pages": pages, "pageCount": page_count}


def ensure_pdf_page_list(
    staging: Path, pdf_rel: str, pdf_path: Path, page_nums: list[int]
) -> dict:
    pdf_rel = pdf_rel_norm(pdf_rel)
    extracted = []
    for num in sorted(set(int(n) for n in page_nums)):
        extracted.append(ensure_pdf_page(staging, pdf_rel, pdf_path, num))
    index = _load_index(staging, pdf_rel) or {}
    return {
        "sourcePdf": pdf_rel,
        "pageCount": index.get("pageCount", get_page_count(pdf_path)),
        "extracted": extracted,
        "pages": index.get("pages", []),
    }


def preview_page_path(staging: Path, pdf_rel: str, pdf_path: Path, page_num: int) -> Path:
    """Render a page for browsing only (not a picker asset until extracted)."""
    pdf_rel = pdf_rel_norm(pdf_rel)
    page_num = int(page_num)
    out_dir = preview_dir(staging, pdf_rel)
    out_file = out_dir / page_filename(page_num)
    try:
        mtime, size = _source_fingerprint(pdf_path)
    except OSError as exc:
        raise FileNotFoundError(str(pdf_path)) from exc
    stamp = out_dir / "source.json"
    stale = True
    if stamp.is_file() and out_file.is_file():
        try:
            meta = json.loads(stamp.read_text(encoding="utf-8"))
            stale = not (
                meta.get("sourceMtime") == mtime
                and meta.get("sourceSize") == size
                and int(meta.get("page") or 0) == page_num
            )
        except (OSError, json.JSONDecodeError, ValueError):
            stale = True
    if stale:
        _render_page_to_file(pdf_path, page_num, out_file)
        stamp.write_text(
            json.dumps(
                {
                    "sourcePdf": pdf_rel,
                    "sourceMtime": mtime,
                    "sourceSize": size,
                    "page": page_num,
                    "renderedAt": _utc_now(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return out_file


def pdf_pages_info(staging: Path, pdf_rel: str, pdf_path: Path | None = None) -> dict | None:
    """Return cached index if source still matches."""
    pdf_rel = pdf_rel_norm(pdf_rel)
    index = _load_index(staging, pdf_rel)
    if not index:
        return None
    if pdf_path is None:
        return index
    if _source_matches(index, pdf_path, pdf_rel):
        return index
    return None
