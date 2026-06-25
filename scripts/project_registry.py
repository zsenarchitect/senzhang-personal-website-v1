#!/usr/bin/env python3
"""Project registry: visibility, category, highlight, resume flags for portfolio grids."""
from __future__ import annotations

import json
from pathlib import Path

from build_section_masonry import SECTIONS

V1 = Path(__file__).resolve().parents[1]
REGISTRY_PATH = V1 / "data" / "projects.json"

DEFAULT_HIGHLIGHTS = {
    "museum-of-verbs",
    "bilibili-hq",
    "enneadtab-ecosystem",
    "autodesk-university-2024",
}

RESUME_DEFAULTS = {
    "enneadtab-ecosystem",
    "bilibili-hq",
    "bimrunner",
    "museum-of-verbs",
}


def _default_title(config, slug: str) -> str:
    return config.labels.get(slug, slug.replace("-", " ").title())


def seed_registry() -> dict:
    projects = {}
    for key, config in SECTIONS.items():
        for slug in config.order:
            projects[slug] = {
                "slug": slug,
                "title": _default_title(config, slug),
                "category": key,
                "visible": True,
                "highlight": slug in DEFAULT_HIGHLIGHTS,
                "includeInResume": slug in RESUME_DEFAULTS,
            }
    return {"version": 1, "projects": projects}


def load_registry() -> dict:
    if not REGISTRY_PATH.is_file():
        data = seed_registry()
        save_registry(data)
        print("created", REGISTRY_PATH.relative_to(V1))
        return data
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def save_registry(data: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge_registry_on_disk() -> dict:
    """Add any new slugs from SECTIONS without overwriting existing flags."""
    data = load_registry()
    projects = data.setdefault("projects", {})
    changed = False
    for key, config in SECTIONS.items():
        for slug in config.order:
            if slug not in projects:
                projects[slug] = {
                    "slug": slug,
                    "title": _default_title(config, slug),
                    "category": key,
                    "visible": True,
                    "highlight": slug in DEFAULT_HIGHLIGHTS,
                    "includeInResume": slug in RESUME_DEFAULTS,
                }
                changed = True
            elif not projects[slug].get("title"):
                projects[slug]["title"] = _default_title(config, slug)
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
    config = SECTIONS[section_key]

    filtered: dict[str, dict] = {}
    order: list[str] = []

    for slug in config.order:
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


def collect_tile_pool(
    academic_html: str | None,
    pro_tiles: dict[str, dict],
    code_tiles: dict[str, dict],
    speak_tiles: dict[str, dict],
) -> dict[str, dict]:
    from build_section_masonry import build_from_page_html, parse_legacy_tiles, parse_masonry_tiles

    pool: dict[str, dict] = {}
    pool.update(pro_tiles)
    pool.update(code_tiles)
    pool.update(speak_tiles)
    if academic_html:
        cfg = SECTIONS["academic"]
        if cfg.marker in academic_html:
            pool.update(parse_masonry_tiles(academic_html, cfg))
        else:
            pool.update(parse_legacy_tiles(academic_html, cfg))
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


if __name__ == "__main__":
    merge_registry_on_disk()
    print("ok", REGISTRY_PATH)