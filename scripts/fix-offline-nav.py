#!/usr/bin/env python3
"""Offline nav: unified sidebar list, folder dropdowns, root-relative hrefs."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

MARKER = "id=\"offline-nav-fix\""

NAV_PATCH = """
<style id=\"offline-nav-fix\">
.main-nav.dropdown-click li.folder > a { cursor: pointer; }
#mobileNav .mobile-folder:not(.active-folder) > ul { display: none; }
#mobileNav .mobile-folder.active-folder > ul { display: block; }
#topNav #secondaryNavigation { display: none !important; }
.sidebar-position-left #topNav #mainNavigation > ul > li {
  margin: 0 0 0.45em 0;
  padding: 0;
}
</style>
<script id=\"offline-nav-fix\">
(function () {
  function bindFolders(root, selector) {
    if (!root) return;
    root.addEventListener("click", function (e) {
      var a = e.target.closest(selector);
      if (!a || a.getAttribute("href")) return;
      var li = a.parentElement;
      if (!li) return;
      e.preventDefault();
      var wasOpen = li.classList.contains("active-folder");
      var scope = li.parentElement;
      if (scope) {
        scope.querySelectorAll(".active-folder").forEach(function (el) {
          if (el !== li) el.classList.remove("active-folder");
        });
      }
      li.classList.toggle("active-folder", !wasOpen);
    });
  }
  function init() {
    bindFolders(document.getElementById("topNav"), "li.folder > a");
    bindFolders(document.getElementById("mobileNav"), ".mobile-folder > a");
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
</script>
"""

RE_NAV_PATCH = re.compile(
    r'<style id="offline-nav-fix">.*?</style>\s*<script id="offline-nav-fix">.*?</script>',
    re.DOTALL,
)

RE_NAV_BLOCK = re.compile(
    r"(<(?:nav|div)[^>]*id=\"(?:mainNavigation|secondaryNavigation|mobileNav)\"[^>]*>.*?</(?:nav|div)>)",
    re.DOTALL | re.IGNORECASE,
)

RE_HTML_HREF = re.compile(
    r"href=\"(?!https?://|/|#|mailto:)([^\"]+\.html(?:#[^\"]*)?)\"",
    re.IGNORECASE,
)

RE_MAIN_TAIL = re.compile(
    r'(<nav id="mainNavigation"[^>]*>\s*<ul>)(.*?)(</ul>\s*</nav>\s*<nav id="secondaryNavigation")',
    re.DOTALL,
)

RE_SECONDARY_ITEMS = re.compile(
    r'<nav id="secondaryNavigation"[^>]*>\s*<ul>\s*(.*?)\s*</ul>\s*</nav>',
    re.DOTALL,
)

EMPTY_SECONDARY = (
    '<nav id="secondaryNavigation" class="main-nav dropdown-click desktop-nav" '
    'aria-hidden="true" hidden></nav>'
)


def root_href(href):
    path = href.split("#", 1)[0]
    frag = ""
    if "#" in href:
        frag = "#" + href.split("#", 1)[1]
    if path.endswith(".html"):
        path = path[: -len(".html")]
    if path in ("index", "cover-page"):
        path = ""
    return "/" + path + frag if path else "/" + frag.lstrip("#")


RE_TAIL_BLOCK = re.compile(
    r'<li class="folder-collection folder">\s*<a href="/code">Code</a>.*?</li>\s*'
    r'<li class="folder-collection folder">\s*<a href="/speaking">Speaking</a>.*?</li>\s*'
    r'<li class="page-collection">\s*<a href="/about-me">About</a>.*?</li>',
    re.DOTALL,
)

RE_MAIN_NAV = re.compile(r'<nav id="mainNavigation"[^>]*>.*?</nav>', re.DOTALL)


def dedupe_main_nav_tail(html: str) -> tuple[str, bool]:
    main = RE_MAIN_NAV.search(html)
    if not main:
        return html, False
    block = main.group(0)
    matches = list(RE_TAIL_BLOCK.finditer(block))
    if len(matches) <= 1:
        return html, False
    for m in reversed(matches[1:]):
        block = block[: m.start()] + block[m.end() :]
    return html[: main.start()] + block + html[main.end() :], True


def merge_desktop_nav(html: str) -> tuple[str, bool]:
    if "secondaryNavigation" not in html:
        return html, False
    sec = RE_SECONDARY_ITEMS.search(html)
    if not sec:
        return html, False
    items = sec.group(1).strip()
    main = RE_MAIN_TAIL.search(html)
    if not main:
        return html, False
    main_block = main.group(2)
    changed = False
    if items and 'href="/code">Code</a>' not in main_block:
        merged = main.group(1) + main.group(2) + "\n" + items + "\n  \n" + main.group(3)
        html = RE_MAIN_TAIL.sub(merged, html, count=1)
        changed = True
    if items or 'hidden></nav>' not in html:
        new_html, n = RE_SECONDARY_ITEMS.subn(EMPTY_SECONDARY, html, count=1)
        if n:
            html = new_html
            changed = True
    return html, changed


def fix_mobile_folder_hrefs(html: str) -> tuple[str, bool]:
    changed = False
    for label, href in (("Code", "/code"), ("Speaking", "/speaking")):
        pat = re.compile(
            r'(<li class="mobile-folder">\s*)<a>' + re.escape(label) + r"</a>",
        )
        html, n = pat.subn(r'\1<a href="' + href + '">' + label + "</a>", html, count=1)
        changed = changed or n > 0
    return html, changed


def normalize_nav_hrefs(html):
    changed = False

    def repl_block(match):
        nonlocal changed
        block = match.group(1)

        def repl_href(m):
            nonlocal changed
            changed = True
            return 'href="{}"'.format(root_href(m.group(1)))

        return RE_HTML_HREF.sub(repl_href, block)

    if "mainNavigation" not in html and "mobileNav" not in html:
        return html, False

    return RE_NAV_BLOCK.sub(repl_block, html), changed


def inject_patch(html):
    if "mainNavigation" not in html and "mobileNav" not in html:
        return html, False
    if MARKER in html:
        new_html, n = RE_NAV_PATCH.subn(NAV_PATCH.strip(), html, count=1)
        return (new_html, n > 0) if n else (html, False)
    return html.replace("</head>", NAV_PATCH + "\n</head>", 1), True


def patch_html(html):
    html, cd = dedupe_main_nav_tail(html)
    html, c0 = merge_desktop_nav(html)
    html, c0b = fix_mobile_folder_hrefs(html)
    html, c1 = normalize_nav_hrefs(html)
    html, c2 = inject_patch(html)
    return html, cd or c0 or c0b or c1 or c2


def main():
    parser = argparse.ArgumentParser(description="Patch offline folder nav dropdowns")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    args = parser.parse_args()
    snap = Path(__file__).resolve().parents[1] / "snapshot" / args.date
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    patched = []
    for path in sorted(snap.rglob("*.html")):
        original = path.read_text(encoding="utf-8")
        updated, changed = patch_html(original)
        if changed:
            path.write_text(updated, encoding="utf-8")
            patched.append(str(path.relative_to(snap)))

    print("Patched {} HTML file(s) with offline nav fix.".format(len(patched)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
