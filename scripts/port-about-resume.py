#!/usr/bin/env python3
"""Port v0 resume.ts body into snapshot about-me.html (Squarespace shell)."""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

from build_section_masonry import SECTIONS
from project_registry import global_slug_order

V0 = Path(r"C:\Users\szhang\github\Personal\senzhang-personal-website-v0-failed-attempt")
V1 = Path(__file__).resolve().parents[1]
SNAP = V1 / "snapshot" / "2026-06-05"
ABOUT = SNAP / "about-me.html"

PROJECT_GROUPS = [
    ("firm", "Office Work - Ennead Architects"),
    ("independent", "Independent Projects - Outside Office"),
]


def esc(x):
    return html.escape(str(x), quote=True)


def nl(s):
    return esc(s).replace("\n", "<br>")


def load_resume():
    cmd = [
        "node",
        "--experimental-strip-types",
        "-e",
        (
            "import { summary, experience, projects, speaking, education, awards, "
            "credentials, confidentialityNote } from './src/data/resume.ts'; "
            "console.log(JSON.stringify({summary, experience, projects, speaking, "
            "education, awards, credentials, confidentialityNote}));"
        ),
    ]
    out = subprocess.check_output(cmd, cwd=str(V0), stderr=subprocess.DEVNULL)
    return json.loads(out.decode("utf-8"))


def html_block(inner):
    return (
        '<div class="row sqs-row"><div class="col sqs-col-12 span-12">'
        '<div class="sqs-block html-block sqs-block-html" data-block-type="2">'
        '<div class="sqs-block-content"><div class="sqs-html-content" data-sqsp-text-block-content>'
        + inner
        + "</div></div></div></div></div>"
    )


def section(title, body):
    h = (
        '<h2 style="font-size:13px;text-transform:uppercase;letter-spacing:0.12em;'
        'color:#666;margin:2.5em 0 1em 0;border-top:1px solid #eee;padding-top:1.25em">'
        + esc(title)
        + "</h2>"
    )
    return html_block(h + body)


def render_highlights(items):
    if not items:
        return ""
    parts = []
    for h in items:
        if isinstance(h, str):
            parts.append(
                '<p style="margin:0.35em 0 0.35em 1em;text-indent:-1em">'
                '<span style="color:#111">&#8226;</span> ' + nl(h) + "</p>"
            )
            continue
        parts.append(
            '<p style="margin:0.5em 0 0.35em 1em;text-indent:-1em;font-weight:600;color:#333">'
            '<span style="color:#111">&#8226;</span> ' + nl(h["role"]) + "</p>"
        )
        for s in h.get("subBullets", []):
            parts.append(
                '<p style="margin:0.2em 0 0.2em 2em;text-indent:-1em;color:#555;font-size:0.95em">'
                '<span style="color:#888">+</span> ' + nl(s) + "</p>"
            )
    return "".join(parts)


def render_experience(experience):
    chunks = []
    for exp in experience:
        head = (
            '<div style="margin-bottom:1.5em">'
            '<p style="margin:0"><strong>' + esc(exp["company"]) + "</strong>"
            '<span style="float:right;color:#666;font-size:0.9em">' + esc(exp["location"]) + "</span></p>"
        )
        for role in exp["roles"]:
            head += (
                '<p style="margin:0.15em 0;color:#444">'
                + esc(role["title"])
                + ' <span style="color:#666;font-size:0.9em">' + esc(role["period"]) + "</span></p>"
            )
        head += render_highlights(exp.get("highlights"))
        chunks.append(head + "</div>")
    return section("Experience", "".join(chunks))


def href_for_slug(slug: str, category: str) -> str:
    cfg = SECTIONS.get(category)
    if cfg:
        return cfg.href_for_slug(slug)
    return "/" + slug


def load_registry():
    path = V1 / "data" / "projects.json"
    if not path.is_file():
        return {"projects": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def render_featured_portfolio(registry):
    projects = registry.get("projects", {})
    featured = [
        p for p in projects.values()
        if p.get("includeInResume") and p.get("visible", True)
    ]
    if not featured:
        return ""
    order = global_slug_order(registry)
    featured.sort(key=lambda p: order.index(p["slug"]) if p["slug"] in order else 9999)
    body = ""
    for p in featured:
        title = p.get("title") or p["slug"].replace("-", " ").title()
        href = href_for_slug(p["slug"], p.get("category", "academic"))
        body += (
            '<p style="margin:0.35em 0">'
            '<a href="' + esc(href) + '"><strong>' + esc(title) + "</strong></a>"
            ' <span style="color:#666;font-size:0.9em">(' + esc(p.get("category", "")) + ")</span></p>"
        )
    return section("Featured Portfolio Work", body)


def render_projects(projects, note):
    body = ""
    for key, label in PROJECT_GROUPS:
        items = [p for p in projects if p.get("category") == key]
        if not items:
            continue
        body += '<p style="font-style:italic;color:#666;margin:1.5em 0 0.75em">' + esc(label) + "</p>"
        for p in items:
            body += (
                '<div style="margin-bottom:1em">'
                '<p style="margin:0"><strong>' + esc(p["name"]) + "</strong>"
                '<span style="font-weight:normal;font-style:italic;color:#666"> / '
                + esc(p["role"])
                + "</span>"
                '<span style="float:right;color:#666;font-size:0.9em">' + esc(p["period"]) + "</span></p>"
                '<p style="margin:0.35em 0 0;color:#444">' + nl(p["description"]) + "</p>"
            )
            if p.get("link"):
                body += (
                    '<p style="margin:0.2em 0 0;font-size:0.9em">'
                    '<a href="' + esc(p["link"]) + '" target="_blank" rel="noopener">' + esc(p["link"]) + "</a></p>"
                )
            body += "</div>"
    if note:
        body += (
            '<p style="margin:1.5em 0 0;padding:0.75em 1em;border-left:2px solid #ccc;'
            'background:#f8f8f8;font-style:italic;color:#555;font-size:0.95em">'
            + nl(note)
            + "</p>"
        )
    return section("Selected Projects", body)


def render_speaking(speaking):
    body = ""
    for s in speaking:
        body += (
            '<div style="margin-bottom:0.75em">'
            '<p style="margin:0"><strong>' + esc(s["venue"]) + "</strong>"
            ' <span style="color:#666">&#183;</span> <em>' + esc(s["title"]) + "</em>"
            '<span style="float:right;color:#666;font-size:0.9em">' + esc(s["year"]) + "</span></p>"
            '<p style="margin:0.15em 0 0;color:#666;font-size:0.9em">'
            + esc(s["role"]) + " - " + esc(s["location"]) + "</p></div>"
        )
    return section("Speaking & Recognition", body)


def render_credentials(credentials):
    items = "".join("<li style=\"margin:0.35em 0\">" + nl(c) + "</li>" for c in credentials)
    return section("Credentials & Technical Stack", '<ul style="margin:0;padding-left:1.25em">' + items + "</ul>")


def render_education(education):
    body = ""
    for ed in education:
        body += (
            '<div style="margin-bottom:1em">'
            '<p style="margin:0"><strong>' + esc(ed["school"]) + "</strong>"
            '<span style="float:right;color:#666;font-size:0.9em">' + esc(ed["period"]) + "</span></p>"
            '<p style="margin:0.15em 0;color:#444">' + esc(ed["degree"]) + "</p>"
            '<p style="margin:0;color:#666;font-size:0.9em">' + esc(ed["location"]) + "</p></div>"
        )
    return section("Education", body)


def render_awards(awards):
    body = ""
    for a in awards:
        line = esc(a["name"])
        if a.get("detail"):
            line += ' <span style="color:#666;font-size:0.9em">' + esc(a["detail"]) + "</span>"
        body += (
            '<p style="margin:0.35em 0">'
            + line
            + '<span style="float:right;color:#666;font-size:0.9em">' + esc(a["year"]) + "</span></p>"
        )
    return section("Awards & Recognition", body)


def render_hero(data):
    return (
        '<h1 style="white-space:pre-wrap;">Sen Zhang</h1>'
        '<p style="font-size:13px;text-transform:uppercase;letter-spacing:0.12em;color:#666;margin:0.5em 0 1em">'
        "Registered Architect &amp; Design Technology Lead</p>"
        '<p style="line-height:1.6;margin-bottom:1.25em">' + nl(data["summary"]) + "</p>"
        '<p style="margin:0.5em 0">'
        '<a href="mailto:zsenarchitect@gmail.com"><strong>zsenarchitect@gmail.com</strong></a>'
        " &middot; 518.618.6150 &middot; New York, NY</p>"
        '<p style="margin:0.5em 0">'
        '<a href="https://senzhang.me">senzhang.me</a> &middot; '
        '<a href="https://github.com/zsenarchitect" target="_blank" rel="noopener">GitHub</a> &middot; '
        '<a href="https://www.linkedin.com/in/sen-zhang-93251639/" target="_blank" rel="noopener">LinkedIn</a>'
        "</p>"
        '<p style="margin:1em 0 0">'
        '<a href="_media/Sen-Zhang-Resume.pdf" target="_blank"><strong>Download Resume (PDF)</strong></a>'
        " &middot; "
        '<a href="https://issuu.com/zsen/docs/portfolio_single_page_med" target="_blank" rel="noopener">'
        "<strong>Portfolio</strong></a></p>"
    )


def extract_headshot_col(page):
    m = re.search(
        r'(<div class="col sqs-col-4 span-4">.*?</div></div></div>)<div class="col sqs-col-8 span-8">',
        page,
        re.DOTALL,
    )
    if not m:
        raise SystemExit("headshot column not found in about-me.html")
    return m.group(1)


def patch_about(data, registry=None):
    registry = registry or load_registry()
    page = ABOUT.read_text(encoding="utf-8")
    headshot = extract_headshot_col(page)
    hero_col = (
        '<div class="col sqs-col-8 span-8"><div class="sqs-block html-block sqs-block-html" '
        'data-block-type="2" data-sqsp-block="text" id="block-e46ab55b099fe551dbfb">'
        '<div class="sqs-block-content"><div class="sqs-html-content" data-sqsp-text-block-content>'
        + render_hero(data)
        + "</div></div></div></div>"
    )
    sections = (
        render_experience(data["experience"])
        + render_projects(data["projects"], data.get("confidentialityNote"))
        + render_featured_portfolio(registry)
        + render_speaking(data["speaking"])
        + render_credentials(data["credentials"])
        + render_education(data["education"])
        + render_awards(data["awards"])
    )
    layout = (
        '<div class="sqs-layout sqs-grid-12 columns-12" data-type="page" '
        'data-updated-on="1578277037029" id="page-5894afc1414fb5fbc726f422">'
        '<div class="row sqs-row">'
        + headshot
        + hero_col
        + "</div>"
        + sections
        + "</div>"
    )
    patched = re.sub(
        r'<div class="sqs-layout sqs-grid-12 columns-12"[^>]*>.*?</div>\s*</div>\s*\n\s*</section>',
        layout + "\n      </div>\n\n      \n\n      </section>",
        page,
        count=1,
        flags=re.DOTALL,
    )
    if patched == page:
        raise SystemExit("failed to patch about-me.html layout")
    ABOUT.write_text(patched, encoding="utf-8")
    print("wrote", ABOUT.relative_to(V1))


def main():
    data = load_resume()
    patch_about(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
