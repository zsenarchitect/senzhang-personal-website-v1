#!/usr/bin/env python3
"""Patch snapshot HTML so Squarespace lightbox works offline and recovers from stuck overlays."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

BASE_EMPTY_RE = re.compile(r'<base href="">', re.IGNORECASE)

LIGHTBOX_STYLE = """
<style id="offline-lightbox-fix">
/* Offline archive: hide Squarespace lightbox layers; we use the fallback viewer instead. */
.yui3-lightbox2,
.yui3-lightboxoverlay,
.sqs-lightbox-overlay,
.sqs-lightbox-slideshow,
.sqs-lightbox-close {
  display: none !important;
}
.offline-fs-lightbox {
  position: fixed;
  inset: 0;
  z-index: 10000001;
  background: rgba(0, 0, 0, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
}
.offline-fs-lightbox img {
  max-width: min(100%, 1600px);
  max-height: calc(100vh - 48px);
  width: auto;
  height: auto;
  object-fit: contain;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.45);
}
.offline-fs-lightbox-close {
  position: fixed;
  top: 16px;
  right: 20px;
  border: 0;
  background: transparent;
  color: #fff;
  font-size: 36px;
  line-height: 1;
  cursor: pointer;
  padding: 8px;
  z-index: 10000002;
}
html.offline-fs-lightbox-open,
html.offline-fs-lightbox-open body {
  overflow: hidden;
}
</style>
"""

LIGHTBOX_SCRIPT = r"""
<script id="offline-lightbox-fix">
(function () {
  function normalizeImageUrl(src) {
    if (!src) {
      return "";
    }
    if (
      src.indexOf("http://") === 0 ||
      src.indexOf("https://") === 0 ||
      src.indexOf("data:") === 0
    ) {
      return src;
    }
    if (src.charAt(0) === "/") {
      return src;
    }
    return "/" + src.replace(/^\.\//, "");
  }

  function bestImageUrl(img) {
    if (!img) {
      return "";
    }
    var srcset = img.getAttribute("srcset");
    if (srcset) {
      var best = "";
      var bestW = -1;
      srcset.split(",").forEach(function (part) {
        part = part.trim();
        var bits = part.split(/\\s+/);
        if (bits.length < 2) {
          return;
        }
        var url = bits[0];
        var descriptor = bits[bits.length - 1];
        if (descriptor.slice(-1) !== "w") {
          return;
        }
        var width = parseInt(descriptor.slice(0, -1), 10);
        if (width > bestW) {
          bestW = width;
          best = url;
        }
      });
      if (best) {
        return best;
      }
    }
    return (
      img.getAttribute("data-image") ||
      img.getAttribute("data-src") ||
      img.currentSrc ||
      img.src ||
      ""
    );
  }

  function isProjectNavLink(anchor) {
    if (!anchor) {
      return false;
    }
    var href = anchor.getAttribute("href") || "";
    return /\.html$/i.test(href) && href.indexOf("#") !== 0;
  }

  function closeSquarespaceLightbox() {
    var close = document.querySelector(".sqs-lightbox-close");
    if (close) {
      close.click();
    }
  }

  function closeFallbackLightbox() {
    var el = document.getElementById("offline-fs-lightbox");
    if (el) {
      el.parentNode.removeChild(el);
    }
    document.documentElement.classList.remove("offline-fs-lightbox-open");
    document.removeEventListener("keydown", onEscape, true);
  }

  function onEscape(event) {
    if (event.key === "Escape") {
      closeFallbackLightbox();
      closeSquarespaceLightbox();
    }
  }

  function openFallbackLightbox(src, alt) {
    src = normalizeImageUrl(src);
    if (!src || src.indexOf("data:") === 0) {
      return;
    }
    closeFallbackLightbox();
    closeSquarespaceLightbox();
    document.documentElement.classList.add("offline-fs-lightbox-open");
    var overlay = document.createElement("div");
    overlay.id = "offline-fs-lightbox";
    overlay.className = "offline-fs-lightbox";
    overlay.innerHTML =
      '<button type="button" class="offline-fs-lightbox-close" aria-label="Close">&times;</button>' +
      '<img src="" alt="">';
    var img = overlay.querySelector("img");
    img.src = src;
    img.alt = alt || "";
    overlay.addEventListener("click", function (event) {
      if (
        event.target === overlay ||
        event.target.classList.contains("offline-fs-lightbox-close")
      ) {
        closeFallbackLightbox();
      }
    });
    document.body.appendChild(overlay);
    document.addEventListener("keydown", onEscape, true);
  }

  function findLightboxImage(target) {
    if (!target || !target.closest) {
      return null;
    }
    var btn = target.closest("[data-sqsp-image-classic-block-lightbox-button]");
    if (btn) {
      return btn.querySelector("img");
    }
    var slide = target.closest(
      ".sqs-gallery-block-slideshow .slide, .sqs-block-gallery .slide"
    );
    if (slide) {
      return slide.querySelector("img");
    }
    var img = target.closest("img");
    if (!img) {
      return null;
    }
    if (!img.closest(".sqs-block-image, .sqs-block-gallery")) {
      return null;
    }
    if (img.closest("[data-sqsp-image-classic-block-lightbox-button]")) {
      return img;
    }
    if (img.hasAttribute("data-sqsp-image-classic-block-image")) {
      return img;
    }
    return null;
  }

  function lightboxImageVisible() {
    var lbImg = document.querySelector(".sqs-lightbox-slideshow img");
    if (!lbImg || lbImg.naturalWidth < 1) {
      return false;
    }
    var rect = lbImg.getBoundingClientRect();
    if (rect.width < 120 || rect.height < 120) {
      return false;
    }
    if (rect.bottom <= 0 || rect.top >= window.innerHeight) {
      return false;
    }
    if (rect.right <= 0 || rect.left >= window.innerWidth) {
      return false;
    }
    var slide = lbImg.closest(".sqs-lightbox-slide");
    if (slide) {
      var slideOpacity = parseFloat(
        window.getComputedStyle(slide).opacity || "0"
      );
      if (slideOpacity < 0.5) {
        return false;
      }
    }
    return true;
  }

  function suppressSquarespaceLightbox() {
    closeSquarespaceLightbox();
    var overlays = document.querySelectorAll(".sqs-lightbox-overlay");
    overlays.forEach(function (overlay) {
      overlay.style.display = "none";
      overlay.style.opacity = "0";
    });
  }

  document.addEventListener(
    "click",
    function (event) {
      var img = findLightboxImage(event.target);
      if (!img) {
        return;
      }
      var nav = img.closest("a[href]");
      if (nav && isProjectNavLink(nav)) {
        return;
      }
      var src = bestImageUrl(img);
      if (!src) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      if (event.stopImmediatePropagation) {
        event.stopImmediatePropagation();
      }

      openFallbackLightbox(src, img.getAttribute("alt") || "");
    },
    true
  );

  setInterval(function () {
    if (document.getElementById("offline-fs-lightbox")) {
      suppressSquarespaceLightbox();
      return;
    }
    var overlay = document.querySelector(".sqs-lightbox-overlay");
    if (!overlay) {
      return;
    }
    var opacity = parseFloat(window.getComputedStyle(overlay).opacity || "0");
    if (opacity < 0.5) {
      return;
    }
    if (!lightboxImageVisible()) {
      suppressSquarespaceLightbox();
    }
  }, 500);
})();
</script>
"""

OLD_LIGHTBOX_STYLE_RE = re.compile(
    r'<style id="offline-lightbox-fix">.*?</style>\s*',
    re.DOTALL | re.IGNORECASE,
)
OLD_LIGHTBOX_SCRIPT_RE = re.compile(
    r'<script id="offline-lightbox-fix">.*?</script>\s*',
    re.DOTALL | re.IGNORECASE,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def patch_html(html: str) -> tuple[str, bool]:
    changed = False
    original = html

    if BASE_EMPTY_RE.search(html):
        html = BASE_EMPTY_RE.sub('<base href="/">', html)

    if OLD_LIGHTBOX_STYLE_RE.search(html):
        html = OLD_LIGHTBOX_STYLE_RE.sub(lambda _m: LIGHTBOX_STYLE, html, count=1)
    if OLD_LIGHTBOX_SCRIPT_RE.search(html):
        html = OLD_LIGHTBOX_SCRIPT_RE.sub(lambda _m: LIGHTBOX_SCRIPT, html, count=1)

    if 'id="offline-lightbox-fix"' not in html:
        html = html.replace("</head>", LIGHTBOX_STYLE + LIGHTBOX_SCRIPT + "\n</head>", 1)

    if html != original:
        changed = True
    return html, changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix offline Squarespace lightbox in snapshot HTML")
    parser.add_argument("date", nargs="?", default="2026-06-05")
    args = parser.parse_args()

    snap = repo_root() / "snapshot" / args.date
    if not snap.is_dir():
        raise SystemExit("Missing snapshot: {}".format(snap))

    patched: list[str] = []
    for html_path in sorted(snap.glob("*.html")):
        original = html_path.read_text(encoding="utf-8")
        updated, changed = patch_html(original)
        if changed:
            html_path.write_text(updated, encoding="utf-8")
            patched.append(html_path.name)

    print("Patched {} HTML files for offline lightbox.".format(len(patched)))
    for name in patched:
        print("  {}".format(name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
