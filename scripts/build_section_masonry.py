#!/usr/bin/env python3
"""Pinterest-style masonry grids for portfolio section index pages."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

STYLE_ID = "section-masonry"
STYLE_CHECK = '<style id="section-masonry">'

MASONRY_CSS = """
<style id="section-masonry">
.section-masonry-wrap {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 12px 48px;
}
.section-masonry {
  columns: 3;
  column-gap: 12px;
}
@media (max-width: 960px) {
  .section-masonry { columns: 2; }
}
@media (max-width: 560px) {
  .section-masonry { columns: 1; }
  .section-masonry-wrap { padding: 0 8px 40px; }
}
.section-pin {
  break-inside: avoid;
  margin-bottom: 12px;
  display: inline-block;
  width: 100%;
}
.section-pin.pin-highlight {
  column-span: all;
  display: block;
}
.section-pin.pin-highlight .section-pin-link {
  width: calc(66.666% - 4px);
  margin-left: auto;
  margin-right: auto;
}
@media (max-width: 960px) {
  .section-pin.pin-highlight .section-pin-link {
    width: 100%;
  }
}
.section-pin-link {
  display: block;
  position: relative;
  overflow: hidden;
  background: #f4f4f4;
  border-radius: 2px;
}
.section-pin-link img {
  display: block;
  width: 100%;
  height: auto;
  vertical-align: middle;
  transition: transform 0.35s ease;
}
.section-pin-link:hover img,
.section-pin-link:focus-visible img {
  transform: scale(1.03);
}
.section-pin-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  padding: 14px 16px;
  background: linear-gradient(to top, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.08) 55%, transparent 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}
.section-pin-link:hover .section-pin-overlay,
.section-pin-link:focus-visible .section-pin-overlay {
  opacity: 1;
}
.section-pin-title {
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.02em;
  line-height: 1.35;
  transform: translateY(6px);
  transition: transform 0.3s ease;
}
.section-pin-link:hover .section-pin-title,
.section-pin-link:focus-visible .section-pin-title {
  transform: translateY(0);
}
.section-pin-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}
.section-pin-meta strong {
  color: #222;
  font-weight: 500;
}
.section-pin.pin-a .section-pin-link { transform: rotate(-0.35deg); }
.section-pin.pin-b .section-pin-link { transform: rotate(0.4deg); }
.section-pin.pin-c .section-pin-link img { min-height: 220px; object-fit: cover; }
</style>
"""


@dataclass
class SectionConfig:
    key: str
    slugs: set[str]
    order: list[str]
    heading: str
    marker: str
    labels: dict[str, str] = field(default_factory=dict)
    href_for_slug: Callable[[str], str] = field(default=lambda s: "/" + s)


ACADEMIC_SLUGS = {
    "museum-of-verbs", "forumfold", "gravity-rises", "negative-memory", "bank-of-15mins-fame",
    "tokyo-antilibrary", "liberty-museum", "new-museum-in-motion", "university-island", "seed-on-mars",
    "block-field", "vertical-campus", "silence-of-the-mask", "mushroom-chair", "a-measurement-of-isolation",
    "app-ghost-hunter-1", "nyc-taxi-20", "bmx-bike", "zen-house", "post-carbon-city",
    "black-hole-horizon-1", "black-hole-horizon", "bubble-bar", "takenaka-pavillion", "hashtag-brunch",
    "walk-on-the-edge", "app-ghost-hunter",
}

ACADEMIC_ORDER = [
    "museum-of-verbs", "gravity-rises", "forumfold", "bank-of-15mins-fame", "hashtag-brunch",
    "negative-memory", "liberty-museum", "mushroom-chair", "a-measurement-of-isolation",
    "block-field", "silence-of-the-mask", "tokyo-antilibrary", "new-museum-in-motion",
    "vertical-campus", "seed-on-mars", "black-hole-horizon", "walk-on-the-edge", "zen-house",
    "university-island", "black-hole-horizon-1", "takenaka-pavillion", "nyc-taxi-20", "bmx-bike",
    "app-ghost-hunter", "app-ghost-hunter-1", "bubble-bar", "post-carbon-city",
]

ACADEMIC_LABELS = {
    "block-field": "Block Field",
    "app-ghost-hunter-1": "Beijing Untouched",
    "black-hole-horizon-1": "Ticket Booth for Nose",
    "takenaka-pavillion": "Takenaka Pavilion",
}

PRO_SLUGS = ["bilibili-hq", "bytedance-hq", "ftz-shanghai", "hudson-yards"]
CODE_SLUGS = [
    "ideafactory", "realm", "fat2fit", "toni", "timebank", "enneadtab-ecosystem",
    "renderpolisher", "bimrunner", "revit-games",
]

CODE_LABELS = {
    "enneadtab-ecosystem": "EnneadTab Ecosystem",
}
SPEAK_SLUGS = [
    "acd-austin-2026",
    "aec-hackathon-2025", "autodesk-university-2024", "aec-hackathon-2023", "digital-built-week-2023",
]

SPEAK_LABELS = {
    "acd-austin-2026": "The Design of Design",
}

SECTIONS: dict[str, SectionConfig] = {
    "academic": SectionConfig(
        key="academic",
        slugs=ACADEMIC_SLUGS,
        order=ACADEMIC_ORDER,
        heading="Academic Architecture",
        marker="<!-- academic-masonry-grid -->",
        labels=ACADEMIC_LABELS,
    ),
    "professional": SectionConfig(
        key="professional",
        slugs=set(PRO_SLUGS),
        order=PRO_SLUGS,
        heading="Professional Architecture",
        marker="<!-- professional-masonry-grid -->",
    ),
    "code": SectionConfig(
        key="code",
        slugs=set(CODE_SLUGS),
        order=CODE_SLUGS,
        heading="Code",
        marker="<!-- code-masonry-grid -->",
        labels=CODE_LABELS,
        href_for_slug=lambda s: "/code/" + s,
    ),
    "speaking": SectionConfig(
        key="speaking",
        slugs=set(SPEAK_SLUGS),
        order=SPEAK_SLUGS,
        heading="Speaking",
        marker="<!-- speaking-masonry-grid -->",
        href_for_slug=lambda s: "/speaking/" + s,
    ),
}


def esc(x):
    return html.escape(str(x), quote=True)



def slug_from_href(href):
    base = href.split("?")[0].split("#")[0]
    if "/" in base:
        base = base.rsplit("/", 1)[-1]
    return base.replace(".html", "")


def clean_title(raw):
    t = re.sub(r"<[^>]+>", " ", raw)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def default_title(config: SectionConfig, slug: str) -> str:
    return config.labels.get(slug, slug.replace("-", " ").title())


def parse_legacy_tiles(page_html: str, config: SectionConfig) -> dict[str, dict]:
    tiles = {}
    for m in re.finditer(
        r"<figure[^>]*sqs-block-image-figure.*?</figure>",
        page_html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        block = m.group(0)
        hm = re.search(r'href="([^"]+)"', block)
        im = re.search(r'<img[^>]+(?:\ssrc|data-src)="([^"]+)"', block, re.IGNORECASE)
        if not hm or not im:
            continue
        slug = slug_from_href(hm.group(1))
        if slug not in config.slugs:
            continue
        src = im.group(1)
        if src.startswith("//"):
            src = "https:" + src
        title = default_title(config, slug)
        cap_m = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", block, re.DOTALL | re.IGNORECASE)
        subtitle = ""
        if cap_m:
            strong = re.search(r"<strong[^>]*>([^<]+)", cap_m.group(1), re.IGNORECASE)
            if strong:
                title = clean_title(strong.group(1))
            subtitle = clean_title(cap_m.group(1))
            if subtitle.lower().startswith(title.lower()):
                subtitle = subtitle[len(title) :].strip(" -|")
        tiles[slug] = {
            "slug": slug,
            "href": config.href_for_slug(slug),
            "src": src,
            "title": title,
            "subtitle": subtitle,
        }
    return tiles


def parse_masonry_tiles(page_html: str, config: SectionConfig) -> dict[str, dict]:
    tiles = {}
    patterns = [
        r'<article class="section-pin[^"]*"[^>]*>.*?</article>',
        r'<article class="academic-pin[^"]*"[^>]*>.*?</article>',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, page_html, flags=re.DOTALL):
            block = m.group(0)
            hm = re.search(r'href="([^"]+)"', block)
            im = re.search(r'<img[^>]+src="([^"]+)"', block)
            if not hm or not im:
                continue
            slug = slug_from_href(hm.group(1))
            if slug not in config.slugs:
                continue
            title_m = re.search(
                r'class="(?:section-pin|academic-pin)-title"[^>]*>([^<]+)', block
            )
            meta_m = re.search(
                r'class="(?:section-pin|academic-pin)-meta"[^>]*><strong>([^<]+)</strong>', block
            )
            tiles[slug] = {
                "slug": slug,
                "href": config.href_for_slug(slug),
                "src": im.group(1),
                "title": clean_title(title_m.group(1)) if title_m else default_title(config, slug),
                "subtitle": clean_title(meta_m.group(1)) if meta_m else "",
            }
    return tiles


def pin_class(index):
    return ["", "pin-a", "pin-b", "pin-c"][index % 4]


def section_heading_html(title: str) -> str:
    return (
        '<div class="row sqs-row"><div class="col sqs-col-12 span-12">'
        '<div class="sqs-block html-block sqs-block-html" data-block-type="2">'
        '<div class="sqs-block-content"><div class="sqs-html-content" data-sqsp-text-block-content>'
        '<h1 style="text-align:center;font-size:14px;text-transform:uppercase;'
        'letter-spacing:0.14em;margin:0 0 1.25em">' + esc(title) + "</h1>"
        "</div></div></div></div></div>"
    )


def render_masonry_inner(config: SectionConfig, tiles_by_slug: dict[str, dict], order: list[str] | None = None) -> str:
    ordered = []
    slug_order = order if order is not None else config.order
    for slug in slug_order:
        if slug in tiles_by_slug:
            ordered.append(tiles_by_slug[slug])
    if not ordered:
        raise ValueError("no tiles for section {}".format(config.key))

    pins = []
    for i, t in enumerate(ordered):
        classes = [pin_class(i)]
        if t.get("highlight"):
            classes.append("pin-highlight")
        meta = ('<div class="section-pin-meta"><strong>' + esc(t["title"]) + "</strong></div>") if t["title"] else ""
        if t.get("subtitle") and t["subtitle"] != t["title"]:
            meta = (
                '<div class="section-pin-meta"><strong>' + esc(t["title"])
                + "</strong> &mdash; " + esc(t["subtitle"]) + "</div>"
            )
        pins.append(
            '<article class="section-pin ' + " ".join(c for c in classes if c) + '">'
            '<a class="section-pin-link" href="' + esc(t["href"]) + '">'
            '<img src="' + esc(t["src"]) + '" alt="' + esc(t["title"]) + '" loading="lazy" decoding="async" />'
            '<span class="section-pin-overlay"><span class="section-pin-title">' + esc(t["title"]) + "</span></span>"
            "</a>" + meta + "</article>"
        )

    return (
        config.marker
        + section_heading_html(config.heading)
        + '<div class="section-masonry-wrap"><div class="section-masonry">'
        + "".join(pins)
        + "</div></div>"
    )


def inject_masonry_style(page_html: str) -> str:
    if STYLE_CHECK in page_html:
        return page_html
    return page_html.replace("</head>", MASONRY_CSS + "\n</head>", 1)


def build_from_page_html(config: SectionConfig, page_html: str) -> str:
    if config.marker in page_html:
        tiles = parse_masonry_tiles(page_html, config)
    else:
        tiles = parse_legacy_tiles(page_html, config)
    if not tiles:
        tiles = parse_legacy_tiles(page_html, config)
    return render_masonry_inner(config, tiles)


def build_from_tile_dict(config: SectionConfig, tiles_by_slug: dict[str, dict], order: list[str] | None = None) -> str:
    return render_masonry_inner(config, tiles_by_slug, order=order)


def backup_legacy_grid(path: Path, page_html: str, marker: str) -> None:
    if marker in page_html:
        return
    backup = path.parent / "_legacy-grid.fragment.html"
    if backup.is_file():
        return
    s = page_html.find('<div class="sqs-layout sqs-grid-12')
    if s < 0:
        return
    e = page_html.find("</div>\n      </div>\n\n      \n\n      </section>", s)
    if e < 0:
        return
    backup.write_text(page_html[s:e], encoding="utf-8")
    print("saved", backup.relative_to(path.parents[2]))


def pin_count(config: SectionConfig, page_html: str) -> int:
    inner = build_from_page_html(config, page_html) if page_html else ""
    return inner.count('<article class="section-pin')
