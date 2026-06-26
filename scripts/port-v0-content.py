#!/usr/bin/env python3
"""Port v0 MDX project pages into snapshot HTML via unified project_page template."""
from __future__ import annotations

import html
import shutil
import subprocess
import sys
from pathlib import Path

V1 = Path(__file__).resolve().parents[1]
SNAP = V1 / "snapshot" / "2026-06-05"
MEDIA = SNAP / "_media"
V0 = Path(r"C:\Users\szhang\github\Personal\senzhang-personal-website-v0-failed-attempt")

sys.path.insert(0, str(V1 / "scripts"))
from port_v0_shared import copy_asset, mdx_path_for, parse_mdx  # noqa: E402
from project_page import mdx_body_to_html, split_abstract, write_project_page  # noqa: E402

PRO = ["bilibili-hq", "bytedance-hq", "ftz-shanghai", "hudson-yards"]
CODE = [
    "ideafactory",
    "realm",
    "fat2fit",
    "toni",
    "timebank",
    "enneadtab-ecosystem",
    "renderpolisher",
    "bimrunner",
    "revit-games",
]
SPEAK = [
    "acd-austin-2026",
    "aec-hackathon-2025",
    "autodesk-university-2024",
    "aec-hackathon-2023",
    "digital-built-week-2023",
]


def esc(x):
    return html.escape(str(x), quote=True)


def port_page(slug: str, category: str) -> None:
    path = mdx_path_for(slug, category)
    if not path:
        print("SKIP no MDX", slug, category)
        return
    mdx_meta, body = parse_mdx(path)
    abstract = (mdx_meta.get("abstract") or "").strip()
    rest = body
    if category == "professional" and not abstract:
        abstract, rest = split_abstract(body)

    if mdx_meta.get("cover"):
        copy_asset(mdx_meta["cover"])
    embed = mdx_meta.get("embed")
    if embed:
        copy_asset(embed)

    page_meta = {
        "slug": slug,
        "category": category,
        "title": mdx_meta.get("title", slug),
        "subtitle": mdx_meta.get("subtitle", ""),
        "role": mdx_meta.get("role", ""),
        "location": mdx_meta.get("location", ""),
        "date": mdx_meta.get("date", ""),
        "event": mdx_meta.get("event", ""),
        "stack": mdx_meta.get("stack", []),
        "cover": mdx_meta.get("cover"),
        "embed": embed,
        "abstract": abstract,
        "studio": mdx_meta.get("studio", ""),
        "partner": mdx_meta.get("partner", ""),
    }
    body_html = mdx_body_to_html(rest, copy_asset)
    out = write_project_page(page_meta, body_html)
    print("wrote", out.relative_to(V1))


def port_resume():
    shutil.copy2(V0 / "public/Sen Zhang Resume.pdf", MEDIA / "Sen-Zhang-Resume.pdf")
    subprocess.check_call([sys.executable, str(V1 / "scripts" / "port-about-resume.py")], cwd=str(V1))
    (V1 / "docs/resume-source.md").parent.mkdir(parents=True, exist_ok=True)
    (V1 / "docs/resume-source.md").write_text(
        "# Resume source\n\n"
        "Canonical: v0 `src/data/resume.ts` in `senzhang-personal-website-v0-failed-attempt`\n\n"
        "PDF: `snapshot/2026-06-05/_media/Sen-Zhang-Resume.pdf` "
        "(copied from v0 `public/Sen Zhang Resume.pdf`)\n\n"
        "Regenerate about-me body from resume.ts:\n\n"
        "```powershell\npy -3 scripts\\port-about-resume.py\n```\n\n"
        "`port-v0-content.py` calls this automatically when porting resume.\n",
        encoding="utf-8",
    )


def nav(href, label, ind=False):
    pad = "            " if ind else "          "
    return '%s<li class="page-collection">\n%s  <a href="%s">%s</a>\n%s</li>\n' % (
        pad,
        pad,
        href,
        esc(label),
        pad,
    )


def folder(title, items, mobile):
    if mobile:
        return (
            '        <li class="mobile-folder">\n          <a>%s</a>\n          <ul>\n%s          </ul>\n        </li>\n'
            % (esc(title), "".join(nav(h, l, True) for h, l in items))
        )
    inner = "".join(
        '                  <li class="page-collection">\n                    <a href="%s">%s</a>\n                  </li>\n\n                \n                \n              '
        % (h, esc(l))
        for h, l in items
    )
    return (
        '      <li class="folder-collection folder">\n\n        \n\n          <a>%s</a>\n          <div class="subnav">\n            <ul>\n              \n                \n%s            </ul>\n          </div>\n\n        \n\n      </li>\n'
        % (esc(title), inner)
    )


def update_menu():
    p = SNAP / "menu.html"
    t = p.read_text(encoding="utf-8")
    pro = [
        ("/ftz-shanghai", "FTZ Free Trade Zone"),
        ("/bilibili-hq", "Bilibili HQ"),
        ("/bytedance-hq", "ByteDance HQ"),
        ("/hudson-yards", "40 Hudson Yards"),
    ]
    code = [("/code", "All Code Projects")] + [
        ("/code/" + s, l)
        for s, l in [
            ("ideafactory", "ideaFactory"),
            ("realm", "REALM"),
            ("fat2fit", "Fat2Fit"),
            ("toni", "Toni"),
            ("timebank", "TimeBank"),
            ("enneadtab-ecosystem", "EnneadTab Ecosystem"),
            ("renderpolisher", "RenderPolisher"),
            ("bimrunner", "BimRunner"),
            ("revit-games", "Revit Games"),
        ]
    ]
    spk = [("/speaking", "All Talks")] + [
        ("/speaking/" + s, l)
        for s, l in [
            ("acd-austin-2026", "The Design of Design"),
            ("aec-hackathon-2025", "Pull Request Control for Revit"),
            ("autodesk-university-2024", "Revit As A Game Engine"),
            ("aec-hackathon-2023", "Educational Tool for Built Environment Innovation"),
            ("digital-built-week-2023", "Promoting Computational Design to Non-Programmers"),
        ]
    ]
    if "bilibili-hq" not in t and "/bilibili-hq" not in t:
        t = t.replace(
            '                <a href="app-ghost-hunter.html">APP: Ghost Hunter</a>',
            '                <a href="app-ghost-hunter.html">APP: Ghost Hunter</a>\n              \n\n            \n\n            </li>\n\n          \n\n'
            + "".join(nav(h, l, True) for h, l in pro)
            + '            <li class="page-collection">\n\n              \n                ',
            1,
        )
        t = t.replace(
            '                    <a href="app-ghost-hunter.html">APP: Ghost Hunter</a>\n                  </li>',
            '                    <a href="app-ghost-hunter.html">APP: Ghost Hunter</a>\n                  </li>\n                \n                \n              \n                \n'
            + "".join(
                '                  <li class="page-collection">\n                    <a href="%s">%s</a>\n                  </li>\n\n                \n                \n              '
                % (h, esc(l))
                for h, l in pro
            ),
            1,
        )
    if 'href="/code/ideafactory"' not in t and 'href="code/ideafactory.html"' not in t:
        t = t.replace(
            '              <a href="about-me.html">About</a>',
            folder("Code", code, True) + folder("Speaking", spk, True) + '              <a href="about-me.html">About</a>',
            1,
        )
        t = t.replace(
            '            <a href="about-me.html">About</a>',
            folder("Code", code, False) + folder("Speaking", spk, False) + '            <a href="about-me.html">About</a>',
            1,
        )
    p.write_text(t, encoding="utf-8")


if __name__ == "__main__":
    MEDIA.mkdir(parents=True, exist_ok=True)
    port_resume()
    for s in PRO:
        port_page(s, "professional")
    for s in CODE:
        port_page(s, "code")
    for s in SPEAK:
        port_page(s, "speaking")
    update_menu()
    subprocess.check_call(
        [sys.executable, str(V1 / "scripts" / "restructure-menu-sections.py")],
        cwd=str(V1),
    )
    print("done")
