#!/usr/bin/env python3
"""Offline nav: toggle folder dropdowns + root-relative hrefs in nav blocks."""
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

RE_NAV_BLOCK = re.compile(
    r"(<(?:nav|div)[^>]*id=\"(?:mainNavigation|secondaryNavigation|mobileNav)\"[^>]*>.*?</(?:nav|div)>)",
    re.DOTALL | re.IGNORECASE,
)

RE_HTML_HREF = re.compile(
    r"href=\"(?!https?://|/|#|mailto:)([^\"]+\.html(?:#[^\"]*)?)\"",
    re.IGNORECASE,
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


def normalize_nav_hrefs(html):
    changed = False

    def repl_block(match):
        nonlocal changed
        block = match.group(1)

        def repl_href(m):
            nonlocal changed
            changed = True
            return "href=\"{}\"".format(root_href(m.group(1)))

        return RE_HTML_HREF.sub(repl_href, block)

    if "mainNavigation" not in html and "mobileNav" not in html:
        return html, False

    return RE_NAV_BLOCK.sub(repl_block, html), changed


def inject_patch(html):
    if MARKER in html:
        return html, False
    if "mainNavigation" not in html and "mobileNav" not in html:
        return html, False
    return html.replace("</head>", NAV_PATCH + "\n</head>", 1), True


def patch_html(html):
    html2, c1 = normalize_nav_hrefs(html)
    html3, c2 = inject_patch(html2)
    return html3, c1 or c2


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
