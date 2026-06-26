#!/usr/bin/env python3
"""Project registry: visibility, category, highlight, resume flags for portfolio grids."""
from __future__ import annotations

import json
from pathlib import Path

from build_section_masonry import SECTIONS

V1 = Path(__file__).resolve().parents[1]
REGISTRY_PATH = V1 / "data" / "projects.json"
DEFAULTS_PATH = V1 / "data" / "registry.defaults.json"
DEFAULT_SNAPSHOT = V1 / "snapshot" / "2026-06-05"

_FALLBACK_NEW_PROJECT = {
    "visible": False,
    "highlight": False,
    "includeInResume": False,
}


def _load_new_project_defaults() -> dict:
    if not DEFAULTS_PATH.is_file():
        return dict(_FALLBACK_NEW_PROJECT)
    data = json.loads(DEFAULTS_PATH.read_text(encoding="utf-8"))
    base = data.get("newProject", {})
    return {
        "visible": bool(base.get("visible", False)),
        "highlight": bool(base.get("highlight", False)),
        "includeInResume": bool(base.get("includeInResume", False)),
    }


def _default_title(config, slug: str) -> str:
    return config.labels.get(slug, slug.replace("-", " ").title())


def default_section_order() -> dict[str, list[str]]:
    return {key: list(config.order) for key, config in SECTIONS.items()}


def section_order_from_registry(registry: dict, section_key: str) -> list[str]:
    custom = registry.get("sectionOrder", {}).get(section_key)
    if custom:
        return list(custom)
    return list(SECTIONS[section_key].order)


def sync_section_order(registry: dict) -> dict[str, list[str]]:
    """Ensure sectionOrder lists include every project slug per category."""
    projects = registry.get("projects", {})
    order = registry.setdefault("sectionOrder", default_section_order())
    for key in SECTIONS:
        slugs_in_cat = [slug for slug, meta in projects.items() if meta.get("category", key) == key]
        current = list(order.get(key) or SECTIONS[key].order)
        merged = [s for s in current if s in slugs_in_cat]
        for slug in slugs_in_cat:
            if slug not in merged:
                merged.append(slug)
        deduped = []
        seen = set()
        for slug in merged:
            if slug not in seen:
                deduped.append(slug)
                seen.add(slug)
        order[key] = deduped
    return order


def seed_registry() -> dict:
    projects = {}
    defaults = _load_new_project_defaults()
    for key, config in SECTIONS.items():
        for slug in config.order:
            projects[slug] = {
                "slug": slug,
                "title": _default_title(config, slug),
                "category": key,
                "visible": defaults["visible"],
                "highlight": defaults["highlight"],
                "includeInResume": defaults["includeInResume"],
            }
    return {"version": 1, "sectionOrder": default_section_order(), "projects": projects}


def load_registry() -> dict:
    if not REGISTRY_PATH.is_file():
        data = seed_registry()
        save_registry(data)
        print("created", REGISTRY_PATH.relative_to(V1))
        return data
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if "sectionOrder" not in data:
        data["sectionOrder"] = default_section_order()
    return data


def save_registry(data: dict) -> None:
    data["sectionOrder"] = sync_section_order(data)
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge_registry_on_disk() -> dict:
    """Add any new slugs from SECTIONS without overwriting existing flags."""
    data = load_registry()
    changed = False
    projects = data.setdefault("projects", {})

    for key, config in SECTIONS.items():
        for slug in config.order:
            if slug not in projects:
                projects[slug] = {
                    "slug": slug,
                    "title": _default_title(config, slug),
                    "category": key,
                    **_load_new_project_defaults(),
                }
                changed = True
            elif not projects[slug].get("title"):
                projects[slug]["title"] = _default_title(config, slug)
                changed = True
    synced = sync_section_order(data)
    if synced != data.get("sectionOrder"):
        data["sectionOrder"] = synced
        changed = True
    if changed:
        save_registry(data)
    return data


def apply_registry_to_tiles(
    tiles_by_slug: dict[str, dict],
    section_key: str,
    registry: dict | None = None,
) -> tuple[dict[str, dict], list[str]]:
    registry = registry or merge_registry_on_disk()
    projects = registry.get("projects", {})
    slug_order = section_order_from_registry(registry, section_key)

    filtered: dict[str, dict] = {}
    order: list[str] = []

    for slug in slug_order:
        meta = projects.get(slug, {})
        if meta.get("category", section_key) != section_key:
            continue
        if meta.get("visible") is False:
            continue
        if slug not in tiles_by_slug:
            continue
        tile = dict(tiles_by_slug[slug])
        tile["highlight"] = bool(meta.get("highlight"))
        filtered[slug] = tile
        order.append(slug)

    for slug, meta in projects.items():
        if meta.get("category") != section_key:
            continue
        if meta.get("visible") is False:
            continue
        if slug in filtered or slug not in tiles_by_slug:
            continue
        tile = dict(tiles_by_slug[slug])
        tile["highlight"] = bool(meta.get("highlight"))
        filtered[slug] = tile
        order.append(slug)

    return filtered, order


def load_academic_tile_html(snap_dir: Path | None = None) -> str | None:
    """Full academic figure grid from works.html (not the derived masonry page)."""
    snap = snap_dir or DEFAULT_SNAPSHOT
    works = snap / "works.html"
    if works.is_file():
        return works.read_text(encoding="utf-8")
    backup = snap / "academic" / "_legacy-grid.fragment.html"
    if backup.is_file():
        return backup.read_text(encoding="utf-8")
    academic = snap / "academic" / "index.html"
    if not academic.is_file():
        return None
    html = academic.read_text(encoding="utf-8")
    if SECTIONS["academic"].marker in html:
        return None
    return html


def collect_tile_pool(
    pro_tiles: dict[str, dict],
    code_tiles: dict[str, dict],
    speak_tiles: dict[str, dict],
    snap_dir: Path | None = None,
) -> dict[str, dict]:
    from build_section_masonry import parse_legacy_tiles

    pool: dict[str, dict] = {}
    pool.update(pro_tiles)
    pool.update(code_tiles)
    pool.update(speak_tiles)
    academic_html = load_academic_tile_html(snap_dir)
    if academic_html:
        pool.update(parse_legacy_tiles(academic_html, SECTIONS["academic"]))
    return pool


def tiles_for_section(
    section_key: str,
    tile_pool: dict[str, dict],
    registry: dict | None = None,
) -> tuple[dict[str, dict], list[str]]:
    section_slugs = {
        slug
        for slug, meta in (registry or merge_registry_on_disk()).get("projects", {}).items()
        if meta.get("category") == section_key and meta.get("visible") is not False
    }
    section_tiles = {s: tile_pool[s] for s in section_slugs if s in tile_pool}
    return apply_registry_to_tiles(section_tiles, section_key, registry)


def global_slug_order(registry: dict | None = None) -> list[str]:
    registry = registry or merge_registry_on_disk()
    order: list[str] = []
    for key in ("academic", "professional", "code", "speaking"):
        order.extend(section_order_from_registry(registry, key))
    return order


if __name__ == "__main__":
    merge_registry_on_disk()
    print("ok", REGISTRY_PATH)