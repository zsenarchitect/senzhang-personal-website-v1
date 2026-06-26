#!/usr/bin/env python3
"""Read-only audit: uncategorized / orphan media in snapshot/_media and HTML refs."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

V1 = Path(__file__).resolve().parents[1]
SNAP = V1 / "snapshot" / "2026-06-05"
MEDIA = SNAP / "_media"
REGISTRY_PATH = V1 / "data" / "projects.json"
DECISIONS_PATH = V1 / "dev" / "job-hunt-staging" / "import-decisions.json"

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp", ".svg"}
VIDEO_EXT = {".mp4", ".webm", ".mov"}
DOC_EXT = {".pdf"}

# HTML pages that are hubs/sections (not individual project detail pages)
HUB_PAGES = {
    SNAP / "menu.html",
    SNAP / "index.html",
    SNAP / "works.html",
    SNAP / "cover-page.html",
    SNAP / "about-me.html",
    SNAP / "academic" / "index.html",
    SNAP / "professional" / "index.html",
    SNAP / "code" / "index.html",
    SNAP / "speaking" / "index.html",
}

IMG_ATTR_RE = re.compile(
    r'(?:src|data-src|data-image|href)\s*=\s*["\']([^"\']+)["\']',
    re.I,
)
CDN_IMAGE_RE = re.compile(
    r"_cdn/images\.squarespace-cdn\.com/[^\"'\s>]+",
    re.I,
)
MEDIA_REF_RE = re.compile(
    r"_media/(?:projects|speaking)/([^/\"'\s>]+)/[^\"'\s>]+",
    re.I,
)
MEDIA_OTHER_RE = re.compile(
    r"_media/(?!projects/|speaking/)([^\"'\s>]+)",
    re.I,
)

SKIP_CDN_SUFFIX = {".js", ".css", ".woff", ".woff2", ".ttf", ".eot"}


def load_registry() -> dict:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return data.get("projects", {})


def is_image_file(p: Path) -> bool:
    return p.suffix.lower() in IMAGE_EXT


def rel_media(p: Path) -> str:
    return p.relative_to(MEDIA).as_posix()


def audit_media_tree(registry: dict) -> dict:
    """Files/folders under _media/ not in projects/<slug>/ or speaking/<slug>/."""
    registry_slugs = set(registry.keys())
    speaking_slugs = {s for s, m in registry.items() if m.get("category") == "speaking"}
    project_slugs = registry_slugs - speaking_slugs

    root_files = []
    root_dirs = []
    ecosystem_files = []
    other_orphans = []

    if not MEDIA.is_dir():
        return {"error": "_media missing"}

    for child in sorted(MEDIA.iterdir()):
        if child.is_dir():
            if child.name in ("projects", "speaking"):
                continue
            root_dirs.append(child.name)
            for f in child.rglob("*"):
                if f.is_file():
                    ecosystem_files.append(rel_media(f))
        else:
            root_files.append(child.name)

    projects_root = MEDIA / "projects"
    speaking_root = MEDIA / "speaking"
    disk_project_slugs = sorted(
        d.name for d in projects_root.iterdir() if d.is_dir()
    ) if projects_root.is_dir() else []
    disk_speaking_slugs = sorted(
        d.name for d in speaking_root.iterdir() if d.is_dir()
    ) if speaking_root.is_dir() else []

    orphan_project_folders = [s for s in disk_project_slugs if s not in registry_slugs]
    orphan_speaking_folders = [s for s in disk_speaking_slugs if s not in registry_slugs]

    registry_no_media = []
    registry_empty = []
    for slug in sorted(registry_slugs):
        cat = registry[slug].get("category", "")
        if cat == "speaking":
            folder = speaking_root / slug
        else:
            folder = projects_root / slug
        if not folder.is_dir():
            registry_no_media.append(slug)
        else:
            files = [f for f in folder.iterdir() if f.is_file()]
            if not files:
                registry_empty.append(slug)

    # Loose files inside projects/ or speaking/ root (not in slug subfolder)
    for sub, label in [(projects_root, "projects"), (speaking_root, "speaking")]:
        if sub.is_dir():
            for f in sub.iterdir():
                if f.is_file():
                    other_orphans.append("{0}/{1}".format(label, f.name))

    return {
        "root_files": root_files,
        "root_dirs": root_dirs,
        "ecosystem_file_count": len(ecosystem_files),
        "ecosystem_files_sample": ecosystem_files[:15],
        "other_orphans": other_orphans,
        "disk_project_slugs": disk_project_slugs,
        "disk_speaking_slugs": disk_speaking_slugs,
        "orphan_project_folders": orphan_project_folders,
        "orphan_speaking_folders": orphan_speaking_folders,
        "registry_no_media_folder": registry_no_media,
        "registry_empty_folder": registry_empty,
        "registry_slug_count": len(registry_slugs),
        "disk_project_folder_count": len(disk_project_slugs),
        "disk_speaking_folder_count": len(disk_speaking_slugs),
    }


def audit_html_cdn(registry: dict) -> dict:
    """Image refs in snapshot HTML still pointing at _cdn/ instead of _media/projects/."""
    html_files = sorted(SNAP.rglob("*.html"))
    by_page: dict[str, list[str]] = {}
    all_cdn_images: Counter = Counter()

    for html_path in html_files:
        text = html_path.read_text(encoding="utf-8", errors="replace")
        refs = CDN_IMAGE_RE.findall(text)
        # dedupe per page
        unique = sorted(set(refs))
        if unique:
            rel = html_path.relative_to(SNAP).as_posix()
            by_page[rel] = unique
            for r in unique:
                all_cdn_images[r] += 1

    # Project pages still on CDN (content images, not shell)
    project_pages_on_cdn = []
    for rel, refs in sorted(by_page.items()):
        slug = Path(rel).stem
        if slug in registry or rel.startswith(("code/", "speaking/")):
            if rel not in {p.relative_to(SNAP).as_posix() for p in HUB_PAGES}:
                project_pages_on_cdn.append((rel, len(refs)))

    hub_pages_on_cdn = []
    for hub in HUB_PAGES:
        if hub.is_file():
            rel = hub.relative_to(SNAP).as_posix()
            if rel in by_page:
                hub_pages_on_cdn.append((rel, len(by_page[rel])))

    return {
        "html_files_scanned": len(html_files),
        "pages_with_cdn_images": len(by_page),
        "unique_cdn_image_urls": len(all_cdn_images),
        "total_cdn_image_refs": sum(all_cdn_images.values()),
        "top_cdn_images": all_cdn_images.most_common(10),
        "hub_pages_with_cdn_images": hub_pages_on_cdn,
        "project_pages_with_cdn_content": sorted(project_pages_on_cdn, key=lambda x: -x[1])[:20],
        "cdn_by_page_sample": {k: v[:3] for k, v in list(by_page.items())[:8]},
    }


def audit_import_decisions(registry: dict) -> dict:
    if not DECISIONS_PATH.is_file():
        return {"error": "import-decisions.json missing"}

    data = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
    files = data.get("files", {})
    by_status = Counter()
    imported = []
    missing_dest = []
    unknown_slug = []
    registry_slugs = set(registry.keys())

    for src, meta in files.items():
        status = meta.get("status", "unknown")
        by_status[status] += 1
        if status != "imported":
            continue
        imported.append(meta)
        dest = meta.get("dest", "")
        slug = meta.get("targetSlug", "")
        if slug and slug not in registry_slugs:
            unknown_slug.append({"src": src, "slug": slug, "dest": dest})
        dest_path = V1 / dest.replace("/", "\\") if dest else None
        if dest_path and not dest_path.is_file():
            missing_dest.append({"src": src, "dest": dest})

    # Count imported files on disk under _media/projects and speaking
    imported_dests = [m.get("dest", "") for m in imported if m.get("dest")]
    on_disk = sum(1 for d in imported_dests if (V1 / d.replace("/", "\\")).is_file())

    slug_counts = Counter(m.get("targetSlug", "?") for m in imported)

    return {
        "updated_at": data.get("updatedAt"),
        "total_decisions": len(files),
        "by_status": dict(by_status),
        "imported_count": len(imported),
        "imported_on_disk": on_disk,
        "imported_missing_on_disk": len(missing_dest),
        "missing_dest_sample": missing_dest[:10],
        "unknown_slug_imports": unknown_slug,
        "imported_by_slug": dict(slug_counts.most_common()),
    }


def audit_hub_images(registry: dict) -> dict:
    """Images on menu/hub/section pages not tied to a project slug folder."""
    registry_slugs = set(registry.keys())
    hub_media_refs: dict[str, list[str]] = defaultdict(list)
    hub_cdn_refs: dict[str, list[str]] = defaultdict(list)
    untagged_media: dict[str, list[str]] = defaultdict(list)

    for hub in sorted(HUB_PAGES):
        if not hub.is_file():
            continue
        rel = hub.relative_to(SNAP).as_posix()
        text = hub.read_text(encoding="utf-8", errors="replace")

        for m in MEDIA_REF_RE.finditer(text):
            slug = m.group(1)
            ref = m.group(0)
            hub_media_refs[rel].append(ref)
            if slug not in registry_slugs:
                untagged_media[rel].append(ref)

        for m in MEDIA_OTHER_RE.finditer(text):
            ref = m.group(0)
            if is_image_file(Path(ref)) or ref.endswith((".mp4", ".jpg", ".png", ".jpeg", ".webp", ".gif")):
                untagged_media[rel].append(ref)

        for cdn in CDN_IMAGE_RE.findall(text):
            hub_cdn_refs[rel].append(cdn)

    summary = {}
    for rel in sorted(set(list(hub_media_refs) + list(hub_cdn_refs) + list(untagged_media))):
        summary[rel] = {
            "media_project_refs": len(hub_media_refs.get(rel, [])),
            "cdn_image_refs": len(hub_cdn_refs.get(rel, [])),
            "non_slug_media_refs": len(untagged_media.get(rel, [])),
            "cdn_sample": hub_cdn_refs.get(rel, [])[:3],
            "non_slug_sample": untagged_media.get(rel, [])[:3],
        }

    return {
        "hub_pages_checked": len([p for p in HUB_PAGES if p.is_file()]),
        "pages_with_cdn_hub_images": sum(1 for v in hub_cdn_refs.values() if v),
        "total_hub_cdn_refs": sum(len(v) for v in hub_cdn_refs.values()),
        "total_hub_non_slug_refs": sum(len(v) for v in untagged_media.values()),
        "by_page": summary,
    }


def print_section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    registry = load_registry()
    media = audit_media_tree(registry)
    cdn = audit_html_cdn(registry)
    imports = audit_import_decisions(registry)
    hubs = audit_hub_images(registry)

    print_section("1. SNAPSHOT _media/ — uncategorized files")
    print("Root files ({0}):".format(len(media.get("root_files", []))))
    for f in media.get("root_files", []):
        note = ""
        if f.endswith(".pdf"):
            note = " [resume — OK at root]"
        elif f.endswith(".mp4"):
            note = " [site video — OK at root]"
        print("  - {0}{1}".format(f, note))
    print("Root dirs outside projects/speaking ({0}): {1}".format(
        len(media.get("root_dirs", [])), media.get("root_dirs")))
    print("  ecosystem/ file count: {0}".format(media.get("ecosystem_file_count", 0)))
    for f in media.get("ecosystem_files_sample", []):
        print("    e.g. {0}".format(f))
    if media.get("other_orphans"):
        print("Loose files in projects/ or speaking/ root:")
        for f in media["other_orphans"]:
            print("  - {0}".format(f))

    print_section("2. PROJECT FOLDERS vs REGISTRY")
    print("Registry slugs: {0}".format(media["registry_slug_count"]))
    print("Disk project folders: {0}".format(media["disk_project_folder_count"]))
    print("Disk speaking folders: {0}".format(media["disk_speaking_folder_count"]))
    print("Orphan project folders (disk, not in registry): {0}".format(
        len(media["orphan_project_folders"])))
    for s in media["orphan_project_folders"]:
        print("  - {0}".format(s))
    print("Orphan speaking folders: {0}".format(len(media["orphan_speaking_folders"])))
    for s in media["orphan_speaking_folders"]:
        print("  - {0}".format(s))
    print("Registry slugs with NO media folder: {0}".format(
        len(media["registry_no_media_folder"])))
    for s in media["registry_no_media_folder"]:
        print("  - {0} ({1})".format(s, registry[s].get("category", "?")))
    print("Registry slugs with EMPTY folder: {0}".format(len(media["registry_empty_folder"])))
    for s in media["registry_empty_folder"]:
        print("  - {0}".format(s))

    print_section("3. HTML _cdn/ IMAGE REFERENCES (legacy Squarespace)")
    print("HTML files scanned: {0}".format(cdn["html_files_scanned"]))
    print("Pages with CDN content images: {0}".format(cdn["pages_with_cdn_images"]))
    print("Unique CDN image URLs: {0}".format(cdn["unique_cdn_image_urls"]))
    print("Total CDN image ref occurrences: {0}".format(cdn["total_cdn_image_refs"]))
    print("Top CDN images:")
    for url, count in cdn["top_cdn_images"]:
        print("  [{0}x] {1}".format(count, url[:90]))
    print("Hub/section pages still using CDN images:")
    for rel, n in cdn["hub_pages_with_cdn_images"]:
        print("  - {0}: {1} refs".format(rel, n))
    print("Project detail pages with most CDN content images:")
    for rel, n in cdn["project_pages_with_cdn_content"][:10]:
        print("  - {0}: {1}".format(rel, n))

    print_section("4. JOB HUNT STAGING — import-decisions.json")
    if "error" in imports:
        print(imports["error"])
    else:
        print("Updated: {0}".format(imports.get("updated_at")))
        print("Total file decisions: {0}".format(imports["total_decisions"]))
        print("By status: {0}".format(imports["by_status"]))
        print("Imported: {0} | on disk: {1} | missing dest: {2}".format(
            imports["imported_count"],
            imports["imported_on_disk"],
            imports["imported_missing_on_disk"],
        ))
        if imports["missing_dest_sample"]:
            print("Missing dest sample:")
            for m in imports["missing_dest_sample"]:
                print("  - {0}".format(m["dest"]))
        if imports["unknown_slug_imports"]:
            print("Imports with unknown slug:")
            for u in imports["unknown_slug_imports"]:
                print("  - {0} -> {1}".format(u["slug"], u["dest"]))
        print("Imported by slug:")
        for slug, n in imports["imported_by_slug"].items():
            print("  - {0}: {1}".format(slug, n))

    print_section("5. MENU / HUB / SECTION PAGES — untagged images")
    print("Hub pages checked: {0}".format(hubs["hub_pages_checked"]))
    print("Pages with CDN hub images: {0}".format(hubs["pages_with_cdn_hub_images"]))
    print("Total hub CDN image refs: {0}".format(hubs["total_hub_cdn_refs"]))
    print("Total non-slug _media refs: {0}".format(hubs["total_hub_non_slug_refs"]))
    for rel, info in hubs["by_page"].items():
        if info["cdn_image_refs"] or info["non_slug_media_refs"]:
            print("  {0}: cdn={1}, non_slug_media={2}".format(
                rel, info["cdn_image_refs"], info["non_slug_media_refs"]))
            for s in info.get("cdn_sample", []):
                print("    cdn: {0}".format(s[:80]))
            for s in info.get("non_slug_sample", []):
                print("    other: {0}".format(s[:80]))

    # JSON dump for parent agent
    report = {
        "media": media,
        "cdn": {
            k: v for k, v in cdn.items()
            if k not in ("cdn_by_page_sample",)
        },
        "imports": imports,
        "hubs": hubs,
    }
    out = V1 / "dev" / "audit-orphan-media-report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nFull JSON report: {0}".format(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
