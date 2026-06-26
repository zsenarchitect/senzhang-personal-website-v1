#!/usr/bin/env python3
"""Inject diegetic CRT/VCR skin on /code/* pages (epic #1742, child #1739)."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

MARKER = 'id="sz-diegetic-code-sector"'
HEAD_PATCH = (
    '<!-- ' + MARKER + " -->\n"
    '<script>document.documentElement.classList.add("sz-diegetic-code");</script>\n'
    '<link rel="stylesheet" href="_sz/diegetic/code-sector.css">\n'
    '<script defer src="_sz/diegetic/code-sector.js"></script>'
)
BODY_CLASS = "sz-diegetic-code"

BLOCK_RE = re.compile(
    r'<!-- ' + re.escape(MARKER) + r' -->\s*'
    r'(?:<script>document\.documentElement\.classList\.add\("sz-diegetic-code"\);</script>\s*)?'
    r'<link rel="stylesheet" href="_sz/diegetic/code-sector\.css">\s*'
    r'<script defer src="_sz/diegetic/code-sector\.js"></script>\s*',
    re.DOTALL,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def code_html_files(snap: Path) -> list[Path]:
    code_dir = snap / "code"
    if not code_dir.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(code_dir.glob("*.html")):
        if path.name.startswith("_"):
            continue
        out.append(path)
    return out


def patch_html(html: str) -> tuple[str, bool]:
    changed = False
    if BLOCK_RE.search(html):
        new_block = HEAD_PATCH + "\n"
        html2 = BLOCK_RE.sub(new_block, html, count=1)
        if html2 != html:
            html = html2
            changed = True
    elif MARKER not in html:
        html = html.replace("</head>", HEAD_PATCH + "\n</head>", 1)
        changed = True

    if ('class="' + BODY_CLASS) not in html and ("<body class=\"" + BODY_CLASS) not in html:
        html = html.replace('<body class="', '<body class="' + BODY_CLASS + " ", 1)
        changed = True

    return html, changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply diegetic CRT skin to code pages")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    args = parser.parse_args()

    snap = repo_root() / "snapshot" / args.date
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    assets = snap / "_sz" / "diegetic"
    for name in ("code-sector.css", "code-sector.js"):
        if not (assets / name).is_file():
            raise SystemExit("Missing asset: {}".format(assets / name))

    patched: list[str] = []
    for path in code_html_files(snap):
        html = path.read_text(encoding="utf-8", errors="replace")
        new_html, changed = patch_html(html)
        if changed:
            path.write_text(new_html, encoding="utf-8")
            patched.append(path.relative_to(snap).as_posix())

    print("Diegetic code sector: patched {} page(s).".format(len(patched)))
    for name in patched:
        print("  {}".format(name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
