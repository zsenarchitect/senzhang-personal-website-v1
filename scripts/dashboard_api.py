#!/usr/bin/env python3
"""Dashboard API helpers: thumbnail enrichment for local project registry."""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

V1 = Path(__file__).resolve().parents[1]
SNAP = V1 / "snapshot" / "2026-06-05"


def _load_restructure_module():
    path = V1 / "scripts" / "restructure-menu-sections.py"
    spec = importlib.util.spec_from_file_location("restructure_menu_sections", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load restructure-menu-sections.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _academic_html_source() -> str | None:
    academic = SNAP / "academic" / "index.html"
    if academic.is_file():
        return academic.read_text(encoding="utf-8")
    backup = SNAP / "academic" / "_legacy-grid.fragment.html"
    if backup.is_file():
        return backup.read_text(encoding="utf-8")
    return None


def build_thumbnail_pool() -> dict[str, str]:
    scripts = str(V1 / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from project_registry import collect_tile_pool

    rms = _load_restructure_module()
    pool = collect_tile_pool(
        _academic_html_source(),
        rms.build_pro_tile_data(),
        rms.build_code_tile_data(),
        rms.build_speak_tile_data(),
    )
    return {slug: tile["src"] for slug, tile in pool.items() if tile.get("src")}


def enrich_registry_with_thumbnails(data: dict) -> dict:
    out = copy.deepcopy(data)
    thumbs = build_thumbnail_pool()
    for slug, meta in out.get("projects", {}).items():
        src = thumbs.get(slug)
        if src:
            meta["thumbnail"] = src
    return out


def strip_dashboard_fields(data: dict) -> dict:
    out = copy.deepcopy(data)
    for meta in out.get("projects", {}).values():
        meta.pop("thumbnail", None)
    return out