#!/usr/bin/env python3
"""Unified Squarespace-shell project page layout for all portfolio categories."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

V1 = Path(__file__).resolve().parents[1]
SNAP = V1 / "snapshot" / "2026-06-05"
REGISTRY_PATH = V1 / "data" / "projects.json"
TEMPLATE_HTML = SNAP / "liberty-museum.html"
PAGE_MARKER = "<!-- project-page-v1"
GALLERY_NUM = re.compile(r"^(\d+)\.(jpg|jpeg|png|webp)$", re.I)

PLACEHOLDER_STYLE = """
<style id="asset-placeholder-style">
.asset-placeholder { margin: 0 0 1.5em; }
.asset-placeholder__box {
  width: 100%; aspect-ratio: 16 / 10; min-height: 160px;
  background: #d8d8d8; position: relative;
}
.asset-placeholder__box--video { aspect-ratio: 16 / 9; min-height: 200px; }
.asset-placeholder__box--embed { aspect-ratio: auto; min-height: 320px; }
.asset-placeholder__box::before,
.asset-placeholder__box::after {
  content: ""; position: absolute; top: 50%; left: 50%;
  width: 70%; height: 2px; background: #999;
  transform: translate(-50%, -50%) rotate(45deg);
}
.asset-placeholder__box::after { transform: translate(-50%, -50%) rotate(-45deg); }
.asset-placeholder__caption {
  font-size: 12px; color: #666; margin-top: 0.5em; text-align: center;
}
.asset-placeholder__caption span { display: block; font-family: monospace; font-size: 11px; }
.project-demo-video { margin: 0 0 1.5em; }
.project-demo-video h3 { font-size: 14px; text-align: center; margin: 0 0 0.5em; }
.offline-embed-video-shell video.offline-embed-video {
  width: 100%; display: block; background: #000;
}
</style>
"""

OFFLINE_EMBED_STYLE_SNIPPET = """
<style id="offline-embed-video-style">
.embed-block-wrapper .offline-embed-video-shell video.offline-embed-video {
  width: 100%; display: block; background: #000;
}
</style>
"""

ROW = (
    '<div class="row sqs-row"><div class="col sqs-col-12 span-12">'
    '<div class="sqs-block html-block sqs-block-html" data-block-type="2">'
    '<div class="sqs-block-content"><div class="sqs-html-content" data-sqsp-text-block-content>'
    "{inner}"
    "</div></div></div></div></div>"
)


def esc(x):
    return html.escape(str(x), quote=True)


def text_row(inner_html: str) -> str:
    return ROW.format(inner=inner_html)


def image_row(src: str, alt: str = "") -> str:
    cap = (
        '<figcaption class="image-caption-wrapper"><div class="image-caption"><p>'
        + esc(alt)
        + "</p></div></figcaption>"
    ) if alt else ""
    return (
        '<div class="row sqs-row"><div class="col sqs-col-12 span-12">'
        '<div class="sqs-block image-block sqs-block-image" data-block-type="5">'
        '<div class="sqs-block-content"><figure class="sqs-block-image-figure intrinsic">'
        '<img src="'
        + esc(src)
        + '" data-asset-id="'
        + esc(src)
        + '" alt="'
        + esc(alt)
        + '" loading="lazy" style="display:block;width:100%;height:auto"/>'
        + cap
        + "</figure></div></div></div></div>"
    )


def canonical_for(category: str, slug: str) -> str:
    if category in ("code", "speaking"):
        return "/{0}/{1}".format(category, slug)
    return "/{0}".format(slug)


def output_path(category: str, slug: str) -> Path:
    if category in ("code", "speaking"):
        d = SNAP / category
        d.mkdir(parents=True, exist_ok=True)
        return d / (slug + ".html")
    return SNAP / (slug + ".html")


def meta_line(category: str, meta: dict) -> str:
    parts = []
    if category == "speaking":
        parts = [meta.get("event", ""), meta.get("location", ""), meta.get("date", "")]
    elif category == "code":
        parts = [meta.get("subtitle", ""), meta.get("date", "")]
    elif category == "professional":
        parts = [
            meta.get("subtitle", ""),
            meta.get("role", ""),
            meta.get("location", ""),
            meta.get("date", ""),
        ]
    else:
        parts = [
            meta.get("subtitle", ""),
            meta.get("date", ""),
            meta.get("studio", ""),
            meta.get("partner", ""),
        ]
    return " | ".join(x for x in parts if x)


def stack_row(stack) -> str:
    if not stack:
        return ""
    if isinstance(stack, str):
        stack = [stack]
    chips = " ".join(
        '<span style="display:inline-block;margin:2px 4px;padding:2px 8px;'
        'border:1px solid #ccc;font-size:12px">'
        + esc(s)
        + "</span>"
        for s in stack
    )
    return text_row('<p class="text-align-center">' + chips + "</p>")


def normalize_cover(cover: str | None, slug: str, category: str) -> str | None:
    if not cover:
        return None
    c = cover.strip().lstrip("/")
    if c.startswith("_media/"):
        return c
    if c.startswith("projects/") or c.startswith("speaking/"):
        return "_media/" + c
    return "_media/projects/{0}/cover.jpg".format(slug)


def media_path_on_disk(rel: str) -> Path:
    """Resolve _media-relative or projects/... path to snapshot file."""
    r = str(rel).strip().lstrip("/")
    if r.startswith("_media/"):
        r = r[len("_media/") :]
    return SNAP / "_media" / r


def asset_exists(rel: str) -> bool:
    p = media_path_on_disk(rel)
    return p.is_file() and p.stat().st_size > 0


def placeholder_row(label: str, expected_path: str, box_class: str = "") -> str:
    rel = expected_path
    if rel.startswith("_media/"):
        rel = rel[len("_media/") :]
    data_attr = esc(rel)
    extra = " asset-placeholder__box--{0}".format(box_class) if box_class else ""
    inner = (
        '<figure class="asset-placeholder" data-missing-asset="'
        + data_attr
        + '" role="img" aria-label="Missing: '
        + esc(label)
        + '">'
        '<div class="asset-placeholder__box'
        + extra
        + '" aria-hidden="true"></div>'
        '<figcaption class="asset-placeholder__caption">'
        "<strong>Missing: "
        + esc(label)
        + "</strong>"
        "<span>"
        + esc(expected_path if expected_path.startswith("_media/") else "_media/" + rel)
        + "</span>"
        "</figcaption></figure>"
    )
    return (
        '<div class="row sqs-row"><div class="col sqs-col-12 span-12">'
        '<div class="sqs-block image-block sqs-block-image" data-block-type="5">'
        '<div class="sqs-block-content">'
        + inner
        + "</div></div></div></div>"
    )


def cover_row(meta: dict, slug: str, title: str) -> str:
    cover = normalize_cover(meta.get("cover"), slug, meta.get("category", "academic"))
    if not cover:
        return ""
    rel = cover[len("_media/") :] if cover.startswith("_media/") else cover
    if asset_exists(rel):
        return image_row(cover, title)
    return placeholder_row("Cover", cover)


def demo_videos_rows(meta: dict) -> str:
    demos = meta.get("demoVideos") or []
    if not demos:
        return ""
    parts = []
    for demo in demos:
        label = demo.get("label") or "Demo video"
        local = demo.get("local") or ""
        youtube_id = demo.get("youtubeId") or ""
        source = demo.get("source") or (
            "https://www.youtube.com/watch?v={0}".format(youtube_id) if youtube_id else ""
        )
        rel = local.lstrip("/")
        if not rel.startswith("projects/"):
            rel = local
        media_rel = rel if rel.startswith("projects/") else local
        src = "_media/" + media_rel.lstrip("/")
        block = '<div class="project-demo-video"><h3>' + esc(label) + "</h3>"
        if media_rel and asset_exists(media_rel):
            block += (
                '<div class="embed-block-wrapper">'
                '<div class="offline-embed-video-shell">'
                '<video class="offline-embed-video" controls playsinline preload="metadata" src="'
                + esc(src)
                + '"></video></div></div>'
            )
        else:
            block += placeholder_row(label, src, "video")
        if source:
            block += (
                '<p class="text-align-center" style="font-size:12px;margin-top:0.5em">'
                '<a href="'
                + esc(source)
                + '" target="_blank" rel="noopener">Watch on YouTube</a></p>'
            )
        block += "</div>"
        parts.append(
            '<div class="row sqs-row"><div class="col sqs-col-12 span-12">'
            '<div class="sqs-block html-block sqs-block-html" data-block-type="2">'
            '<div class="sqs-block-content"><div class="sqs-html-content">'
            + block
            + "</div></div></div></div></div>"
        )
    return "".join(parts)


def embed_row(meta: dict, title: str) -> str:
    embed = meta.get("embed")
    if not embed:
        return ""
    e = embed if str(embed).startswith("_media/") else "_media/" + str(embed).lstrip("/")
    rel = e[len("_media/") :]
    if asset_exists(rel):
        return text_row(
            '<iframe src="'
            + esc(e)
            + '" title="'
            + esc(title)
            + '" style="width:100%;min-height:640px;border:1px solid #ddd" loading="lazy"></iframe>'
        )
    return placeholder_row("Embed", e, "embed")


def slot_image_row(slug: str, slot: dict) -> str:
    role = slot.get("role", "gallery")
    file_name = slot.get("file") or ""
    label = slot.get("label") or file_name or role
    if role == "cover":
        rel_path = "projects/{0}/{1}".format(slug, file_name)
    else:
        rel_path = "projects/{0}/{1}".format(slug, file_name)
    src = "_media/" + rel_path
    if asset_exists(rel_path):
        return image_row(src, label)
    return placeholder_row(label, src)


def gallery_body_from_slots(meta: dict) -> tuple[str, int]:
    slug = meta.get("slug", "")
    slots = meta.get("mediaSlots") or []
    missing = 0
    rows = []
    gallery_slots = [s for s in slots if s.get("role") in ("gallery", "cover", "converted_gallery")]
    if gallery_slots:
        for slot in gallery_slots:
            row = slot_image_row(slug, slot)
            if "data-missing-asset" in row:
                missing += 1
            rows.append(row)
        listed = {s.get("file") for s in gallery_slots}
        for f in list_numbered_gallery_files(slug):
            if f.name not in listed:
                src = "_media/projects/{0}/{1}".format(slug, f.name)
                rows.append(image_row(src, f.stem))
    else:
        for f in list_numbered_gallery_files(slug):
            m = GALLERY_NUM.match(f.name)
            n = int(m.group(1)) if m else 0
            src = "_media/projects/{0}/{1}".format(slug, f.name)
            alt = "View {0}".format(n) if n >= 2 else f.stem
            rows.append(image_row(src, alt))
    return "".join(rows), missing


def source_downloads_row(meta: dict) -> str:
    slots = meta.get("mediaSlots") or []
    sources = [s for s in slots if str(s.get("role", "")).startswith("source_")]
    if not sources:
        return ""
    items = []
    slug = meta.get("slug", "")
    for slot in sources:
        file_name = slot.get("file") or ""
        label = slot.get("label") or file_name
        rel_path = "projects/{0}/{1}".format(slug, file_name)
        if asset_exists(rel_path):
            href = "_media/" + rel_path
            items.append(
                '<li><a href="'
                + esc(href)
                + '" download>'
                + esc(label)
                + "</a></li>"
            )
        else:
            items.append(
                "<li>"
                + placeholder_row(label, "_media/" + rel_path)
                + "</li>"
            )
    if not items:
        return ""
    return text_row("<h3>Source files</h3><ul>" + "".join(items) + "</ul>")


def marker_row(slug: str, category: str) -> str:
    return (
        '<div class="row sqs-row" style="display:none" aria-hidden="true">'
        '<div class="col sqs-col-12 span-12">'
        + PAGE_MARKER
        + " slug="
        + esc(slug)
        + " category="
        + esc(category)
        + " -->"
        "</div></div>"
    )


def render_project_inner(meta: dict, body_html: str) -> str:
    category = meta.get("category", "academic")
    slug = meta.get("slug", "")
    title = meta.get("title", slug)
    line = meta_line(category, meta)

    blocks = [marker_row(slug, category)]
    blocks.append(
        text_row(
            '<h1 class="text-align-center">'
            + esc(title)
            + "</h1>"
            + ('<p class="text-align-center">' + esc(line) + "</p>" if line else "")
        )
    )
    if category == "code":
        blocks.append(stack_row(meta.get("stack")))

    abstract = (meta.get("abstract") or "").strip()
    if abstract:
        blocks.append(
            text_row("<h3>abstract:</h3><p>" + esc(abstract) + "</p>")
        )

    blocks.append(demo_videos_rows(meta))
    blocks.append(cover_row(meta, slug, title))

    gallery_html, missing_count = gallery_body_from_slots(meta)
    if body_html and not gallery_html:
        blocks.append(body_html)
    elif gallery_html:
        blocks.append(gallery_html)
    elif body_html:
        blocks.append(body_html)

    blocks.append(source_downloads_row(meta))
    blocks.append(embed_row(meta, title))

    if missing_count:
        blocks.append(
            "<!-- project-missing-assets: {0} -->".format(missing_count)
        )
    return "".join(blocks)


def _template_parts():
    t = TEMPLATE_HTML.read_text(encoding="utf-8")
    s = t.index('<div class="main-content" data-content-field="main-content">')
    ls = t.index('<div class="sqs-layout sqs-grid-12', s)
    le = t.index(">", ls) + 1
    lc = t.index("</div>\n      </div>\n\n      \n\n      </section>", s)
    return t[:le], t[lc:]


def set_page_head(shell: str, title: str, canonical: str) -> str:
    full = "{0} &mdash; Sen Zhang".format(title)
    plain = "{0} - Sen Zhang".format(title)
    shell = re.sub(r"<title>.*?</title>", "<title>{0}</title>".format(full), shell, 1)
    reps = [
        (r'<meta property="og:title" content="[^"]*"', '<meta property="og:title" content="{0}"'.format(esc(title))),
        (r'<meta name="twitter:title" content="[^"]*"', '<meta name="twitter:title" content="{0}"'.format(esc(plain))),
        (r'<link rel="canonical" href="[^"]*"', '<link rel="canonical" href="{0}"'.format(canonical)),
        (r'<meta property="og:url" content="[^"]*"', '<meta property="og:url" content="{0}"'.format(canonical)),
        (r'<meta name="twitter:url" content="[^"]*"', '<meta name="twitter:url" content="{0}"'.format(canonical)),
        (r'<meta itemprop="name" content="[^"]*"', '<meta itemprop="name" content="{0}"'.format(esc(plain))),
        (r'<meta itemprop="url" content="[^"]*"', '<meta itemprop="url" content="{0}"'.format(canonical)),
    ]
    for a, b in reps:
        shell = re.sub(a, b, shell, 1)
    return shell


def inject_page_styles(shell: str) -> str:
    styles = PLACEHOLDER_STYLE
    if 'id="offline-embed-video-style"' not in shell:
        styles += OFFLINE_EMBED_STYLE_SNIPPET
    if 'id="asset-placeholder-style"' not in shell:
        shell = shell.replace("</head>", styles + "\n</head>", 1)
    return shell


def write_project_page(meta: dict, body_html: str) -> Path:
    slug = meta["slug"]
    category = meta.get("category", "academic")
    title = meta.get("title", slug)
    path = output_path(category, slug)
    canonical = canonical_for(category, slug)
    pre, suf = _template_parts()
    inner = render_project_inner(meta, body_html)
    html_out = set_page_head(pre, title, canonical) + inner + suf
    html_out = inject_page_styles(html_out)
    path.write_text(html_out, encoding="utf-8")
    return path


def list_numbered_gallery_files(slug: str) -> list[Path]:
    folder = SNAP / "_media" / "projects" / slug
    if not folder.is_dir():
        return []
    numbered = []
    for f in folder.iterdir():
        if not f.is_file():
            continue
        m = GALLERY_NUM.match(f.name)
        if m:
            numbered.append((int(m.group(1)), f))
    numbered.sort(key=lambda x: x[0])
    return [f for _, f in numbered]


def gallery_body_from_disk(slug: str) -> str:
    rows = []
    for f in list_numbered_gallery_files(slug):
        m = GALLERY_NUM.match(f.name)
        n = int(m.group(1)) if m else 0
        src = "_media/projects/{0}/{1}".format(slug, f.name)
        alt = "View {0}".format(n) if n >= 2 else f.stem
        rows.append(image_row(src, alt))
    return "".join(rows)


def load_project_meta(slug: str, registry: dict | None = None) -> dict:
    if registry is None:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    project = registry.get("projects", {}).get(slug)
    if not project:
        raise KeyError("unknown project slug: " + slug)
    meta = dict(project)
    meta["slug"] = slug
    return meta


def sync_project_gallery(slug: str, registry: dict | None = None) -> Path:
    """Rebuild a project page from registry mediaSlots and on-disk gallery files."""
    meta = load_project_meta(slug, registry)
    return write_project_page(meta, "")


def sync_all_project_galleries(registry: dict | None = None) -> list[str]:
    """Sync every slug that has a numbered gallery folder under _media/projects."""
    if registry is None:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    projects_root = SNAP / "_media" / "projects"
    synced = []
    if not projects_root.is_dir():
        return synced
    for folder in sorted(projects_root.iterdir()):
        if not folder.is_dir():
            continue
        slug = folder.name
        if slug not in registry.get("projects", {}):
            continue
        has_slots = bool(registry.get("projects", {}).get(slug, {}).get("mediaSlots"))
        if not list_numbered_gallery_files(slug) and not has_slots:
            continue
        sync_project_gallery(slug, registry)
        synced.append(slug)
    return synced


# --- Markdown body helpers (shared with port-v0-content) ---

IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def mdx_body_to_html(body: str, media_url) -> str:
    """media_url(relative_public_path) -> snapshot _media path or None."""
    out = []
    for chunk in re.split(r"\n\s*\n", body.strip()):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = IMG.fullmatch(chunk)
        if m:
            p = media_url(m.group(2))
            if p:
                out.append(image_row(p, m.group(1)))
            continue
        if chunk.startswith("#"):
            n = len(chunk) - len(chunk.lstrip("#"))
            tag = "h{0}".format(min(n + 1, 4))
            out.append(text_row("<{0}>{1}</{0}>".format(tag, esc(chunk.lstrip("#").strip()))))
            continue
        para = LINK.sub(r'<a href="\2">\1</a>', chunk)
        if "<a " not in para:
            para = esc(para)
        out.append(text_row("<p>{0}</p>".format(para)))
    return "".join(out)


def split_abstract(body: str) -> tuple[str, str]:
    rest = body.strip()
    if not rest or rest.lstrip().startswith("!") or rest.lstrip().startswith("#"):
        return "", rest
    ps = rest.split("\n\n", 1)
    abstract = ps[0].strip()
    tail = ps[1] if len(ps) > 1 else ""
    if len(abstract) > 800 or "\n" in abstract:
        return "", rest
    return abstract, tail
