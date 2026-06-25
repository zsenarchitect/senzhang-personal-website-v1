#!/usr/bin/env python3
"""Create /code and /speaking index pages (simple link lists)."""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

CODE = [
    ("ideafactory", "ideaFactory"),
    ("realm", "REALM"),
    ("fat2fit", "Fat2Fit"),
    ("toni", "Toni"),
    ("timebank", "TimeBank"),
    ("enneadtab-ecosystem", "EnneadTab Ecosystem"),
    ("enneadtab-revit", "EnneadTab for Revit"),
    ("enneadtab-rhino", "EnneadTab for Rhino"),
    ("enneadtabwiki", "EnneadTab Wiki"),
    ("renderpolisher", "RenderPolisher"),
    ("bimrunner", "BimRunner"),
    ("revit-games", "Revit Games"),
]

SPEAKING = [
    ("aec-hackathon-2025", "Pull Request Control for Revit"),
    ("autodesk-university-2024", "Revit As A Game Engine"),
    ("aec-hackathon-2023", "Educational Tool for Built Environment Innovation"),
    ("digital-built-week-2023", "Promoting Computational Design to Non-Programmers"),
]


def esc(x: str) -> str:
    return html.escape(x, quote=True)


def link_list(items, prefix):
    lis = "".join(
        '<li class="page-collection"><a href="/{p}/{slug}">{label}</a></li>'.format(
            p=prefix, slug=slug, label=esc(label)
        )
        for slug, label in items
    )
    return (
        '<div class="row sqs-row"><div class="col sqs-col-12 span-12">'
        '<div class="sqs-block html-block sqs-block-html" data-block-type="2">'
        '<div class="sqs-block-content"><div class="sqs-html-content">'
        "<ul>{lis}</ul></div></div></div></div></div>"
    ).format(lis=lis)


def build_page(tpl, title, filename, inner):
    s = tpl.index('<div class="main-content" data-content-field="main-content">')
    ls = tpl.index('<div class="sqs-layout sqs-grid-12', s)
    le = tpl.index(">", ls) + 1
    lc = tpl.index("</div>\n      </div>\n\n      \n\n      </section>", s)
    shell = tpl[:le] + inner + tpl[lc:]
    full = "{} &mdash; Sen Zhang".format(title)
    plain = "{} - Sen Zhang".format(title)
    shell = re.sub(r"<title>.*?</title>", "<title>{}</title>".format(full), shell, 1)
    for pat, rep in (
        (r'<meta property="og:title" content="[^"]*"', '<meta property="og:title" content="{}"'.format(esc(title))),
        (r'<meta name="twitter:title" content="[^"]*"', '<meta name="twitter:title" content="{}"'.format(esc(plain))),
        (r'<link rel="canonical" href="[^"]*"', '<link rel="canonical" href="{}"'.format(filename)),
        (r'<meta property="og:url" content="[^"]*"', '<meta property="og:url" content="{}"'.format(filename)),
        (r'<meta name="twitter:url" content="[^"]*"', '<meta name="twitter:url" content="{}"'.format(filename)),
        (r'<meta itemprop="name" content="[^"]*"', '<meta itemprop="name" content="{}"'.format(esc(plain))),
        (r'<meta itemprop="url" content="[^"]*"', '<meta itemprop="url" content="{}"'.format(filename)),
    ):
        shell = re.sub(pat, rep, shell, 1)
    return shell


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("date", nargs="?", default="2026-06-05")
    args = parser.parse_args()
    snap = Path(__file__).resolve().parents[1] / "snapshot" / args.date
    tpl = (snap / "liberty-museum.html").read_text(encoding="utf-8")
    code_dir = snap / "code"
    speak_dir = snap / "speaking"
    code_dir.mkdir(exist_ok=True)
    speak_dir.mkdir(exist_ok=True)
    code_path = code_dir / "index.html"
    speak_path = speak_dir / "index.html"
    code_path.write_text(build_page(tpl, "Code", "index.html", link_list(CODE, "code")), encoding="utf-8")
    speak_path.write_text(build_page(tpl, "Speaking", "index.html", link_list(SPEAKING, "speaking")), encoding="utf-8")
    print("Wrote", code_path, "and", speak_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
