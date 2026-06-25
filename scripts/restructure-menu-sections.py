#!/usr/bin/env python3
"""Split portfolio into section grid pages + menu hub (Academic / Pro / Code / Speaking)."""
from __future__ import annotations

import html
import re
import shutil
import sys
from pathlib import Path

from build_section_masonry import (
    SECTIONS,
    CODE_SLUGS,
    PRO_SLUGS,
    SPEAK_SLUGS,
    backup_legacy_grid,
    build_from_page_html,
    build_from_tile_dict,
    inject_masonry_style,
)
from project_registry import (
    collect_tile_pool,
    merge_registry_on_disk,
    tiles_for_section,
)

V0 = Path(r"C:\Users\szhang\github\Personal\senzhang-personal-website-v0-failed-attempt")
V1 = Path(__file__).resolve().parents[1]
SNAP = V1 / "snapshot" / "2026-06-05"
MENU = SNAP / "menu.html"
MEDIA = SNAP / "_media"

MARK_ACADEMIC = "<!-- menu-section-academic-heading -->"
MARK_PRO = "<!-- menu-section-professional -->"
MARK_CODE = "<!-- menu-section-code -->"
MARK_SPEAK = "<!-- menu-section-speaking -->"
MARK_HUB = "<!-- menu-hub-sections -->"
OLD_V0 = "<!-- v0-ported-works-grid -->"
LAYOUT_ID = 'id="page-593e0796c534a5c8d10121cb">'
VIDEO_ANCHOR = '<div class="sqs-block website-component-block sqs-block-website-component sqs-block-video video-block"'

ACADEMIC = [
    ("/museum-of-verbs", "Museum of Verbs"),
    ("/forumfold", "ForumFold"),
    ("/gravity-rises", "Gravity Rises"),
    ("/negative-memory", "Negative Memory"),
    ("/bank-of-15mins-fame", "Bank of 15mins Fame"),
    ("/tokyo-antilibrary", "Tokyo Anti-Library"),
    ("/liberty-museum", "Liberty Museum"),
    ("/new-museum-in-motion", "New Museum in Motion"),
    ("/university-island", "University Island"),
    ("/seed-on-mars", "Seed on Mars"),
    ("/zen-house-1", "Block Field"),
    ("/vertical-campus", "Vertical Campus"),
    ("/silence-of-the-mask", "Silence of the Mask"),
    ("/mushroom-chair", "Mushroom Chair"),
    ("/a-measurement-of-isolation", "A Measurement of Isolation"),
    ("/app-ghost-hunter-1", "Beijing Untouched"),
    ("/nyc-taxi-20", "NYC Taxi 2.0"),
    ("/bmx-bike", "BMX Bike"),
    ("/zen-house", "Zen House"),
    ("/post-carbon-city", "Post Carbon City"),
    ("/black-hole-horizon-1", "Ticket Booth for Nose"),
    ("/black-hole-horizon", "Black Hole Horizon"),
    ("/bubble-bar", "Bubble Bar"),
    ("/takenaka-pavillion", "Takenaka Pavilion"),
    ("/hashtag-brunch", "Hashtag Brunch"),
    ("/walk-on-the-edge", "Walk on the Edge"),
    ("/app-ghost-hunter", "APP: Ghost Hunter"),
]

PRO = [
    ("/ftz-shanghai", "FTZ Free Trade Zone"),
    ("/bilibili-hq", "Bilibili HQ"),
    ("/bytedance-hq", "ByteDance HQ"),
    ("/hudson-yards", "40 Hudson Yards"),
]
CODE = [("/code", "All Code Projects")] + [
    ("/code/" + s, l) for s, l in [
        ("ideafactory", "ideaFactory"), ("realm", "REALM"), ("fat2fit", "Fat2Fit"), ("toni", "Toni"),
        ("timebank", "TimeBank"), ("enneadtab-ecosystem", "EnneadTab Ecosystem"),
        ("enneadtab-revit", "EnneadTab for Revit"), ("enneadtab-rhino", "EnneadTab for Rhino"),
        ("enneadtabwiki", "EnneadTab Wiki"), ("renderpolisher", "RenderPolisher"),
        ("bimrunner", "BimRunner"), ("revit-games", "Revit Games"),
    ]
]
SPEAK = [("/speaking", "All Talks")] + [
    ("/speaking/" + s, l) for s, l in [
        ("aec-hackathon-2025", "Pull Request Control for Revit"),
        ("autodesk-university-2024", "Revit As A Game Engine"),
        ("aec-hackathon-2023", "Educational Tool for Built Environment Innovation"),
        ("digital-built-week-2023", "Promoting Computational Design to Non-Programmers"),
    ]
]

ACADEMIC_NAV = [("/academic", "View all")] + ACADEMIC
PRO_NAV = [("/professional", "View all")] + PRO

HUB_SECTIONS = [
    ("/academic", "Academic Architecture", "_cdn/images.squarespace-cdn.com/9f4cda6f3009dc8a28b0.jpeg"),
    ("/professional", "Professional Architecture", "_media/projects/bilibili-hq/cover.jpg"),
    ("/code", "Code", "_media/projects/enneadtab-ecosystem/cover.png"),
    ("/speaking", "Speaking", "_media/speaking/autodesk-university-2024/cover.jpg"),
]

SECTION_MARKERS = (MARK_PRO, MARK_CODE, MARK_SPEAK)


def esc(x):
    return html.escape(str(x), quote=True)


def parse_mdx(path):
    t = path.read_text(encoding="utf-8")
    e = t.index("---", 3)
    fr = t[3:e].strip()
    meta, lk = {}, None
    for line in fr.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and lk:
            meta.setdefault(lk, []).append(line.strip()[2:].strip())
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if v == "":
                lk, meta[k] = k, []
            else:
                lk, meta[k] = None, v
    return meta


def copy_cover(url):
    if not url:
        return None
    src = V0 / "public" / url.lstrip("/")
    if not src.is_file():
        print("WARN missing cover", src, file=sys.stderr)
        return None
    dst = MEDIA / url.lstrip("/")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.is_file() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
    return "_media/" + url.lstrip("/")


def pro_caption(meta):
    parts = [meta.get("subtitle", ""), meta.get("role", ""), meta.get("location", ""), meta.get("date", "")]
    return " | ".join(x for x in parts if x)


def speak_caption(meta):
    parts = [meta.get("event", ""), meta.get("location", ""), meta.get("date", "")]
    return " | ".join(x for x in parts if x)


def tile(href, cover, title, caption):
    alt = esc(title + (" " + caption if caption else ""))
    cap = ('<p class="">' + esc(caption) + "</p>") if caption else ""
    return (
        '<div class="col sqs-col-4 span-4"><div class="sqs-block image-block sqs-block-image" '
        'data-block-type="5" data-sqsp-block="image-classic"><div class="sqs-block-content">'
        '<div class="image-block-outer-wrapper layout-caption-overlay-hover design-layout-inline '
        'combination-animation-none individual-animation-none individual-text-animation-none" '
        'data-test="image-block-inline-outer-wrapper" data-sqsp-image-classic-block-layout="inline">'
        '<figure class="sqs-block-image-figure intrinsic" style="max-width:2500px;">'
        '<a class="sqs-block-image-link" href="' + esc(href) + '">'
        '<div class="image-block-wrapper" data-animation-role="image">'
        '<div class="sqs-image-shape-container-element has-aspect-ratio" style="position:relative;'
        "padding-bottom:66.67%;overflow:hidden;-webkit-mask-image:-webkit-radial-gradient(white,black);\">"
        '<img src="' + esc(cover) + '" alt="' + alt + '" loading="lazy" '
        'style="display:block;object-fit:cover;width:100%;height:100%;object-position:50% 50%"/>'
        "</div></div></a>"
        '<figcaption class="image-caption-wrapper"><div class="image-caption">'
        '<p class=""><strong>' + esc(title) + "</strong></p>" + cap + "</div></figcaption>"
        "</figure></div></div></div></div>"
    )


def hub_tile(href, title, cover):
    return (
        '<div class="col sqs-col-6 span-6"><div class="sqs-block image-block sqs-block-image" '
        'data-block-type="5"><div class="sqs-block-content">'
        '<figure class="sqs-block-image-figure intrinsic">'
        '<a class="sqs-block-image-link" href="' + esc(href) + '">'
        '<div class="image-block-wrapper"><div class="sqs-image-shape-container-element has-aspect-ratio" '
        'style="position:relative;padding-bottom:56%;overflow:hidden;">'
        '<img src="' + esc(cover) + '" alt="' + esc(title) + '" loading="lazy" '
        'style="display:block;object-fit:cover;width:100%;height:100%"/>'
        "</div></div></a>"
        '<figcaption class="image-caption-wrapper"><div class="image-caption">'
        '<p class=""><strong>' + esc(title) + "</strong></p></div></figcaption>"
        "</figure></div></div></div>"
    )


def row(tiles):
    return '<div class="row sqs-row">' + "".join(tiles) + "</div>"


def chunks(items, n):
    for i in range(0, len(items), n):
        yield items[i : i + n]


def section_heading(title, first=False):
    top = "margin:0 0 1.25em" if first else "margin:2.5em 0 1.25em;padding-top:1.5em;border-top:1px solid #ddd"
    inner = (
        '<h1 style="text-align:center;font-size:14px;text-transform:uppercase;'
        'letter-spacing:0.14em;' + top + '">' + esc(title) + "</h1>"
    )
    return (
        '<div class="row sqs-row"><div class="col sqs-col-12 span-12">'
        '<div class="sqs-block html-block sqs-block-html" data-block-type="2">'
        '<div class="sqs-block-content"><div class="sqs-html-content" data-sqsp-text-block-content>'
        + inner + "</div></div></div></div></div>"
    )


def grid_from_tiles(tiles):
    return "".join(row(chunk) for chunk in chunks(tiles, 3))


def build_pro_tile_data():
    tiles = {}
    for slug in PRO_SLUGS:
        meta = parse_mdx(V0 / "src/content/architecture" / (slug + ".mdx"))
        cover = copy_cover(meta.get("cover", ""))
        if cover:
            tiles[slug] = {
                "slug": slug,
                "href": "/" + slug,
                "src": cover,
                "title": meta.get("title", slug),
                "subtitle": pro_caption(meta),
            }
    return tiles


def build_code_tile_data():
    tiles = {}
    for slug in CODE_SLUGS:
        meta = parse_mdx(V0 / "src/content/code" / (slug + ".mdx"))
        cover = copy_cover(meta.get("cover", ""))
        if cover:
            tiles[slug] = {
                "slug": slug,
                "href": "/code/" + slug,
                "src": cover,
                "title": meta.get("title", slug),
                "subtitle": meta.get("subtitle", ""),
            }
    return tiles


def build_speak_tile_data():
    tiles = {}
    for slug in SPEAK_SLUGS:
        meta = parse_mdx(V0 / "src/content/speaking" / (slug + ".mdx"))
        cover = copy_cover(meta.get("cover", ""))
        if cover:
            tiles[slug] = {
                "slug": slug,
                "href": "/speaking/" + slug,
                "src": cover,
                "title": meta.get("title", slug),
                "subtitle": speak_caption(meta),
            }
    return tiles


def build_pro_tiles():
    out = []
    for slug in PRO_SLUGS:
        meta = parse_mdx(V0 / "src/content/architecture" / (slug + ".mdx"))
        cover = copy_cover(meta.get("cover", ""))
        if cover:
            out.append(tile("/" + slug, cover, meta.get("title", slug), pro_caption(meta)))
    return out


def build_code_tiles():
    out = []
    for slug in CODE_SLUGS:
        meta = parse_mdx(V0 / "src/content/code" / (slug + ".mdx"))
        cover = copy_cover(meta.get("cover", ""))
        if cover:
            out.append(tile("/code/" + slug, cover, meta.get("title", slug), meta.get("subtitle", "")))
    return out


def build_speak_tiles():
    out = []
    for slug in SPEAK_SLUGS:
        meta = parse_mdx(V0 / "src/content/speaking" / (slug + ".mdx"))
        cover = copy_cover(meta.get("cover", ""))
        if cover:
            out.append(tile("/speaking/" + slug, cover, meta.get("title", slug), speak_caption(meta)))
    return out


def build_menu_hub():
    tiles = [hub_tile(h, t, c) for h, t, c in HUB_SECTIONS]
    return (
        MARK_HUB
        + section_heading("Portfolio", first=True)
        + row(tiles[:2])
        + row(tiles[2:])
    )


def nav_item(href, label, indent=10):
    pad = " " * indent
    return (
        pad + '<li class="page-collection">\n'
        + pad + '  <a href="' + href + '">' + esc(label) + "</a>\n"
        + pad + "</li>\n"
    )


def nav_folder(title, items, index_href, indent=8, mobile=False):
    pad = " " * indent
    inner = "".join(nav_item(h, l, indent + 2) for h, l in items)
    cls = "mobile-folder" if mobile else "folder-collection folder"
    return (
        pad + '<li class="' + cls + '">\n'
        + pad + '  <a href="' + index_href + '">' + esc(title) + "</a>\n"
        + pad + "  <ul>\n"
        + inner
        + pad + "  </ul>\n"
        + pad + "</li>\n"
    )


def desktop_folder(title, items, index_href):
    inner = "".join(
        '                  <li class="page-collection">\n'
        '                    <a href="' + h + '">' + esc(l) + "</a>\n"
        "                  </li>\n\n                \n                \n              "
        for h, l in items
    )
    return (
        '      <li class="folder-collection folder">\n\n        \n\n          '
        '<a href="' + index_href + '">' + esc(title) + '</a>\n          <div class="subnav">\n            <ul>\n              \n                \n'
        + inner
        + "            </ul>\n          </div>\n\n        \n\n      </li>\n"
    )


def restructure_nav(text):
    mobile_academic = re.compile(
        r'<li class="mobile-folder">\s*<a(?: href="[^"]*")?>Academic Architecture</a>\s*<ul>.*?</ul>\s*</li>',
        re.DOTALL,
    )
    mobile_pro = re.compile(
        r'<li class="mobile-folder">\s*<a(?: href="[^"]*")?>Professional Architecture</a>\s*<ul>.*?</ul>\s*</li>',
        re.DOTALL,
    )
    text = mobile_academic.sub(
        nav_folder("Academic Architecture", ACADEMIC_NAV, "/academic", mobile=True), text, count=1
    )
    text = mobile_pro.sub(
        nav_folder("Professional Architecture", PRO_NAV, "/professional", mobile=True), text, count=1
    )

    desktop_academic = re.compile(
        r'<li class="folder-collection folder">\s*<a(?: href="[^"]*")?>Academic Architecture</a>\s*<div class="subnav">.*?</div>\s*</li>',
        re.DOTALL,
    )
    desktop_pro = re.compile(
        r'<li class="folder-collection folder">\s*<a(?: href="[^"]*")?>Professional Architecture</a>\s*<div class="subnav">.*?</div>\s*</li>',
        re.DOTALL,
    )
    text = desktop_academic.sub(desktop_folder("Academic Architecture", ACADEMIC_NAV, "/academic"), text, count=1)
    text = desktop_pro.sub(desktop_folder("Professional Architecture", PRO_NAV, "/professional"), text, count=1)

    mobile_works = re.compile(
        r'<li class="mobile-folder">\s*<a(?: href="/works")?>Works</a>\s*<ul>.*?</ul>\s*</li>',
        re.DOTALL,
    )
    if mobile_works.search(text):
        text = mobile_works.sub(
            nav_folder("Academic Architecture", ACADEMIC_NAV, "/academic", mobile=True)
            + nav_folder("Professional Architecture", PRO_NAV, "/professional", mobile=True),
            text,
            count=1,
        )

    desktop_works = re.compile(
        r'<li class="folder-collection folder">\s*<a>Works</a>\s*<div class="subnav">.*?</div>\s*</li>',
        re.DOTALL,
    )
    if desktop_works.search(text):
        text = desktop_works.sub(
            desktop_folder("Academic Architecture", ACADEMIC_NAV, "/academic")
            + desktop_folder("Professional Architecture", PRO_NAV, "/professional"),
            text,
            count=1,
        )

    secondary = re.compile(r'<nav id="secondaryNavigation"[^>]*>.*?</nav>', re.DOTALL)

    def secondary_nav(_):
        return (
            '<nav id="secondaryNavigation" class="main-nav dropdown-click desktop-nav">\n'
            "            <ul>\n  \n"
            + desktop_folder("Code", CODE, "/code")
            + desktop_folder("Speaking", SPEAK, "/speaking")
            + '      <li class="page-collection">\n\n        \n\n          '
            '<a href="/about-me">About</a>\n          \n\n          \n\n\n        \n\n      </li>\n\n  \n'
            "</ul>\n\n          </nav>"
        )

    text = secondary.sub(secondary_nav, text, count=1)
    return text


def remove_ported_sections(text):
    if OLD_V0 in text:
        start = text.index(OLD_V0)
        end = text.index(VIDEO_ANCHOR, start)
        text = text[:start] + text[end:]
    for marker in SECTION_MARKERS:
        while marker in text:
            start = text.index(marker)
            end = len(text)
            for other in SECTION_MARKERS:
                if other == marker:
                    continue
                pos = text.find(other, start + 1)
                if pos >= 0 and pos < end:
                    end = pos
            video_pos = text.find(VIDEO_ANCHOR, start + 1)
            if video_pos >= 0 and video_pos < end:
                end = video_pos
            text = text[:start] + text[end:]
    return text


def extract_post_carbon_chunk(text):
    key = 'href="post-carbon-city.html"'
    if key not in text:
        return ""
    idx = text.index(key)
    row_start = text.rfind('<div class="row sqs-row">', 0, idx)
    if row_start < 0:
        return ""
    video = text.find(VIDEO_ANCHOR, idx)
    if video < 0:
        return ""
    return text[row_start:video]


def extract_academic_grid(text):
    if LAYOUT_ID not in text:
        raise SystemExit("menu layout id not found")
    layout_pos = text.index(LAYOUT_ID) + len(LAYOUT_ID)
    if MARK_PRO in text:
        pro_pos = text.index(MARK_PRO)
    else:
        pro_pos = text.index(VIDEO_ANCHOR, layout_pos)
    if MARK_ACADEMIC in text:
        hm = text.index(MARK_ACADEMIC)
        after_heading = text.index("</div></div></div></div></div>", hm) + len("</div></div></div></div></div>")
        start = text.index('<div class="row sqs-row">', after_heading)
    else:
        start = text.index('<div class="row sqs-row">', layout_pos)
    grid = text[start:pro_pos]
    tail = extract_post_carbon_chunk(text)
    if tail and tail not in grid:
        grid += tail
    return grid


def replace_main_inner(shell, inner_rows):
    s = shell.index('<div class="main-content" data-content-field="main-content">')
    ls = shell.index('<div class="sqs-layout sqs-grid-12', s)
    le = shell.index(">", ls) + 1
    lc = shell.index("</div>\n      </div>\n\n      \n\n      </section>", s)
    return shell[:le] + inner_rows + shell[lc:]


def set_page_meta(shell, title, canonical):
    full = "{} &mdash; Sen Zhang".format(title)
    plain = "{} - Sen Zhang".format(title)
    shell = re.sub(r"<title>.*?</title>", "<title>{}</title>".format(full), shell, 1)
    reps = [
        (r'<meta property="og:title" content="[^"]*"', '<meta property="og:title" content="{}"'.format(esc(title))),
        (r'<meta name="twitter:title" content="[^"]*"', '<meta name="twitter:title" content="{}"'.format(esc(plain))),
        (r'<link rel="canonical" href="[^"]*"', '<link rel="canonical" href="{}"'.format(canonical)),
        (r'<meta property="og:url" content="[^"]*"', '<meta property="og:url" content="{}"'.format(canonical)),
        (r'<meta name="twitter:url" content="[^"]*"', '<meta name="twitter:url" content="{}"'.format(canonical)),
        (r'<meta itemprop="name" content="[^"]*"', '<meta itemprop="name" content="{}"'.format(esc(plain))),
        (r'<meta itemprop="url" content="[^"]*"', '<meta itemprop="url" content="{}"'.format(canonical)),
    ]
    for a, b in reps:
        shell = re.sub(a, b, shell, 1)
    return shell


def write_section_page(path, shell, title, canonical, inner_rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    page = set_page_meta(shell, title, canonical)
    page = replace_main_inner(page, inner_rows)
    path.write_text(page, encoding="utf-8")
    print("wrote", path.relative_to(V1))


def slim_menu_to_hub(text):
    if VIDEO_ANCHOR not in text:
        raise SystemExit("video block not found in menu.html")
    text = remove_ported_sections(text)
    lo = text.index(LAYOUT_ID) + len(LAYOUT_ID)
    vp = text.index(VIDEO_ANCHOR)
    hub = build_menu_hub()
    return text[:lo] + hub + text[vp:]


def read_section_inner(path):
    text = path.read_text(encoding="utf-8")
    s = text.index('<div class="sqs-layout sqs-grid-12')
    le = text.index(">", s) + 1
    lc = text.index("</div>\n      </div>\n\n      \n\n      </section>", s)
    return text[le:lc]


def write_masonry_section(path, shell, title, canonical, section_key, tile_pool, registry=None, source_html=None):
    config = SECTIONS[section_key]
    path.parent.mkdir(parents=True, exist_ok=True)
    if source_html:
        backup_legacy_grid(path, source_html, config.marker)
    filtered, order = tiles_for_section(section_key, tile_pool, registry)
    inner = build_from_tile_dict(config, filtered, order=order)
    page = set_page_meta(shell, title, canonical)
    page = replace_main_inner(page, inner)
    page = inject_masonry_style(page)
    path.write_text(page, encoding="utf-8")
    pin_n = inner.count('<article class="section-pin')
    hi_n = inner.count("pin-highlight")
    print("wrote", path.relative_to(V1), "(masonry, {} pins, {} highlights)".format(pin_n, hi_n))


def patch_all():
    if not MENU.is_file():
        raise SystemExit("missing menu.html")
    MEDIA.mkdir(parents=True, exist_ok=True)
    raw = MENU.read_text(encoding="utf-8")
    academic_path = SNAP / "academic" / "index.html"
    backup = academic_path.parent / "_legacy-grid.fragment.html"

    if academic_path.is_file():
        backup_legacy_grid(academic_path, academic_path.read_text(encoding="utf-8"), SECTIONS["academic"].marker)
        academic_source = academic_path.read_text(encoding="utf-8")
    elif backup.is_file():
        academic_source = backup.read_text(encoding="utf-8")
    elif MARK_HUB not in raw:
        academic_source = extract_academic_grid(raw)
    else:
        raise SystemExit("no academic source grid; restore academic/_legacy-grid.fragment.html")

    shell = restructure_nav(raw)
    registry = merge_registry_on_disk()
    pro_tiles = build_pro_tile_data()
    code_tiles = build_code_tile_data()
    speak_tiles = build_speak_tile_data()
    tile_pool = collect_tile_pool(academic_source, pro_tiles, code_tiles, speak_tiles)

    write_masonry_section(
        academic_path,
        shell,
        "Academic Architecture",
        "/academic",
        "academic",
        tile_pool,
        registry,
        source_html=academic_source,
    )
    write_masonry_section(
        SNAP / "professional" / "index.html",
        shell,
        "Professional Architecture",
        "/professional",
        "professional",
        tile_pool,
        registry,
        source_html=(SNAP / "professional" / "index.html").read_text(encoding="utf-8")
        if (SNAP / "professional" / "index.html").is_file()
        else None,
    )
    write_masonry_section(
        SNAP / "code" / "index.html",
        shell,
        "Code",
        "/code",
        "code",
        tile_pool,
        registry,
        source_html=(SNAP / "code" / "index.html").read_text(encoding="utf-8")
        if (SNAP / "code" / "index.html").is_file()
        else None,
    )
    write_masonry_section(
        SNAP / "speaking" / "index.html",
        shell,
        "Speaking",
        "/speaking",
        "speaking",
        tile_pool,
        registry,
        source_html=(SNAP / "speaking" / "index.html").read_text(encoding="utf-8")
        if (SNAP / "speaking" / "index.html").is_file()
        else None,
    )

    menu_out = slim_menu_to_hub(shell)
    MENU.write_text(menu_out, encoding="utf-8")
    print("wrote menu.html (hub + video)")


def main():
    patch_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
