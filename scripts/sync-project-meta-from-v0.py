#!/usr/bin/env python3
"""Merge v0 MDX frontmatter into data/projects.json (content fields only)."""
from __future__ import annotations

import sys
from pathlib import Path

V0 = Path(r"C:\Users\szhang\github\Personal\senzhang-personal-website-v0-failed-attempt")
V1 = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(V1 / "scripts"))
from port_v0_shared import META_FIELDS, mdx_path_for, parse_mdx  # noqa: E402
from project_registry import load_registry, save_registry  # noqa: E402


def merge_meta(project: dict, mdx_meta: dict) -> bool:
    changed = False
    for key in META_FIELDS:
        val = mdx_meta.get(key)
        if val is None or val == "" or val == []:
            continue
        if project.get(key) != val:
            project[key] = val
            changed = True
    title = mdx_meta.get("title")
    if title and project.get("title") != title:
        project["title"] = title
        changed = True
    return changed


def main() -> int:
    data = load_registry()
    projects = data.setdefault("projects", {})
    touched = 0
    missing = []

    for slug, project in projects.items():
        category = project.get("category", "academic")
        path = mdx_path_for(slug, category)
        if not path:
            missing.append(slug)
            continue
        mdx_meta, body = parse_mdx(path)
        if not mdx_meta.get("abstract") and body.strip():
            first = body.strip().split("\n\n", 1)[0].strip()
            if first and not first.startswith("!") and not first.startswith("#"):
                if len(first) < 800 and "\n" not in first:
                    mdx_meta["abstract"] = first
        if merge_meta(project, mdx_meta):
            touched += 1

    if data.get("version", 1) < 2:
        data["version"] = 2
        touched += 1

    save_registry(data)
    print("synced", touched, "projects from v0 MDX")
    if missing:
        print("no MDX for", len(missing), "slugs (legacy HTML only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
